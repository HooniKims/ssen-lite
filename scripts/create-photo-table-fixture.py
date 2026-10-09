"""Build a complex photo-in-table fixture from three original generated PNGs.
No upscaling or padding: actual native image sizes are recorded in the manifest.
"""
from pathlib import Path
import importlib.util
import json
import sys
import zipfile
import hashlib
from PIL import Image
from lxml import etree as E

ROOT = Path(__file__).resolve().parent.parent
CASE = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'test-documents/photo-tables-261009'
spec = importlib.util.spec_from_file_location('corpus', ROOT/'scripts/create-complex-corpus.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
c.OUT = CASE/'originals'; c.OUT.mkdir(parents=True,exist_ok=True)
media, sources = {}, []
for key in ['forest','architecture','interior']:
    file = CASE/'photos'/f'{key}.png'
    im = Image.open(file); im.load()
    jpeg = file.with_suffix('.jpg')
    im.convert('RGB').save(jpeg,'JPEG',quality=98,subsampling=0,dpi=(300,300))
    for f, mime in [(file,'image/png'),(jpeg,'image/jpeg')]:
        identifier = key+'_'+f.suffix[1:]
        data = f.read_bytes(); media[identifier]=(f.name,mime,data)
        sources.append({'id':identifier,'file':str(f),'width':im.width,'height':im.height,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'origin':'native generated PNG' if f==file else 'JPEG quality 98, no resize'})

def pic(key,width=19000,**kwargs):
    item = next(s for s in sources if s['id']==key)
    return c.picture(key,width,round(width*item['height']/item['width']),**kwargs)

def section(title):
    sec=c.section(title);c.header_footer(sec)
    for tag,text in [('header','쎈Lite | 고해상도 사진 · 복합 표 검증'),('footer','테스트용 생성 사진 · 개인정보 없음 · 2026. 10. 09.')]:
        sec.find('.//{'+c.HP+'}'+tag+'//{'+c.HP+'}t').text=text
    return sec

sections=[]
s=section('01. 고해상도 사진이 들어간 복합 표')
s.append(c.para('사진의 용량·해상도 변화와 표 안의 배치·형식 보존을 확인합니다.'))
s.append(c.table(3,3,{0:[(0,1,3,'고화질 사진 최적화 검증 기록')],1:[(0,2,1,'검증 대상'),(1,1,1,'JPEG / PNG'),(2,1,1,'3단계 품질')],2:[(1,1,2,'일반 셀 · 병합 셀 · 표 안의 표')]},row_height=2800))
s.append(c.para('사진 A / 숲과 계곡 - 가로 병합 셀에 삽입한 PNG 원본'))
s.append(c.table(1,2,{0:[(0,1,2,[pic('forest_png',40000)])]},row_height=31000))
s.append(c.para('사진의 나뭇잎·돌·물결과 표 바깥선이 모두 보여야 합니다.'))
sections.append(s)

s=section('02. 좌우 셀과 병합 셀의 사진')
s.append(c.para('서로 다른 사진 2개와 전체 폭의 사진을 한 표에 함께 배치했습니다.'))
t=c.table(2,2,{0:[(0,1,1,[c.para('사진 B / 건축물 · JPEG'),pic('architecture_jpg')]),(1,1,1,[c.para('사진 C / 도서관 · JPEG'),pic('interior_jpg')])],1:[(0,1,2,[c.para('사진 B / 병합 셀 · PNG'),pic('architecture_png',40000)])]},row_height=24500)
s.append(t);sections.append(s)

s=section('03. 표 안의 표에 넣은 사진')
s.append(c.para('왼쪽은 중첩 표, 오른쪽은 한 셀 안의 여러 사진입니다.'))
inner=c.table(2,1,{0:[(0,1,1,[c.para('중첩 1 / PNG'),pic('interior_png',17500)])],1:[(0,1,1,[c.para('중첩 2 / JPEG'),pic('forest_jpg',17500)])]},width=19500,row_height=15500)
inner.find('.//{'+c.HP+'}pos').set('treatAsChar','1')
s.append(c.table(1,2,{0:[(0,1,1,[inner]),(1,1,1,[c.para('일반 셀 / 사진 2개'),pic('forest_png',19000),c.para('아래 사진 / 중앙 자르기'),pic('architecture_jpg',19000,crop=True)])]},row_height=39000))
s.append(c.para('중첩 표의 경계, 각 그림의 위아래 간격과 제목을 확인합니다.'))
sections.append(s)

s=section('04. 셀 안의 자르기 · 회전 · 뒤집기')
variants=[('원본',{}),('중앙 자르기',{'crop':True}),('12도 회전',{'angle':12}),('좌우 뒤집기',{'flip':True})]
cells={r:[(col,1,1,[c.para(variants[r*2+col][0]),pic('forest_jpg',17500,**variants[r*2+col][1])]) for col in range(2)] for r in range(2)}
s.append(c.table(2,2,cells,row_height=18000))
s.append(c.para('같은 그림 데이터를 네 셀에서 참조합니다. 배치 속성은 셀마다 다릅니다.'))
sections.append(s)

s=section('05. 사진 9개가 들어간 반복 표')
s.append(c.para('세 종류의 사진과 두 형식을 섞어 3 × 3 표 안에 배치했습니다.'))
ids=list(media)
cells={r:[(col,1,1,[c.para(f'{r*3+col+1:02d} / '+ids[(r*3+col)%len(ids)]),pic(ids[(r*3+col)%len(ids)],12500)]) for col in range(3)] for r in range(3)}
s.append(c.table(3,3,cells,row_height=13500))
s.append(c.para('반복 참조여도 사진이 누락되거나 다른 셀의 그림으로 바뀌면 안 됩니다.'))
sections.append(s)

file=c.write('고해상도사진_복합표_공유참조_261009',sections,media)
with zipfile.ZipFile(file) as z:
    roots=[E.fromstring(z.read(n)) for n in z.namelist() if n.startswith('Contents/section') and n.endswith('.xml')]
    pictures=[p for r in roots for p in r.findall('.//{'+c.HP+'}pic')]
    in_cells=sum(bool(p.xpath('ancestor::*[local-name()="tc"]')) for p in pictures)
    assert in_cells==len(pictures)
    info={'source':str(file),'bytes':file.stat().st_size,'sections':len(roots),'tables':sum(len(r.findall('.//{'+c.HP+'}tbl')) for r in roots),'nestedTables':sum(len(r.xpath('//*[local-name()="tbl"]//*[local-name()="tbl"]')) for r in roots),'pictureInstances':len(pictures),'picturesInsideCells':in_cells,'imagePayloads':len(media),'photos':sources}
separate={}
for sec in sections:
    for image in sec.findall('.//{'+c.HC+'}img'):
        old=image.get('binaryItemIDRef');new=f'photo_{len(separate)+1:02d}'
        filename,mime,data=media[old]
        separate[new]=(new+Path(filename).suffix,mime,data)
        image.set('binaryItemIDRef',new)
large=c.write('고해상도사진_복합표_개별삽입_261009',sections,separate)
info['separateEmbedding']={'source':str(large),'bytes':large.stat().st_size,'imagePayloads':len(separate),'note':'Each picture instance embeds its own PNG/JPEG copy, as repeated independent insertion can do. No padding or upscaling.'}
(CASE/'fixture.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8'); print(json.dumps(info,ensure_ascii=False,indent=2))
