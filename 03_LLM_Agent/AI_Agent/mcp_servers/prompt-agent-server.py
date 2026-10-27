"""prompt-agent-server.py - 프롬프트 분석, 개선 및 대화형 개입(Intervention) 자율 AI 에이전트 FastMCP 서버.

특징:
1. 사용자의 입력 프롬프트 품질(명확성, 세부조건, 경로 지정, 모호성 등)을 실시간 분석
2. 프롬프트가 부실/모호한 경우: 친절한 끼어들기 개입 메시지(Intervention)와 함께 구체화된 개선 프롬프트 생성
3. 프롬프트가 이미 구체적인 경우: 불필요한 개입 없이 패스(Pass)하여 신속한 작업 진행
4. FastMCP 기반 멀티 전송 (HTTP 8102, SSE, stdio) + CORS 허용 + CLI 대화형 직접 실행 모드 (--direct)
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# LangChain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


# ==============================================================================
# 1. 설정 로드
# ==============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "agent_config.json"

DEFAULT_CONFIG = {
    "AGENT_URL": "http://127.0.0.1:1234/v1",
    "API_KEY": "not-needed",
    "MODEL_NAME": "google/gemma-4-24b",
    "TEMPERATURE": 0.2,
}

AGENT_CONFIG = dict(DEFAULT_CONFIG)
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
            AGENT_CONFIG.update(user_cfg)
    except Exception as e:
        print(f"⚠️ 설정 파일 로드 실패: {e}", file=sys.stderr)


# ==============================================================================
# 2. LLM 인스턴스 생성
# ==============================================================================

def create_llm():
    return ChatOpenAI(
        base_url=AGENT_CONFIG.get("AGENT_URL", "http://127.0.0.1:1234/v1"),
        api_key=AGENT_CONFIG.get("API_KEY", "not-needed"),
        model=AGENT_CONFIG.get("MODEL_NAME", "google/gemma-4-24b"),
        temperature=AGENT_CONFIG.get("TEMPERATURE", 0.2),
    )


# ==============================================================================
# 3. 프롬프트 분석 및 개선 핵심 엔진
# ==============================================================================

PROMPT_REFINER_SYSTEM_PROMPT = """당신은 사용자의 요청 프롬프트를 분석하여 최적의 실행 지시문으로 다듬어주는 '프롬프트 최적화 & 개입 전문 AI 에이전트(Prompt Refiner Agent)'입니다.

[역할 및 임무]
1. 사용자가 입력한 요청(user_prompt)과 이전 맥락(context)을 면밀히 분석합니다.
2. 프롬프트가 '부실하거나 모호한지(is_vague)'를 엄격하고 정확하게 판단합니다.
   - [부실/모호한 경우 (is_vague = True)]:
     • 너무 짧거나 추상적인 지시 (예: "파일 정리해줘", "정리해", "백업해줘", "지워", "요약해")
     • 필수 세부 정보가 누락된 경우 (작업 대상 디렉토리 경로, 파일 확장자, 대상 조건, 텍스트 등)
     • 안전하지 않거나 불명확한 파괴적 명령
   - [명확한 경우 (is_vague = False)]:
     • 대상 경로와 조건, 구체적인 동작이 명시된 경우 (예: "D:\\temp 경로의 모든 txt 파일 중 '메롱'이 들어있는 파일만 삭제해줘", "C:\\work에 report.md 만들고 내용 써줘")

