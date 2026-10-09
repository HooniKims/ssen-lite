'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {optimizeFile}=require('../src/optimizer.cjs');
const {openArchive}=require('../src/archive.cjs');
const sharp=require('sharp');
const root=path.resolve(__dirname,'../test-documents');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
  const cases=JSON.parse(await fs.readFile(path.join(root,'manifest.json'),'utf8')),report=[];
  for(const fixture of cases){
    const input=path.join(root,'originals',fixture.file),sourceHash=hash(await fs.readFile(input));
    for(const preset of ['high','balanced','small']){
      const folder=path.join(root,'verified-results',preset);await fs.mkdir(folder,{recursive:true});
      const began=performance.now();const result=await optimizeFile(input,{preset,outputFolder:folder});
      const source=await openArchive(input),output=await openArchive(result.path);
      let unchangedEntries=0,verifiedImages=0;
      try{
        const changed=new Set(result.records.filter(r=>r.changed).map(r=>r.name));
        if(source.entries.length!==output.entries.length)throw Error('Entry count mismatch');
        for(const entry of source.entries){
          if(entry.fileName.endsWith('/'))continue;
          const a=await source.read(entry),b=await output.read(entry.fileName);
          if(!changed.has(entry.fileName)){
            if(!a.equals(b))throw Error('Unexpected mutation: '+entry.fileName);unchangedEntries++;
          }else{
            const [am,bm]=await Promise.all([sharp(a).metadata(),sharp(b).metadata()]);
            if(am.format!==bm.format||am.hasAlpha!==bm.hasAlpha||bm.width>am.width||bm.height>am.height)throw Error('Image metadata mismatch');
            await sharp(b).raw().toBuffer();verifiedImages++;
          }
        }
      }finally{source.close();output.close();}
      if(sourceHash!==hash(await fs.readFile(input)))throw Error('Source changed');
      const item={file:fixture.file,preset,source:input,output:result.path,before:result.before,after:result.after,reductionPercent:Math.round(1000*result.saved/result.before)/10,images:result.images,changed:result.changed,unchangedEntries,verifiedImages,sourceHash,seconds:Math.round((performance.now()-began)/100)/10,records:result.records,status:'PASS'};
      report.push(item);console.log(`${fixture.file} | ${preset} | ${item.reductionPercent}% | ${verifiedImages} optimized | PASS`);
      await fs.writeFile(path.join(root,'structural-report.json'),JSON.stringify(report,null,2));
    }
  }
  console.log(`Completed ${report.length} document/preset combinations.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
