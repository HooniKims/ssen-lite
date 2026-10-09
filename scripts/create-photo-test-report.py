"""Human-readable local report linking final photo-table fixtures and results."""
from pathlib import Path
import json,html
from urllib.parse import quote
ROOT=Path(__file__).resolve().parent.parent
CASE=ROOT/'test-documents/photo-tables-261009'
data=json.loads((CASE/'structural-report.json').read_text(encoding='utf-8'))
visual=json.loads((CASE/'render-report.json').read_text(encoding='utf-8'))
fixture=json.loads((CASE/'fixture.json').read_text(encoding='utf-8'))
assert len(data)==len(visual)==6 and all(r['status']=='PASS' for r in data) and all(r['layoutStatus']=='PASS' for r in visual)
def link(file,label):return '<a href="'+quote(Path(file).relative_to(CASE).as_posix())+'">'+html.escape(label)+'</a>'
names={'high':'화질 우선','balanced':'균형','small':'용량 우선'}
rows=[]
for row in data:
    kind='개별 삽입 / 21개 내장' if '개별삽입' in row['file'] else '공유 참조 / 6개 내장'
    v=next(v for v in visual if v['file']==row['file'] and v['preset']==row['preset'])
    quality='통과' if v['qualityStatus']=='PASS' else '일부 사진 기준 미달'
    rows.append(f'<tr><td>{kind}</td><td>{names[row["preset"]]}</td><td>{row["before"]/1e6:.2f} MB</td><td>{row["after"]/1e6:.2f} MB</td><td>{row["reductionPercent"]:.1f}%</td><td>{quality}</td><td>{link(row["source"],"원본")} · {link(row["output"],"결과")}</td></tr>')
