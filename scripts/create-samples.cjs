'use strict';
const fs=require('node:fs/promises'),path=require('node:path');
const sharp=require('sharp'),yazl=require('yazl');
const {createWriteStream}=require('node:fs');
const {pipeline}=require('node:stream/promises');
function picture(id,w,h,n){return `<hp:p id="${900+n}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="0"><hp:pic id="${800+n}" zOrder="0" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="${700+n}" reverse="0"><hp:offset x="0" y="0"/><hp:orgSz width="${w}" height="${h}"/><hp:curSz width="${w}" height="${h}"/><hp:flip horizontal="0" vertical="0"/><hp:rotationInfo angle="0" centerX="${w/2}" centerY="${h/2}" rotateimage="0"/><hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo><hc:img binaryItemIDRef="${id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/><hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="${w}" y="0"/><hc:pt2 x="${w}" y="${h}"/><hc:pt3 x="0" y="${h}"/></hp:imgRect><hp:imgClip left="0" right="${w}" top="0" bottom="${h}"/><hp:inMargin left="0" right="0" top="0" bottom="0"/><hp:imgDim dimwidth="${w}" dimheight="${h}"/><hp:effects/><hp:sz width="${w}" widthRelTo="ABSOLUTE" height="${h}" heightRelTo="ABSOLUTE" protect="0"/><hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="CENTER" vertOffset="0" horzOffset="0"/><hp:outMargin left="0" right="0" top="0" bottom="0"/></hp:pic><hp:t/></hp:run></hp:p>`;}
async function main(){
  const root=path.resolve(__dirname,'..'),base=path.join(__dirname,'sample-base');
  const photo=await sharp(path.join(root,'build/installer/desk-original.png')).resize(3600,5400).jpeg({quality:100,chromaSubsampling:'4:4:4'}).toBuffer();
  const mark=await sharp({create:{width:3200,height:500,channels:4,background:{r:0,g:117,b:74,alpha:.4}}}).png({compressionLevel:0}).toBuffer();
  await fs.mkdir(path.join(root,'assets/samples'),{recursive:true});
  const zip=new yazl.ZipFile(),writing=pipeline(zip.outputStream,createWriteStream(path.join(root,'assets/samples/쎈Lite_이미지_예제.hwpx')));
  async function walk(folder){for(const item of await fs.readdir(folder,{withFileTypes:true})){const full=path.join(folder,item.name);if(item.isDirectory()){await walk(full);continue;}const name=path.relative(base,full).replaceAll('\\','/');if(name==='mimetype')continue;let data=await fs.readFile(full);
    if(name==='Contents/section0.xml')data=Buffer.from(data.toString().replace('<hp:t/>','<hp:t>쎈Lite 체험 문서 · 이미지 용량 줄이기</hp:t>').replace('</hs:sec>',picture('photo',24000,36000,1)+picture('mark',24000,3750,2)+'</hs:sec>'));
    if(name==='Contents/content.hpf')data=Buffer.from(data.toString().replace('</opf:manifest>','<opf:item id="photo" href="BinData/photo.jpg" media-type="image/jpeg" isEmbeded="1"/><opf:item id="mark" href="BinData/mark.png" media-type="image/png" isEmbeded="1"/></opf:manifest>'));
    if(name==='Preview/PrvText.txt')data=Buffer.from('쎈Lite 이미지 용량 줄이기 체험 문서');
    zip.addBuffer(data,name);
  }}
  zip.addBuffer(Buffer.from('application/hwp+zip'),'mimetype',{compress:false});await walk(base);
  zip.addBuffer(photo,'BinData/photo.jpg',{compress:false});zip.addBuffer(mark,'BinData/mark.png',{compress:false});zip.end();await writing;
  console.log('체험 문서를 만들었습니다.');
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={picture};
