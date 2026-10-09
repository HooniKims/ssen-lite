"""Compare all 30 result pages and prove every in-cell photo is actually visible."""
from pathlib import Path
import importlib.util,json,sys
import fitz
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent.parent
CASE=ROOT/'test-documents/photo-tables-261009'
spec=importlib.util.spec_from_file_location('cmp',ROOT/'scripts/compare-corpus-rendering.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
rows=json.loads((CASE/'hancom-report.json').read_text(encoding='utf-8'))
report=[]
for row in rows:
    a,b=fitz.open(row['originalRender']['pdf']),fitz.open(row['optimizedRender']['pdf'])
    assert len(a)==len(b)==5
    pages=[]
    for num,(pa,pb) in enumerate(zip(a,b)):
        boxes_a=c.normalize([i['bbox'] for i in pa.get_image_info()]);boxes_b=c.normalize([i['bbox'] for i in pb.get_image_info()])
        ap,bp=pa.get_pixmap(alpha=False),pb.get_pixmap(alpha=False)
        aa=np.frombuffer(ap.samples,np.uint8).reshape(ap.height,ap.width,3)
        bb=np.frombuffer(bp.samples,np.uint8).reshape(bp.height,bp.width,3)
        outside=np.ones(aa.shape[:2],dtype=bool);similarities=[]
        for x0,y0,x1,y1 in boxes_a+boxes_b:
            outside[max(0,int(y0)-3):min(aa.shape[0],int(y1)+4),max(0,int(x0)-3):min(aa.shape[1],int(x1)+4)]=False
        for x0,y0,x1,y1 in boxes_a:
            x0,x1=max(0,int(x0)),min(aa.shape[1],int(x1)+1);y0,y1=max(0,int(y0)),min(aa.shape[0],int(y1)+1)
            original,result=aa[y0:y1,x0:x1],bb[y0:y1,x0:x1]
            similarities.append({'ssim':round(c.block_ssim(original,result),6),'meanAbsoluteError':round(float(np.abs(original.astype(float)-result.astype(float)).mean()),4)})
        changed=int(np.count_nonzero((np.max(np.abs(aa.astype(np.int16)-bb.astype(np.int16)),axis=2)>2)&outside))
        p={'page':num+1,'imageInstances':len(boxes_a),'expectedImageInstances':[1,3,4,4,9][num],'vectorCount':len(pa.get_drawings()),'wordsAndPositionsEqual':c.normalize(pa.get_text('words'))==c.normalize(pb.get_text('words')),'imageRectanglesEqual':boxes_a==boxes_b,'tableLinesEqual':c.drawing_info(pa)==c.drawing_info(pb),'changedPixelsOutsideImages':changed,'imageSimilarity':similarities}
        layout_ok=p['imageInstances']==p['expectedImageInstances'] and p['vectorCount']>0 and p['wordsAndPositionsEqual'] and p['imageRectanglesEqual'] and p['tableLinesEqual'] and changed==0
        quality_ok=all(s['ssim']>=.95 and s['meanAbsoluteError']<=5 for s in similarities)
        p['layoutStatus']='PASS' if layout_ok else 'FAIL'
        p['qualityStatus']='PASS' if quality_ok else 'BELOW_THRESHOLD'
        p['status']='PASS' if layout_ok and quality_ok else 'FAIL'
        pages.append(p)
        if row['preset'] in ['balanced','small'] and '개별삽입' in row['file']:
            ims=[]
            for page in [pa,pb]:
                pix=page.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False);ims.append(Image.frombytes('RGB',(pix.width,pix.height),pix.samples))
            canvas=Image.new('RGB',(ims[0].width*2+30,ims[0].height+55),'#eeeeee');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',20)
            draw.text((10,10),'원본',font=font,fill='black');draw.text((ims[0].width+25,10),('균형' if row['preset']=='balanced' else '용량 우선')+' 설정 결과',font=font,fill='black')
            suffix='' if row['preset']=='balanced' else 'small-'
            canvas.paste(ims[0],(5,50));canvas.paste(ims[1],(ims[0].width+25,50));canvas.save(CASE/'rendered'/f'comparison-{suffix}page{num+1}.png')
    item={'file':row['file'],'preset':row['preset'],'pages':pages,'layoutStatus':'PASS' if all(p['layoutStatus']=='PASS' for p in pages) else 'FAIL','qualityStatus':'PASS' if all(p['qualityStatus']=='PASS' for p in pages) else 'BELOW_THRESHOLD','status':'PASS' if all(p['status']=='PASS' for p in pages) else 'FAIL'}
    report.append(item);print(row['file'],row['preset'],item['status'],flush=True)
    a.close();b.close()
(CASE/'render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(r['status']=='PASS' for r in report),'Render comparison failure; inspect page checks.'