scores=[s for r in visual for p in r['pages'] for s in p['imageSimilarity']]
min_ssim=min(s['ssim'] for s in scores)
comparisons=''.join(f'<article><h3>{n}쪽 원본과 균형 결과</h3><a href="rendered/comparison-page{n}.png"><img loading="lazy" src="rendered/comparison-page{n}.png" alt="{n}쪽 전후 비교"></a></article>' for n in range(1,6))
photos=''.join(f'<li>{link(CASE/"photos"/(name+".png"),label+" PNG 원본")}</li>' for name,label in [('forest','숲과 계곡'),('architecture','건축물'),('interior','도서관')])
content=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>쎈Lite 사진·복합 표 검증</title>
<style>body{{font:16px/1.7 "Malgun Gothic",sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;background:#f2f0eb;color:#22372e}}h1,h2,h3{{line-height:1.4}}a{{color:#00754a}}.status{{padding:18px;border-radius:14px;background:#e0efe5}}table{{width:100%;border-collapse:collapse;background:white}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}img{{max-width:100%;height:auto}}article{{margin:32px 0}}</style>
<h1>고용량 사진을 넣은 복합 표 검증</h1><p>2026-10-09 · 공개 배포본 쎈Lite 1.0.0 · 한컴오피스 2024</p>
<p class="status">두 문서 × 세 품질 설정 = 구조·배치 6조합 통과<br>결과 30페이지 · 사진 126개 표시 위치·수량 보존<br>엄격한 화질 기준: 화질 우선·균형 4조합 통과 / 용량 우선 2조합 일부 사진 기준 미달</p>
<h2>무엇을 만들었나</h2><p>기본 내장 ImageGen으로 생성한 사진 3장(숲·건축물·도서관)을 사용했습니다. 실제 원본은 모두 <b>1536×1024</b>이며 PNG 한 장당 약 3.1~4.0MB입니다. 4K 이미지가 아니며 확대나 파일 크기 패딩을 하지 않았습니다. 원본 PNG와 크기 변경 없이 품질 98로 저장한 JPEG를 함께 넣었습니다. 따라서 이 검증은 1536px 사진의 재압축과 용량 우선의 1400px 축소를 확인하며, 3200px 초과 사진의 축소는 이번 자료로 검증하지 않습니다.</p>
<p>문서마다 <b>5페이지·7개 표·중첩 표 1개·사진 배치 21개</b>가 있습니다. 모든 그림이 실제 표 셀 안에 있습니다. 일반 셀, 가로·세로 병합, 표 안의 표, 한 셀에 여러 사진, 자르기·12도 회전·좌우 반전, 3×3 사진 표를 포함했습니다. 공유 참조 문서는 내장 이미지 6개를 여러 셀에서 사용하고, 개별 삽입 문서는 사진 배치마다 이미지 사본을 별도로 넣어 21개를 내장했습니다.</p>
<h2>실제 용량 변화</h2><p>MB는 1,000,000바이트 기준입니다. 앱의 1024 단위 표시와 숫자가 다를 수 있습니다.</p><table><thead><tr><th>문서</th><th>설정</th><th>처리 전</th><th>처리 후</th><th>감소율</th><th>화질 비교</th><th>열기</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>PNG의 픽셀 크기가 설정 한도 이내이면 팔레트 감색이나 JPEG 변환을 하지 않으므로 감소 폭이 작을 수 있습니다. 이미 압축된 사진이 섞인 이번 자료의 감소율은 이전 합성 패턴 자료보다 작았습니다. 실제 감소율은 파일마다 다릅니다.</p>
<h2>확인한 내용</h2><ul><li>배포 실행 파일의 UI에서 두 원본을 추가하고 세 설정으로 실제 저장했습니다.</li><li>원본 SHA-256이 유지되고, 변경 이미지 외 모든 내부 파일의 바이트가 일치했습니다. 모든 결과 이미지를 디코드하여 형식·투명도·크기를 확인했습니다.</li><li>원본과 모든 결과를 한글로 직접 열어 페이지 수·본문·컨트롤 목록이 일치하는지 확인했습니다.</li><li>총 30개 결과 페이지의 글자 위치, 표 선, 그림 위치가 일치했습니다. 이미지 영역 밖 변경 픽셀은 0입니다.</li><li>각 문서 21개 그림이 PDF에 실제 표시되는지 셌습니다. 126개 표시 영역의 최소 SSIM은 {min_ssim:.6f}입니다(한글 PDF를 72dpi로 렌더한 비교). 픽셀 단위 무손실이나 모든 확대 배율의 동일 화질을 의미하지 않습니다.</li></ul>
<h2>화질 검사에서 발견한 차이</h2><p>사전에 정한 비교 기준은 SSIM 0.95 이상, 평균 RGB 오차 5/255 이하입니다. 기준은 결과를 본 뒤 낮추지 않았습니다. 화질 우선과 균형은 모든 사진이 통과했습니다. 용량 우선은 1쪽 큰 숲 사진의 평균 오차가 5.19, 4쪽 중앙 자르기 사진이 SSIM 0.912·평균 오차 9.94로 기준에 미달했습니다. 문서 구조 손상이나 사진 누락은 없지만, 자세히 볼 사진·잘라 확대한 사진에는 균형 또는 화질 우선을 권합니다.</p><p><a href="rendered/comparison-small-page1.png">용량 우선 큰 사진 비교</a> · <a href="rendered/comparison-small-page4.png">용량 우선 자르기·회전 비교</a></p>
<p><a href="app-balanced.png">실제 앱 처리 화면</a> · <a href="structural-report.json">구조·용량·이미지 기록</a> · <a href="hancom-report.json">한글 열기 기록</a> · <a href="render-report.json">렌더 비교 기록</a> · <a href="photos/PROMPTS.md">생성 프롬프트</a></p>
<h2>테스트 사진 원본</h2><ul>{photos}</ul><h2>표와 사진의 전후 비교</h2><p>왼쪽: 원본 / 오른쪽: 균형 결과. 이미지를 누르면 큰 화면으로 볼 수 있습니다.</p>{comparisons}</html>'''
(CASE/'index.html').write_text(content,encoding='utf-8')
print('Photo-table report created; minimum SSIM',min_ssim)
