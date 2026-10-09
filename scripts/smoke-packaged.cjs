'use strict';
const {_electron}=require('@playwright/test');
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
(async()=>{
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'lite-packaged-')),env={...process.env,LITE_TEST_DATA:path.join(temp,'profile'),LITE_TEST_HIDDEN:'1'};delete env.ELECTRON_RUN_AS_NODE;
  const electron=await _electron.launch({executablePath:path.resolve(process.argv[2]||'release/win-unpacked/SsenLite.exe'),env});
  try{
    const page=await electron.firstWindow();await page.waitForLoadState('domcontentloaded');
    await page.locator('#demo').click();await page.locator('.document-row').waitFor();
    await electron.evaluate(({dialog},folder)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},temp);
    await page.locator('#choose-folder').click();await page.locator('#start').click();
    await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='1개 저장 완료',null,{timeout:60000});
    const state=await page.evaluate(()=>window.lite.updateState());assert.equal(state.mode,'zip');
    const output=(await fs.readdir(temp)).find(n=>n.endsWith('.hwpx'));assert.ok(output);
    const bytes=(await fs.stat(path.join(temp,output))).size;assert.ok(bytes<1024*1024);
    const screenshotPath=process.argv[3]||'docs/screenshots/packaged-result.png';await fs.mkdir(path.dirname(screenshotPath),{recursive:true});
    const screenshot=await electron.evaluate(async({BrowserWindow})=>(await BrowserWindow.getAllWindows()[0].capturePage(undefined,{stayHidden:true,stayAwake:true})).toPNG().toString('base64'));
    assert.ok(screenshot.length>1000);await fs.writeFile(screenshotPath,Buffer.from(screenshot,'base64'));
    console.log(JSON.stringify({packaged:true,mode:state.mode,output,bytes,nativeEngine:'OpenHWP',imageLibrary:'sharp'},null,2));
  }finally{await electron.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
