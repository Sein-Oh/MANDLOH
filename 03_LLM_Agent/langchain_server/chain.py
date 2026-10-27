from typing import List, Dict, Any, AsyncIterator
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# LM Studio 엔드포인트 설정
DEFAULT_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://192.168.45.146:1234/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma-4")


def get_llm(model_name: str = DEFAULT_MODEL, temperature: float = 0.7, streaming: bool = False, base_url: str = DEFAULT_BASE_URL):
    """LM Studio에 연결되는 ChatOpenAI 인스턴스 생성"""
    return ChatOpenAI(
        base_url=base_url,
        api_key="lm-studio",  # LM Studio는 임의의 키 문자열 허용
        model=model_name or DEFAULT_MODEL,
        temperature=temperature,
        streaming=streaming,
    )


def convert_dict_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """클라이언트 메시지 딕셔너리 리스트를 LangChain 메시지 객체로 변환"""
    lc_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    return lc_messages


# 1단계: 프롬프트 개선기 (Prompt Refinement Chain)
refine_system_prompt = (
    "당신은 AI 프롬프트 엔지니어링 전문가입니다. "
    "사용자의 질문이나 요청을 분석하여, LLM이 가장 정확하고 풍부하며 체계적인 답변을 도출할 수 있도록 "
    "의도를 명확히 하고 세부 요구사항을 보완한 최적의 프롬프트로 재작성(Refine)해주세요.\n"
    "주의사항:\n"
    "- 다른 불필요한 설명, 인사말, 부가 주석 없이 오직 '개선된 프롬프트 내용'만 바로 출력하세요.\n"
    "- 원래 질문의 핵심 의도와 언어를 그대로 유지하세요."
)

refine_prompt = ChatPromptTemplate.from_messages([
    ("system", refine_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "원래 요청:\n{user_input}\n\n위 요청을 개선된 프롬프트로 재작성해 주세요.")
])

# 2단계: 최종 AI 응답 생성기 (Response Generation Chain)
generation_system_prompt = (
    "당신은 친절하고 전문적이며 뛰어난 능력을 가진 AI 어시스턴트입니다. "
    "사용자의 의도에 맞춰 정확하고 유익하며 구조화된 답변을 제공하세요."
)

generation_prompt = ChatPromptTemplate.from_messages([
    ("system", generation_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{refined_prompt}")
])


async def refine_prompt_async(user_input: str, chat_history: List[BaseMessage], llm: ChatOpenAI) -> str:
    """사용자의 입력을 분석하여 개선된 프롬프트를 생성"""
    refine_chain = refine_prompt | llm | StrOutputParser()
    refined = await refine_chain.ainvoke({
        "user_input": user_input,
        "chat_history": chat_history
    })
    return refined.strip()


async def generate_response_stream(
    messages: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    enable_thinking: bool = True,
    base_url: str = DEFAULT_BASE_URL
) -> AsyncIterator[str]:
    """
    사용자 입력 -> 프롬프트 개선 -> AI 응답 생성 파이프라인 (전체 과정 실시간 스트리밍)
    """
    lc_messages = convert_dict_messages(messages)
    
    # 마지막 사용자 메시지와 이전 대화 기록 분리
    chat_history = []
    user_input = ""
    for i in range(len(lc_messages) - 1, -1, -1):
        if isinstance(lc_messages[i], HumanMessage):
            user_input = lc_messages[i].content
            chat_history = lc_messages[:i]
            break
            
    if not user_input and lc_messages:
        user_input = lc_messages[-1].content
        chat_history = lc_messages[:-1]

    # 1. 프롬프트 개선 체인 (스트리밍)
    refine_llm = get_llm(model_name=model_name, temperature=0.3, streaming=True, base_url=base_url)
    refine_chain = refine_prompt | refine_llm | StrOutputParser()

    refined_prompt_chunks = []
    
    # 중간 과정: 프롬프트 개선 시작을 클라이언트에 실시간 알림
    yield "<think>\n🔍 [1단계: 사용자 입력 분석 및 최적화된 프롬프트 작성 중...]\n"
    
    async for chunk in refine_chain.astream({
        "user_input": user_input,
        "chat_history": chat_history
    }):
        refined_prompt_chunks.append(chunk)
        yield chunk

    refined_prompt = "".join(refined_prompt_chunks).strip()
    yield "\n\n✅ [프롬프트 개선 완료 -> 최종 응답 생성 시작]\n</think>\n\n"

    # 2. 최종 응답 생성 체인 (스트리밍)
    streaming_llm = get_llm(model_name=model_name, temperature=temperature, streaming=True, base_url=base_url)
    generation_chain = generation_prompt | streaming_llm | StrOutputParser()

    async for chunk in generation_chain.astream({
        "refined_prompt": refined_prompt,
        "chat_history": chat_history
    }):
        yield chunk


async def generate_response_complete(
    messages: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    enable_thinking: bool = True,
    base_url: str = DEFAULT_BASE_URL
) -> str:
    """
    사용자 입력 -> 프롬프트 개선 -> AI 응답 생성 파이프라인 (일반 응답)
    """
    lc_messages = convert_dict_messages(messages)
    
    chat_history = []
    user_input = ""
    for i in range(len(lc_messages) - 1, -1, -1):
        if isinstance(lc_messages[i], HumanMessage):
            user_input = lc_messages[i].content
            chat_history = lc_messages[:i]
            break
            
    if not user_input and lc_messages:
        user_input = lc_messages[-1].content
        chat_history = lc_messages[:-1]

    refine_llm = get_llm(model_name=model_name, temperature=0.3, streaming=False, base_url=base_url)
    refined_prompt = await refine_prompt_async(user_input, chat_history, refine_llm)

    llm = get_llm(model_name=model_name, temperature=temperature, streaming=False, base_url=base_url)
    generation_chain = generation_prompt | llm | StrOutputParser()

    result = await generation_chain.ainvoke({
        "refined_prompt": refined_prompt,
        "chat_history": chat_history
    })
    
    return f"<think>\n🔍 [1단계 개선된 프롬프트]:\n{refined_prompt}\n</think>\n\n{result}"

