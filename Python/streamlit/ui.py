"""ui.py - Streamlit 기반 로컬 LLM 대화형 웹 애플리케이션 (사이드바 ⚙️ 설정 모달 통합).

실행 방법:
    streamlit run ui.py

주요 특징:
- 사이드바 대화방 목록 옆에 조그만 설정(⚙️) 버튼 배치
- ⚙️ 버튼 클릭 시 화면 중앙에 '통합 설정 모달 다이얼로그(@st.dialog)' 오픈:
  * ✏️ 대화방 이름 변경
  * ⚙️ System Prompt (역할/지침) 수정
  * 🧹 대화 내용 비우기
  * 🗑️ 대화방 영구 삭제
  * 💾 Enter 키 즉시 저장 & Esc 키 즉시 취소
- 상단 메인 화면: 대화방 제목과 모델 정보만 심플하고 시원하게 유지
- 브라우저 창/탭을 닫으면 백그라운드 서버 프로세스 100% 자동 종료 (Auto-Shutdown)
- 실시간 토큰 스트리밍 (st.write_stream + LangChain ChatOpenAI)
- 별도 DB 없이 로컬 JSON 파일(conversations/ 폴더)에 100% 영구 보존
"""

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import streamlit as st

# ==========================================
# 1. 환경 설정 및 브라우저 종료 시 자동 서버 종료
# ==========================================
LM_STUDIO_BASE_URL = "http://192.168.45.146:1234/v1"
LM_STUDIO_API_KEY = "lm-studio"
MODEL_NAME = "gemma"
DEFAULT_SYSTEM_PROMPT = "당신은 친절하고 유능한 AI 어시스턴트입니다."
CONVERSATIONS_DIR = Path(__file__).parent / "conversations"
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="AI Chat Assistant", page_icon="💬", layout="wide")


# 브라우저 창이 모두 닫히면 서버 프로세스를 자동으로 종료하는 백그라운드 모니터
def monitor_browser_sessions():
    """브라우저의 활성 WebSocket 연결이 모두 끊어지면 2초 후 서버 프로세스를 자동 종료"""
    time.sleep(3)
    has_connected = False
    while True:
        time.sleep(1)
        try:
            from streamlit.runtime import get_instance
            runtime = get_instance()
            if runtime and hasattr(runtime, "_session_mgr"):
                active_count = runtime._session_mgr.num_active_sessions()
                if active_count > 0:
                    has_connected = True
                elif has_connected and active_count == 0:
                    print("[INFO] 모든 활성 브라우저 탭이 닫혔습니다. 서버를 자동 종료합니다...")
                    os._exit(0)
        except Exception:
            pass


if "auto_shutdown_monitor" not in st.session_state:
    st.session_state["auto_shutdown_monitor"] = True
    threading.Thread(target=monitor_browser_sessions, daemon=True).start()


