"""
agent.py - LangGraph 기반 에이전트 빌더 및 LLM/노드/엣지 구성 모듈

이 파일은 순수하게 LLM 생성 및 LangGraph의 StateGraph(노드, 엣지, 상태 관리)를
실험하고 확장하는 데 집중할 수 있도록 구조화되어 있습니다.

[주요 구성]
1. AgentState: LangGraph의 상태(State) 스키마 정의 (필요 시 필드 자유 확장)
2. create_agent(): StateGraph를 기반으로 노드(Nodes)와 엣지(Edges)를 연결하는 메인 빌더
3. build_llm(): LLM 인스턴스 생성 및 옵션 바인딩
4. MCP 도구 연동: FastMCP 도구 로드 및 에이전트 통합 (build_full_agent)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Tuple, TypedDict

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
    """
    LangGraph 에이전트의 상태(State) 정의.
    새로운 노드 간에 주고받고 싶은 데이터(예: step, intent, context 등)가 있다면
    여기에 자유롭게 필드를 추가하여 확장할 수 있습니다.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    # 예시 확장 필드 (필요 시 활성화):
    # current_step: int
    # summary: str


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
# 3. LangGraph 에이전트 빌더 (노드 및 엣지 구성 영역)
# ============================================================================
def create_agent(
    llm: ChatOpenAI,
    tools: List[Any],
    prompt: Optional[str] = None,
) -> Any:
    """
    LangGraph 기반 StateGraph 에이전트를 생성합니다.
    여기서 노드(Node)와 엣지(Edge), 분기 조건(Conditional Edge)을 직접 추가하고 수정할 수 있습니다.

    [기본 흐름]:
    START ──► agent (LLM 노드) ──┬──► (도구 호출 필요 시) ──► tools (ToolNode) ──► agent (루프)
                                  └──► (답변 완료 시)   ──► END
    """
    # 1. 도구가 있는 경우 LLM에 도구 스키마 바인딩
    model = llm.bind_tools(tools) if tools else llm

    # ------------------------------------------------------------------------
    # [노드 1] AI 어시스턴트 추론 노드 (Agent Node)
    # ------------------------------------------------------------------------
    async def agent_node(state: AgentState) -> Dict[str, Any]:
        """사용자 입력 및 대화 이력을 바탕으로 LLM 응답 또는 도구 호출 요청을 생성하는 노드"""
        messages = list(state["messages"])

        # 시스템 프롬프트가 설정되어 있다면 최우선 주입
        if prompt:
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=prompt)] + messages

        response = await model.ainvoke(messages)
        return {"messages": [response]}

    # ------------------------------------------------------------------------
    # [조건부 엣지] 도구 실행 여부 분기 라우터 (Conditional Edge Router)
    # ------------------------------------------------------------------------
    def should_continue(state: AgentState) -> str:
        """LLM 응답에 도구 호출(Tool Calls)이 포함되어 있는지 검사하여 다음 노드 결정"""
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        # LLM이 도구 사용을 요청한 경우 'tools' 노드로 이동
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # 추가 도구 호출이 없으면 대화 종료 (END)
        return END

    # ------------------------------------------------------------------------
    # [그래프 구성] StateGraph 빌드 & 노드/엣지 연결
    # ------------------------------------------------------------------------
    builder = StateGraph(AgentState)

    # 노드 등록
    builder.add_node("agent", agent_node)

    if tools:
        # 도구 실행 노드 등록
        tool_node = ToolNode(tools)
        builder.add_node("tools", tool_node)

        # 엣지 연결 (START -> agent -> [tools or END] -> agent)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", should_continue, ["tools", END])
        builder.add_edge("tools", "agent")  # 도구 실행 결과를 다시 agent 노드로 전달하여 최종 답변 생성
    else:
        # 도구가 비활성화된 경우: START -> agent -> END
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

    # 컴파일 (MemorySaver 없이 순수 JSON 대화 기록 전달 방식으로 동작)
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
