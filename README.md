# 🌐 Bside Browser & AI Agent (`v1.0.0`)

**Bside Browser**는 크로미움(Chromium / QtWebEngine) 기반 웹 브라우저에 **AI 에이전트 원격 페이지 제어(Remote Control)**, **구독형 CLI 모델 연동(Claude Code / Codex / Antigravity)**, **Bside Vault 자동 로그인/결제카드 입력**, **크롬 확장 프로그램(Chrome Extensions) 호환**을 결합한 차세대 AI 브라우저입니다.

---

## ✨ 주요 기능 (`v1.0.0`)

1. **AI 페이지 분석 & 실시간 원격 제어 (`Bsidewright`)**
   - 현재 열려 있는 웹페이지가 우측 AI 채팅창 하단 컨텍스트 카드에 자동 표시됩니다.
   - `🕹️ 원격조정` 버튼 또는 채팅 지시(`"네이버 열어줘"`, `"검색창에 날씨 입력해줘"`, `"아래로 스크롤해줘"`)로 AI가 브라우저를 직접 조작합니다.
2. **구독형 AI CLI + API + 로컬 LLM 통합 지원**
   - **Codex 구독** (`GPT-6.1 Sol`, `GPT-6 Astra`, `GPT-6 Luna`, `GPT-5.6 Terra` 등)
   - **Claude 구독** (`Claude 4.5 Opus`, `Claude 4.5 Sonnet`, `Claude 4.5 Haiku`)
   - **Antigravity 구독** (`Gemini 3.8 Pro`, `Gemini 3.8 Flash`, `Antigravity Luna`)
   - 추론 노력 단계(`Low`, `Medium`, `High`, `Extra High`, `Max`, `Ultrabrowse`) 및 `Fast mode` 실시간 설정 지원
3. **🔐 Bside Vault (비밀번호 & 결제카드 자동입력 매니저)**
   - 저장된 사이트 접속 시 아이디/비밀번호 자동 입력 및 1클릭 자동 로그인 실행
   - 결제 카드(카드번호, 유효기간, CVC, 명의자) 저장 및 결제창 1클릭 자동 입력
4. **🧩 크롬 확장 프로그램 (Chrome Extensions) 설치 및 관리**
   - 크롬 웹 스토어 URL/ID 직설치, `.crx` / `.zip` 설치, 압축 해제된 확장앱 폴더 로드, PC 크롬/엣지 확장앱 가져오기 지원
5. **🔄 버전업 자동 감지 · 무소음 자동 설치 · 자동 재실행**
   - GitHub Releases(`cybereun/BsideBrowser`)에서 상위 버전이 감지되면 자동으로 설치 파일을 내려받아 백그라운드 설치 후 앱을 자동 재시작합니다.
   - 완전한 윈도우 GUI 모드(`console=False`)로 동작하여 실행 시 검은색 터미널 창이 전혀 나타나지 않습니다.

---

## 📦 설치 및 빌드 방법

- **설치 파일 실행**: GitHub Releases에서 최신 `Bside_Setup_v1.0.0.exe`를 다운로드하여 실행하세요.
- **직접 빌드**:
  ```bash
  python build_installer.py
  ```
