'use strict';
const fs=require('node:fs'),path=require('node:path');
const {pipeline}=require('node:stream/promises');
const {ZipFile}=require('yazl');
(async()=>{
  const target=path.resolve(process.argv[2]),version=process.argv[3];
  if(!/^\d+\.\d+\.\d+$/.test(version))throw Error('Invalid version');
  const zip=new ZipFile();
  const names=['01-start.png','02-quality.png','03-result.png','04-image-details.png','05-guide.png','README.md'];
  for(const name of names)zip.addFile(path.resolve('docs/showcase',name),name);
  const output=path.join(target,`SsenLite-Screenshots-${version}.zip`);
  const done=pipeline(zip.outputStream,fs.createWriteStream(output));zip.end();await done;console.log(output);
})().catch(error=>{console.error(error);process.exitCode=1;});
