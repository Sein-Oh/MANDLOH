# 🚀 NeuJS AI Assistant (무설치 초경량 데스크톱 AI 챗봇)

> **🎉 No Node.js! No Python! No Build! — 100% 포터블(Portable) 무설치 AI 챗봇**  
> Electron 대비 1/50 수준의 극도로 가벼운 용량(실행 파일 약 2.4MB)과 초고속 실행 속도를 자랑합니다.  
> 복잡한 개발 환경 설치나 빌드 과정 없이, **폴더 그대로 압축을 풀고 `neutralino-win_x64.exe`를 더블 클릭하는 즉시 실행**됩니다.

---

## 💎 이 앱의 가장 큰 강점 (Zero-Dependency)

1. **완벽한 무설치 포터블 (Zero-Install / Standalone)**:
   * **Node.js, npm, Python, Visual Studio 등 아무런 개발 도구도 설치할 필요가 없습니다.**
   * USB나 외장 드라이브에 폴더째 복사해서 어떤 Windows PC에서든 즉시 실행할 수 있습니다.
2. **초경량 & 초고속 (Ultra-Lightweight)**:
   * 무거운 크로뮴을 내장하는 Electron과 달리 Windows OS 네이티브 웹뷰(WebView2)를 활용하여 **메모리 점유율이 극도로 낮고 0.1초 만에 켜집니다.**
3. **듀얼 실행 모드 지원**:
   * 🖥️ **데스크톱 네이티브 모드**: `neutralino-win_x64.exe` 실행
   * 🌐 **웹 브라우저 단독 모드**: `resources/app.html`을 브라우저(Chrome, Edge 등)로 그냥 열기

---

## 🌟 핵심 주요 기능 (Key Features)

### 1. 🤖 강력한 LLM 연동 및 스트리밍 응답
* **OpenAI 호환 API 완벽 지원**: LM Studio, Ollama, vLLM, OpenAI 등 다양한 로컬/원격 백엔드 연동.
* **실시간 모델 감지 & 핫스왑**: 서버 주소 입력 시 구동 중인 모델 목록 자동 조회 및 즉시 전환.
* **마크다운 & LaTeX 렌더링**: 코드 하이라이팅(Highlight.js), 수학 수식(KaTeX), 마크다운 테이블 완벽 지원.

### 2. 🕒 실시간 일시 인지 시스템 (Real-time Clock Context)
* 메시지 전송 시 현재 브라우저/시스템의 **날짜, 시간, 요일 정보가 LLM 시스템 프롬프트에 실시간 자동 주입**됩니다.
* LLM이 별도 설정 없이도 *"오늘이 며칠이지?"*, *"이번 주 금요일 날짜가 언제야?"* 같은 시간 기반 질문에 즉시 정확히 답변합니다.

### 3. ⌨️ 스마트 단축어 & 인텔리센스 자동완성
* **`#` 트리거**: 자주 사용하는 단축 프롬프트(인사, 프롬프트 개선 등) 자동완성 팝업.
* **`@` 트리거**: `@오늘`, `@현재시간`, `@날짜` 등 실시간 시스템 일시를 텍스트창에 즉시 삽입.
* **`?` 트리거**: 단축어 및 시스템 도움말 팝업 호출.

### 4. 🎨 모던 UI/UX
* **라이트 / 다크 테마 지원** 및 드래그를 통한 **사이드바 너비 자유 조절**.
* 대화 히스토리 로컬 저장 및 관리 기능.

---

## 📂 포터블 폴더 구성 (Folder Structure)

빌드 과정 없이 아래 폴더 구성 그대로 배포 및 즉시 사용됩니다:

```text
NeuJS/
├── 🚀 neutralino-win_x64.exe  # 🌟 [더블 클릭하여 실행!] (약 2.4MB 단독 실행 파일)
├── neutralino.config.json     # 앱 창 크기, 포트, 타이틀 설정 파일
├── config.json                # LLM 엔드포인트 및 단축어 설정 파일
├── README.md                  # 프로젝트 설명서
├── build_app_html.py          # 단독 웹 버전 app.html 생성 스크립트
└── resources/                 # UI 프론트엔드 리소스 (HTML/JS/CSS 통합)
    ├── index.html             # 데스크톱 네이티브 앱 화면
    ├── app.html               # 웹 브라우저 단독 실행용 HTML
    ├── neutralino.js          # Neutralino.js 클라이언트 라이브러리
    ├── marked.min.js          # 마크다운 파서 라이브러리
    ├── highlight.min.js       # 코드 하이라이팅 라이브러리
    ├── atom-one-dark.min.css  # 코드 테마 스타일시트
    └── icon.png               # 앱 아이콘
```

---

## 🚀 사용 방법 (How to Use)

### 🖥️ 1. 데스크톱 앱으로 실행 (가장 추천)
1. 본 저장소 폴더를 원하는 곳에 다운로드(또는 압축 해제)합니다.
2. **`neutralino-win_x64.exe`** 파일을 더블 클릭하여 바로 실행합니다!
3. 앱 화면의 **`⚙️ 환경 설정`**에서 로컬 LLM(LM Studio, Ollama 등) 주소를 입력하고 대화를 시작하세요.

---

### 🌐 2. 웹 브라우저로 실행 (무설치 웹 버전)
* `resources/app.html` 파일을 크롬, 엣지 등 웹 브라우저로 더블 클릭하여 열면 별도의 웹서버나 런타임 없이도 브라우저에서 즉시 사용 가능합니다.
* *(UI나 스크립트를 수정한 경우, `python build_app_html.py`로 최신 `app.html`을 갱신할 수 있습니다.)*

---

## ⚙️ 기본 설정 (`config.json`)

앱 실행 시 `config.json`에서 기본값을 불러오며, 앱 내 GUI 설정창에서 자유롭게 변경할 수 있습니다:

```json
{
  "BASE_URL": "http://127.0.0.1:1234",
  "API_KEY": "",
  "MODEL_NAME": "google/gemma-4-e4b:2",
  "TEMPERATURE": 0.2,
  "THEME": "light",
  "sidebarWidth": 216,
  "DEFAULT_PROMPT": "당신은 친절한 AI 입니다.",
  "shortcuts": {
    "인사": "안녕하세요? 만들오 입니다.",
    "프롬프트개선": "보유한 스킬 중 prompt-optimizer를 이용해 다음 프롬프트를 개선해 주세요."
  }
}
```

