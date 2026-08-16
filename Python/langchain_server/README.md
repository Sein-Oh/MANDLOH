# LangChain 2-Step Prompt Refinement & FastAPI Server

이 프로젝트는 **WinPython 3.10.11** 환경에서 실행 가능하도록 구성된 LangChain 기반의 AI 백엔드 프록시 서버입니다.

LM Studio에서 서빙 중인 **Gemma 4** (`http://192.168.45.146:1234`)와 연동하여 **[사용자 입력 ➔ 프롬프트 개선 ➔ 최종 AI 응답]** 2단계 파이프라인을 거치며, 브라우저의 `fetch` 요청 및 OpenAI SSE 스트리밍 표준과 완벽히 호환됩니다.

---

## 📁 프로젝트 구조

```
langchain_server/
├── requirements.txt   # WinPython 3.10.11 호환 필수 패키지
├── chain.py           # LangChain 2단계 파이프라인 (Prompt Refinement -> Response Generation)
├── main.py            # FastAPI 서버 (OpenAI 호환 /v1/chat/completions 및 SSE 스트리밍)
├── index.html         # 브라우저 테스트용 채팅 UI
├── .env               # LM Studio URL 및 설정값
├── run.bat            # 윈도우 원클릭 실행 배치 파일
└── README.md          # 사용 설명서
```

---

## 🚀 설치 및 실행 방법 (WinPython 3.10.11)

WinPython Command Prompt 또는 일반 터미널에서 다음 단계를 순서대로 진행하세요.

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 서버 실행
**방법 A. 배치 파일 실행:**
- `run.bat` 파일을 더블 클릭하여 실행합니다.

**방법 B. 터미널 명령어로 직접 실행:**
```bash
python main.py
```
또는
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 아래 주소로 접속할 수 있습니다:
- **웹 채팅 인터페이스 (테스트 UI):** `http://localhost:8000/`
- **Swagger OpenAPI 문서:** `http://localhost:8000/docs`
- **API 엔드포인트:** `http://localhost:8000/v1/chat/completions`

---

## 🔄 LangChain 2단계 파이프라인 실시간 스트리밍 흐름

1. **사용자 입력 (User Input)**: 클라이언트로부터 대화 기록 및 최근 질문 수신
2. **중간 과정 실시간 스트리밍 (Prompt Refinement Streaming)**: 
   - 사용자가 질문을 보내는 즉시 `<think>` 블록으로 1단계 프롬프트 개선 과정이 토큰 단위로 실시간 스트리밍됩니다.
   - 클라이언트는 대기 시간 없이 AI가 입력을 어떻게 분석하고 최적화하고 있는지 실시간으로 중간 response를 받습니다.
3. **최종 응답 생성 및 실시간 스트리밍 (Final Response Generation)**:
   - 프롬프트 최적화가 완료되면(`</think>`), 개선된 프롬프트를 바탕으로 Gemma 4 모델의 최종 답변이 연이어 실시간 스트리밍됩니다.


---

## 🌐 브라우저 `fetch` 연동 코드 호환

제공해주신 클라이언트 `fetch` 코드와 100% 호환됩니다:

```javascript
const endpoint = 'http://localhost:8000/v1/chat/completions';

const config = {
    modelName: 'gemma-4',
    temperature: 0.7,
    enableThinking: true
};

const apiMessages = [
    { role: 'user', content: '파이썬으로 웹 크롤러 만드는 법 알려줘' }
];

const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        model: config.modelName,
        messages: apiMessages,
        stream: true,
        temperature: config.temperature,
        chat_template_kwargs: {
            enable_thinking: config.enableThinking
        }
    })
});

// SSE 스트림 읽기 예시
const reader = response.body.getReader();
const decoder = new TextDecoder('utf-8');
let buffer = '';

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;
        const dataStr = trimmed.replace(/^data:\s*/, '');
        if (dataStr === '[DONE]') break;

        const parsed = JSON.parse(dataStr);
        const token = parsed.choices?.[0]?.delta?.content;
        if (token) {
            process.stdout.write(token); // 또는 DOM 업데이트
        }
    }
}
```
