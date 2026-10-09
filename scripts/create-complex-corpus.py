"""Generate deterministic synthetic HWPX fixtures. No AI or external data."""
from pathlib import Path
from copy import deepcopy
import io
import json
import math
import zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lxml import etree as E

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test-documents" / "originals"
BASE = ROOT / "scripts/sample-base"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
OPF = "http://www.idpf.org/2007/opf/"
BORDER_ID = 3
serial = 10000

def uid():
    global serial
    serial += 1
    return str(serial)

def node(tag, **attrs):
    return E.Element("{" + HP + "}" + tag, **{k: str(v) for k, v in attrs.items()})

def child(parent, tag, **attrs):
    element = node(tag, **attrs)
    parent.append(element)
    return element

def para(text="", page_break=False):
    p = node("p", id=uid(), paraPrIDRef=0, styleIDRef=0, pageBreak=int(page_break), columnBreak=0, merged=0)
    child(child(p, "run", charPrIDRef=0), "t").text = text
    return p

def sublist():
    return node("subList", id="", textDirection="HORIZONTAL", lineWrap="BREAK", vertAlign="TOP", linkListIDRef=0, linkListNextIDRef=0, textWidth=0, textHeight=0, hasTextRef=0, hasNumRef=0)

def picture(image_id, width=18000, height=12000, angle=0, crop=False, flip=False):
    p = para()
    run = p[0]
    pic = child(run, "pic", id=uid(), zOrder=0, numberingType="PICTURE", textWrap="TOP_AND_BOTTOM", textFlow="BOTH_SIDES", lock=0, dropcapstyle="None", href="", groupLevel=0, instid=uid(), reverse=0)
    child(pic, "offset", x=0, y=0)
    child(pic, "orgSz", width=width, height=height)
    child(pic, "curSz", width=width, height=height)
    child(pic, "flip", horizontal=int(flip), vertical=0)
    child(pic, "rotationInfo", angle=angle, centerX=width // 2, centerY=height // 2, rotateimage=1)
    render = child(pic, "renderingInfo")
    for tag in ["transMatrix", "scaMatrix", "rotMatrix"]:
        values = [1, 0, 0, 0, 1, 0]
        if tag == "rotMatrix" and angle:
            a = math.radians(angle)
            c, s = math.cos(a), math.sin(a)
            values = [c, -s, width / 2 * (1 - c) + height / 2 * s, s, c, height / 2 * (1 - c) - width / 2 * s]
        if tag == "scaMatrix" and flip:
            values = [-1, 0, width, 0, 1, 0]
        E.SubElement(render, "{" + HC + "}" + tag, **{f"e{i+1}": str(v) for i, v in enumerate(values)})
    E.SubElement(pic, "{" + HC + "}img", binaryItemIDRef=image_id, bright="0", contrast="0", effect="REAL_PIC", alpha="0")
    rect = child(pic, "imgRect")
    for i, (x, y) in enumerate([(0, 0), (width, 0), (width, height), (0, height)]):
        E.SubElement(rect, "{" + HC + "}pt" + str(i), x=str(x), y=str(y))
    child(pic, "imgClip", left=width // 4 if crop else 0, right=width * 3 // 4 if crop else width, top=height // 4 if crop else 0, bottom=height * 3 // 4 if crop else height)
    child(pic, "inMargin", left=0, right=0, top=0, bottom=0)
    child(pic, "imgDim", dimwidth=width, dimheight=height)
    child(pic, "effects")
    child(pic, "sz", width=width, widthRelTo="ABSOLUTE", height=height, heightRelTo="ABSOLUTE", protect=0)
    child(pic, "pos", treatAsChar=1, affectLSpacing=0, flowWithText=1, allowOverlap=0, holdAnchorAndSO=0, vertRelTo="PARA", horzRelTo="COLUMN", vertAlign="TOP", horzAlign="LEFT", vertOffset=0, horzOffset=0)
    child(pic, "outMargin", left=0, right=0, top=0, bottom=0)
    return p

def table(rows, cols, cells, width=42000, row_height=4500):
    p = para()
    t = child(p[0], "tbl", id=uid(), zOrder=0, numberingType="TABLE", textWrap="TOP_AND_BOTTOM", textFlow="BOTH_SIDES", lock=0, dropcapstyle="None", pageBreak="CELL", repeatHeader=1, rowCnt=rows, colCnt=cols, cellSpacing=0, borderFillIDRef=BORDER_ID, noAdjust=0)
    child(t, "sz", width=width, widthRelTo="ABSOLUTE", height=rows * row_height, heightRelTo="ABSOLUTE", protect=0)
    child(t, "pos", treatAsChar=0, affectLSpacing=0, flowWithText=1, allowOverlap=0, holdAnchorAndSO=0, vertRelTo="PARA", horzRelTo="COLUMN", vertAlign="TOP", horzAlign="LEFT", vertOffset=0, horzOffset=0)
    child(t, "outMargin", left=0, right=0, top=280, bottom=280)
    child(t, "inMargin", left=140, right=140, top=140, bottom=140)
    for row in range(rows):
        tr = child(t, "tr")
        for col, rowspan, colspan, content in cells.get(row, []):
            tc = child(tr, "tc", name="", header=int(row == 0), hasMargin=0, protect=0, editable=0, dirty=0, borderFillIDRef=BORDER_ID)
            sub = sublist()
            tc.append(sub)
            for item in content if isinstance(content, list) else [para(content)]:
                sub.append(item)
            child(tc, "cellAddr", colAddr=col, rowAddr=row)
            child(tc, "cellSpan", colSpan=colspan, rowSpan=rowspan)
            child(tc, "cellSz", width=width // cols * colspan, height=row_height * rowspan)
            child(tc, "cellMargin", left=140, right=140, top=140, bottom=140)
    return p

def simple_table(label, rows=4, cols=3, width=42000):
    return table(rows, cols, {r: [(c, 1, 1, f"{label} {r+1}-{c+1}") for c in range(cols)] for r in range(rows)}, width)

def section(title, landscape=False):
    root = E.fromstring((BASE / "Contents/section0.xml").read_bytes())
    root[0].set("id", uid())
    for p in list(root)[1:]:
        root.remove(p)
    root.find(".//{" + HP + "}t").text = title
    for line in root.findall(".//{" + HP + "}linesegarray"):
        line.getparent().remove(line)
    if landscape:
        page = root.find(".//{" + HP + "}pagePr")
        page.set("landscape", "WIDELY")
    return root

def header_footer(section_root):
    run = section_root[0][0]
    for kind, text in [("header", "쎈Lite 복잡한 문서 테스트 | 머리말"), ("footer", "합성 자료 · 실제 개인정보 없음 | 꼬리말")]:
        control = child(child(run, "ctrl"), kind, id=uid(), applyPageType="BOTH")
        sub = sublist()
        control.append(sub)
        sub.append(para(text))

def png_bytes(image):
    stream = io.BytesIO()
    image.save(stream, "PNG", compress_level=1)
    return stream.getvalue()

def images():
    y, x = np.mgrid[0:2400, 0:3600]
    rng = np.random.default_rng(42)
    noise = rng.integers(-12, 13, (2400, 3600), dtype=np.int16)
    channels = [(x / 16 + y / 23 + noise) % 256, (110 + 75 * np.sin(x / 170) + noise) % 256, (120 + 80 * np.cos(y / 130) + noise) % 256]
    photo = Image.fromarray(np.stack(channels, axis=2).astype('uint8'))
    draw = ImageDraw.Draw(photo)
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 90)
    draw.rectangle((140, 140, 2100, 360), fill='white')
    draw.text((170, 175), '이미지 품질 확인 ABC 123 가나다', font=font, fill='black')
    for i, color in enumerate(['red', 'green', 'blue', 'yellow']):
        draw.rectangle((100 + i * 850, 1900, 750 + i * 850, 2200), fill=color)
    buffer = io.BytesIO()
    photo.save(buffer, 'JPEG', quality=99, subsampling=0)
    alpha = Image.new('RGBA', (3000, 1200), (0, 0, 0, 0))
    d = ImageDraw.Draw(alpha)
    d.rounded_rectangle((100, 100, 2900, 1100), radius=180, fill=(0, 117, 74, 130), outline=(0, 80, 50, 255), width=30)
    d.text((240, 450), '반투명 그림 · 배경이 보여야 함', font=font, fill=(20, 20, 20, 255))
    small = Image.new('RGB', (360, 240), 'white')
    ImageDraw.Draw(small).text((10, 90), '작은 이미지 360px', font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 28), fill='black')
    bmp = io.BytesIO(); small.save(bmp, 'BMP')
    gif = io.BytesIO(); small.save(gif, 'GIF', save_all=True, append_images=[small.transpose(Image.Transpose.FLIP_LEFT_RIGHT)], duration=300, loop=0)
    return {'photo.jpg': ('image/jpeg', buffer.getvalue()), 'alpha.png': ('image/png', png_bytes(alpha)), 'small.png': ('image/png', png_bytes(small)), 'legacy.bmp': ('image/bmp', bmp.getvalue()), 'animation.gif': ('image/gif', gif.getvalue())}

def write(name, sections, media, extras=None):
    files = {p.relative_to(BASE).as_posix(): p.read_bytes() for p in BASE.rglob('*') if p.is_file()}
    header = E.fromstring(files['Contents/header.xml'])
    header.set('secCnt', str(len(sections)))
    borders = header.find('.//{' + HH + '}borderFills')
    b = deepcopy(borders[-1]);borders.append(b);b.set('id', str(BORDER_ID))
    for side in ['leftBorder', 'rightBorder', 'topBorder', 'bottomBorder', 'diagonal']:
        edge = b.find('{' + HH + '}' + side)
        if edge is None: edge = E.SubElement(b, '{' + HH + '}' + side)
        edge.set('type', 'SOLID' if side != 'diagonal' else 'NONE');edge.set('width', '0.12 mm');edge.set('color', '#444444')
    borders.set('itemCnt', str(len(borders)))
    files['Contents/header.xml'] = E.tostring(header, encoding='utf-8', xml_declaration=True)
    manifest = E.fromstring(files['Contents/content.hpf'])
    listing = manifest.find('{' + OPF + '}manifest')
    spine = manifest.find('{' + OPF + '}spine')
    for i, sec in enumerate(sections):
        files[f'Contents/section{i}.xml'] = E.tostring(sec, encoding='utf-8', xml_declaration=True)
        if i:
            E.SubElement(listing, '{' + OPF + '}item', id=f'section{i}', href=f'Contents/section{i}.xml', **{'media-type': 'application/xml'})
            E.SubElement(spine, '{' + OPF + '}itemref', idref=f'section{i}', linear='yes')
    for identifier, (filename, mime, data) in media.items():
        files['BinData/' + filename] = data
        E.SubElement(listing, '{' + OPF + '}item', id=identifier, href='BinData/' + filename, **{'media-type': mime, 'isEmbeded': '1'})
    files['Contents/content.hpf'] = E.tostring(manifest, encoding='utf-8', xml_declaration=True)
    files['Preview/PrvText.txt'] = name.encode()
    files.update(extras or {})
    file = OUT / (name + '.hwpx')
    with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('mimetype', b'application/hwp+zip', compress_type=zipfile.ZIP_STORED)
        for key, data in files.items():
            if key != 'mimetype': z.writestr(key, data)
    return file

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    imgs = images()
    photo = {'photo': ('photo.jpg', *imgs['photo.jpg'])}
    standard = {**photo, 'alpha': ('alpha.png', *imgs['alpha.png'])}
    docs = []
    sec = section('01 병합 표 · 중첩 표 · 셀 안의 그림')
    sec.append(table(3, 3, {0: [(0, 1, 3, '가로 병합 제목')], 1: [(0, 2, 1, '세로 병합'), (1, 1, 1, '금액 12,345원'), (2, 1, 1, '2026. 10. 9.')], 2: [(1, 1, 2, '가로 병합 · 특수문자 & < >')]}, row_height=3500))
    sec.append(para('아래 왼쪽 셀에는 표 안의 표, 오른쪽 셀에는 그림이 있습니다.'))
    inner = simple_table('중첩', 3, 2, 18500)
    inner.find('.//{' + HP + '}pos').set('treatAsChar', '1')
    sec.append(table(2, 2, {0: [(0, 1, 1, [inner]), (1, 1, 1, [picture('photo', 18000, 12000)])], 1: [(0, 1, 2, [picture('alpha', 30000, 12000)])]}, row_height=16000))
    docs.append(write('01_병합표_중첩표_셀그림', [sec], standard))
    sections = []
    for i in range(3):
        sec = section(f'02 구역 {i+1} · ' + ('가로 용지' if i == 1 else '세로 용지'), landscape=i == 1)
        header_footer(sec)
        sec.append(simple_table('구역별 표', 5, 3))
        sec.append(picture('photo', 21000, 14000))
        note_para = para('각주가 있는 문장입니다. ')
        note = child(child(note_para[0], 'ctrl'), 'footNote', instId=uid())
        sub = sublist(); note.append(sub); sub.append(para('각주: 처리 전후 같은 위치에 남아야 합니다.'))
        sec.append(note_para)
        sections.append(sec)
    docs.append(write('02_여러구역_머리말_꼬리말_각주', sections, photo))
    sec = section('03 같은 이미지 반복 참조 · 회전 · 자르기 · 뒤집기')
    for label, angle, crop, flip in [('원본', 0, False, False), ('중앙 자르기', 0, True, False), ('15도 회전', 15, False, False), ('가로 뒤집기', 0, False, True)]:
        sec.append(para(label))
        sec.append(picture('photo', 15000, 10000, angle, crop, flip))
    docs.append(write('03_반복그림_회전_자르기_뒤집기', [sec], photo))
    sec = section('04 투명도 · 작은 그림 · 지원하지 않는 형식')
    med = {}
    for filename, (mime, data) in imgs.items():
        identifier = filename.split('.')[0]
        med[identifier] = (filename, mime, data)
        sec.append(para(filename + (' · 원본 보존 대상' if filename.endswith(('.bmp', '.gif')) else '')))
        sec.append(picture(identifier, 18000, 7200 if identifier == 'alpha' else 12000))
    docs.append(write('04_투명PNG_작은그림_BMP_GIF', [sec], med))
    sec = section('05 반복되는 긴 문서 · 이미지 24개 · 표 12개')
    med = {}
    for page in range(12):
        sec.append(para(f'페이지 {page+1:02d} / 12 · 긴 문서 처리 검증', page_break=page > 0))
        sec.append(simple_table(f'문서 {page+1:02d}', 3, 3))
        for j in range(2):
            identifier = f'p{page}_{j}'
            med[identifier] = (identifier + '.jpg', *imgs['photo.jpg'])
            sec.append(picture(identifier, 18000, 12000))
    docs.append(write('05_12페이지_24이미지_긴문서', [sec], med))
    sec = section('06 이미지 없는 복잡한 표 · 변경 없음 검증')
    for i in range(6):
        sec.append(simple_table(f'빈 양식 {i+1}', 5, 4))
    docs.append(write('06_이미지없는_다중표', [sec], {}, {'Custom/opaque.bin': bytes(range(256)) * 4}))
    manifest = []
    for file in docs:
        with zipfile.ZipFile(file) as z:
            roots = [E.fromstring(z.read(n)) for n in z.namelist() if n.startswith('Contents/section') and n.endswith('.xml')]
            counts = {tag: sum(len(r.findall('.//{' + HP + '}' + tag)) for r in roots) for tag in ['tbl', 'pic', 'header', 'footer', 'footNote', 'tc']}
            counts['nestedTables'] = sum(len(r.xpath('//*[local-name()="tbl"]//*[local-name()="tbl"]')) for r in roots)
            counts['sections'] = len(roots)
        manifest.append({'file': file.name, 'bytes': file.stat().st_size, **counts})
    (OUT.parent / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
