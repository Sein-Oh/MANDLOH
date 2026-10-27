import os
import json
import uuid
import datetime
from typing import List, Dict, Tuple, Generator, Any

import gradio as gr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ==========================================
# 1. 설정 및 상수
# ==========================================
DEFAULT_SERVER_URL = "http://192.168.45.146:1234"
DEFAULT_MODEL_NAME = "gemma4"
DEFAULT_SYSTEM_PROMPT = "당신은 친절하고 유능한 AI 어시스턴트입니다."
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_histories")

os.makedirs(HISTORY_DIR, exist_ok=True)


# ==========================================
# 2. 대화 이력 저장 및 관리 함수
# ==========================================
def get_session_file_path(session_id: str) -> str:
    """세션 ID에 해당하는 JSON 파일 경로 반환"""
    return os.path.join(HISTORY_DIR, f"{session_id}.json")


def list_sessions() -> List[Tuple[str, str]]:
    """
    저장된 모든 대화 세션 목록을 반환합니다.
    반환값: [(세션 표시 제목, 세션 ID), ...] (최신 수정순)
    """
    sessions = []
    for file_name in os.listdir(HISTORY_DIR):
        if file_name.endswith(".json"):
            file_path = os.path.join(HISTORY_DIR, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session_id = data.get("id", file_name[:-5])
                    title = data.get("title", "대화 세션")
                    updated_at = data.get("updated_at", "")
                    sessions.append((title, session_id, updated_at))
            except Exception:
                continue

    # 최근 업데이트 순으로 정렬
    sessions.sort(key=lambda x: x[2], reverse=True)
    return [(f"{title} ({s_id[:6]})", s_id) for title, s_id, _ in sessions]


def load_session(session_id: str) -> Tuple[List[Dict[str, str]], str, str]:
    """
    특정 세션의 대화 이력을 로드합니다.
    반환값: (chatbot_history, system_prompt, session_title)
    chatbot_history: [{'role': 'user'|'assistant', 'content': '...'}, ...]
    """
    if not session_id:
        return [], DEFAULT_SYSTEM_PROMPT, "새 대화"

    file_path = get_session_file_path(session_id)
    if not os.path.exists(file_path):
        return [], DEFAULT_SYSTEM_PROMPT, "새 대화"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            messages = data.get("messages", [])
            system_prompt = data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
            title = data.get("title", "대화 세션")

            # messages 형식 검증 및 보정
            chatbot_history = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"]:
                    chatbot_history.append({"role": role, "content": content})

            return chatbot_history, system_prompt, title
    except Exception as e:
        print(f"세션 로드 오류: {e}")
        return [], DEFAULT_SYSTEM_PROMPT, "새 대화"


def save_session(session_id: str, title: str, system_prompt: str, chatbot_history: List[Dict[str, str]]) -> None:
    """대화 이력을 로컬 JSON 파일로 저장합니다."""
    if not session_id:
        return

    # 첫 메시지로 제목 자동 생성 (기존 제목이 기본값인 경우)
    if (title == "새 대화" or not title) and len(chatbot_history) > 0:
        first_user_msg = next((m["content"] for m in chatbot_history if m.get("role") == "user"), "")
        if first_user_msg:
            title = first_user_msg.strip()[:25] + ("..." if len(first_user_msg.strip()) > 25 else "")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = get_session_file_path(session_id)

    data = {
        "id": session_id,
        "title": title,
        "system_prompt": system_prompt,
        "updated_at": now_str,
        "messages": chatbot_history,
    }

    # 파일이 처음 생성되는 경우 created_at 추가
    if not os.path.exists(file_path):
        data["created_at"] = now_str
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                data["created_at"] = old_data.get("created_at", now_str)
        except Exception:
            data["created_at"] = now_str

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_session(session_id: str) -> None:
    """대화 세션을 삭제합니다."""
    if not session_id:
        return
    file_path = get_session_file_path(session_id)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"세션 삭제 오류: {e}")


# ==========================================
# 3. LangChain 연동 및 스트리밍 응답 함수
# ==========================================
def get_langchain_chat_model(server_url: str, model_name: str, temperature: float) -> ChatOpenAI:
    """LM Studio의 OpenAI 호환 API를 호출하는 LangChain ChatOpenAI 객체를 생성합니다."""
    base_url = server_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    return ChatOpenAI(
        base_url=base_url,
        api_key="not-needed",  # LM Studio는 API Key가 필요 없으나 빈값 방지용 더미 전달
        model=model_name if model_name else DEFAULT_MODEL_NAME,
        temperature=temperature,
        streaming=True,
    )


