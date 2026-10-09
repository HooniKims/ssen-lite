'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {createWriteStream,constants}=require('node:fs');
const {pipeline}=require('node:stream/promises');
const sharp=require('sharp'),yazl=require('yazl');
const {openArchive,parseXml,LIMITS}=require('./archive.cjs');
const {parseManifest,resolveItem}=require('./manifest.cjs');
sharp.cache({memory:64,files:0,items:20});sharp.concurrency(2);
const PRESETS=Object.freeze({high:{edge:3200,quality:90},balanced:{edge:2200,quality:82},small:{edge:1400,quality:70}});
const hash=buffer=>crypto.createHash('sha256').update(buffer).digest('hex');
function checkCancel(isCanceled){if(isCanceled?.()){const e=Error('작업을 중지했습니다.');e.code='CANCELED';throw e;}}
async function optimizeImage(buffer,preset){
  const options={limitInputPixels:80*1000*1000,failOn:'warning'};
  const metadata=await sharp(buffer,options).metadata();
  if(!['jpeg','png'].includes(metadata.format))return {buffer,reason:'JPEG·PNG 외 형식은 원본 유지'};
  if(metadata.pages>1)return {buffer,reason:'여러 프레임 이미지는 원본 유지'};
  // Preserve orientation and density; the HWPX drawing/crop coordinate system is untouched.
  const image=sharp(buffer,options).keepMetadata().resize({width:preset.edge,height:preset.edge,fit:'inside',withoutEnlargement:true}).timeout({seconds:45});
  const candidate=await (metadata.format==='jpeg'?image.jpeg({quality:preset.quality,chromaSubsampling:'4:4:4',mozjpeg:true}):image.png({compressionLevel:9,palette:false})).toBuffer();
  if(candidate.length>=buffer.length)return {buffer,reason:'이미 최적화되어 원본 유지'};
  const after=await sharp(candidate,options).metadata();
  if(after.format!==metadata.format||Boolean(after.hasAlpha)!==Boolean(metadata.hasAlpha))throw Error('이미지 형식 검증에 실패했습니다.');
  return {buffer:candidate,beforeWidth:metadata.width,beforeHeight:metadata.height,width:after.width,height:after.height};
}
async function uniqueCommit(temp,folder,stem){
  for(let n=0;n<10000;n++){
    const destination=path.join(folder,`${stem}_가볍게${n?'_'+n:''}.hwpx`);
    try{await fs.link(temp,destination);return destination;}catch(e){if(e.code==='EEXIST')continue;if(['EPERM','ENOTSUP','EXDEV','EACCES'].includes(e.code)){
      try{await fs.copyFile(temp,destination,constants.COPYFILE_EXCL);return destination;}catch(copyError){if(copyError.code==='EEXIST')continue;throw copyError;}
    }throw e;}
  }throw Error('사용 가능한 결과 파일 이름이 없습니다.');
}
async function optimizeFile(input,{preset='balanced',outputFolder,nativePath,isCanceled,onProgress=()=>{}}={}){
  if(!PRESETS[preset])throw Error('올바른 품질 설정을 선택해 주세요.');
  const info=await fs.stat(input);
  if(!info.isFile()||info.size>LIMITS.file)throw Error('500MB 이하 HWPX 파일만 처리할 수 있습니다.');
  const folder=outputFolder||path.dirname(input);await fs.access(folder,constants.W_OK);
  const archive=await openArchive(input),temp=path.join(folder,`.ssenlite-${crypto.randomUUID()}.tmp`);
  let output,writing;
  const records=[],originalHashes=new Map(),imageCache=new Map();let cachedBytes=0;
  try{
    checkCancel(isCanceled);
    const mime=(await archive.read('mimetype')).toString('utf8').trim();
    if(mime!=='application/hwp+zip')throw Error('HWPX 파일 형식이 아닙니다.');
    const manifest=await archive.read('Contents/content.hpf');parseXml(manifest,'content.hpf');
    const items=await parseManifest(manifest,nativePath),imagePaths=new Set(),ids=new Map();
    for(const item of items){
      if(ids.has(item.id))throw Error('문서 파일 목록에 중복 ID가 있습니다.');
      const target=resolveItem(item.href,archive.byName);ids.set(item.id,target);
      if(/^image\//i.test(item.mediaType)){if(!target)throw Error('참조된 이미지 파일이 없습니다.');imagePaths.add(target);}
    }
    // Unlisted images are not modified; OLE payloads and embedded documents stay intact.
    const list=[archive.byName.get('mimetype'),...archive.entries.filter(e=>e.fileName!=='mimetype')];
    output=new yazl.ZipFile();
    writing=pipeline(output.outputStream,createWriteStream(temp,{flags:'wx'}));
    writing.catch(()=>{});
    for(let i=0;i<list.length;i++){
      checkCancel(isCanceled);
      const entry=list[i],name=entry.fileName;
      if(name.endsWith('/')){output.addEmptyDirectory(name);continue;}
      const original=await archive.read(entry);originalHashes.set(name,hash(original));
      if(/\.(xml|hpf)$/i.test(name)){
        const doc=parseXml(original,name);
        for(const node of Array.from(doc.getElementsByTagName('*'))){
          if(node.hasAttribute('binaryItemIDRef')){const ref=node.getAttribute('binaryItemIDRef');if(ref&&!ids.get(ref))throw Error(`이미지 참조를 찾을 수 없습니다: ${ref}`);}
        }
      }
      let data=original;
      if(imagePaths.has(name)){
        onProgress({image:records.length+1,imageTotal:imagePaths.size,name,phase:'optimizing'});
        try{
          const fingerprint=originalHashes.get(name);
          let result=imageCache.get(fingerprint);
          if(!result){
            result=await optimizeImage(original,PRESETS[preset]);
            // Some HWPX writers embed identical bytes under many image IDs.
            // Reuse the encoding, but retain every original package entry and reference.
            if(result.buffer.length<original.length&&result.buffer.length<=64*1024*1024){
              while(cachedBytes+result.buffer.length>64*1024*1024&&imageCache.size){const oldest=imageCache.keys().next().value;cachedBytes-=imageCache.get(oldest).buffer.length;imageCache.delete(oldest);}
              imageCache.set(fingerprint,result);cachedBytes+=result.buffer.length;
            }
          }
          data=result.buffer;
          records.push({name,before:original.length,after:data.length,changed:data!==original,reason:result.reason||'용량 줄임',...Object.fromEntries(Object.entries(result).filter(([k])=>!['buffer','reason'].includes(k)))});
        }catch(e){records.push({name,before:original.length,after:original.length,changed:false,reason:'이미지를 읽지 못해 원본 유지'});}
      }
      // Reuse original bytes for all content, styles, OLE, scripts, previews, and unsupported media.
      output.addBuffer(data,name,{compressionLevel:name==='mimetype'?0:6,mtime:entry.getLastModDate()});
    }
    output.end();await writing;writing=null;archive.close();
    checkCancel(isCanceled);onProgress({phase:'verifying',image:records.length,imageTotal:imagePaths.size});
    const candidate=await openArchive(temp);
    try{
      const changed=new Set(records.filter(r=>r.changed).map(r=>r.name));
      if(candidate.entries.length!==archive.entries.length)throw Error('저장 결과의 파일 수가 다릅니다.');
      for(const entry of candidate.entries){
        checkCancel(isCanceled);if(entry.fileName.endsWith('/'))continue;
        const data=await candidate.read(entry);
        if(!changed.has(entry.fileName)&&hash(data)!==originalHashes.get(entry.fileName))throw Error('문서 원본 내용 보존 검증에 실패했습니다.');
      }
    }finally{candidate.close();}
    const current=await fs.stat(input);
    if(current.size!==info.size||current.mtimeMs!==info.mtimeMs||current.ino!==info.ino)throw Error('처리 중 원본이 변경되었습니다. 문서를 닫고 다시 시도해 주세요.');
    let size=(await fs.stat(temp)).size;
    if(size>=info.size){await fs.copyFile(input,temp);size=info.size;records.forEach(r=>{if(r.changed){r.after=r.before;r.changed=false;r.reason='전체 용량 감소가 없어 원본 유지';delete r.width;delete r.height;delete r.beforeWidth;delete r.beforeHeight;}});}
    checkCancel(isCanceled);
    const saved=await uniqueCommit(temp,folder,path.basename(input,path.extname(input)));
    return {path:saved,name:path.basename(input),before:info.size,after:size,saved:info.size-size,images:records.length,changed:records.filter(r=>r.changed).length,records,preset};
  }finally{
    archive.close();
    if(writing){output.outputStream.destroy();await writing.catch(()=>{});}
    await fs.unlink(temp).catch(()=>{});
  }
}
module.exports={PRESETS,optimizeImage,optimizeFile,uniqueCommit};