# Deploy 버튼 및 불필요한 UI 숨김 CSS
st.markdown(
    """
    <style>
    .stDeployButton, [data-testid="stDeployButton"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# LLM 클라이언트 초기화 (캐싱)
@st.cache_resource
def get_llm():
    return ChatOpenAI(
        base_url=LM_STUDIO_BASE_URL,
        api_key=LM_STUDIO_API_KEY,
        model=MODEL_NAME,
        temperature=0.7,
        streaming=True,
    )


llm = get_llm()


# ==========================================
# 2. 로컬 JSON 저장소 함수
# ==========================================
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def get_room_file(room_name: str) -> Path:
    safe_name = sanitize_filename(room_name) or "General"
    return CONVERSATIONS_DIR / f"{safe_name}.json"


def normalize_room_data(raw: Dict[str, Any], fallback_name: str) -> Dict[str, Any]:
    name = raw.get("name") or fallback_name
    sys_prompt = (
        raw.get("system_prompt")
        or raw.get("metadata", {}).get("system_prompt")
        or DEFAULT_SYSTEM_PROMPT
    )
    created_at = raw.get("created_at") or raw.get("createdAt") or "-"
    updated_at = raw.get("updated_at") or raw.get("createdAt") or "-"

    messages = raw.get("messages")
    if not isinstance(messages, list):
        messages = []
        if "steps" in raw and isinstance(raw["steps"], list):
            for step in raw["steps"]:
                stype = step.get("type")
                output = step.get("output", "")
                if isinstance(output, str) and output.strip():
                    if stype == "user_message":
                        messages.append({"role": "user", "content": output.strip()})
                    elif stype == "assistant_message":
                        messages.append({"role": "assistant", "content": output.strip()})

    return {
        "name": name,
        "created_at": created_at,
        "updated_at": updated_at,
        "system_prompt": sys_prompt,
        "messages": messages,
    }


def load_room(room_name: str) -> Dict[str, Any]:
    file_path = get_room_file(room_name)
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    return normalize_room_data(raw, room_name)
        except Exception:
            pass

    return {
        "name": room_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "messages": [],
    }


def save_room(room_data: Dict[str, Any]):
    room_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = get_room_file(room_data["name"])
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(room_data, f, ensure_ascii=False, indent=2)


def get_all_room_names() -> List[str]:
    rooms = []
    for file in CONVERSATIONS_DIR.glob("*.json"):
        rooms.append(file.stem)
    return sorted(rooms) if rooms else ["General"]


# ==========================================
# 3. 팝업 모달 다이얼로그 (@st.dialog)
# ==========================================
@st.dialog("➕ 새 대화방 만들기")
def create_room_dialog():
    st.write("생성할 **대화방 이름**을 입력하세요:")
    with st.form("create_room_form", clear_on_submit=False):
        new_name = st.text_input("대화방 이름", placeholder="예: 파이썬 스터디", key="dialog_new_room_name")
        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("생성 (Enter)", use_container_width=True, type="primary")
        cancelled = col2.form_submit_button("취소 (Esc)", use_container_width=True)

        if submitted:
            clean_name = sanitize_filename(new_name)
            all_rooms = get_all_room_names()
            if not clean_name:
                st.error("대화방 이름을 입력해주세요.")
            elif clean_name in all_rooms:
                st.error("이미 존재하는 대화방 이름입니다.")
            else:
                new_data = load_room(clean_name)
                save_room(new_data)
                st.session_state.current_room = clean_name
                st.rerun()
        if cancelled:
            st.rerun()


@st.dialog("⚙️ 대화방 설정")
def room_settings_dialog(room_name: str):
    """이름 변경, 프롬프트 수정, 내용 비우기, 삭제를 한 번에 처리하는 통합 설정 모달"""
    r_data = load_room(room_name)
    st.subheader(f"💬 '{room_name}' 설정")

    with st.form(f"settings_form_{room_name}", clear_on_submit=False):
        # 1. 이름 변경 입력
        new_name = st.text_input("대화방 이름", value=room_name, key=f"dialog_rename_{room_name}")

        # 2. System Prompt 수정 입력
        current_p = r_data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        new_p = st.text_area("System Prompt (역할/지침)", value=current_p, height=130, key=f"dialog_prompt_{room_name}")

        col1, col2 = st.columns(2)
        saved = col1.form_submit_button("💾 변경사항 저장 (Enter)", use_container_width=True, type="primary")
        cancelled = col2.form_submit_button("취소 (Esc)", use_container_width=True)

        if saved:
            clean_name = sanitize_filename(new_name)
            all_rooms = get_all_room_names()
            if not clean_name:
                st.error("올바른 대화방 이름을 입력해주세요.")
            elif clean_name != room_name and clean_name in all_rooms:
                st.error("이미 존재하는 대화방 이름입니다.")
            else:
                # 프롬프트 저장
                r_data["system_prompt"] = new_p.strip() or DEFAULT_SYSTEM_PROMPT

                # 이름 변경 시 파일 이동
                if clean_name != room_name:
                    old_file = get_room_file(room_name)
                    if old_file.exists():
                        old_file.unlink()
                    r_data["name"] = clean_name
                    if st.session_state.current_room == room_name:
                        st.session_state.current_room = clean_name

                save_room(r_data)
                st.rerun()

        if cancelled:
            st.rerun()

    st.markdown("---")
    st.write("⚠️ **대화방 정리 및 삭제**")
    c_col1, c_col2 = st.columns(2)

    with c_col1:
        if st.button("🧹 대화 내용 비우기", key=f"dialog_clear_{room_name}", use_container_width=True, help="메시지만 싹 비웁니다"):
            r_data["messages"] = []
            save_room(r_data)
            st.success("대화 내용이 초기화되었습니다.")
            st.rerun()

    with c_col2:
        if st.button("🗑️ 대화방 삭제", key=f"dialog_delete_{room_name}", type="primary", use_container_width=True, help="대화방을 영구 삭제합니다"):
            old_file = get_room_file(room_name)
            if old_file.exists():
                old_file.unlink()
            if st.session_state.current_room == room_name:
                st.session_state.current_room = "General"
            st.rerun()


# ==========================================
# 4. 사이드바 (대화방 목록 및 조그만 ⚙️ 설정 버튼)
# ==========================================
st.sidebar.title("💬 대화방 관리")

all_rooms = get_all_room_names()
if "current_room" not in st.session_state or st.session_state.current_room not in all_rooms:
    st.session_state.current_room = all_rooms[0]

# 1. 새 대화방 만들기 버튼
if st.sidebar.button("➕ **새 대화방 만들기**", use_container_width=True, type="primary"):
    create_room_dialog()

st.sidebar.markdown("---")
st.sidebar.markdown("**📁 대화방 목록**")

# 2. 대화방 선택 목록 & 조그만 ⚙️ 설정 버튼
for room in all_rooms:
    is_active = (room == st.session_state.current_room)
    icon = "👉" if is_active else "💬"

    col_room, col_set = st.sidebar.columns([4.2, 1.0])

    # 1) 대화방 선택 버튼
    if col_room.button(
        f"{icon} {room}",
        key=f"btn_sel_{room}",
        use_container_width=True,
        type="primary" if is_active else "secondary",
    ):
        st.session_state.current_room = room
        st.rerun()

    # 2) 조그만 설정 버튼 (⚙️)
    if col_set.button("⚙️", key=f"btn_set_{room}", help=f"'{room}' 대화방 설정 열기"):
        room_settings_dialog(room)


# ==========================================
# 5. 메인 화면 (상단 헤더 & 대화창)
# ==========================================
current_data = load_room(st.session_state.current_room)

# 상단: 대화방 제목 및 모델 정보만 심플하게 표시
st.subheader(f"💬 {st.session_state.current_room}")
st.caption(f"🤖 Model: `{MODEL_NAME}` | Host: `{LM_STUDIO_BASE_URL}` | Messages: `{len(current_data.get('messages', []))}`")
st.divider()

# 과거 대화 이력 렌더링
messages = current_data.get("messages", [])
if not messages:
    st.info("👋 대화 내용이 없습니다. 아래 입력창에 질문을 입력하세요!")
else:
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 사용자 메시지 입력 및 실시간 스트리밍
if user_query := st.chat_input("메시지를 입력하세요..."):
    # 1. 사용자 메시지 즉시 화면 출력 및 저장
    with st.chat_message("user"):
        st.markdown(user_query)
    current_data["messages"].append({"role": "user", "content": user_query})

    # 2. LangChain 메시지 페이로드 구성
    messages_payload = [SystemMessage(content=current_data.get("system_prompt", DEFAULT_SYSTEM_PROMPT))]
    for m in current_data["messages"]:
        if m["role"] == "user":
            messages_payload.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            messages_payload.append(AIMessage(content=m["content"]))

    # 3. LLM 실시간 스트리밍 응답 렌더링
    with st.chat_message("assistant"):
        def response_generator():
            for chunk in llm.stream(messages_payload):
                if chunk.content:
                    yield chunk.content

        full_response = st.write_stream(response_generator())

    # 4. 응답 저장
    current_data["messages"].append({"role": "assistant", "content": full_response})
    save_room(current_data)