3. 출력 형식:
반드시 아래 JSON 형식으로만 응답하십시오 (설명 텍스트 제외):
```json
{
  "is_vague": true,
  "vague_reasons": ["작업 대상 폴더 경로가 명시되지 않음", "정리할 파일의 기준(0바이트, 임시파일 등)이 모호함"],
  "improved_prompt": "현재 작업 폴더(.)의 모든 파일 목록을 조회하여, 0바이트 빈 파일과 임시 파일(.tmp)을 안전하게 휴지통으로 이동하고 실물 검증 보고서를 작성해줘",
  "intervention_message": "💡 **[Prompt Refiner] 프롬프트 개선 개입**:\n입력하신 요청이 다소 모호하여, 안전하고 구체적인 실행 계획으로 보강하여 진행합니다!\n\n> 🎯 **개선된 실행 지시문**:\n> *\"현재 작업 폴더(.)의 모든 파일 목록을 조회하여, 0바이트 빈 파일과 임시 파일(.tmp)을 안전하게 휴지통으로 이동하고 실물 검증 보고서를 작성해줘\"*\n\n위 개선된 목표에 맞추어 다음 실행 에이전트에게 전달합니다. 🚀"
}
```

만약 `is_vague`가 `false`인 경우:
```json
{
  "is_vague": false,
  "vague_reasons": [],
  "improved_prompt": "사용자 원본 프롬프트 그대로",
  "intervention_message": "✅ 프롬프트가 구체적이고 명확합니다. 원본 요청 그대로 진행합니다."
}
```
"""


async def analyze_and_refine_prompt(user_prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
    """사용자의 입력을 분석하고 개선안과 개입 메시지를 반환합니다."""
    llm = create_llm()
    input_text = f"사용자 입력 프롬프트: \"{user_prompt}\""
    if context:
        input_text += f"\n이전 대화 맥락: {context}"

    messages = [
        SystemMessage(content=PROMPT_REFINER_SYSTEM_PROMPT),
        HumanMessage(content=input_text),
    ]

    try:
        response = await llm.ainvoke(messages)
        res_text = response.content.strip()

        # JSON 파싱 시도
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", res_text)
        json_str = match.group(1).strip() if match else res_text

        # 중괄호 추출
        if "{" in json_str and "}" in json_str:
            start = json_str.index("{")
            end = json_str.rindex("}") + 1
            json_str = json_str[start:end]

        data = json.loads(json_str)
        return data
    except Exception as e:
        # Fallback 규칙 기반 처리
        is_short = len(user_prompt.strip()) < 15 and not any(ch in user_prompt for ch in [":", "\\", "/", "."])
        if is_short:
            improved = f"현재 경로(.)에서 '{user_prompt}'와 관련된 항목을 상세히 조회하고 안전하게 처리해줘"
            return {
                "is_vague": True,
                "vague_reasons": ["요청이 너무 간략하여 대상 경로와 세부 조건이 불명확함"],
                "improved_prompt": improved,
                "intervention_message": f"💡 **[Prompt Refiner] 프롬프트 보강 개입**:\n요청이 다소 간략하여 다음과 같이 구체화하여 진행합니다:\n\n> 🎯 **개선된 프롬프트**: *\"{improved}\"*",
            }
        else:
            return {
                "is_vague": False,
                "vague_reasons": [],
                "improved_prompt": user_prompt,
                "intervention_message": "✅ 프롬프트가 구체적이고 명확합니다. 원본 요청 그대로 진행합니다.",
            }


# ==============================================================================
# 4. FastMCP 서버 및 도구 등록
# ==============================================================================

mcp = FastMCP("Prompt-Refiner-Agent-Server")


@mcp.tool(name="prompt_refine_task")
async def prompt_refine_task(
    user_prompt: str = Field(
        description="[프롬프트 개선 에이전트] 사용자가 입력한 요청이 모호하거나(예: '파일 정리해줘', '백업해', '지워줘'), 경로/조건이 부실할 때 먼저 이 도구를 호출하여 개입 메시지를 띄우고 개선된 실행 프롬프트를 획득합니다.",
    ),
    context: Optional[str] = Field(
        default=None,
        description="이전 대화 맥락 또는 작업 디렉토리 정보",
    ),
) -> str:
    """[프롬프트 개선 및 개입 에이전트] 사용자의 요청이 모호하거나 부실한지 평가하고, 필요한 경우 대화형 개입 메시지와 함께 완벽하게 다듬어진 개선 프롬프트를 반환합니다."""
    result = await analyze_and_refine_prompt(user_prompt, context)

    if result.get("is_vague"):
        output = [
            result.get("intervention_message", ""),
            "",
            f"🎯 **[전달용 개선 프롬프트]**: `{result.get('improved_prompt')}`",
            f"🔍 **[개선 사유]**: {', '.join(result.get('vague_reasons', []))}",
        ]
        return "\n".join(output).strip()
    else:
        return f"✅ **[프롬프트 검토 통과]**: 명확하고 구체적인 지시문입니다.\n- 진행 프롬프트: `{result.get('improved_prompt')}`"


@mcp.tool(name="prompt_evaluate_score")
async def prompt_evaluate_score(
    user_prompt: str = Field(description="평가할 프롬프트 텍스트"),
) -> str:
    """프롬프트의 구체성, 명확성, 안전성 점수(0~100점)와 분석 피드백을 제공합니다."""
    result = await analyze_and_refine_prompt(user_prompt)
    is_vague = result.get("is_vague", False)
    score = 45 if is_vague else 95

    status = "⚠️ 부실/모호 (개선 권장)" if is_vague else "🌟 우수 (매우 명확함)"
    lines = [
        f"📊 **프롬프트 품질 평가 점수**: **{score}점 / 100점** ({status})",
        f"- 대상 프롬프트: \"{user_prompt}\"",
        f"- 개선된 버전: \"{result.get('improved_prompt')}\"",
    ]
    if result.get("vague_reasons"):
        lines.append(f"- 보강 필요 사항: {', '.join(result['vague_reasons'])}")
    return "\n".join(lines)


# ==============================================================================
# 5. CLI Direct 대화형 테스트 모드
# ==============================================================================

async def run_direct_cli_mode():
    print("\n" + "=" * 65)
    print("🤖 Prompt Refiner AI Agent [DIRECT CLI MODE]")
    print("=" * 65)
    print(f"📌 LLM 엔드포인트 : {AGENT_CONFIG.get('AGENT_URL')}")
    print(f"📌 타겟 모델명     : {AGENT_CONFIG.get('MODEL_NAME')}")
    print("💡 종료하려면 'exit', 'quit', 'q' 입력")
    print("=" * 65 + "\n")

    while True:
        try:
            user_input = input("\n👤 테스트할 프롬프트 입력 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 종료합니다.")
            break

        if not user_input or user_input.lower() in ("exit", "quit", "q"):
            print("👋 종료합니다.")
            break

        print("\n⏳ 프롬프트 분석 및 개입 판단 중...")
        res = await analyze_and_refine_prompt(user_input)

        if res.get("is_vague"):
            print("\n" + "=" * 60)
            print("🚨 [개입 발생] 프롬프트가 부실합니다!")
            print("=" * 60)
            print(res.get("intervention_message"))
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("✅ [패스] 명확한 프롬프트입니다.")
            print("=" * 60)
            print(f"진행 프롬프트: {res.get('improved_prompt')}")
            print("=" * 60)


# ==============================================================================
# 6. 메인 실행 엔트리포인트
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Prompt Refiner Agent FastMCP Server")
    parser.add_argument("--direct", action="store_true", help="CLI 대화형 직접 테스트 모드로 실행")
    parser.add_argument("--transport", choices=["http", "sse", "stdio", "direct"], default="http", help="전송 방식 (기본값: http)")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE 호스트 (기본값: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8102, help="HTTP/SSE 포트 번호 (기본값: 8102)")

    args = parser.parse_args()

    if args.direct or args.transport == "direct":
        asyncio.run(run_direct_cli_mode())
        return

    cors_middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    ]

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        print(f"🚀 Prompt Refiner Agent FastMCP HTTP Server 시작: http://{args.host}:{args.port}", file=sys.stderr)
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
    elif args.transport == "sse":
        print(f"🚀 Prompt Refiner Agent FastMCP SSE Server 시작: http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )


if __name__ == "__main__":
    main()
