'use strict';
const {test,expect,_electron}=require('@playwright/test');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
async function launch(){
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'lite-ui-')),env={...process.env,LITE_TEST_DATA:path.join(temp,'profile'),LITE_TEST_HIDDEN:'1'};delete env.ELECTRON_RUN_AS_NODE;
  const electron=await _electron.launch({args:[path.resolve(__dirname,'..')],env});const page=await electron.firstWindow();await page.waitForLoadState('domcontentloaded');return {electron,page,temp};
}
async function screenshot(electron,name){
  const encoded=await electron.evaluate(async({BrowserWindow})=>(await BrowserWindow.getAllWindows()[0].capturePage(undefined,{stayHidden:true,stayAwake:true})).toPNG().toString('base64'));
  expect(encoded.length).toBeGreaterThan(1000);await fs.mkdir('test-results',{recursive:true});await fs.writeFile(`test-results/${name}`,Buffer.from(encoded,'base64'));
}
test('desktop: demo, settings, real optimization, details and repeat save',async()=>{
  const {electron,page,temp}=await launch();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try{
    await expect(page.locator('h1').first()).toHaveText('한글 문서를 가볍게.');
    expect(await page.locator('body').evaluate(el=>getComputedStyle(el).fontFamily)).toContain('Ghanachocolate');
    await screenshot(electron,'01-empty.png');
    await page.getByRole('button',{name:'예제 불러오기'}).click();await expect(page.locator('.document-row')).toHaveCount(1);
    await electron.evaluate(({dialog},folder)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},temp);
    await page.getByRole('button',{name:'폴더 변경'}).click();await expect(page.locator('#folder-label')).toHaveText(temp);
    await screenshot(electron,'02-ready.png');
    await page.getByRole('button',{name:'가볍게 저장',exact:true}).click();await expect(page.locator('#run-status')).toHaveText('1개 저장 완료',{timeout:45000});
    await expect(page.locator('.document-size strong')).toContainText('줄었어요');
    await screenshot(electron,'03-result.png');
    await page.getByRole('button',{name:'처리 내역'}).click();await expect(page.locator('.image-detail')).toHaveCount(2);await page.locator('#detail-dialog').getByRole('button',{name:'닫기',exact:true}).click();
    await page.getByRole('button',{name:'가볍게 저장',exact:true}).click();await expect(page.locator('#run-status')).toHaveText('1개 저장 완료',{timeout:45000});
    expect((await fs.readdir(temp)).filter(n=>n.endsWith('.hwpx'))).toHaveLength(2);
    await page.getByRole('button',{name:'설정',exact:true}).click();await expect(page.locator('#update-action')).toHaveText('개발 실행');await expect(page.locator('#update-action')).toBeDisabled();await page.locator('#update-dialog').getByRole('button',{name:'닫기',exact:true}).click();
    await page.getByRole('button',{name:'사용 안내',exact:true}).click();await expect(page.locator('#guide-page')).toBeVisible();await page.getByRole('button',{name:'용량 줄이기',exact:true}).click();
    await electron.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1040,720));await screenshot(electron,'04-compact.png');
    const clipped=await page.locator('#start').evaluate(el=>{const r=el.getBoundingClientRect();return r.bottom>innerHeight||r.right>innerWidth;});expect(clipped).toBe(false);
    await page.getByRole('button',{name:'새 작업',exact:true}).click();await expect(page.locator('#empty-view')).toBeVisible();expect(errors).toEqual([]);
  }finally{await electron.close();}
});
test('batch isolates damaged document, cancellation allows retry',async()=>{
  const {electron,page,temp}=await launch();
  try{
    const bad=path.join(temp,'broken.hwpx');await fs.writeFile(bad,'invalid zip');
    await electron.evaluate(({dialog},files)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:files});},[bad,path.resolve('assets/samples/쎈Lite_이미지_예제.hwpx')]);
    await page.getByRole('button',{name:'파일 선택',exact:false}).click();await expect(page.locator('.document-row')).toHaveCount(2);
    await electron.evaluate(({dialog},folder)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},temp);
    await page.getByRole('button',{name:'폴더 변경'}).click();await page.locator('#start').click();await expect(page.locator('#run-status')).toHaveText('1개 저장 완료 · 1개 처리 실패',{timeout:45000});
    await expect(page.locator('.file-error')).toHaveCount(1);
    await page.locator('#start').click();await page.locator('#cancel').dispatchEvent('click');await expect(page.locator('#run-status')).toContainText('작업 중지',{timeout:45000});await expect(page.locator('#start')).toBeVisible();
  }finally{await electron.close();}
});
