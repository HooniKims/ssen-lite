# GitHub Releases 업데이트

쎈Pick과 같은 방식입니다. 설치형은 시작 15초 후와 4시간마다 업데이트를 확인합니다. 다운로드와 재시작 설치는 사용자가 선택합니다. 일반 종료만으로 설치하지 않으며 문서 처리 중에는 설치를 막습니다. ZIP은 최신 릴리즈 페이지에서 새 ZIP을 받도록 안내합니다. 개발 실행에서는 업데이트 네트워크가 꺼집니다.

## 첫 게시

전용 공개 저장소는 `HooniKims/ssen-lite`입니다. 소스를 커밋·push한 뒤 해당 커밋을 대상으로 릴리즈를 게시합니다. 초안 릴리즈는 일반 사용자에게 노출되지 않으며, 정식 게시 후 업데이트 주소에서 읽을 수 있습니다.

로컬 설치 파일과 ZIP은 `npm run dist`로 빌드합니다. 게시 전 저장소명이 바뀌면 `package.json`의 `build.publish`, `app/updater.cjs`의 `RELEASE_REPOSITORY`, 업데이트 테스트의 URL을 함께 바꿉니다. 쎈Pick의 `moa-review` 피드를 사용하지 않습니다.

## 다음 버전

1. package.json 버전을 올리고 `npm install --package-lock-only`를 실행합니다.
2. CHANGELOG.md에 버전별 변경 내용을 작성합니다.
3. 커밋하고 원격으로 push합니다.
4. `npm run release -- --draft`로 검증·빌드 후 초안 릴리즈를 만들거나 `npm run release`로 게시합니다.
5. 첫 설치와 업데이트를 실제 Windows 환경에서 확인합니다.

릴리즈 스크립트는 깨끗하고 원격과 같은 커밋인지 확인하고 Rust 엔진 빌드, 단위 테스트, Electron UI 및 실제 업데이트 전송 테스트, Windows 패키징, 체크섬 생성 순으로 실행합니다.

필수 첨부: `SsenLite-Setup-VERSION.exe`, EXE.blockmap, `SsenLite-VERSION-x64.zip`, `latest.yml`, `SHA256SUMS.txt`. latest.yml과 EXE는 같은 빌드여야 합니다. 게시한 버전은 덮어쓰지 말고 버전을 올려 배포합니다.

GitHub Releases 미게시 상태의 404는 ‘배포된 업데이트 정보를 찾지 못했습니다’로 표시합니다. 실제 최신 버전이라고 잘못 표시하지 않습니다. Windows 코드 서명 인증서는 현재 구성하지 않았습니다.
