"""
agent_v1.py - 질문-답변 적절성 검증(Validator) 노드가 포함된 LangGraph 에이전트

[워크플로우 구조]
START ──► agent (초안 작성) ──┬──► (도구 필요 시) ──► tools ──► agent (루프)
                              └──► (답변 생성 시) ──► validator (적절성 검증 및 교정) ──► END

[노드 역할]
1. agent: 사용자의 질문을 분석하고 1차 답변 초안을 생성하거나 필요한 도구를 호출합니다.
2. tools: FastMCP 도구를 실행하고 결과를 agent에게 반환합니다.
3. validator: 사용자의 원래 질문과 1차 답변을 비교 검증하여, 질문의 의도에 맞는지 확인하고 더 완성도 높은 최종 답변으로 검증/보완합니다.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Tuple, TypedDict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

BASE_DIR = Path(__file__).parent.resolve()


# ============================================================================
# 1. LangGraph State (상태 정의)
# ============================================================================
class AgentState(TypedDict):
    """LangGraph 에이전트의 상태 정의"""

    messages: Annotated[List[BaseMessage], add_messages]
    validation_status: Optional[str]  # 검증 상태 (예: "PASSED", "REFINED")


# ============================================================================
# 2. LLM 인스턴스 빌더
# ============================================================================
def normalize_base_url(url: Optional[str]) -> str:
    """LM Studio 및 OpenAI 호환 API Base URL의 /v1 경로 누락을 자동 보정합니다."""
    clean = (url or "").strip().rstrip("/")
    if not clean:
        return "http://192.168.45.146:1234/v1"
    if not clean.endswith("/v1"):
        clean += "/v1"
    return clean


def build_llm(
    app_config: Dict[str, Any],
    temperature: Optional[float] = None,
    streaming: bool = True,
) -> ChatOpenAI:
    """app_config를 기반으로 ChatOpenAI 인스턴스를 생성합니다."""
    temp_val = temperature if temperature is not None else float(app_config.get("TEMPERATURE", 0.2))
    api_key_val = app_config.get("API_KEY", "").strip() or "lm-studio"
    raw_base_url = app_config.get("BASE_URL", "http://192.168.45.146:1234/v1")
    base_url_val = normalize_base_url(raw_base_url)
    model_val = app_config.get("MODEL_NAME", "google/gemma-4-e4b:2")

    return ChatOpenAI(
        base_url=base_url_val,
        api_key=api_key_val,
        model=model_val,
        temperature=temp_val,
        streaming=streaming,
    )


# ============================================================================
# 3. LangGraph 에이전트 빌더 (Agent Node + Validator Node)
# ============================================================================
def create_agent(
    llm: ChatOpenAI,
    tools: List[Any],
    prompt: Optional[str] = None,
) -> Any:
    """
    1차 초안 생성 노드(agent)와 답변 적절성 검증 노드(validator)가 연결된 StateGraph 에이전트 생성
    """
    model = llm.bind_tools(tools) if tools else llm

    # ------------------------------------------------------------------------
    # [노드 1] AI 어시스턴트 1차 초안 생성 노드 (Agent Node)
    # ------------------------------------------------------------------------
    async def agent_node(state: AgentState) -> Dict[str, Any]:
        messages = list(state["messages"])
        if prompt:
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=prompt)] + messages

        response = await model.ainvoke(messages)
        return {"messages": [response]}

    # ------------------------------------------------------------------------
    # [노드 2] 답변 적절성 검증 및 교정 노드 (Validator Node)
    # ------------------------------------------------------------------------
    async def validator_node(state: AgentState) -> Dict[str, Any]:
        """
        사용자의 질문과 1차 초안 답변을 비교하여:
        1. 질문의 핵심 요구사항을 정확히 충족했는지 검증
        2. 부자연스럽거나 누락된 부분을 보완하여 최종 답변 완성
        """
        messages = state["messages"]

        # 최근 사용자 질문 추출
        user_question = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human":
                user_question = str(m.content)
                break

        draft_reply = str(messages[-1].content) if messages else ""

        validation_prompt = (
            "당신은 AI 응답의 품질과 정확성을 평가하고 다듬는 수석 품질 검증관(Validator)입니다.\n\n"
            f"[사용자의 원래 질문]:\n{user_question}\n\n"
            f"[AI의 1차 초안 답변]:\n{draft_reply}\n\n"
            "[검증 및 개선 지침]:\n"
            "1. 1차 답변이 사용자의 질문 의도를 정확하게 충족하는지 확인하세요.\n"
            "2. 초안이 충분히 우수하다면 자연스러운 한국어로 완성도를 높여 출력하세요.\n"
            "3. 초안에 부족하거나 부정확한 점이 있다면 보완하여 완벽한 최종 답변을 작성하세요.\n"
            "4. 검증 과정에 대한 설명 없이 사용자에게 전달할 최종 완성 답변만 출력하세요."
        )

        # 검증 모델 호출 (일관성을 위해 낮은 온도로 추론)
        validator_response = await llm.ainvoke([HumanMessage(content=validation_prompt)])
        final_text = str(validator_response.content).strip()

        return {
            "messages": [AIMessage(content=final_text)],
            "validation_status": "PASSED",
        }

    # ------------------------------------------------------------------------
    # [조건부 엣지] 도구 실행 여부 분기 라우터
    # ------------------------------------------------------------------------
    def should_continue(state: AgentState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return "validator"

        last_message = messages[-1]
        # 도구 호출이 남아있으면 'tools'로 이동
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # 도구 호출이 없으면 초안 작성이 완료되었으므로 'validator' 노드로 이동하여 검증
        return "validator"

    # ------------------------------------------------------------------------
    # [그래프 구성]
    # ------------------------------------------------------------------------
    builder = StateGraph(AgentState)

    # 1. 노드 등록
    builder.add_node("agent", agent_node)
    builder.add_node("validator", validator_node)

    if tools:
        tool_node = ToolNode(tools)
        builder.add_node("tools", tool_node)

        # 시작 -> agent
        builder.add_edge(START, "agent")
        # agent -> [tools 또는 validator]
        builder.add_conditional_edges("agent", should_continue, ["tools", "validator"])
        # tools -> agent
        builder.add_edge("tools", "agent")
        # validator -> END (최종 종료)
        builder.add_edge("validator", END)
    else:
        builder.add_edge(START, "agent")
        builder.add_edge("agent", "validator")
        builder.add_edge("validator", END)

    return builder.compile()


# ============================================================================
# 4. MCP 도구 로더 및 전체 에이전트 초기화 인터페이스
# ============================================================================
def build_mcp_configs(
    enabled_servers: Set[str],
    mcp_servers_config: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """활성화된 MCP 서버 목록을 바탕으로 MultiServerMCPClient용 연결 설정을 구성합니다."""
    work_dir = base_dir or BASE_DIR
    active_configs: Dict[str, Dict[str, Any]] = {}

    for s_name in enabled_servers:
        if s_name not in mcp_servers_config:
            continue

        s_info = mcp_servers_config[s_name]
        if not isinstance(s_info, dict):
            continue

        s_type = str(s_info.get("type", "")).lower()

        # 1. STDIO 방식 (로컬 파이썬 스크립트 또는 CLI 실행)
        if s_type == "stdio" or "command" in s_info:
            cmd = s_info.get("command", "python")
            if cmd == "python":
                cmd = sys.executable

            args = s_info.get("args", [])
            resolved_args = []
            for a in args:
                if isinstance(a, str) and a.endswith(".py"):
                    p = (work_dir / a).resolve()
                    resolved_args.append(str(p) if p.exists() else a)
                else:
                    resolved_args.append(a)

            env_merged = dict(os.environ)
            if "env" in s_info and isinstance(s_info["env"], dict):
                env_merged.update(s_info["env"])

            conn_dict: Dict[str, Any] = {
                "transport": "stdio",
                "command": cmd,
                "args": resolved_args,
                "env": env_merged,
            }
            if "cwd" in s_info and s_info["cwd"]:
                conn_dict["cwd"] = s_info["cwd"]

            active_configs[s_name] = conn_dict

        # 2. HTTP / SSE 방식 (원격 서버 연결)
        elif s_type in ("http", "streamable_http", "sse") or "url" in s_info or "serverUrl" in s_info:
            url = s_info.get("url") or s_info.get("serverUrl") or ""
            transport_val = "sse" if s_type == "sse" else "streamable_http"
            conn_dict = {
                "transport": transport_val,
                "url": url,
            }
            if "headers" in s_info and s_info["headers"]:
                conn_dict["headers"] = s_info["headers"]
            if "timeout" in s_info and s_info["timeout"]:
                conn_dict["timeout"] = float(s_info["timeout"])
            if "sse_read_timeout" in s_info and s_info["sse_read_timeout"]:
                conn_dict["sse_read_timeout"] = float(s_info["sse_read_timeout"])

            active_configs[s_name] = conn_dict

    return active_configs


async def load_mcp_tools(
    active_configs: Dict[str, Dict[str, Any]],
    timeout: float = 8.0,
    check_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[List[Any], Dict[str, str], List[str]]:
    """개별 MCP 서버별로 안전하게 도구를 로드하고 (도구목록, 설명맵, 실패목록)을 반환합니다."""
    tools: List[Any] = []
    server_tools_map: Dict[str, str] = {}
    failed_servers: List[str] = []

    for s_name, conn_conf in active_configs.items():
        if check_cancelled and check_cancelled():
            break

        try:
            client = MultiServerMCPClient({s_name: conn_conf})
            server_tools = await asyncio.wait_for(client.get_tools(), timeout=timeout)
            tools.extend(server_tools)
            for t in server_tools:
                server_tools_map[t.name] = getattr(t, "description", "")
        except BaseException as s_err:
            failed_servers.append(f"{s_name} ({str(s_err)[:80]})")

    return tools, server_tools_map, failed_servers


async def build_full_agent(
    enabled_servers: Set[str],
    temperature: float,
    system_prompt: Optional[str] = None,
    app_config: Optional[Dict[str, Any]] = None,
    mcp_servers_config: Optional[Dict[str, Any]] = None,
    base_dir: Optional[Path] = None,
    check_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[Any, List[Any], Dict[str, str]]:
    """
    설정과 활성 MCP 도구들을 기반으로 LLM을 로드하고 최종 LangGraph 에이전트를 빌드합니다.
    (app.py의 AgentInitWorker가 이 함수를 호출하여 에이전트를 로드합니다)
    """
    cfg = app_config or {}
    mcp_cfg = mcp_servers_config or cfg.get("mcpServers", {})

    active_configs = build_mcp_configs(enabled_servers, mcp_cfg, base_dir=base_dir)

    tools, server_tools_map, failed_servers = await load_mcp_tools(
        active_configs, timeout=8.0, check_cancelled=check_cancelled
    )

    if check_cancelled and check_cancelled():
        return None, [], {}

    if active_configs and not tools and failed_servers:
        raise RuntimeError(f"MCP 서버 연결 실패: {', '.join(failed_servers)}")

    llm = build_llm(cfg, temperature=temperature, streaming=True)
    agent = create_agent(llm, tools, prompt=system_prompt)

    return agent, tools, server_tools_map


# ============================================================================
# 5. 단독 실행 테스트 (CLI)
# ============================================================================
if __name__ == "__main__":
    import json

    async def main():
        print("🔍 agent_v1.py (Validator Node 연동) 검증 테스트 시작...")
        cfg = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
        agent, tools, _ = await build_full_agent(
            enabled_servers=set(),
            temperature=0.2,
            system_prompt="당신은 친절한 AI 어시스턴트입니다.",
            app_config=cfg,
        )

        test_query = "파이썬에서 가변(Mutable) 객체와 불변(Immutable) 객체의 차이점을 간략히 설명해줘."
        print(f"\n[사용자 질문]: {test_query}\n")

        inputs = {"messages": [HumanMessage(content=test_query)]}

        async for mode, chunk in agent.astream(inputs, stream_mode=["updates"]):
            if mode == "updates":
                for node_name, state_update in chunk.items():
                    print(f"🚀 노드 실행 완료: [{node_name}]")
                    if "messages" in state_update and state_update["messages"]:
                        last_msg = state_update["messages"][-1]
                        preview = str(last_msg.content).strip().replace("\n", " ")
                        print(f"   내용: {preview[:100]}...\n")

        print("✨ 검증 테스트 완료!")

    asyncio.run(main())