def chat_stream_response(
    user_message: str,
    chatbot_history: List[Dict[str, str]],
    session_id: str,
    session_title: str,
    system_prompt: str,
    server_url: str,
    model_name: str,
    temperature: float,
) -> Generator[Tuple[List[Dict[str, str]], str, str, Any], None, None]:
    """
    사용자 입력을 받아 LangChain 스트리밍으로 챗봇 답변을 생성하고 로컬에 저장합니다.
    chatbot_history 형식: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    """
    if chatbot_history is None:
        chatbot_history = []

    if not user_message.strip():
        yield chatbot_history, "", session_title, gr.update()
        return

    # 세션 ID가 없으면 신규 생성
    if not session_id:
        session_id = str(uuid.uuid4())
        session_title = user_message.strip()[:25] + ("..." if len(user_message.strip()) > 25 else "")

    # 챗봇 이력에 사용자 메시지 및 빈 답변 버블 추가 (Gradio messages format)
    chatbot_history = list(chatbot_history) + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": ""},
    ]
    yield chatbot_history, "", session_title, gr.update()

    # LangChain 메시지 구조 변환
    langchain_messages = []
    if system_prompt.strip():
        langchain_messages.append(SystemMessage(content=system_prompt.strip()))

    # 직전까지의 대화 이력 포함
    for msg in chatbot_history[:-2]:
        role = msg.get("role")
        content = msg.get("content", "")
        if content:
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

    # 현재 사용자 질문 추가
    langchain_messages.append(HumanMessage(content=user_message))

    # LLM 인스턴스 생성 및 스트리밍 호출
    try:
        llm = get_langchain_chat_model(server_url, model_name, temperature)
        accumulated_response = ""

        for chunk in llm.stream(langchain_messages):
            content = chunk.content
            if content:
                accumulated_response += content
                chatbot_history[-1]["content"] = accumulated_response
                yield chatbot_history, "", session_title, gr.update()

    except Exception as e:
        error_msg = f"\n\n[오류 발생: LM Studio 서버 연결 실패 또는 호출 오류]\n상세 내용: {str(e)}"
        chatbot_history[-1]["content"] += error_msg
        yield chatbot_history, "", session_title, gr.update()

    # 대화 완료 후 로컬에 저장
    save_session(session_id, session_title, system_prompt, chatbot_history)

    # 세션 목록 드롭다운 갱신
    sessions = list_sessions()
    dropdown_update = gr.update(choices=sessions, value=session_id)
    yield chatbot_history, "", session_title, dropdown_update


# ==========================================
# 4. Gradio UI 구성
# ==========================================
custom_css = """
.chat-container {
    height: 65vh;
}
.sidebar-panel {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
}
"""

