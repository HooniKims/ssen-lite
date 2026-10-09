"""Compare Hancom PDF output: text, drawings, image placement and pixels outside images."""
from pathlib import Path
import json
import sys
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent / 'test-documents'
sys.stdout.reconfigure(encoding='utf-8')

def normalize(value):
    if isinstance(value, float): return round(value, 3)
    if isinstance(value, (str, int, bool)) or value is None: return value
    if isinstance(value, dict): return {k: normalize(v) for k, v in value.items()}
    return [normalize(v) for v in value]

def drawing_info(page):
    keys = ['items', 'type', 'rect', 'fill', 'color', 'width', 'lineCap', 'lineJoin', 'dashes', 'fill_opacity', 'stroke_opacity']
    return normalize([{k: d.get(k) for k in keys} for d in page.get_drawings()])

def block_ssim(a, b):
    """Luminance SSIM over non-overlapping 8px blocks, for rendered image content."""
    a = a.astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    b = b.astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    h, w = a.shape[0] // 8 * 8, a.shape[1] // 8 * 8
    if h < 8 or w < 8: return 1.0 if np.max(np.abs(a-b)) <= 2 else 0.0
    a = a[:h, :w].reshape(h//8, 8, w//8, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    b = b[:h, :w].reshape(h//8, 8, w//8, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    ma, mb = a.mean(1), b.mean(1)
    va, vb = a.var(1), b.var(1)
    cov = (a*b).mean(1)-ma*mb
    return float(np.mean(((2*ma*mb+6.5025)*(2*cov+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))))

def main():
    cases = json.loads((ROOT / 'hancom-report.json').read_text(encoding='utf-8'))
    results = []
    for case in cases:
        source, result = [fitz.open(p['pdf']) for p in case['pair']]
        if len(source) != len(result): raise RuntimeError('Page count mismatch')
        pages = []
        for number, (a, b) in enumerate(zip(source, result)):
            words_equal = normalize(a.get_text('words')) == normalize(b.get_text('words'))
            aboxes = normalize([i['bbox'] for i in a.get_image_info()])
            bboxes = normalize([i['bbox'] for i in b.get_image_info()])
            vectors_equal = drawing_info(a) == drawing_info(b)
            apix, bpix = a.get_pixmap(alpha=False), b.get_pixmap(alpha=False)
            av = np.frombuffer(apix.samples, np.uint8).reshape(apix.height, apix.width, 3)
            bv = np.frombuffer(bpix.samples, np.uint8).reshape(bpix.height, bpix.width, 3)
            if av.shape != bv.shape: raise RuntimeError('Page dimensions mismatch')
            outside = np.ones(av.shape[:2], dtype=bool)
            for box in aboxes + bboxes:
                x0, y0, x1, y1 = box
                outside[max(0, int(y0)-3):min(av.shape[0], int(y1)+4), max(0, int(x0)-3):min(av.shape[1], int(x1)+4)] = False
            diff = np.max(np.abs(av.astype(np.int16)-bv.astype(np.int16)), axis=2)
            changed_outside = int(np.count_nonzero((diff > 2) & outside))
            similarities = []
            for x0, y0, x1, y1 in aboxes:
                y0,y1=max(0,int(y0)),min(av.shape[0],int(y1)+1)
                x0,x1=max(0,int(x0)),min(av.shape[1],int(x1)+1)
                aa,bb=av[y0:y1,x0:x1],bv[y0:y1,x0:x1]
                if aa.size:
                    similarities.append({'ssim': round(block_ssim(aa,bb),6), 'meanAbsoluteError': round(float(np.abs(aa.astype(float)-bb.astype(float)).mean()),4)})
            image_content_ok=all(s['ssim']>=0.95 and s['meanAbsoluteError']<=5 for s in similarities)
            row = {'page': number+1, 'wordsAndPositionsEqual': words_equal, 'imageRectanglesEqual': aboxes == bboxes, 'vectorDrawingsEqual': vectors_equal, 'vectorDrawingCount':len(a.get_drawings()), 'imageInstances': len(aboxes), 'changedPixelsOutsideImages': changed_outside, 'imageContentSimilarity':similarities}
            row['status'] = 'PASS' if words_equal and aboxes == bboxes and vectors_equal and changed_outside == 0 and image_content_ok else 'FAIL'
            pages.append(row)
            if number == 0 or (case['file'].startswith('05_') and number == len(source)-1):
                scale = 1.25
                pngs = []
                for page in [a, b]:
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    pngs.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
                comparison = Image.new('RGB', (pngs[0].width + pngs[1].width + 30, max(p.height for p in pngs) + 55), '#eeeeee')
                draw = ImageDraw.Draw(comparison)
                font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 20)
                draw.text((12, 12), '원본', fill='black', font=font)
                draw.text((pngs[0].width+26, 12), '쎈Lite 처리 후 · 균형', fill='black', font=font)
                comparison.paste(pngs[0], (5, 50)); comparison.paste(pngs[1], (pngs[0].width+25, 50))
                comparison.save(ROOT / 'rendered' / (Path(case['file']).stem + f'_page{number+1}_comparison.png'))
        item = {'file': case['file'], 'pageCount': len(pages), 'pages': pages, 'status': 'PASS' if all(p['status']=='PASS' for p in pages) else 'FAIL'}
        if case['file'].startswith(('01_','02_','05_','06_')) and sum(p['vectorDrawingCount'] for p in pages)==0:
            item['status']='FAIL';item['fixtureError']='Table border fixture is not visible'
        if case['file'].startswith('03_'):
            boxes=[i['bbox'] for i in source[0].get_image_info()]
            crops=[]
            for box in [boxes[0],boxes[-1]]:
                pix=source[0].get_pixmap(clip=fitz.Rect(box),matrix=fitz.Matrix(2,2),alpha=False)
                crops.append(np.asarray(Image.frombytes('RGB',(pix.width,pix.height),pix.samples).resize((400,267))).astype(float))
            normal=float(np.abs(crops[0]-crops[1]).mean()); mirrored=float(np.abs(crops[0][:,::-1]-crops[1]).mean())
            item['flipFixture']={'normalError':round(normal,3),'mirroredError':round(mirrored,3),'genuineFlip':mirrored<normal*.5}
            if not item['flipFixture']['genuineFlip']:item['status']='FAIL'
        results.append(item)
        print(case['file'], len(pages), 'pages', item['status'], flush=True)
        source.close();result.close()
    (ROOT / 'render-report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    if any(r['status'] != 'PASS' for r in results): raise RuntimeError('Visual comparison found differences outside optimized images')

if __name__ == '__main__': main()
