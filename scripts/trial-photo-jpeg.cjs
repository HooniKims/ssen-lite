'use strict';
// Explicit photo-only experiment. Not a general PNG converter or a shipped preset.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {createWriteStream}=require('node:fs'),{pipeline}=require('node:stream/promises');
const sharp=require('sharp'),yazl=require('yazl');
const {openArchive,parseXml}=require('../src/archive.cjs');
const {parseManifest,resolveItem}=require('../src/manifest.cjs');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
  const root=path.resolve('test-documents/photo-tables-261009');
  const fixture=JSON.parse(await fs.readFile(path.join(root,'fixture.json'),'utf8'));
  const input=fixture.separateEmbedding.source,sourceHash=hash(await fs.readFile(input));
  const quality=95,folder=path.join(root,'photo-jpeg-trial');await fs.mkdir(folder,{recursive:true});
  const output=path.join(folder,'복합표_사진JPEG95_해상도유지.hwpx');
  const original=await openArchive(input),replacements=new Map(),records=[],rename=new Map(),cache=new Map();
  let manifest=(await original.read('Contents/content.hpf')).toString('utf8');
  const items=await parseManifest(Buffer.from(manifest));
  const allowed=new Set(fixture.photos.map(p=>p.sha256));
  try{
    for(const item of items){
      if(!/^image\//.test(item.mediaType))continue;
      const name=resolveItem(item.href,original.byName),bytes=await original.read(name),fingerprint=hash(bytes);
      assert.ok(allowed.has(fingerprint),'Only explicitly known test photographs may be converted');
      const meta=await sharp(bytes).metadata();assert.ok(['jpeg','png'].includes(meta.format));
      assert.ok((await sharp(bytes).stats()).isOpaque,'Transparency must not be discarded');
      let candidate=cache.get(fingerprint);
      if(!candidate){candidate=await sharp(bytes).keepMetadata().jpeg({quality,chromaSubsampling:'4:4:4',mozjpeg:true}).toBuffer();cache.set(fingerprint,candidate);}
      const after=await sharp(candidate).metadata();assert.equal(after.width,meta.width);assert.equal(after.height,meta.height);assert.equal(after.format,'jpeg');
      assert.ok(candidate.length<bytes.length);
      let target=name;
      if(meta.format==='png'){
        target=name.replace(/\.png$/i,'.jpg');assert.notEqual(target,name);assert.ok(!original.byName.has(target));rename.set(name,target);
        let count=0;
        manifest=manifest.replace(/<(?:[A-Za-z_][\w.-]*:)?item\b[^>]*>/g,tag=>{
          if(!tag.includes(`id="${item.id}"`))return tag;
          count++;return tag.replace(`href="${item.href}"`,`href="${item.href.replace(/\.png$/i,'.jpg')}"`).replace(/media-type="[^"]*"/,'media-type="image/jpeg"');
        });assert.equal(count,1);
      }
      replacements.set(name,candidate);records.push({original:name,result:target,before:bytes.length,after:candidate.length,from:meta.format,to:'jpeg',width:meta.width,height:meta.height,quality});
    }
    parseXml(Buffer.from(manifest),'content.hpf');
    const zip=new yazl.ZipFile(),writing=pipeline(zip.outputStream,createWriteStream(output,{flags:'wx'}));
    for(const entry of original.entries){
      const name=entry.fileName;if(name.endsWith('/')){zip.addEmptyDirectory(name);continue;}
      const data=name==='Contents/content.hpf'?Buffer.from(manifest):replacements.get(name)||await original.read(entry);
      zip.addBuffer(data,rename.get(name)||name,{compressionLevel:name==='mimetype'?0:6,mtime:entry.getLastModDate()});
    }
    zip.end();await writing;
    const result=await openArchive(output);let unchanged=0;
    try{
      assert.equal(result.entries.length,original.entries.length);
      for(const e of original.entries){
        if(e.fileName.endsWith('/'))continue;
        const b=await result.read(rename.get(e.fileName)||e.fileName);
        if(!replacements.has(e.fileName)&&e.fileName!=='Contents/content.hpf'){assert.deepEqual(b,await original.read(e));unchanged++;}
        if(replacements.has(e.fileName))await sharp(b).raw().toBuffer();
      }
      const oldItems=items,newItems=await parseManifest(await result.read('Contents/content.hpf'));
      assert.equal(newItems.length,oldItems.length);
      for(let i=0;i<newItems.length;i++){
        assert.equal(newItems[i].id,oldItems[i].id);
        if(!/^image\//.test(oldItems[i].mediaType))assert.deepEqual(newItems[i],oldItems[i]);
        assert.ok(resolveItem(newItems[i].href,result.byName));
      }
    }finally{result.close();}
    assert.equal(sourceHash,hash(await fs.readFile(input)));
    const before=(await fs.stat(input)).size,after=(await fs.stat(output)).size;
    const report={source:input,output,before,after,reductionPercent:100*(before-after)/before,belowHalf:after<before/2,preset:'photo-jpeg95',quality,resize:false,unchangedEntries:unchanged,changedXml:['Contents/content.hpf'],sourceHash,outputHash:hash(await fs.readFile(output)),records,status:'PASS'};
    assert.ok(report.belowHalf,'Target not reached');await fs.writeFile(path.join(folder,'trial-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({...report,records:records.length},null,2));
  }finally{original.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
