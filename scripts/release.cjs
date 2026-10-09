'use strict';
// Build and publish an immutable GitHub Release from a clean, pushed commit.
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),pkg=require('../package.json');
const {owner,repo}=pkg.build.publish,version=pkg.version,tag=`v${version}`;
const dir=path.join(root,'release',version);
const run=(command,args,inherit=false)=>execFileSync(command,args,{cwd:root,encoding:'utf8',stdio:inherit?'inherit':['ignore','pipe','pipe'],windowsHide:true});
const fail=message=>{throw new Error(message);};
function main(){
  if(!/^\d+\.\d+\.\d+$/.test(version))fail('정식 릴리즈에는 숫자 세 자리 버전을 사용하세요.');
  if(run('git',['status','--porcelain']).trim())fail('변경 사항을 먼저 커밋하세요.');
  run('git',['fetch','origin','--tags']);
  const head=run('git',['rev-parse','HEAD']).trim(),branch=run('git',['branch','--show-current']).trim();
  if(head!==run('git',['rev-parse',`origin/${branch}`]).trim())fail('현재 커밋을 origin에 먼저 push하세요.');
  if(run('git',['tag','--list',tag]).trim())fail('이미 배포한 버전입니다. 버전을 올려 주세요.');
  const notes=fs.readFileSync(path.join(root,'CHANGELOG.md'),'utf8').replace(/\r\n/g,'\n');
  const section=notes.split(`## ${version}\n`)[1]?.split(/\n## /)[0]?.trim();
  if(!section)fail('CHANGELOG.md에 이번 버전의 변경 내용을 적어 주세요.');
  run(process.execPath,['scripts/build-native.cjs'],true);
  run(process.execPath,['--test',...fs.readdirSync(path.join(root,'tests')).filter(n=>n.endsWith('.test.cjs')).map(n=>`tests/${n}`)],true);
  run(process.execPath,[require.resolve('@playwright/test/cli'),'test'],true);
  run(process.execPath,[require.resolve('electron-builder/cli'),'--win','nsis','zip','--x64','--publish','never',`--config.directories.output=${dir}`],true);
  run(process.execPath,['scripts/package-showcase.cjs',dir,version],true);
  const names=[`SsenLite-Setup-${version}.exe`,`SsenLite-Setup-${version}.exe.blockmap`,`SsenLite-${version}-x64.zip`,'latest.yml',`SsenLite-Screenshots-${version}.zip`];
  const paths=names.map(n=>path.join(dir,n));
  paths.forEach(file=>{if(!fs.existsSync(file))fail(`배포 파일 누락: ${file}`);});
  const metadata=fs.readFileSync(path.join(dir,'latest.yml'),'utf8'),installer=fs.readFileSync(paths[0]);
  if(!metadata.includes(`version: ${version}`))fail('업데이트 메타데이터 버전이 다릅니다.');
  if(!metadata.includes(`sha512: ${crypto.createHash('sha512').update(installer).digest('base64')}`)||!metadata.includes(`size: ${installer.length}`))fail('업데이트 설치 파일의 해시 또는 크기가 다릅니다.');
  run(process.execPath,['scripts/smoke-packaged.cjs',path.join(dir,'win-unpacked/SsenLite.exe'),path.join(dir,'packaged-result.png')],true);
  fs.writeFileSync(path.join(dir,'SHA256SUMS.txt'),names.map(n=>`${crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,n))).digest('hex')}  ${n}`).join('\n')+'\n');
  const notesPath=path.join(dir,'release-notes.md');
  fs.writeFileSync(notesPath,`**HWPX 문서 안의 큰 이미지를 한 번에 줄여 새 문서로 저장합니다.**\n\nAI와 로그인 없이 내 PC에서 처리하며 원본은 덮어쓰지 않습니다. JPEG·PNG를 최적화하고 글·표·서식 데이터는 그대로 보존합니다.\n\n### 예제로 보는 쎈Lite\n\n문서를 추가하고 품질 기준이나 목표 용량을 선택한 뒤 **가볍게 저장**을 누릅니다. 아래는 앱에 포함된 예제 문서를 실제 처리한 결과입니다. 이 예제는 15.2MB → 231KB로 줄었으며 실제 감소율은 문서에 따라 다릅니다.\n\n![쎈Lite 실제 처리 화면](https://raw.githubusercontent.com/${owner}/${repo}/${tag}/docs/showcase/03-result.png)\n\n**처리 내역**에서 이미지별 용량·해상도 변화와 처리 사유를 확인할 수 있습니다.\n\n![이미지별 처리 내역](https://raw.githubusercontent.com/${owner}/${repo}/${tag}/docs/showcase/04-image-details.png)\n\n[스크린샷 7장으로 전체 흐름 보기](https://github.com/${owner}/${repo}#예제로-살펴보기)\n\n### 목표 용량\n\n바·감소율(%)·MB 입력이 함께 바뀌며 문서별 목표 달성 여부를 표시합니다. 불투명 PNG의 JPEG 변환을 선택할 수 있습니다.\n\n![목표 용량 설정](https://raw.githubusercontent.com/${owner}/${repo}/${tag}/docs/showcase/06-target.png)\n\n### 이번 버전\n\n${section}\n\n### 다운로드\n\n- 설치형: **SsenLite-Setup-${version}.exe**\n- 압축 배포본: **SsenLite-${version}-x64.zip** — 전체 압축 해제 후 SsenLite.exe 실행\n- 소개용 스크린샷 7장: **SsenLite-Screenshots-${version}.zip**\n\nWindows 10/11 x64용입니다. 설치형은 앱에서 업데이트를 받고, ZIP 배포본은 새 ZIP을 내려받아 교체합니다. SHA256SUMS.txt는 파일 검증용이며 latest.yml과 blockmap은 업데이트에 사용합니다.\n\n복합 양식 6종·18조합 구조 검사, 균형 설정 22페이지의 실제 한글 렌더 비교를 통과했습니다. [검증 범위와 결과](https://github.com/${owner}/${repo}/blob/${tag}/docs/TESTING.md)\n`);
  run('gh',['release','create',tag,...paths,path.join(dir,'SHA256SUMS.txt'),'--repo',`${owner}/${repo}`,'--target',head,'--title',`쎈Lite ${version}`,'--notes-file',notesPath,...(process.argv.includes('--draft')?['--draft']:[])],true);
}
try{main();}catch(error){console.error(`릴리즈 중단: ${error.message}`);process.exitCode=1;}
