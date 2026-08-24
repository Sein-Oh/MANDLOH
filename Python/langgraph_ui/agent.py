"""
agent.py - LangGraph 기반 에이전트 빌더 및 MCP 도구 연동 모듈
다양한 에이전트 구조(ReAct, 커스텀 StateGraph, 멀티 에이전트 등)를 유연하게 확장/교체할 수 있습니다.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

BASE_DIR = Path(__file__).parent.resolve()


def build_llm(
    app_config: Dict[str, Any],
    temperature: Optional[float] = None,
    streaming: bool = True,
) -> ChatOpenAI:
    """app_config를 기반으로 ChatOpenAI 인스턴스를 생성합니다."""
    temp_val = temperature if temperature is not None else float(app_config.get("TEMPERATURE", 0.0))
    api_key_val = app_config.get("API_KEY", "").strip() or "lm-studio"
    base_url_val = app_config.get("BASE_URL", "http://192.168.45.146:1234/v1")
    model_val = app_config.get("MODEL_NAME", "gemma")

    return ChatOpenAI(
        base_url=base_url_val,
        api_key=api_key_val,
        model=model_val,
        temperature=temp_val,
        streaming=streaming,
    )


def build_mcp_configs(
    enabled_servers: Set[str],
    mcp_servers_config: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """활성화된 MCP 서버 목록을 바탕으로 MultiServerMCPClient용 연결 설정 딕셔너리를 구성합니다."""
    work_dir = base_dir or BASE_DIR
    active_configs: Dict[str, Dict[str, Any]] = {}

    for s_name in enabled_servers:
        if s_name not in mcp_servers_config:
            continue

        s_info = mcp_servers_config[s_name]
        if not isinstance(s_info, dict):
            continue

        s_type = str(s_info.get("type", "")).lower()

        # 1. STDIO 방식 (로컬 프로세스/파이썬 스크립트 실행)
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

        # 2. HTTP / SSE 방식 (원격 엔드포인트)
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
    """개별 MCP 서버별로 안전하게 도구를 로드하고 도구 목록과 실패 서버 목록을 반환합니다."""
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


def create_agent(
    llm: ChatOpenAI,
    tools: List[Any],
    prompt: Optional[str] = None,
    checkpointer: Optional[Any] = None,
) -> Any:
    """
    LangGraph ReAct 에이전트를 생성합니다.
    (이 함수를 수정하여 다양한 커스텀 StateGraph, Supervisor 또는 플랜-실행 에이전트로 교체할 수 있습니다)
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    agent = create_react_agent(
        llm,
        tools,
        prompt=prompt if prompt else None,
        checkpointer=checkpointer,
    )
    return agent


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
    설정과 MCP 서버를 기반으로 LLM 및 도구를 로드하고 완성된 에이전트를 초기화합니다.
    반환값: (agent, tools, server_tools_map)
    """
    cfg = app_config or {}
    mcp_cfg = mcp_servers_config or cfg.get("mcpServers", {})

    active_configs = build_mcp_configs(enabled_servers, mcp_cfg, base_dir=base_dir)

    tools, server_tools_map, failed_servers = await load_mcp_tools(
        active_configs, timeout=8.0, check_cancelled=check_cancelled
    )

    if check_cancelled and check_cancelled():
        return None, [], {}

    # 선택된 서버가 있는데 모든 서버 연결이 실패한 경우 예외 발생
    if active_configs and not tools and failed_servers:
        raise RuntimeError(f"MCP 서버 연결 실패: {', '.join(failed_servers)}")

    llm = build_llm(cfg, temperature=temperature, streaming=True)
    checkpointer = MemorySaver()
    agent = create_agent(llm, tools, prompt=system_prompt, checkpointer=checkpointer)

    return agent, tools, server_tools_map
