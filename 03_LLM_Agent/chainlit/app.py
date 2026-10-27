import os
import sqlite3
from typing import Optional, List

import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser

# ---------------------------------------------------------
# 설정 (Configuration)
# ---------------------------------------------------------
LM_STUDIO_BASE_URL = "http://192.168.45.146:1234/v1"
LM_STUDIO_API_KEY = "lm-studio"
MODEL_NAME = "gemma4"
DB_FILE = "chainlit_history.db"
DB_CONN_STRING = f"sqlite+aiosqlite:///{DB_FILE}"


# ---------------------------------------------------------
# SQLite 데이터베이스 테이블 초기화 (users, threads, steps 등 생성)
# ---------------------------------------------------------
def init_db():
    """Chainlit SQLAlchemyDataLayer에 필요한 SQLite 테이블을 자동 생성합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        identifier TEXT NOT NULL UNIQUE,
        createdAt TEXT,
        metadata TEXT
    );

    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        createdAt TEXT,
        name TEXT,
        userId TEXT,
        userIdentifier TEXT,
        tags TEXT,
        metadata TEXT
    );

    CREATE TABLE IF NOT EXISTS steps (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        threadId TEXT NOT NULL,
        parentId TEXT,
        disableFeedback INTEGER,
        streaming INTEGER,
        waitForAnswer INTEGER,
        isError INTEGER,
        metadata TEXT,
        tags TEXT,
        input TEXT,
        output TEXT,
        createdAt TEXT,
        start TEXT,
        end TEXT,
        generation TEXT,
        showInput TEXT,
        language TEXT,
        indent INTEGER
    );

    CREATE TABLE IF NOT EXISTS elements (
        id TEXT PRIMARY KEY,
        threadId TEXT,
        type TEXT,
        url TEXT,
        chainlitKey TEXT,
        name TEXT NOT NULL,
        display TEXT,
        size TEXT,
        language TEXT,
        page INTEGER,
        props TEXT,
        mime TEXT
    );

    CREATE TABLE IF NOT EXISTS feedbacks (
        id TEXT PRIMARY KEY,
        forId TEXT NOT NULL,
        threadId TEXT NOT NULL,
        value INTEGER NOT NULL,
        comment TEXT
    );
    """)
    conn.commit()
    conn.close()

# 앱 로드 시 DB 테이블 초기화 실행
init_db()


# ---------------------------------------------------------
# Chainlit 공식 Data Layer 설정 (SQLite 로컬 DB 기반 대화 이력 저장)
# ---------------------------------------------------------
@cl.data_layer
def get_data_layer():
    """SQLAlchemyDataLayer를 등록하여 사이드바에 과거 대화(Thread) 목록을 유지/관리합니다."""
    return SQLAlchemyDataLayer(conninfo=DB_CONN_STRING)


# ---------------------------------------------------------
# 사용자 인증 (대화 이력 사이드바 표시를 위해 필요)
# ---------------------------------------------------------
@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """
    로컬 실행 시 간편하게 로그인할 수 있도록 기본 인증을 제공합니다.
    (원하는 아이디/비밀번호 아무거나 입력하여 로그인 가능)
    """
    if username and password:
        return cl.User(identifier=username, metadata={"role": "user", "provider": "credentials"})
    return None


# ---------------------------------------------------------
# 헬퍼 함수: LangChain 체인 생성
# ---------------------------------------------------------
def create_chain():
    llm = ChatOpenAI(
        base_url=LM_STUDIO_BASE_URL,
        api_key=LM_STUDIO_API_KEY,
        model=MODEL_NAME,
        temperature=0.7,
        streaming=True,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 친절하고 유능한 AI 어시스턴트입니다. 사용자의 질문에 성실하게 답변해주세요."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])
    return prompt | llm | StrOutputParser()


# ---------------------------------------------------------
# 새 대화 시작 (@cl.on_chat_start)
# ---------------------------------------------------------
@cl.on_chat_start
async def on_chat_start():
    chain = create_chain()
    cl.user_session.set("chain", chain)
    cl.user_session.set("history_messages", [])

    await cl.Message(
        content=f"👋 안녕하세요! LM Studio (`{MODEL_NAME}`)와 새 대화를 시작합니다.\n"
                f"좌측 사이드바에서 이전 대화 이력을 언제든지 다시 확인하고 이어갈 수 있습니다."
    ).send()


# ---------------------------------------------------------
# 사이드바에서 이전 대화 클릭 시 재개 (@cl.on_chat_resume)
# ---------------------------------------------------------
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """사이드바에서 선택한 과거 대화의 맥락을 LangChain 체인에 복원합니다."""
    chain = create_chain()
    cl.user_session.set("chain", chain)

    # 과거 대화 메시지들을 LangChain BaseMessage 형태로 복원
    history_messages: List[BaseMessage] = []
    steps = thread.get("steps", [])
    for step in steps:
        step_type = step.get("type")
        content = step.get("output", "")
        if step_type == "user_message":
            history_messages.append(HumanMessage(content=content))
        elif step_type == "assistant_message":
            history_messages.append(AIMessage(content=content))

    cl.user_session.set("history_messages", history_messages)


# ---------------------------------------------------------
# 메시지 수신 및 스트리밍 답변 (@cl.on_message)
# ---------------------------------------------------------
@cl.on_message
async def on_message(message: cl.Message):
    chain = cl.user_session.get("chain")
    history_messages: List[BaseMessage] = cl.user_session.get("history_messages", [])

    response_msg = cl.Message(content="")
    await response_msg.send()

    try:
        collected_chunks = []
        async for chunk in chain.astream({
            "history": history_messages,
            "input": message.content
        }):
            await response_msg.stream_token(chunk)
            collected_chunks.append(chunk)

        await response_msg.update()
        full_response = "".join(collected_chunks)

        # 세션 메모리 갱신
        history_messages.append(HumanMessage(content=message.content))
        history_messages.append(AIMessage(content=full_response))
        cl.user_session.set("history_messages", history_messages)

    except Exception as e:
        error_msg = f"⚠️ 오류가 발생했습니다: {str(e)}\n\nLM Studio 서버({LM_STUDIO_BASE_URL}) 연결 상태를 확인해주세요."
        response_msg.content = error_msg
        await response_msg.update()
