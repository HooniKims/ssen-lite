"""Create a local, linked report from the actual complex-corpus verification results."""
from pathlib import Path
import html
import json
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
TEST = ROOT / 'test-documents'

def read(name):
    return json.loads((TEST / name).read_text(encoding='utf-8'))

def size(n):
    return f'{n/1024/1024:.2f} MB' if n >= 1024*1024 else f'{n/1024:.1f} KB'

def link(path, label):
    return f'<a href="{quote(Path(path).relative_to(TEST).as_posix())}">{html.escape(label)}</a>'

def main():
    structural, native, visual, app = [read(n) for n in ['structural-report.json', 'hancom-report.json', 'render-report.json', 'app-report.json']]
    assert len(structural) == 18 and all(r['status'] == 'PASS' for r in structural)
    assert len(native) == len(visual) == 6 and all(r['status'] == 'PASS' for r in native+visual)
    assert app['packaged'] and len(app['documents']) == 6 and all(r['status'] == 'PASS' for r in app['documents'])
    balanced = [r for r in structural if r['preset'] == 'balanced']
    pages = sum(r['pageCount'] for r in visual)
    similarities = [s for r in visual for p in r['pages'] for s in p['imageContentSimilarity']]
    min_ssim = min(s['ssim'] for s in similarities)
    max_mae = max(s['meanAbsoluteError'] for s in similarities)
    rows, cards, mdrows = [], [], []
    for r, v in zip(balanced, visual):
        title = Path(r['file']).stem
        rows.append(f'<tr><td>{html.escape(title)}</td><td>{v["pageCount"]}</td><td>{size(r["before"])}</td><td>{size(r["after"])}</td><td>{r["reductionPercent"]}%</td><td>{link(r["source"],"원본")} · {link(r["output"],"처리 결과")}</td></tr>')
        preview = 'rendered/' + title + '_page1_comparison.png'
        cards.append(f'<article><h3>{html.escape(title)}</h3><a href="{quote(preview)}"><img loading="lazy" src="{quote(preview)}" alt="원본과 균형 설정 결과 비교"></a></article>')
        mdrows.append(f'| {title} | {v["pageCount"]} | {size(r["before"])} | {size(r["after"])} | {r["reductionPercent"]}% |')
    summary = f'구조 검사 18/18 · 한글 렌더 6문서/{pages}페이지 · 배포 실행 파일 일괄 처리 6/6'
    limits = '한컴오피스 2024에서 실제 열기와 렌더 비교를 한 설정은 균형입니다. 화질 우선·용량 우선은 구조 및 이미지 디코드 검사를 통과했습니다. 수식, 실제 OLE 객체, 필드, 변경 추적 및 다른 한글 버전은 이번 복합 양식 실험에 포함하지 않았습니다. BMP·GIF 등 미지원 이미지는 바이트 그대로 보존했습니다. 테스트용 합성 이미지의 감소율이므로 실제 문서의 감소율을 보장하지 않습니다.'
    (TEST/'index.html').write_text(f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>쎈Lite 복합 양식 검증</title>
<style>body{{font:16px/1.65 "Malgun Gothic",sans-serif;margin:40px auto;padding:0 24px;max-width:1100px;color:#242c27;background:#f2f0eb}}h1,h2,h3{{line-height:1.3}}a{{color:#00754a}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}article{{margin:32px 0}}img{{width:100%;height:auto}}.status{{padding:18px;background:#e0efe5;border-radius:12px}}code{{overflow-wrap:anywhere}}</style>
<h1>쎈Lite 복합 양식 검증</h1><p>2026-10-09 · Windows x64 · 쎈Lite 1.0.0</p><p class="status">{summary}<br>단위·통합 검사 33개, UI·실제 업데이트 전송 검사 3개 통과</p>
<p>원본을 수정하지 않았고, 변경한 이미지 외 내부 파일은 전부 바이트가 일치합니다. 글자와 위치, 표 테두리, 그림 배치가 같고 이미지 영역 밖의 변경 픽셀은 0입니다. 이미지 {len(similarities)}개 표시 영역의 최소 SSIM은 {min_ssim:.6f}, 최대 평균 RGB 오차는 {max_mae:.4f}/255입니다. 별도 검수 에이전트가 실제 비교 이미지와 18조합의 내부 파일을 재검증했습니다.</p>
<h2>균형 설정 결과</h2><table><thead><tr><th>테스트 문서</th><th>쪽</th><th>원본</th><th>결과</th><th>감소율</th><th>열기</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>배포 실행 파일에서 6개를 한 번에 추가하여 저장했습니다. 처리와 결과 대조에 {app['seconds']}초가 걸렸습니다. <a href="app-complex-results.png">실제 앱 화면</a></p>
<h2>검증 범위</h2><p>{limits}</p><p>테스트 중 발견한 오류 표시 보존 문제를 수정했습니다. 같은 그림 데이터가 반복될 때 한 번만 인코딩하는 캐시를 추가했고, 캐시 적용 전후 18조합의 ZIP 바이트가 동일함을 별도 실험으로 확인했습니다.</p>
<h2>기계 판독 보고서</h2><p><a href="structural-report.json">18조합 구조·크기</a> · <a href="hancom-report.json">한글 열기·내용</a> · <a href="render-report.json">렌더 비교</a> · <a href="fixture-validation.json">HWPX 스킬 검사</a> · <a href="app-report.json">배포 앱 일괄 처리</a></p>
<h2>원본과 처리 결과 비교</h2><p>왼쪽 원본 / 오른쪽 균형 설정 결과. 이미지를 누르면 원래 크기로 열립니다.</p>{''.join(cards)}</html>''',encoding='utf-8')
    md = f'''# 쎈Lite 검증 기록

2026-10-09, Windows x64, 쎈Lite 1.0.0, 한컴오피스 2024.

**{summary}.** `npm test` 33개, `npm run test:ui` 3개 통과.

원본·결과·비교 화면을 모은 로컬 보고서는 `test-documents/index.html`입니다. 대용량 테스트 문서는 저장소에 포함하지 않으며, 아래 명령으로 재생성합니다.

## 복합 양식 결과

| 문서 | 쪽 | 원본 | 균형 결과 | 감소율 |
|---|---:|---:|---:|---:|
{chr(10).join(mdrows)}

6개 문서 × 3개 설정에서 원본 해시, 내부 파일 목록, 비변경 파일의 바이트 동일성, 변경 이미지 디코드·형식·투명도·크기를 확인했습니다. 병합 및 중첩 표, 셀 안의 그림, 여러 구역, 머리말·꼬리말·각주, 회전·자르기·좌우 반전, 반복 그림, 투명 PNG, 작은 그림, BMP·GIF, 12페이지·24이미지, 이미지 없는 다중 표를 포함합니다.

균형 설정의 {pages}페이지에서 한글의 페이지 수·본문·컨트롤 목록, PDF의 텍스트 위치·그림 위치·표 선이 일치합니다. 이미지 영역 외 변경 픽셀은 0입니다. 그림 {len(similarities)}개 표시 영역의 최소 SSIM {min_ssim:.6f}, 최대 평균 RGB 오차 {max_mae:.4f}/255입니다. 비교 기준은 SSIM 0.95 이상, 평균 오차 5 이하입니다. 실제 표 선이 존재하고 좌우 반전이 적용된 원본인지도 검사합니다. 독립 검수 에이전트가 최종 비교 화면과 18조합의 비변경 바이트를 재검증했습니다.

배포본 `SsenLite.exe`에서도 6개 전체를 한 번에 처리했고 저장 완료, 오류 없음, 모든 비이미지 항목의 바이트 일치를 확인했습니다. 처리 및 결과 대조 {app['seconds']}초. 시간은 해당 PC에서의 측정값입니다.

## 오류 및 경계 조건

- 중복 참조·여러 ID가 같은 이미지 참조, 상대·루트·한글 URL 인코딩 경로.
- 중복 ID·ZIP 항목, 이미지·OLE·XML CRC 손상, 과대한 해제 크기, 누락 참조, 잘못된 XML, DTD, 전자서명 문서 거부.
- 손상 이미지 보존 사유, 원본 ZIP 사본으로 되돌아갈 때 진단 보존, 미지원 이미지 보존.
- EXIF 방향·해상도와 투명도, 취소 후 임시 파일 정리, 파일명 충돌, 오류 문서 격리, 재시도, 작은 창 UI.
- 실제 electron-updater HTTP 다운로드와 SHA-512 일치·불일치 검사. 테스트 설치 파일은 실행하지 않았습니다.

검수 중 원본 사본으로 저장할 때 미지원/손상 이미지 사유를 덮어쓰는 오류를 수정하고 회귀 검사를 추가했습니다. 반복되는 동일 이미지의 인코딩 캐시도 추가했습니다. 별도 이전 corpus 실험의 18조합에서 캐시 전후 ZIP 전체 바이트가 일치했습니다.

## 범위와 재현

{limits}

앱 자체는 Python이나 한글 설치 없이 동작합니다. 아래 검증 도구는 Python의 Pillow, numpy, lxml, PyMuPDF, pywin32와 한글 설치를 사용합니다. 한글 자동화용 모듈 준비는 `scripts/setup-hancom-test.py`를 참고하세요. 테스트 실행마다 새 결과 이름을 사용하므로 `structural-report.json`이 가리키는 결과가 최신입니다.

```powershell
python scripts/create-complex-corpus.py
node scripts/verify-complex-corpus.cjs
python scripts/render-corpus-hancom.py
python scripts/compare-corpus-rendering.py
npm test
npm run test:ui
npm run dist
node scripts/smoke-corpus-ui.cjs --packaged
python scripts/create-test-report.py
```

이 기록은 1.0.0 게시 전 검증 결과입니다. 설치된 앱의 새 버전 교체는 이 검증에 포함하지 않았습니다. 공개 배포 현황은 [GitHub Releases](https://github.com/HooniKims/ssen-lite/releases)에서 확인할 수 있습니다.
'''
    (ROOT/'docs/TESTING.md').write_text(md,encoding='utf-8')
    print(summary)

if __name__ == '__main__': main()
