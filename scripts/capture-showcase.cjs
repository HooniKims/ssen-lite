'use strict';
// Capture real app screens from the packaged executable with the bundled example.
const {_electron}=require('@playwright/test');
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
(async()=>{
  const output=path.resolve('docs/showcase');await fs.mkdir(output,{recursive:true});
  const profile=await fs.mkdtemp(path.join(os.tmpdir(),'ssen-lite-showcase-'));
  const env={...process.env,LITE_TEST_DATA:profile,LITE_TEST_HIDDEN:'1'};delete env.ELECTRON_RUN_AS_NODE;
  const electron=await _electron.launch({executablePath:path.resolve(process.argv[2]||'release/win-unpacked/SsenLite.exe'),env});
  try{
    const page=await electron.firstWindow();await page.waitForLoadState('domcontentloaded');
    await electron.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].showInactive());
    await page.evaluate(()=>document.fonts.ready);
    async function capture(name){
      await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
      const base64=await electron.evaluate(async({BrowserWindow})=>(await BrowserWindow.getAllWindows()[0].capturePage(undefined,{stayHidden:true,stayAwake:true})).toPNG().toString('base64'));
      assert.ok(base64.length>1000);await fs.writeFile(path.join(output,name),Buffer.from(base64,'base64'));console.log(name);
    }
    await capture('01-start.png');
    await page.locator('#demo').click();await page.locator('.document-row').waitFor();
    await capture('02-quality.png');
    const exampleFolder=path.join(process.env.PUBLIC||os.tmpdir(),'Documents','쎈Lite 예제');await fs.mkdir(exampleFolder,{recursive:true});
    await electron.evaluate(({dialog},folder)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},exampleFolder);
    await page.locator('#choose-folder').click();
    await page.locator('#start').click();
    await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='1개 저장 완료',null,{timeout:60000});
    await capture('03-result.png');
    await page.getByRole('button',{name:'처리 내역'}).click();
    assert.equal(await page.locator('.image-detail').count(),2);
    await capture('04-image-details.png');
    await page.locator('#detail-dialog').getByRole('button',{name:'닫기',exact:true}).click();
    await page.getByRole('button',{name:'사용 안내',exact:true}).click();
    await capture('05-guide.png');
  }finally{await electron.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
