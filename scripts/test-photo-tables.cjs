'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {_electron}=require('@playwright/test'),sharp=require('sharp');
const {openArchive}=require('../src/archive.cjs');
const hash=data=>crypto.createHash('sha256').update(data).digest('hex');
(async()=>{
  const root=path.resolve('test-documents/photo-tables-261009');
  const fixture=JSON.parse(await fs.readFile(path.join(root,'fixture.json'),'utf8'));
  const sources=[fixture.source,fixture.separateEmbedding.source];
  const originalHashes=await Promise.all(sources.map(async f=>hash(await fs.readFile(f))));
  const profile=await fs.mkdtemp(path.join(os.tmpdir(),'lite-photo-')),env={...process.env,LITE_TEST_DATA:profile,LITE_TEST_HIDDEN:'1'};delete env.ELECTRON_RUN_AS_NODE;
  const electron=await _electron.launch({executablePath:path.resolve('release/1.0.0/win-unpacked/SsenLite.exe'),env});
  const report=[];
  try{
    const page=await electron.firstWindow();await page.waitForLoadState('domcontentloaded');
    await electron.evaluate(({dialog},files)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:files});},sources);
    await page.locator('#pick-empty').click();assert.equal(await page.locator('.document-row').count(),2);
    await page.evaluate(()=>{window.photoResults=[];window.lite.onResult(r=>window.photoResults.push(r));});
    for(const preset of ['high','balanced','small']){
      const folder=path.join(root,'results',preset);await fs.mkdir(folder,{recursive:true});
      await electron.evaluate(({dialog},f)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[f]});},folder);
      await page.locator('#choose-folder').click();await page.locator(`input[name="quality"][value="${preset}"]`).check();
      await page.evaluate(()=>{window.photoResults=[];});const start=performance.now();await page.locator('#start').click();
      await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='2개 저장 완료',null,{timeout:120000});
      const results=await page.evaluate(()=>window.photoResults);assert.equal(results.length,2);
      for(let i=0;i<results.length;i++){
        const result=results[i];assert.ok(result.ok);const source=await openArchive(sources[i]),output=await openArchive(result.path);
        let unchanged=0;const images=[];
        try{
          assert.deepEqual(source.entries.map(e=>e.fileName).sort(),output.entries.map(e=>e.fileName).sort());
          const changed=new Set(result.records.filter(r=>r.changed).map(r=>r.name));
          for(const entry of source.entries){
            if(entry.fileName.endsWith('/'))continue;
            const a=await source.read(entry),b=await output.read(entry.fileName);
            if(!changed.has(entry.fileName)){assert.deepEqual(a,b);unchanged++;}
            if(entry.fileName.startsWith('BinData/')){
              const [am,bm]=await Promise.all([sharp(a).metadata(),sharp(b).metadata()]);
              assert.equal(am.format,bm.format);assert.equal(am.hasAlpha,bm.hasAlpha);assert.ok(bm.width<=am.width&&bm.height<=am.height);await sharp(b).raw().toBuffer();
              images.push({name:entry.fileName,format:bm.format,beforeBytes:a.length,afterBytes:b.length,width:bm.width,height:bm.height});
            }
          }
        }finally{source.close();output.close();}
        assert.equal(hash(await fs.readFile(sources[i])),originalHashes[i]);
        report.push({file:path.basename(sources[i]),source:sources[i],output:result.path,preset,before:result.before,after:result.after,reductionPercent:100*(result.before-result.after)/result.before,unchangedEntries:unchanged,images,records:result.records,sourceHash:originalHashes[i],status:'PASS'});
        console.log(path.basename(sources[i]),preset,result.before,'->',result.after,'PASS');
      }
      await electron.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].showInactive());
      await page.evaluate(async()=>{await document.fonts.ready;await Promise.all(document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));});
      const png=await electron.evaluate(async({BrowserWindow})=>(await BrowserWindow.getAllWindows()[0].capturePage(undefined,{stayAwake:true})).toPNG().toString('base64'));
      await fs.writeFile(path.join(root,`app-${preset}.png`),Buffer.from(png,'base64'));
      console.log(preset,'batch seconds',Math.round((performance.now()-start)/100)/10);
      await fs.writeFile(path.join(root,'structural-report.json'),JSON.stringify(report,null,2));
    }
  }finally{await electron.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
