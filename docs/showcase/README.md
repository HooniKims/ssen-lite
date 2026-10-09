# 쎈Lite 1.0.0 소개 화면

Windows 배포본에서 앱에 포함된 예제 문서를 실제 처리하여 캡처했습니다.

1. `01-start.png` — 파일 선택·끌어 놓기·예제 불러오기
2. `02-quality.png` — 문서 목록과 화질 우선·균형·용량 우선
3. `03-result.png` — 원본을 보존한 사본 저장과 전후 용량
4. `04-image-details.png` — 이미지별 용량·해상도 변화와 처리 사유
5. `05-guide.png` — 사용 순서와 지원 범위

예제 결과는 15.2MB → 231KB입니다. 실제 감소율은 문서의 이미지 형식·해상도·기존 압축 상태에 따라 다릅니다. 축소한 이미지의 작은 글씨는 흐려질 수 있습니다.

AI·로그인·인터넷 없이 문서를 처리합니다. 업데이트 확인에만 인터넷을 사용합니다.

저장소: https://github.com/HooniKims/ssen-lite

릴리즈: https://github.com/HooniKims/ssen-lite/releases/latest

화면 재생성: `node scripts/capture-showcase.cjs` (기본 배포본 경로: `release/win-unpacked/SsenLite.exe`).
