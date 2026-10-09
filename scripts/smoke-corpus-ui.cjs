'use strict';
const {_electron}=require('@playwright/test');
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {openArchive}=require('../src/archive.cjs');
(async()=>{
  const root=path.resolve('test-documents'),cases=JSON.parse(await fs.readFile(path.join(root,'manifest.json'),'utf8'));
  await fs.mkdir(path.join(root,'app-results'),{recursive:true});
  const output=await fs.mkdtemp(path.join(root,'app-results','run-'));
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'lite-complex-ui-')),env={...process.env,LITE_TEST_DATA:temp,LITE_TEST_HIDDEN:'1'};delete env.ELECTRON_RUN_AS_NODE;
  const packaged=process.argv.includes('--packaged');
  const electron=await _electron.launch(packaged?{executablePath:path.resolve('release/win-unpacked/SsenLite.exe'),env}:{args:[path.resolve('.')],env});
  try{
    const page=await electron.firstWindow();await page.waitForLoadState('domcontentloaded');
    await electron.evaluate(({dialog},files)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:files});},cases.map(c=>path.join(root,'originals',c.file)));
    await page.locator('#pick-empty').click();assert.equal(await page.locator('.document-row').count(),6);
    await electron.evaluate(({dialog},folder)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},output);
    await page.locator('#choose-folder').click();
    const began=performance.now();await page.locator('#start').click();
    await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='6개 저장 완료',null,{timeout:120000});
    assert.equal(await page.locator('.file-error').count(),0);
    const audit=[];
    for(const fixture of cases){
      const original=await openArchive(path.join(root,'originals',fixture.file));
      const result=await openArchive(path.join(output,fixture.file.replace(/\.hwpx$/,'_가볍게.hwpx')));
      let count=0;
      try{for(const entry of original.entries){if(entry.fileName.endsWith('/')||entry.fileName.startsWith('BinData/'))continue;assert.deepEqual(await result.read(entry.fileName),await original.read(entry));count++;}}finally{original.close();result.close();}
      audit.push({file:fixture.file,unchangedEntries:count,status:'PASS'});
    }
    const screenshot=await electron.evaluate(async({BrowserWindow})=>(await BrowserWindow.getAllWindows()[0].capturePage(undefined,{stayHidden:true,stayAwake:true})).toPNG().toString('base64'));
    assert.ok(screenshot.length>1000);await fs.writeFile(path.join(root,'app-complex-results.png'),Buffer.from(screenshot,'base64'));
    const report={packaged,output,seconds:Math.round((performance.now()-began)/100)/10,documents:audit};
    await fs.writeFile(path.join(root,'app-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }finally{await electron.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