with gr.Blocks(title="LM Studio LangChain Chatbot") as demo:
    # 현재 상태 관리용 State
    current_session_id = gr.State(value="")

    gr.Markdown(
        """
        # 🤖 LangChain & LM Studio Chat Client
        **LM Studio** (`gemma4`) 모델과 **LangChain**을 통해 실시간 스트리밍 대화를 제공하며, 대화 이력을 로컬에 자동 보관합니다.
        """
    )

    with gr.Row():
        # -----------------------------
        # 좌측: 세션 관리 및 설정 패널
        # -----------------------------
        with gr.Column(scale=1, min_width=300, elem_classes=["sidebar-panel"]):
            gr.Markdown("### 🗂 대화 세션 관리")
            new_chat_btn = gr.Button("➕ 새 대화 시작", variant="primary")
            
            session_dropdown = gr.Dropdown(
                label="저장된 대화 목록",
                choices=list_sessions(),
                value=None,
                interactive=True,
            )
            
            session_title_box = gr.Textbox(
                label="현재 대화 제목",
                value="새 대화",
                interactive=True,
            )
            
            with gr.Row():
                rename_btn = gr.Button("✏️ 제목 수정", size="sm")
                delete_btn = gr.Button("🗑️ 현재 대화 삭제", variant="stop", size="sm")

            gr.Markdown("---")
            gr.Markdown("### ⚙️ 서버 및 모델 설정")
            
            server_url_input = gr.Textbox(
                label="LM Studio 서버 URL",
                value=DEFAULT_SERVER_URL,
                placeholder="http://192.168.45.146:1234",
            )
            model_name_input = gr.Textbox(
                label="모델 이름",
                value=DEFAULT_MODEL_NAME,
                placeholder="gemma4",
            )
            temperature_slider = gr.Slider(
                label="Temperature (창의성)",
                minimum=0.0,
                maximum=1.5,
                value=0.7,
                step=0.1,
            )
            
            with gr.Accordion("🛠 시스템 프롬프트 (System Prompt)", open=False):
                system_prompt_input = gr.Textbox(
                    label="System Message",
                    value=DEFAULT_SYSTEM_PROMPT,
                    lines=3,
                )

        # -----------------------------
        # 우측: 메인 채팅창 및 입력 패널
        # -----------------------------
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Chat History",
                elem_classes=["chat-container"],
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    label="메시지 입력",
                    placeholder="질문이나 요청 사항을 입력하세요... (Enter 키로 전송)",
                    lines=2,
                    max_lines=5,
                    scale=8,
                )
                submit_btn = gr.Button("전송 🚀", variant="primary", scale=1)

            with gr.Row():
                clear_view_btn = gr.Button("🧹 화면 대화 비우기 (기록은 유지)", size="sm")


    # ==========================================
    # 5. 이벤트 핸들러 바인딩
    # ==========================================
    
    # 1) 새 대화 시작 버튼 클릭
    def on_new_chat():
        new_id = str(uuid.uuid4())
        return (
            [],                    # chatbot clear (empty list of messages)
            new_id,                # current_session_id
            "새 대화",             # session_title_box
            DEFAULT_SYSTEM_PROMPT, # system_prompt_input
            gr.update(value=None), # session_dropdown
        )

    new_chat_btn.click(
        fn=on_new_chat,
        inputs=[],
        outputs=[chatbot, current_session_id, session_title_box, system_prompt_input, session_dropdown],
    )

    # 2) 저장된 세션 드롭다운 선택 변경
    def on_select_session(selected_session_id):
        if not selected_session_id:
            return [], "", "새 대화", DEFAULT_SYSTEM_PROMPT
        history, sys_prompt, title = load_session(selected_session_id)
        return history, selected_session_id, title, sys_prompt

    session_dropdown.change(
        fn=on_select_session,
        inputs=[session_dropdown],
        outputs=[chatbot, current_session_id, session_title_box, system_prompt_input],
    )

    # 3) 세션 제목 수정 버튼
    def on_rename_session(session_id, new_title, sys_prompt, history):
        if not session_id:
            return gr.update()
        save_session(session_id, new_title, sys_prompt, history)
        sessions = list_sessions()
        return gr.update(choices=sessions, value=session_id)

    rename_btn.click(
        fn=on_rename_session,
        inputs=[current_session_id, session_title_box, system_prompt_input, chatbot],
        outputs=[session_dropdown],
    )

    # 4) 세션 삭제 버튼
    def on_delete_session(session_id):
        if session_id:
            delete_session(session_id)
        sessions = list_sessions()
        return (
            [],                    # chatbot clear
            "",                    # current_session_id clear
            "새 대화",             # session_title_box
            gr.update(choices=sessions, value=None), # session_dropdown
        )

    delete_btn.click(
        fn=on_delete_session,
        inputs=[current_session_id],
        outputs=[chatbot, current_session_id, session_title_box, session_dropdown],
    )

    # 5) 화면 대화 비우기 버튼
    clear_view_btn.click(lambda: [], None, chatbot)

    # 6) 메시지 전송 및 스트리밍 처리 (Enter 키 및 전송 버튼)
    submit_params = {
        "fn": chat_stream_response,
        "inputs": [
            msg_input,
            chatbot,
            current_session_id,
            session_title_box,
            system_prompt_input,
            server_url_input,
            model_name_input,
            temperature_slider,
        ],
        "outputs": [chatbot, msg_input, session_title_box, session_dropdown],
    }

    msg_input.submit(**submit_params)
    submit_btn.click(**submit_params)


# ==========================================
# 6. 메인 실행 진입점
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Gradio LLM Client를 시작합니다.")
    print(f"🔗 Target LM Studio Server: {DEFAULT_SERVER_URL}")
    print(f"🧠 Default Model: {DEFAULT_MODEL_NAME}")
    print("=" * 60)
    
    # 로컬 브라우저에서 실행
    launch_kwargs = {
        "server_name": "127.0.0.1",
        "server_port": 7860,
        "share": False,
        "inbrowser": True,
    }
    
    try:
        demo.queue().launch(theme=gr.themes.Soft(), css=custom_css, **launch_kwargs)
    except TypeError:
        demo.queue().launch(**launch_kwargs)
