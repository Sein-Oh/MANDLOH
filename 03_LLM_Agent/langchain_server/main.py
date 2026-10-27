import time
import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn
import os

from chain import generate_response_stream, generate_response_complete, DEFAULT_MODEL, DEFAULT_BASE_URL

app = FastAPI(
    title="LangChain OpenAI-Compatible Proxy Server",
    description="LangChain 2-Step Pipeline (Prompt Refinement -> Response Generation) Server",
    version="1.0.0"
)

# CORS 설정 (브라우저 fetch 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(default=DEFAULT_MODEL, description="Model identifier")
    messages: List[Dict[str, Any]] = Field(..., description="Chat history list")
    stream: Optional[bool] = Field(default=False, description="Enable SSE streaming")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")
    chat_template_kwargs: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional kwargs, e.g. {'enable_thinking': True}"
    )


def create_chunk_payload(request_id: str, model: str, content: str = "", finish_reason: Optional[str] = None) -> str:
    """OpenAI SSE Chat Completion Chunk 포맷 생성"""
    payload = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }
        ]
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def sse_stream_generator(
    messages: List[Dict[str, Any]],
    model_name: str,
    temperature: float,
    enable_thinking: bool
):
    """LangChain 결과를 OpenAI SSE 형식으로 변환하여 스트리밍"""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    # 1. 초기 롤 전달 델타 (OpenAI 호환성)
    initial_payload = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None
            }
        ]
    }
    yield f"data: {json.dumps(initial_payload, ensure_ascii=False)}\n\n"

    # 2. 토큰 스트리밍
    try:
        async for chunk in generate_response_stream(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            enable_thinking=enable_thinking
        ):
            if chunk:
                yield create_chunk_payload(request_id, model_name, content=chunk, finish_reason=None)
    except Exception as e:
        error_msg = f"\n\n[Error occurred during generation: {str(e)}]"
        yield create_chunk_payload(request_id, model_name, content=error_msg, finish_reason="error")
        yield "data: [DONE]\n\n"
        return

    # 3. 종료 알림
    yield create_chunk_payload(request_id, model_name, content="", finish_reason="stop")
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI 호환 Chat Completions API 엔드포인트
    브라우저의 fetch 요청과 100% 호환
    """
    enable_thinking = False
    if req.chat_template_kwargs and isinstance(req.chat_template_kwargs, dict):
        enable_thinking = req.chat_template_kwargs.get("enable_thinking", False)

    model_name = req.model or DEFAULT_MODEL
    temperature = req.temperature if req.temperature is not None else 0.7

    # 스트리밍 응답
    if req.stream:
        return StreamingResponse(
            sse_stream_generator(
                messages=req.messages,
                model_name=model_name,
                temperature=temperature,
                enable_thinking=enable_thinking
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # 논스트리밍(일반) 응답
    try:
        reply_content = await generate_response_complete(
            messages=req.messages,
            model_name=model_name,
            temperature=temperature,
            enable_thinking=enable_thinking
        )
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": reply_content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """사용 가능한 모델 목록 반환 (OpenAI 호환)"""
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "lm-studio"
            }
        ]
    }


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """테스트용 웹 인터페이스 제공"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>LangChain Server Running</h1><p>OpenAPI docs available at <a href='/docs'>/docs</a></p>"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
