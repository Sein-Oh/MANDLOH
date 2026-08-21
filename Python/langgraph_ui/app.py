"""app.py - PySide6 기반 모던 데스크톱 AI 비서 애플리케이션.

pip install PySide6 langchain-openai langchain-core langgraph langchain-mcp-adapters mcp pygments httpx

주요 특징:
1. 2단 분할 레이아웃 & 부드러운 햄버거(☰) 사이드바 슬라이드 애니메이션
2. 대화방 관리: messages/ 폴더 내 JSON 파일로 대화 이력 관리 (대화방 제목 = 파일명)
   - 새 대화 생성 시 중복 이름 검증 및 재입력 루프
   - 사이드바 목록 위젯: | 💬 대화방 제목 [✏️ 편집] [🗑️ 삭제] |
3. 상단 헤더 기능:
   - [🧹 지우기]: 현재 대화방 메시지 내역 초기화
   - [🗜️ 컨텍스트 압축]: 최근 5개 대화는 보존하고 이전 대화들을 LLM으로 요약 압축
4. 간결한 mcp_config.json (enabled 키 없음):
   - 앱 시작 시 모든 MCP 서버는 기본 비활성화 상태
   - MCP 설정창에서 체크박스로 활성화 및 [🛠️ 도구 목록] 드롭다운 확인
5. Temperature 설정 모달:
   - 슬라이더(0.0 ~ 2.0, 0.1 단위) 조작 및 실시간 수치 표시
   - 친절한 구간별 설명 가이드 카드 탑재
6. Assistant 응답 소요 시간 및 토큰 사용량 표기 (⏱️ 1.8s | 🔤 ~245 tokens)
7. 다크 / 라이트 모드 테마 전환 버튼 (설정 config.json 영구 기억)
8. 일원화된 모던 그라데이션 전송 버튼 & 전체 너비(Full-width) 대화창 & 복사(📋) 버튼
"""

import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ==========================================
# 1. 파일 경로 및 기본 설정 로드
# ==========================================
BASE_DIR = Path(__file__).parent.resolve()
MESSAGES_DIR = BASE_DIR / "messages"
CONFIG_FILE = BASE_DIR / "config.json"
MCP_CONFIG_FILE = BASE_DIR / "mcp_config.json"

MESSAGES_DIR.mkdir(parents=True, exist_ok=True)


def load_app_config() -> Dict[str, Any]:
    """config.json 로드 (없으면 기본 생성)"""
    default_cfg = {
        "BASE_URL": "http://192.168.45.146:1234/v1",
        "MODEL_NAME": "gemma",
        "TEMPERATURE": 0.0,
        "THEME": "dark",
        "SYSTEM_PROMPT": "당신은 유능하고 친절한 AI 어시스턴트입니다.",
    }
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, ensure_ascii=False, indent=2)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default_cfg, **data}
    except Exception:
        return default_cfg


def save_app_config(config_data: Dict[str, Any]):
    """config.json 저장"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)


def load_mcp_config() -> Dict[str, Any]:
    """mcp_config.json 로드 (mcpServers 루트 키 및 stdio/http 타입 구조 완벽 지원)"""
    default_mcp = {
        "mcpServers": {
            "filesystem": {
                "type": "stdio",
                "command": "python",
                "args": ["fs_mcp_server.py"],
            }
        }
    }
    if not MCP_CONFIG_FILE.exists():
        with open(MCP_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_mcp, f, ensure_ascii=False, indent=2)
        return default_mcp["mcpServers"]

    try:
        with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            servers = raw.get("mcpServers", raw) if isinstance(raw, dict) else {}
            clean_servers = {}
            for k, v in servers.items():
                if isinstance(v, dict):
                    clean_item = {kk: vv for kk, vv in v.items() if kk != "enabled"}
                    clean_servers[k] = clean_item
            return clean_servers
    except Exception:
        return default_mcp["mcpServers"]


def save_mcp_config(servers_data: Dict[str, Any]):
    """mcp_config.json 저장 (mcpServers 루트 키로 래핑하여 저장)"""
    clean_servers = {}
    for k, v in servers_data.items():
        if isinstance(v, dict):
            clean_item = {kk: vv for kk, vv in v.items() if kk != "enabled"}
            clean_servers[k] = clean_item
    full_data = {"mcpServers": clean_servers}
    with open(MCP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)


# ==========================================
# 2. 대화 세션 JSON 관리자
# ==========================================
class ConversationManager:
    """messages/ 폴더 내 대화방 JSON 파일 CRUD 관리자"""

    @staticmethod
    def list_conversations() -> List[str]:
        files = list(MESSAGES_DIR.glob("*.json"))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return [f.stem for f in files]

    @staticmethod
    def load_conversation(title: str) -> Dict[str, Any]:
        file_path = MESSAGES_DIR / f"{title}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "title": title,
            "thread_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }

    @staticmethod
    def save_conversation(title: str, data: Dict[str, Any]):
        file_path = MESSAGES_DIR / f"{title}.json"
        data["title"] = title
        data["updated_at"] = datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def rename_conversation(old_title: str, new_title: str) -> bool:
        old_file = MESSAGES_DIR / f"{old_title}.json"
        new_file = MESSAGES_DIR / f"{new_title}.json"
        if not old_file.exists() or (new_file.exists() and old_title != new_title):
            return False
        try:
            data = ConversationManager.load_conversation(old_title)
            data["title"] = new_title
            old_file.unlink(missing_ok=True)
            ConversationManager.save_conversation(new_title, data)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_conversation(title: str) -> bool:
        file_path = MESSAGES_DIR / f"{title}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False


# ==========================================
# 3. 백그라운드 LangGraph 워커 스레드
# ==========================================
class AgentInitWorker(QThread):
    """선택된 MCP 서버 및 LLM(Temperature 적용) 비동기 초기화 스레드"""

    success = Signal(object, list, dict)
    failed = Signal(str)

    def __init__(self, enabled_servers: Set[str], temperature: float, system_prompt: str = ""):
        super().__init__()
        self.enabled_servers = enabled_servers
        self.temperature = temperature
        self.system_prompt = system_prompt

    def run(self):
        async def _init():
            app_cfg = load_app_config()
            mcp_cfg = load_mcp_config()

            active_configs = {}
            for s_name in self.enabled_servers:
                if s_name in mcp_cfg:
                    s_info = mcp_cfg[s_name]
                    s_type = s_info.get("type", "").lower()

                    if s_type == "stdio" or "command" in s_info:
                        cmd = s_info.get("command", "python")
                        if cmd == "python":
                            cmd = sys.executable
                        args = s_info.get("args", [])
                        resolved_args = []
                        for a in args:
                            if isinstance(a, str) and a.endswith(".py"):
                                p = (BASE_DIR / a).resolve()
                                resolved_args.append(str(p) if p.exists() else a)
                            else:
                                resolved_args.append(a)

                        conn_dict = {
                            "transport": "stdio",
                            "command": cmd,
                            "args": resolved_args,
                        }
                        if "env" in s_info and s_info["env"]:
                            conn_dict["env"] = s_info["env"]
                        if "cwd" in s_info and s_info["cwd"]:
                            conn_dict["cwd"] = s_info["cwd"]

                        active_configs[s_name] = conn_dict

                    elif s_type in ("http", "streamable_http", "sse") or "url" in s_info:
                        url = s_info.get("url", "")
                        # FastMCP의 transport="http"는 MCP Streamable HTTP 사양(streamable_http)을 사용합니다.
                        transport_val = "sse" if s_type == "sse" else "streamable_http"
                        conn_dict = {
                            "transport": transport_val,
                            "url": url,
                        }
                        if "headers" in s_info and s_info["headers"]:
                            conn_dict["headers"] = s_info["headers"]

                        active_configs[s_name] = conn_dict

            tools = []
            server_tools_map = {}

            if active_configs:
                client = MultiServerMCPClient(active_configs)
                tools = await client.get_tools()
                for t in tools:
                    server_tools_map[t.name] = getattr(t, "description", "")

            llm = ChatOpenAI(
                base_url=app_cfg.get("BASE_URL", "http://192.168.45.146:1234/v1"),
                api_key="lm-studio",
                model=app_cfg.get("MODEL_NAME", "gemma"),
                temperature=self.temperature,
                streaming=True,
            )

            checkpointer = MemorySaver()
            agent = create_react_agent(
                llm,
                tools,
                prompt=self.system_prompt if self.system_prompt else None,
                checkpointer=checkpointer,
            )
            return agent, tools, server_tools_map

        try:
            agent, tools, st_map = asyncio.run(_init())
            self.success.emit(agent, tools, st_map)
        except Exception as e:
            self.failed.emit(str(e))


class AgentStreamWorker(QThread):
    """LangGraph 실시간 토큰 스트리밍, 시간/토큰 수 측정 스레드"""

    token_chunk = Signal(str)
    tool_started = Signal(str, str)
    tool_finished = Signal(str, str)
    stream_complete = Signal(str, float, int)
    error_occurred = Signal(str)

    def __init__(self, agent, query: str, thread_id: str):
        super().__init__()
        self.agent = agent
        self.query = query
        self.thread_id = thread_id

    def run(self):
        async def _stream():
            start_time = time.perf_counter()
            config = {"configurable": {"thread_id": self.thread_id}}
            inputs = {"messages": [("user", self.query)]}
            accumulated_content = ""
            chunk_count = 0

            async for mode, chunk in self.agent.astream(
                inputs, config=config, stream_mode=["messages", "updates"]
            ):
                if mode == "messages":
                    msg, metadata = chunk
                    if getattr(msg, "type", "") == "AIMessageChunk" and msg.content:
                        if isinstance(msg.content, str):
                            accumulated_content += msg.content
                            chunk_count += 1
                            self.token_chunk.emit(msg.content)

                elif mode == "updates":
                    if "agent" in chunk and "messages" in chunk["agent"]:
                        for m in chunk["agent"]["messages"]:
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                for tc in m.tool_calls:
                                    self.tool_started.emit(
                                        tc["name"],
                                        json.dumps(tc.get("args", {}), ensure_ascii=False, indent=2),
                                    )
                            elif m.content and not accumulated_content:
                                accumulated_content = str(m.content)

                    if "tools" in chunk and "messages" in chunk["tools"]:
                        for m in chunk["tools"]["messages"]:
                            t_name = getattr(m, "name", "Tool")
                            res_str = str(m.content)
                            self.tool_finished.emit(t_name, res_str)

            elapsed_sec = round(time.perf_counter() - start_time, 2)
            estimated_tokens = max(chunk_count, len(accumulated_content) // 3) if accumulated_content else 0

            self.stream_complete.emit(accumulated_content, elapsed_sec, estimated_tokens)

        try:
            asyncio.run(_stream())
        except Exception as e:
            self.error_occurred.emit(str(e))


class ContextCompressWorker(QThread):
    """최근 5개 대화 외 이전 대화들을 요약 압축하는 비동기 워커 스레드"""

    success = Signal(str)  # 요약된 텍스트
    failed = Signal(str)

    def __init__(self, old_messages: List[Dict[str, Any]]):
        super().__init__()
        self.old_messages = old_messages

    def run(self):
        async def _compress():
            app_cfg = load_app_config()
            llm = ChatOpenAI(
                base_url=app_cfg.get("BASE_URL", "http://192.168.45.146:1234/v1"),
                api_key="lm-studio",
                model=app_cfg.get("MODEL_NAME", "gemma"),
                temperature=0.1,
            )

            # 이전 대화 텍스트 조합
            dialogue_text = ""
            for m in self.old_messages:
                role = "사용자" if m.get("role") == "user" else "Assistant"
                content = m.get("content", "")
                dialogue_text += f"[{role}]: {content}\n\n"

            prompt = (
                "다음은 사용자와 AI 어시스턴트의 이전 대화 기록입니다.\n"
                "주요 맥락, 결정된 사항, 핵심 정보와 파일 작업 내역을 빠짐없이 간결하고 일목요연하게 한국어로 요약해 주세요.\n\n"
                f"[대화 기록]\n{dialogue_text}\n\n"
                "[핵심 요약]:"
            )

            res = await llm.ainvoke([HumanMessage(content=prompt)])
            return str(res.content).strip()

        try:
            summary = asyncio.run(_compress())
            self.success.emit(summary)
        except Exception as e:
            self.failed.emit(str(e))


# ==========================================
# 4. 커스텀 UI 위젯 컴포넌트
# ==========================================
def create_emoji_icon(emoji: str = "✨", size: int = 64) -> QIcon:
    """이모지 텍스트를 고화질 QIcon으로 렌더링하여 반환"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    font = QFont("Segoe UI Emoji", int(size * 0.7))
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)


def create_copy_button(get_text_func, tooltip: str = "메시지 복사") -> QPushButton:
    """조그만 복사 버튼 생성 헬퍼 함수"""
    btn = QPushButton("📋")
    btn.setToolTip(tooltip)
    btn.setFixedSize(24, 22)
    btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #A6ADC8;
            border: none;
            border-radius: 4px;
            font-size: 11px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: rgba(128, 128, 128, 0.2);
            color: #89B4FA;
        }
    """)

    def _copy():
        text_to_copy = get_text_func() if callable(get_text_func) else str(get_text_func)
        QApplication.clipboard().setText(text_to_copy)
        btn.setText("✓")
        btn.setStyleSheet("color: #A6E3A1; font-weight: bold; background-color: rgba(128, 128, 128, 0.25); border-radius: 4px;")
        QTimer.singleShot(1500, lambda: _reset_btn())

    def _reset_btn():
        btn.setText("📋")
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A6ADC8;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.2);
                color: #89B4FA;
            }
        """)

    btn.clicked.connect(_copy)
    return btn


class CodeBlockWidget(QFrame):
    """Pygments 구문 강조 및 원클릭 복사 버튼이 포함된 전체 너비 코드 블록 위젯"""

    def __init__(self, code: str, language: str = "python", parent=None):
        super().__init__(parent)
        self.code = code
        self.language = language or "text"

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setObjectName("codeBlock")
        self.setStyleSheet("""
            QFrame#codeBlock {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                margin: 4px 0px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        lang_label = QLabel(self.language.upper(), self)
        lang_label.setStyleSheet("color: #89B4FA; font-weight: bold; font-size: 11px;")
        top_bar.addWidget(lang_label)

        top_bar.addStretch()

        self.copy_btn = create_copy_button(lambda: self.code, tooltip="코드 복사")
        top_bar.addWidget(self.copy_btn)
        layout.addLayout(top_bar)

        self.code_view = QTextBrowser(self)
        self.code_view.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #CDD6F4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        self.code_view.setOpenExternalLinks(False)
        self.code_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.code_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        highlighted_html = self._get_highlighted_html(self.code, self.language)
        self.code_view.setHtml(highlighted_html)

        line_count = len(self.code.split("\n"))
        calculated_height = min(max(line_count * 18 + 20, 60), 420)
        self.code_view.setFixedHeight(calculated_height)

        layout.addWidget(self.code_view)

    def _get_highlighted_html(self, code: str, language: str) -> str:
        try:
            lexer = get_lexer_by_name(language.lower())
        except Exception:
            try:
                lexer = guess_lexer(code)
            except Exception:
                lexer = get_lexer_by_name("text")

        formatter = HtmlFormatter(style="monokai", nowrap=True)
        highlighted_code = pygments.highlight(code, lexer, formatter)

        html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Consolas, monospace; font-size: 12px; line-height: 1.4; color: #CDD6F4; margin: 0; padding: 0; }}
            pre {{ margin: 0; white-space: pre-wrap; word-break: break-all; }}
            .c {{ color: #75715e; }}
            .k {{ color: #66d9ef; font-weight: bold; }}
            .s {{ color: #e6db74; }}
            .nf {{ color: #a6e3a1; font-weight: bold; }}
            .nc {{ color: #a6e3a1; font-weight: bold; }}
            .nb {{ color: #89b4fa; }}
            .mi {{ color: #ae81ff; }}
            .o {{ color: #f38ba8; }}
        </style>
        </head>
        <body>
        <pre>{highlighted_code}</pre>
        </body>
        </html>
        """
        return html


class ToolAccordionWidget(QFrame):
    """화면 폭을 넘치지 않고 내부 스크롤을 지원하는 접이식 아코디언 도구 카드"""

    def __init__(self, tool_name: str, args_text: str = "", is_light: bool = False, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.args_text = args_text
        self.result_text = ""
        self.is_expanded = False
        self.is_light = is_light

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setObjectName("toolAccordion")
        self._apply_running_style()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 8)
        self.main_layout.setSpacing(6)

        header_layout = QHBoxLayout()

        self.icon_label = QLabel("⚡", self)
        self.icon_label.setStyleSheet("font-size: 13px;")
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(f"도구 실행 중: <b>{self.tool_name}</b>", self)
        if self.is_light:
            self.title_label.setStyleSheet("color: #B45309; font-size: 12px;")
        else:
            self.title_label.setStyleSheet("color: #F9E2AF; font-size: 12px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.toggle_btn = QPushButton("펼치기 ▼", self)
        self._update_btn_style(completed=False)
        self.toggle_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.toggle_btn)

        self.main_layout.addLayout(header_layout)

        self.details_widget = QWidget(self)
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(6)

        args_title = QLabel("<b>[호출 인자]</b>", self.details_widget)
        args_title.setStyleSheet("color: #64748B; font-size: 11px;" if self.is_light else "color: #BAC2DE; font-size: 11px;")
        details_layout.addWidget(args_title)

        self.args_browser = QTextBrowser(self.details_widget)
        if self.is_light:
            self.args_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        else:
            self.args_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #181825;
                    color: #BAC2DE;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        self.args_browser.setPlainText(self.args_text)
        self.args_browser.setMaximumHeight(100)
        details_layout.addWidget(self.args_browser)

        res_title = QLabel("<b>[실행 결과]</b>", self.details_widget)
        res_title.setStyleSheet("color: #64748B; font-size: 11px;" if self.is_light else "color: #CBA6F7; font-size: 11px;")
        details_layout.addWidget(res_title)

        self.result_browser = QTextBrowser(self.details_widget)
        if self.is_light:
            self.result_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #F8FAFC;
                    color: #1E293B;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        else:
            self.result_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #181825;
                    color: #CDD6F4;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        self.result_browser.setPlainText("대기 중...")
        self.result_browser.setMaximumHeight(180)
        details_layout.addWidget(self.result_browser)

        self.details_widget.setVisible(False)
        self.main_layout.addWidget(self.details_widget)

    def _apply_running_style(self):
        if self.is_light:
            self.setStyleSheet("""
                QFrame#toolAccordion {
                    background-color: #F8F9FA;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    margin: 4px 0px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#toolAccordion {
                    background-color: rgba(30, 30, 46, 0.7);
                    border: 1px solid #F9E2AF;
                    border-radius: 8px;
                    margin: 4px 0px;
                }
            """)

    def _update_btn_style(self, completed: bool = False):
        if self.is_light:
            if completed:
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E2E8F0;
                        color: #334155;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: #CBD5E1;
                    }
                """)
            else:
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EDE9FE;
                        color: #6D28D9;
                        border: 1px solid #DDD6FE;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: #DDD6FE;
                    }
                """)
        else:
            color_val = "#A6E3A1" if completed else "#F9E2AF"
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #313244;
                    color: {color_val};
                    border: none;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: #45475A;
                }}
            """)

    def set_result(self, result_text: str):
        self.result_text = result_text
        self.icon_label.setText("📦")
        self.title_label.setText(f"도구 완료: <b>{self.tool_name}</b>")
        if self.is_light:
            self.title_label.setStyleSheet("color: #2D3748; font-size: 12px;")
            self.setStyleSheet("""
                QFrame#toolAccordion {
                    background-color: #F1F5F2;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    margin: 4px 0px;
                }
            """)
            self.result_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #F8FAFC;
                    color: #1E293B;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        else:
            self.title_label.setStyleSheet("color: #A6E3A1; font-size: 12px;")
            self.setStyleSheet("""
                QFrame#toolAccordion {
                    background-color: rgba(30, 30, 46, 0.7);
                    border: 1px solid #A6E3A1;
                    border-radius: 8px;
                    margin: 4px 0px;
                }
            """)
        self._update_btn_style(completed=True)
        self.result_browser.setPlainText(result_text)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.details_widget.setVisible(self.is_expanded)
        self.toggle_btn.setText("접기 ▲" if self.is_expanded else "펼치기 ▼")


class ConversationItemWidget(QFrame):
    """사이드바 대화방 아이템 위젯: | 💬 대화방 제목 [✏️ 편집] [🗑️ 삭제] |"""

    clicked = Signal(str)
    renamed = Signal(str, str)
    deleted = Signal(str)

    def __init__(self, title: str, is_active: bool = False, is_light: bool = False, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_active = is_active
        self.is_light = is_light

        self.setObjectName("convItem")
        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(6)

        self.title_btn = QPushButton(f"💬 {self.title}", self)
        title_color = "#212529" if self.is_light else "#FFFFFF"
        self.title_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {title_color};
                font-size: 13px;
                text-align: left;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: #0D6EFD;
            }}
        """)
        self.title_btn.clicked.connect(lambda: self.clicked.emit(self.title))
        layout.addWidget(self.title_btn, 1)

        self.edit_btn = QPushButton("✏️", self)
        self.edit_btn.setToolTip("대화방 제목 변경")
        self.edit_btn.setFixedSize(26, 26)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.15);
            }
        """)
        self.edit_btn.clicked.connect(self._on_edit_click)
        layout.addWidget(self.edit_btn)

        self.del_btn = QPushButton("🗑️", self)
        self.del_btn.setToolTip("대화방 삭제")
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F38BA8;
                color: #11111B;
            }
        """)
        self.del_btn.clicked.connect(self._on_delete_click)
        layout.addWidget(self.del_btn)

    def set_active(self, active: bool):
        self.is_active = active
        self._update_style()

    def _update_style(self):
        if self.is_active:
            accent_bg = "rgba(13, 110, 253, 0.15)" if self.is_light else "rgba(137, 180, 250, 0.18)"
            accent_border = "#0D6EFD" if self.is_light else "#89B4FA"
            self.setStyleSheet(f"""
                QFrame#convItem {{
                    background-color: {accent_bg};
                    border: 1px solid {accent_border};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame#convItem {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                }
                QFrame#convItem:hover {
                    background-color: rgba(128, 128, 128, 0.08);
                }
            """)

    def _on_edit_click(self):
        new_name, ok = QInputDialog.getText(
            self, "대화방 제목 변경", "새 대화방 제목을 입력하세요:", text=self.title
        )
        if ok and new_name.strip() and new_name.strip() != self.title:
            self.renamed.emit(self.title, new_name.strip())

    def _on_delete_click(self):
        reply = QMessageBox.question(
            self,
            "대화방 삭제",
            f"'{self.title}' 대화방을 삭제하시겠습니까?\n(파일이 완전히 제거됩니다)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.deleted.emit(self.title)


class ChatInputEdit(QTextEdit):
    """Enter로 전송, Shift+Enter로 줄바꿈을 지원하는 텍스트 입력창"""

    send_triggered = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                event.accept()
                self.send_triggered.emit()
        else:
            super().keyPressEvent(event)


# ==========================================
# 5. Temperature 설정 다이얼로그 (슬라이더 및 실시간 수치 표시)
# ==========================================
class TemperatureDialog(QDialog):
    """슬라이더(0.0 ~ 2.0, 0.1 단위) 조작 기반 Temperature 설정 모달"""

    applied = Signal(float)

    def __init__(self, current_temp: float, is_light: bool = False, parent=None):
        super().__init__(parent)
        self.current_val = current_temp
        self.is_light = is_light
        self.setWindowTitle("🌡️ Temperature (온도) 설정")
        self.resize(480, 340)

        if self.is_light:
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    color: #212529;
                }
                QLabel {
                    color: #212529;
                }
                QSlider::groove:horizontal {
                    height: 8px;
                    background: #E2E8F0;
                    border-radius: 4px;
                }
                QSlider::sub-page:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #FFFFFF;
                    border: 2px solid #3B82F6;
                    width: 16px;
                    margin-top: -5px;
                    margin-bottom: -5px;
                    border-radius: 9px;
                }
                QPushButton {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
                QPushButton#applyBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                }
                QPushButton#applyBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8);
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                }
                QLabel {
                    color: #CDD6F4;
                }
                QSlider::groove:horizontal {
                    height: 8px;
                    background: #313244;
                    border-radius: 4px;
                }
                QSlider::sub-page:horizontal {
                    background: #89B4FA;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #FFFFFF;
                    width: 16px;
                    margin-top: -4px;
                    margin-bottom: -4px;
                    border-radius: 8px;
                }
                QPushButton {
                    background-color: #313244;
                    color: #CDD6F4;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45475A;
                }
                QPushButton#applyBtn {
                    background-color: #89B4FA;
                    color: #11111B;
                    font-weight: bold;
                }
                QPushButton#applyBtn:hover {
                    background-color: #B4BEFE;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title_lbl = QLabel("<b>🌡️ Temperature (온도) 설정</b>", self)
        title_color = "#1D4ED8" if self.is_light else "#89B4FA"
        title_lbl.setStyleSheet(f"font-size: 15px; color: {title_color};")
        layout.addWidget(title_lbl)

        slider_card = QFrame(self)
        if self.is_light:
            slider_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        else:
            slider_card.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 10px;")
        s_layout = QVBoxLayout(slider_card)
        s_layout.setSpacing(8)

        val_color = "#1D4ED8" if self.is_light else "#89B4FA"
        self.val_label = QLabel(f"현재 설정 값: <b style='color:{val_color}; font-size:15px;'>{self.current_val:.1f}</b>", slider_card)
        self.val_label.setTextFormat(Qt.RichText)
        s_layout.addWidget(self.val_label)

        self.slider = QSlider(Qt.Horizontal, slider_card)
        self.slider.setRange(0, 20)
        self.slider.setValue(int(round(self.current_val * 10)))
        self.slider.valueChanged.connect(self._on_slider_moved)
        s_layout.addWidget(self.slider)

        sub_color = "#64748B" if self.is_light else "#6C7086"
        range_lbl = QLabel(f"<span style='color:{sub_color}; font-size:10px;'>0.0 (최소/엄격)</span> <span style='float:right; color:{sub_color}; font-size:10px;'>2.0 (최대/창의적)</span>", slider_card)
        range_lbl.setTextFormat(Qt.RichText)
        s_layout.addWidget(range_lbl)

        layout.addWidget(slider_card)

        desc_card = QFrame(self)
        if self.is_light:
            desc_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px;")
        else:
            desc_card.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 8px;")
        d_layout = QVBoxLayout(desc_card)
        d_layout.setSpacing(6)

        d_title = QLabel("💡 <b>Temperature 값 가이드:</b>", desc_card)
        d_title.setStyleSheet("color: #B45309; font-size: 12px;" if self.is_light else "color: #F9E2AF; font-size: 12px;")
        d_layout.addWidget(d_title)

        c1 = "#15803D" if self.is_light else "#A6E3A1"
        c2 = "#1D4ED8" if self.is_light else "#89B4FA"
        c3 = "#DC2626" if self.is_light else "#F38BA8"
        guide_text = f"""
        • <b style='color:{c1};'>0.0 ~ 0.3 (권장)</b>: 일관성 높고 정확한 코딩, 파일 시스템 작업, 사실 기반 답변<br>
        • <b style='color:{c2};'>0.4 ~ 0.7</b>: 일반적인 대화 및 균형 잡힌 응답<br>
        • <b style='color:{c3};'>0.8 ~ 2.0</b>: 창의적이고 다양한 아이디어 생성 (환각 가능성 증가)
        """
        guide_lbl = QLabel(guide_text.strip(), desc_card)
        guide_lbl.setTextFormat(Qt.RichText)
        guide_lbl.setStyleSheet("font-size: 11px; line-height: 1.4; color: #334155;" if self.is_light else "font-size: 11px; line-height: 1.4; color: #BAC2DE;")
        d_layout.addWidget(guide_lbl)

        layout.addWidget(desc_card)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        apply_btn = QPushButton("적용", self)
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._on_apply)
        btn_box.addWidget(apply_btn)

        layout.addLayout(btn_box)

    def _on_slider_moved(self, val: int):
        self.current_val = round(val / 10.0, 1)
        val_color = "#1D4ED8" if self.is_light else "#89B4FA"
        self.val_label.setText(f"현재 설정 값: <b style='color:{val_color}; font-size:15px;'>{self.current_val:.1f}</b>")

    def _on_apply(self):
        self.applied.emit(self.current_val)
        self.accept()


# ==========================================
# 6. 시스템 프롬프트 설정 다이얼로그
# ==========================================
class SystemPromptDialog(QDialog):
    """대화방별 시스템 프롬프트(지침/페르소나) 설정 모달"""

    applied = Signal(str)

    def __init__(self, current_prompt: str, default_prompt: str = "당신은 유능하고 친절한 AI 어시스턴트입니다.", is_light: bool = False, parent=None):
        super().__init__(parent)
        self.current_prompt = current_prompt
        self.default_prompt = default_prompt
        self.is_light = is_light
        self.setWindowTitle("⚙️ 시스템 프롬프트 설정")
        self.resize(540, 380)

        if self.is_light:
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    color: #212529;
                }
                QLabel {
                    color: #212529;
                }
                QTextEdit {
                    background-color: #F8FAFC;
                    color: #212529;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 13px;
                    line-height: 1.4;
                }
                QTextEdit:focus {
                    border: 1px solid #3B82F6;
                }
                QPushButton {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
                QPushButton#applyBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                }
                QPushButton#applyBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8);
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                }
                QLabel {
                    color: #CDD6F4;
                }
                QTextEdit {
                    background-color: #181825;
                    color: #CDD6F4;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 13px;
                    line-height: 1.4;
                }
                QTextEdit:focus {
                    border: 1px solid #89B4FA;
                }
                QPushButton {
                    background-color: #313244;
                    color: #CDD6F4;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45475A;
                }
                QPushButton#applyBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                }
                QPushButton#applyBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8);
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_lbl = QLabel("<b>⚙️ 현재 대화방의 시스템 프롬프트 (지침/역할)</b>", self)
        title_color = "#1D4ED8" if self.is_light else "#89B4FA"
        title_lbl.setStyleSheet(f"font-size: 14px; color: {title_color};")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("AI에게 부여할 기본 역할, 답변 스타일 및 업무 지침을 자유롭게 작성하세요.", self)
        desc_color = "#64748B" if self.is_light else "#A6ADC8"
        desc_lbl.setStyleSheet(f"font-size: 11px; color: {desc_color};")
        layout.addWidget(desc_lbl)

        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(self.current_prompt)
        layout.addWidget(self.text_edit, 1)

        btn_box = QHBoxLayout()
        reset_btn = QPushButton("🔄 기본값 복원", self)
        reset_btn.clicked.connect(self._on_reset)
        btn_box.addWidget(reset_btn)

        btn_box.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        apply_btn = QPushButton("적용", self)
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._on_apply)
        btn_box.addWidget(apply_btn)

        layout.addLayout(btn_box)

    def _on_reset(self):
        self.text_edit.setPlainText(self.default_prompt)

    def _on_apply(self):
        val = self.text_edit.toPlainText().strip()
        self.applied.emit(val)
        self.accept()


# ==========================================
# 7. MCP 서버 설정 다이얼로그 (tools 드롭다운 지원)
# ==========================================
class MCPServerCard(QFrame):
    """서버별 이름, 활성화 체크박스 및 tools 목록 드롭다운 아코디언 카드"""

    def __init__(self, server_name: str, server_info: dict, is_checked: bool, tools_map: dict, is_light: bool = False, parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.server_info = server_info
        self.tools_map = tools_map
        self.is_light = is_light
        self.is_tools_expanded = False

        if self.is_light:
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #24273A;
                    border: 1px solid #313244;
                    border-radius: 6px;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.checkbox = QCheckBox(f"<b>{self.server_name}</b>", self)
        self.checkbox.setChecked(is_checked)
        self.checkbox.setStyleSheet("color: #212529; font-size: 13px;" if self.is_light else "color: #CDD6F4; font-size: 13px;")
        top_row.addWidget(self.checkbox)

        top_row.addStretch()

        self.tools_btn = QPushButton("🛠️ 도구 목록 ▼", self)
        if self.is_light:
            self.tools_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #1D4ED8;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
            """)
        else:
            self.tools_btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #89B4FA;
                    border: none;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #45475A;
                }
            """)
        self.tools_btn.clicked.connect(self._toggle_tools)
        top_row.addWidget(self.tools_btn)

        layout.addLayout(top_row)

        s_type = str(self.server_info.get("type", "stdio")).lower()
        if s_type in ("http", "sse", "streamable_http") or "url" in self.server_info:
            info_str = f"Type: {s_type.upper()} | URL: {self.server_info.get('url', '')}"
        else:
            cmd = self.server_info.get('command', 'python')
            args_str = ' '.join(self.server_info.get('args', []))
            info_str = f"Type: STDIO | Command: {cmd} {args_str}".strip()

        info_color = "#64748B" if self.is_light else "#6C7086"
        cmd_lbl = QLabel(f"<span style='color:{info_color}; font-size:11px;'>{info_str}</span>", self)
        cmd_lbl.setTextFormat(Qt.RichText)
        layout.addWidget(cmd_lbl)

        self.tools_container = QWidget(self)
        t_layout = QVBoxLayout(self.tools_container)
        t_layout.setContentsMargins(0, 4, 0, 0)
        t_layout.setSpacing(4)

        self.tools_browser = QTextBrowser(self.tools_container)
        if self.is_light:
            self.tools_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #F8FAFC;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        else:
            self.tools_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #181825;
                    color: #A6ADC8;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    font-size: 11px;
                    padding: 6px;
                }
            """)
        self.tools_browser.setMaximumHeight(140)

        tools_text = ""
        if self.tools_map:
            for t_name, t_desc in self.tools_map.items():
                tools_text += f"• {t_name}\n  - {t_desc}\n\n"
        else:
            tools_text = "이 서버를 활성화하고 적용하면 로드된 도구 목록이 여기에 표시됩니다."

        self.tools_browser.setPlainText(tools_text.strip())
        t_layout.addWidget(self.tools_browser)

        self.tools_container.setVisible(False)
        layout.addWidget(self.tools_container)

    def _toggle_tools(self):
        self.is_tools_expanded = not self.is_tools_expanded
        self.tools_container.setVisible(self.is_tools_expanded)
        self.tools_btn.setText("🛠️ 도구 목록 ▲" if self.is_tools_expanded else "🛠️ 도구 목록 ▼")


class MCPSettingsDialog(QDialog):
    """동적 MCP 서버 설정 및 도구 목록 조회 모달"""

    applied = Signal(set)

    def __init__(self, current_enabled_servers: Set[str], tools_map: dict, is_light: bool = False, parent=None):
        super().__init__(parent)
        self.current_enabled = current_enabled_servers
        self.tools_map = tools_map
        self.is_light = is_light
        self.setWindowTitle("⚙️ FastMCP 서버 설정")
        self.resize(560, 420)

        if self.is_light:
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    color: #212529;
                }
                QLabel {
                    color: #212529;
                }
                QPushButton {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
                QPushButton#applyBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                }
                QPushButton#applyBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8);
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                }
                QLabel {
                    color: #CDD6F4;
                }
                QPushButton {
                    background-color: #313244;
                    color: #CDD6F4;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45475A;
                }
                QPushButton#applyBtn {
                    background-color: #89B4FA;
                    color: #11111B;
                    font-weight: bold;
                }
                QPushButton#applyBtn:hover {
                    background-color: #B4BEFE;
                }
            """)

        self.config_data = load_mcp_config()
        self.server_cards: Dict[str, MCPServerCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_lbl = QLabel("<b>활성화할 MCP 서버 선택 및 도구 목록:</b>", self)
        title_color = "#1D4ED8" if self.is_light else "#89B4FA"
        title_lbl.setStyleSheet(f"font-size: 14px; color: {title_color};")
        layout.addWidget(title_lbl)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        if self.is_light:
            scroll.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px;")
        else:
            scroll.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 6px;")

        server_container = QWidget()
        server_layout = QVBoxLayout(server_container)
        server_layout.setContentsMargins(12, 12, 12, 12)
        server_layout.setSpacing(10)

        if not self.config_data:
            server_layout.addWidget(QLabel("등록된 MCP 서버가 없습니다.", server_container))
        else:
            for s_name, s_info in self.config_data.items():
                if isinstance(s_info, dict):
                    is_chk = s_name in self.current_enabled
                    card = MCPServerCard(s_name, s_info, is_chk, self.tools_map, is_light=self.is_light, parent=server_container)
                    self.server_cards[s_name] = card
                    server_layout.addWidget(card)

        server_layout.addStretch()
        scroll.setWidget(server_container)
        layout.addWidget(scroll, 1)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        apply_btn = QPushButton("적용 및 재연결", self)
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._on_apply)
        btn_box.addWidget(apply_btn)

        layout.addLayout(btn_box)

    def _on_apply(self):
        new_enabled = set()
        for s_name, card in self.server_cards.items():
            if card.checkbox.isChecked():
                new_enabled.add(s_name)

        save_mcp_config(self.config_data)
        self.applied.emit(new_enabled)
        self.accept()


# ==========================================
# 7. 컨텍스트 압축 로딩 프로그레스 모달
# ==========================================
class CompressProgressDialog(QDialog):
    """컨텍스트 압축 중 사용자 입력을 차단하고 회전/진행 상태를 보여주는 모달"""

    def __init__(self, is_light: bool = False, parent=None):
        super().__init__(parent)
        self.is_light = is_light
        self.setWindowTitle("🗜️ 컨텍스트 압축 중...")
        self.setFixedSize(380, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        self.setModal(True)

        if self.is_light:
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    color: #212529;
                    border: 1px solid #CBD5E1;
                    border-radius: 10px;
                }
                QLabel {
                    color: #212529;
                }
                QProgressBar {
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    background-color: #F1F5F9;
                    height: 12px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    border-radius: 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                    border: 1px solid #313244;
                    border-radius: 10px;
                }
                QLabel {
                    color: #CDD6F4;
                }
                QProgressBar {
                    border: 1px solid #313244;
                    border-radius: 6px;
                    background-color: #181825;
                    height: 12px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                    border-radius: 5px;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_lbl = QLabel("<b>🧠 이전 대화를 요약 압축하고 있습니다...</b>", self)
        title_color = "#1D4ED8" if self.is_light else "#89B4FA"
        title_lbl.setStyleSheet(f"color: {title_color}; font-size: 13px;")
        layout.addWidget(title_lbl)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        desc_lbl = QLabel("LLM이 주요 맥락을 추출 중입니다. 잠시만 기다려 주세요.", self)
        desc_color = "#64748B" if self.is_light else "#A6ADC8"
        desc_lbl.setStyleSheet(f"color: {desc_color}; font-size: 11px;")
        layout.addWidget(desc_lbl)


# ==========================================
# 8. 메인 애플리케이션 윈도우
# ==========================================
class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.app_config = load_app_config()
        self.temperature = float(self.app_config.get("TEMPERATURE", 0.0))
        self.current_theme = self.app_config.get("THEME", "dark")
        self.active_mcp_servers: Set[str] = set()

        self.setWindowTitle(f"LangGraph & FastMCP Assistant ({self.app_config.get('MODEL_NAME', 'gemma')})")
        self.setWindowIcon(create_emoji_icon("✨"))
        self.resize(1020, 800)
        self.setMinimumSize(720, 560)
        self.move(40, 40)  # 화면 좌측 상단 위치 설정

        self.current_title = "새 대화"
        self.current_data = ConversationManager.load_conversation(self.current_title)
        self.agent = None
        self.tools = []
        self.server_tools_map = {}
        self.is_busy = False

        self.init_worker = None
        self.stream_worker = None
        self.compress_worker = None
        self.current_ai_bubble = None
        self.current_tool_card = None
        self.current_ai_raw_text = ""
        self.sidebar_visible = True
        self.sidebar_width = 260

        self._apply_global_style()
        self._create_layout()

        self._refresh_conversation_list()
        self._load_session_to_ui(self.current_title)

        # 백그라운드 에이전트 초기화
        self._init_agent()

    def _apply_global_style(self):
        """다크 / 라이트 모드 스타일시트 적용"""
        btn_gradient = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1); color: #FFFFFF; font-weight: bold; border: none; border-radius: 8px;"
        btn_hover_gradient = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8); color: #FFFFFF;"

        if self.current_theme == "light":
            # 라이트 테마 (모던 & 클린)
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: #F8F9FA;
                    color: #212529;
                    font-family: 'Segoe UI', 'Pretendard', sans-serif;
                }}
                QFrame#sidebarFrame {{
                    background-color: #E9ECEF;
                    border-right: 1px solid #DEE2E6;
                }}
                QFrame#headerBar {{
                    background-color: #E9ECEF;
                    border-bottom: 1px solid #DEE2E6;
                }}
                QFrame#headerBar QLabel {{
                    background-color: transparent;
                }}
                QScrollArea {{
                    background-color: #F8F9FA;
                    border: none;
                }}
                QWidget#chatContent {{
                    background-color: #F8F9FA;
                }}
                QPushButton#newChatBtn {{
                    {btn_gradient}
                    padding: 10px;
                    font-size: 13px;
                }}
                QPushButton#newChatBtn:hover {{
                    {btn_hover_gradient}
                }}
                QPushButton#tempBtn, QPushButton#themeBtn, QPushButton#mcpSettingsBtn {{
                    background-color: #FFFFFF;
                    color: #212529;
                    border: 1px solid #CED4DA;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton#tempBtn:hover, QPushButton#themeBtn:hover, QPushButton#mcpSettingsBtn:hover {{
                    background-color: #E2E6EA;
                    color: #0D6EFD;
                }}
                QPushButton#headerActionBtn {{
                    background-color: #FFFFFF;
                    color: #212529;
                    border: 1px solid #CED4DA;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton#headerActionBtn:hover {{
                    background-color: #E2E6EA;
                    color: #0D6EFD;
                }}
                QPushButton#hamburgerBtn {{
                    background-color: transparent;
                    border: none;
                    color: #212529;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                QPushButton#hamburgerBtn:hover {{
                    background-color: #DEE2E6;
                }}
                QTextEdit#chatInput {{
                    background-color: #FFFFFF;
                    color: #212529;
                    border: 1px solid #CED4DA;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 13px;
                }}
                QTextEdit#chatInput:focus {{
                    border: 1px solid #0D6EFD;
                }}
                QPushButton#sendBtn {{
                    {btn_gradient}
                    font-size: 14px;
                    padding: 0px 16px;
                }}
                QPushButton#sendBtn:hover {{
                    {btn_hover_gradient}
                }}
                QPushButton#sendBtn:disabled {{
                    background: #CED4DA;
                    color: #6C757D;
                }}
                QScrollBar:vertical {{
                    background: #F8F9FA;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: #CED4DA;
                    min-height: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: #ADB5BD;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)
        else:
            # 다크 테마 (Catppuccin Macchiato + 모던 액센트)
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                    font-family: 'Segoe UI', 'Pretendard', sans-serif;
                }}
                QFrame#sidebarFrame {{
                    background-color: #181825;
                    border-right: 1px solid #313244;
                }}
                QFrame#headerBar {{
                    background-color: #181825;
                    border-bottom: 1px solid #313244;
                }}
                QFrame#headerBar QLabel {{
                    background-color: transparent;
                }}
                QScrollArea {{
                    background-color: #1E1E2E;
                    border: none;
                }}
                QWidget#chatContent {{
                    background-color: #1E1E2E;
                }}
                QPushButton#newChatBtn {{
                    {btn_gradient}
                    padding: 10px;
                    font-size: 13px;
                }}
                QPushButton#newChatBtn:hover {{
                    {btn_hover_gradient}
                }}
                QPushButton#tempBtn, QPushButton#themeBtn, QPushButton#mcpSettingsBtn {{
                    background-color: #24273A;
                    color: #CDD6F4;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton#tempBtn:hover, QPushButton#themeBtn:hover, QPushButton#mcpSettingsBtn:hover {{
                    background-color: #313244;
                    color: #89B4FA;
                }}
                QPushButton#headerActionBtn {{
                    background-color: #24273A;
                    color: #CDD6F4;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton#headerActionBtn:hover {{
                    background-color: #313244;
                    color: #89B4FA;
                }}
                QPushButton#hamburgerBtn {{
                    background-color: transparent;
                    border: none;
                    color: #FFFFFF;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                QPushButton#hamburgerBtn:hover {{
                    background-color: #313244;
                }}
                QTextEdit#chatInput {{
                    background-color: #181825;
                    color: #FFFFFF;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 13px;
                }}
                QTextEdit#chatInput:focus {{
                    border: 1px solid #3B82F6;
                }}
                QPushButton#sendBtn {{
                    {btn_gradient}
                    font-size: 14px;
                    padding: 0px 16px;
                }}
                QPushButton#sendBtn:hover {{
                    {btn_hover_gradient}
                }}
                QPushButton#sendBtn:disabled {{
                    background: #313244;
                    color: #6C7086;
                }}
                QScrollBar:vertical {{
                    background: #181825;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: #45475A;
                    min-height: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: #585B70;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)

    def _create_layout(self):
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 1. 좌측 사이드바
        self.sidebar_frame = QFrame(self)
        self.sidebar_frame.setObjectName("sidebarFrame")
        self.sidebar_frame.setFixedWidth(self.sidebar_width)
        self.sidebar_frame.setMinimumWidth(0)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        # 블루-인디고 그라데이션 및 굵은 흰색 글씨 공통 스타일
        grad_btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #818CF8);
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background: #4B5563;
                color: #9CA3AF;
            }
        """

        # [+ 새 대화] 버튼
        self.new_chat_btn = QPushButton("✨ + 새 대화", self.sidebar_frame)
        self.new_chat_btn.setObjectName("newChatBtn")
        self.new_chat_btn.setStyleSheet(grad_btn_style)
        self.new_chat_btn.clicked.connect(self._create_new_conversation)
        sidebar_layout.addWidget(self.new_chat_btn)

        sidebar_title = QLabel("대화 기록", self.sidebar_frame)
        sidebar_title.setStyleSheet("color: #A6ADC8; font-size: 11px; font-weight: bold; margin-top: 4px;")
        sidebar_layout.addWidget(sidebar_title)

        self.conv_scroll = QScrollArea(self.sidebar_frame)
        self.conv_scroll.setWidgetResizable(True)
        self.conv_container = QWidget()
        self.conv_layout = QVBoxLayout(self.conv_container)
        self.conv_layout.setContentsMargins(0, 0, 0, 0)
        self.conv_layout.setSpacing(4)
        self.conv_layout.addStretch()
        self.conv_scroll.setWidget(self.conv_container)
        sidebar_layout.addWidget(self.conv_scroll, 1)

        # 사이드바 하단 버튼들
        bottom_ctrl_frame = QFrame(self.sidebar_frame)
        bottom_ctrl_frame.setStyleSheet("background-color: transparent; border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 4px;")
        b_layout = QVBoxLayout(bottom_ctrl_frame)
        b_layout.setContentsMargins(2, 2, 2, 2)
        b_layout.setSpacing(6)

        # [🌡️ Temperature 설정] 버튼
        self.temp_btn = QPushButton(f"🌡️ Temperature: {self.temperature:.1f}", bottom_ctrl_frame)
        self.temp_btn.setObjectName("tempBtn")
        self.temp_btn.setToolTip("클릭하여 Temperature(온도) 슬라이더 조절")
        self.temp_btn.clicked.connect(self._open_temperature_dialog)
        b_layout.addWidget(self.temp_btn)

        # [⚙️ MCP 서버 설정] 버튼
        self.mcp_settings_btn = QPushButton("⚙️ MCP 서버 설정", bottom_ctrl_frame)
        self.mcp_settings_btn.setObjectName("mcpSettingsBtn")
        self.mcp_settings_btn.clicked.connect(self._open_mcp_settings)
        b_layout.addWidget(self.mcp_settings_btn)

        # [🌓 모드 변경] 버튼
        self.theme_btn = QPushButton("🌓 모드 변경", bottom_ctrl_frame)
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setToolTip("다크 모드 / 라이트 모드 전환")
        self.theme_btn.clicked.connect(self._toggle_theme)
        b_layout.addWidget(self.theme_btn)

        sidebar_layout.addWidget(bottom_ctrl_frame)

        main_h_layout.addWidget(self.sidebar_frame)

        # 2. 우측 메인 영역
        self.main_content_widget = QWidget(self)
        main_v_layout = QVBoxLayout(self.main_content_widget)
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)

        # 상단 헤더 바
        self.header_bar = QFrame(self.main_content_widget)
        self.header_bar.setObjectName("headerBar")
        self.header_bar.setFixedHeight(50)
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(12, 0, 16, 0)
        header_layout.setSpacing(8)

        # 햄버거 버튼
        self.hamburger_btn = QPushButton("☰", self.header_bar)
        self.hamburger_btn.setObjectName("hamburgerBtn")
        self.hamburger_btn.setToolTip("사이드바 토글 (애니메이션)")
        self.hamburger_btn.clicked.connect(self._toggle_sidebar_animation)
        header_layout.addWidget(self.hamburger_btn)

        # 대화방 제목 라벨 (테마별 색상)
        self.title_label = QLabel(self.current_title, self.header_bar)
        self.title_label.setObjectName("headerTitle")
        title_c = "#212529" if self.current_theme == "light" else "#FFFFFF"
        self.title_label.setStyleSheet(f"background-color: transparent; color: {title_c}; font-size: 14px; font-weight: bold; margin-left: 4px;")
        header_layout.addWidget(self.title_label)

        # [⚙️ 프롬프트] 버튼 (대화방 제목과 지우기 사이)
        self.prompt_btn = QPushButton("⚙️ 프롬프트", self.header_bar)
        self.prompt_btn.setObjectName("headerActionBtn")
        self.prompt_btn.setToolTip("현재 대화방의 시스템 프롬프트(AI 역할/지침)를 설정합니다")
        self.prompt_btn.clicked.connect(self._open_system_prompt_dialog)
        header_layout.addWidget(self.prompt_btn)

        # [🧹 지우기] 버튼
        self.clear_btn = QPushButton("🧹 지우기", self.header_bar)
        self.clear_btn.setObjectName("headerActionBtn")
        self.clear_btn.setToolTip("현재 대화방의 모든 메시지 내역을 비웁니다")
        self.clear_btn.clicked.connect(self._clear_current_conversation)
        header_layout.addWidget(self.clear_btn)

        # [🗜️ 컨텍스트 압축] 버튼
        self.compress_btn = QPushButton("🗜️ 컨텍스트 압축", self.header_bar)
        self.compress_btn.setObjectName("headerActionBtn")
        self.compress_btn.setToolTip("최근 5개 대화는 유지하고, 이전 대화들을 LLM으로 요약 압축합니다")
        self.compress_btn.clicked.connect(self._compress_context)
        header_layout.addWidget(self.compress_btn)

        header_layout.addStretch()

        # 상태 라벨
        self.status_label = QLabel("⏳ 서버 초기화 중...", self.header_bar)
        self.status_label.setObjectName("statusLabel")
        status_c = "#475569" if self.current_theme == "light" else "#BAC2DE"
        self.status_label.setStyleSheet(f"background-color: transparent; color: {status_c}; font-size: 12px;")
        header_layout.addWidget(self.status_label)

        main_v_layout.addWidget(self.header_bar)

        # 중앙 대화 스크롤 영역
        self.chat_scroll = QScrollArea(self.main_content_widget)
        self.chat_scroll.setWidgetResizable(True)
        self.chat_content = QWidget()
        self.chat_content.setObjectName("chatContent")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(24, 16, 24, 16)
        self.chat_layout.setSpacing(16)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_content)
        main_v_layout.addWidget(self.chat_scroll, 1)

        # 하단 메시지 입력 바
        input_container = QFrame(self.main_content_widget)
        input_container.setStyleSheet("background-color: transparent; border-top: 1px solid rgba(128,128,128,0.2); padding: 12px 24px;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(12)

        self.chat_input = ChatInputEdit(input_container)
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setFixedHeight(100)
        self.chat_input.setPlaceholderText("메시지를 입력하세요 (Enter: 전송, Shift+Enter: 줄바꿈)...")
        self.chat_input.send_triggered.connect(self._on_send_click)
        input_layout.addWidget(self.chat_input, 1)

        self.send_btn = QPushButton("전송", input_container)
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedSize(75, 100)
        self.send_btn.setStyleSheet(grad_btn_style)
        self.send_btn.clicked.connect(self._on_send_click)
        input_layout.addWidget(self.send_btn)

        main_v_layout.addWidget(input_container)
        main_h_layout.addWidget(self.main_content_widget, 1)

    # ==========================================
    # 8. 상단 헤더 기능 (지우기 & 컨텍스트 압축)
    # ==========================================
    def _clear_current_conversation(self):
        """현재 대화방의 모든 메시지 내역 비우기"""
        if self.is_busy:
            QMessageBox.warning(self, "알림", "에이전트가 응답 중일 때는 대화를 지울 수 없습니다.")
            return

        reply = QMessageBox.question(
            self,
            "대화 내용 지우기",
            f"'{self.current_title}' 대화방의 모든 메시지를 지우시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.current_data["messages"] = []
            ConversationManager.save_conversation(self.current_title, self.current_data)
            self._load_session_to_ui(self.current_title)

    def _compress_context(self):
        """최근 5개 대화는 보존하고 이전 대화들을 LLM으로 요약 압축"""
        if self.is_busy:
            QMessageBox.warning(self, "알림", "에이전트가 응답 중일 때는 압축할 수 없습니다.")
            return

        msgs = self.current_data.get("messages", [])
        if len(msgs) <= 5:
            QMessageBox.information(
                self,
                "컨텍스트 압축 알림",
                f"현재 대화 개수가 {len(msgs)}개입니다.\n(최근 5개 대화는 보존되므로 6개 이상일 때 압축 가능합니다)",
            )
            return

        old_msgs = msgs[:-5]
        recent_msgs = msgs[-5:]

        reply = QMessageBox.question(
            self,
            "컨텍스트 압축 확인",
            f"최근 5개 대화는 보존하고, 이전 {len(old_msgs)}개의 대화를 요약 압축하시겠습니까?\n(압축 후에는 요약본 카드로 대체됩니다)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        # 사용자 입력 차단 및 로딩 프로그레스 모달 표시
        self.is_busy = True
        self._set_status("🗜️ 이전 대화 요약 압축 중...", "tool")
        self.compress_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.chat_input.setEnabled(False)
        self.clear_btn.setEnabled(False)

        is_light = (self.current_theme == "light")
        progress_dialog = CompressProgressDialog(is_light=is_light, parent=self)
        progress_dialog.show()

        self.compress_worker = ContextCompressWorker(old_msgs)

        def _on_compress_success(summary_text: str):
            progress_dialog.accept()
            self.is_busy = False
            self.compress_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.chat_input.setEnabled(True)
            self.clear_btn.setEnabled(True)

            # 압축된 요약본을 첫 번째 메시지로 삽입하고 최근 5개 유지
            summary_msg = {
                "role": "assistant",
                "content": f"🗜️ **[이전 대화 핵심 요약]**\n\n{summary_text}",
            }
            self.current_data["messages"] = [summary_msg] + recent_msgs
            ConversationManager.save_conversation(self.current_title, self.current_data)

            mcp_status = f"{len(self.tools)}개 도구" if self.tools else "MCP 비활성"
            self._set_status(f"● 온라인 ({mcp_status} | {self.app_config.get('MODEL_NAME', 'gemma')} | T:{self.temperature:.1f})", "online")

            self._load_session_to_ui(self.current_title)
            QMessageBox.information(self, "압축 완료", f"이전 {len(old_msgs)}개의 대화가 성공적으로 압축 요약되었습니다!")

        def _on_compress_failed(error_msg: str):
            progress_dialog.reject()
            self.is_busy = False
            self.compress_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.chat_input.setEnabled(True)
            self.clear_btn.setEnabled(True)

            self._set_status("❌ 압축 실패", "offline")
            QMessageBox.warning(self, "오류", f"컨텍스트 압축 실패: {error_msg}")

        self.compress_worker.success.connect(_on_compress_success)
        self.compress_worker.failed.connect(_on_compress_failed)
        self.compress_worker.start()

    def _open_system_prompt_dialog(self):
        """현재 대화방의 시스템 프롬프트 설정 모달 열기"""
        curr = self.current_data.get("system_prompt", self.app_config.get("SYSTEM_PROMPT", "당신은 유능하고 친절한 AI 어시스턴트입니다."))
        default_p = self.app_config.get("SYSTEM_PROMPT", "당신은 유능하고 친절한 AI 어시스턴트입니다.")
        dialog = SystemPromptDialog(
            current_prompt=curr,
            default_prompt=default_p,
            is_light=(self.current_theme == "light"),
            parent=self,
        )
        dialog.applied.connect(self._on_system_prompt_applied)
        dialog.exec()

    def _on_system_prompt_applied(self, new_prompt: str):
        """시스템 프롬프트 저장 및 에이전트 즉시 재초기화"""
        self.current_data["system_prompt"] = new_prompt
        ConversationManager.save_conversation(self.current_title, self.current_data)
        self._init_agent()
        QMessageBox.information(self, "시스템 프롬프트 적용", "시스템 프롬프트가 이 대화방에 성공적으로 적용 및 반영되었습니다.")

    # ==========================================
    # 9. 테마 변경 핸들러
    # ==========================================
    def _toggle_theme(self):
        """다크 / 라이트 모드 상호 전환"""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.app_config["THEME"] = self.current_theme
        save_app_config(self.app_config)

        self.theme_btn.setText("🌓 모드 변경")
        self._apply_global_style()

        # 헤더 제목 색상 및 배경 투명 업데이트
        title_c = "#212529" if self.current_theme == "light" else "#FFFFFF"
        self.title_label.setStyleSheet(f"background-color: transparent; color: {title_c}; font-size: 14px; font-weight: bold; margin-left: 4px;")

        # 상태 라벨 텍스트 유지 및 테마 색상 갱신
        mcp_status = f"{len(self.tools)}개 도구" if self.tools else "MCP 비활성"
        self._set_status(f"● 온라인 ({mcp_status} | {self.app_config.get('MODEL_NAME', 'gemma')} | T:{self.temperature:.1f})", "online")

        self._refresh_conversation_list()
        self._load_session_to_ui(self.current_title)

    # ==========================================
    # 10. Temperature 설정 모달 열기
    # ==========================================
    def _open_temperature_dialog(self):
        dialog = TemperatureDialog(self.temperature, is_light=(self.current_theme == "light"), parent=self)
        dialog.applied.connect(self._on_temperature_applied)
        dialog.exec()

    def _on_temperature_applied(self, new_temp: float):
        self.temperature = new_temp
        self.temp_btn.setText(f"🌡️ Temperature: {self.temperature:.1f}")
        self.app_config["TEMPERATURE"] = self.temperature
        save_app_config(self.app_config)
        self._init_agent()

    # ==========================================
    # 11. 햄버거 토글 슬라이드 애니메이션
    # ==========================================
    def _toggle_sidebar_animation(self):
        self.sidebar_anim = QPropertyAnimation(self.sidebar_frame, b"maximumWidth")
        self.sidebar_anim.setDuration(220)
        self.sidebar_anim.setEasingCurve(QEasingCurve.OutCubic)

        if self.sidebar_visible:
            self.sidebar_anim.setStartValue(self.sidebar_frame.width())
            self.sidebar_anim.setEndValue(0)
            self.sidebar_anim.finished.connect(lambda: self.sidebar_frame.setFixedWidth(0))
            self.sidebar_visible = False
        else:
            self.sidebar_frame.setMaximumWidth(self.sidebar_width)
            self.sidebar_anim.setStartValue(0)
            self.sidebar_anim.setEndValue(self.sidebar_width)
            self.sidebar_anim.finished.connect(lambda: self.sidebar_frame.setFixedWidth(self.sidebar_width))
            self.sidebar_visible = True

        self.sidebar_anim.start()

    # ==========================================
    # 12. 대화방 CRUD 핸들러 (중복 검증 루프)
    # ==========================================
    def _refresh_conversation_list(self):
        while self.conv_layout.count() > 1:
            item = self.conv_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        conversations = ConversationManager.list_conversations()
        if not conversations:
            ConversationManager.save_conversation("새 대화", self.current_data)
            conversations = ["새 대화"]

        is_light = (self.current_theme == "light")
        for c_title in conversations:
            is_active = (c_title == self.current_title)
            item_widget = ConversationItemWidget(c_title, is_active=is_active, is_light=is_light)
            item_widget.clicked.connect(self._switch_conversation)
            item_widget.renamed.connect(self._rename_conversation)
            item_widget.deleted.connect(self._delete_conversation)
            self.conv_layout.insertWidget(self.conv_layout.count() - 1, item_widget)

    def _create_new_conversation(self):
        prompt_text = "만들 대화방의 이름을 입력하세요:"
        while True:
            new_name, ok = QInputDialog.getText(self, "새 대화방 만들기", prompt_text, text="새 대화")
            if not ok:
                return

            new_name = new_name.strip()
            if not new_name:
                prompt_text = "대화방 이름은 비워둘 수 없습니다. 다시 입력하세요:"
                continue

            existing = ConversationManager.list_conversations()
            if new_name in existing:
                QMessageBox.warning(
                    self,
                    "중복 오류",
                    f"'{new_name}'은(는) 이미 존재하는 대화방입니다.\n다른 이름을 입력해 주세요.",
                )
                prompt_text = f"'{new_name}'은(는) 이미 존재합니다. 다른 이름을 입력하세요:"
                continue

            break

        new_data = {
            "title": new_name,
            "thread_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        ConversationManager.save_conversation(new_name, new_data)
        self._switch_conversation(new_name)

    def _switch_conversation(self, title: str):
        if self.is_busy:
            QMessageBox.warning(self, "알림", "에이전트가 응답 중일 때는 대화방을 변경할 수 없습니다.")
            return

        self.current_title = title
        self.current_data = ConversationManager.load_conversation(title)
        self.title_label.setText(title)
        self._refresh_conversation_list()
        self._load_session_to_ui(title)
        self._init_agent()

    def _rename_conversation(self, old_title: str, new_title: str):
        if ConversationManager.rename_conversation(old_title, new_title):
            if self.current_title == old_title:
                self.current_title = new_title
                self.title_label.setText(new_title)
                self.current_data["title"] = new_title
            self._refresh_conversation_list()
        else:
            QMessageBox.warning(self, "오류", "이미 존재하는 대화방 이름이거나 변경에 실패했습니다.")

    def _delete_conversation(self, title: str):
        ConversationManager.delete_conversation(title)
        if self.current_title == title:
            remain = ConversationManager.list_conversations()
            if remain:
                self._switch_conversation(remain[0])
            else:
                self._create_new_conversation()
        else:
            self._refresh_conversation_list()

    def _open_mcp_settings(self):
        dialog = MCPSettingsDialog(
            self.active_mcp_servers,
            self.server_tools_map,
            is_light=(self.current_theme == "light"),
            parent=self,
        )
        dialog.applied.connect(self._on_mcp_settings_applied)
        dialog.exec()

    def _on_mcp_settings_applied(self, new_enabled_servers: Set[str]):
        self.active_mcp_servers = new_enabled_servers
        self._init_agent()

    # ==========================================
    # 13. 전체 너비 대화 렌더링 & 메트릭 표기
    # ==========================================
    def _clear_chat_ui(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            l = item.layout()
            if l:
                while l.count():
                    sub = l.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _load_session_to_ui(self, title: str):
        self._clear_chat_ui()
        msgs = self.current_data.get("messages", [])

        if not msgs:
            self._add_system_message("새로운 대화 세션입니다. 무엇을 도와드릴까요?")
            return

        for idx, m in enumerate(msgs):
            role = m.get("role", "user")
            content = m.get("content", "")
            tool_steps = m.get("tool_steps", [])
            elapsed = m.get("elapsed_sec")
            tokens = m.get("tokens")

            if role == "user":
                self._render_user_bubble(content)
            elif role == "assistant":
                is_light = (self.current_theme == "light")
                for ts in tool_steps:
                    if ts.get("type") == "tool_call":
                        t_card = ToolAccordionWidget(
                            ts.get("name", "Tool"),
                            json.dumps(ts.get("args", {}), ensure_ascii=False, indent=2),
                            is_light=is_light,
                        )
                        if "result" in ts:
                            t_card.set_result(ts["result"])
                        self._insert_widget_to_chat(t_card)

                if content:
                    self._render_ai_response_blocks(content, elapsed_sec=elapsed, tokens=tokens, msg_index=idx)

        self._scroll_to_bottom()

    def _render_user_bubble(self, text: str):
        container = QFrame(self.chat_content)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if self.current_theme == "light":
            container.setStyleSheet("background-color: #E7F1FF; border: 1px solid #B6D4FE; border-radius: 8px; padding: 6px;")
        else:
            container.setStyleSheet("background-color: #1F314D; border: 1px solid #2B456B; border-radius: 8px; padding: 6px;")

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(10, 6, 10, 8)
        vbox.setSpacing(4)

        header_row = QHBoxLayout()
        header = QLabel("👤 사용자", container)
        header.setStyleSheet("color: #0D6EFD; font-size: 11px; font-weight: bold;" if self.current_theme == "light" else "color: #89B4FA; font-size: 11px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()

        copy_btn = create_copy_button(lambda: text, tooltip="사용자 메시지 복사")
        header_row.addWidget(copy_btn)
        vbox.addLayout(header_row)

        msg_lbl = QLabel(text, container)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        msg_lbl.setStyleSheet("font-size: 13px; line-height: 1.4;")
        vbox.addWidget(msg_lbl)

        self._insert_widget_to_chat(container)

    def _render_ai_response_blocks(self, full_text: str, elapsed_sec: Optional[float] = None, tokens: Optional[int] = None, msg_index: Optional[int] = None):
        container = QFrame(self.chat_content)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if self.current_theme == "light":
            container.setStyleSheet("background-color: #FFFFFF; border: 1px solid #DEE2E6; border-radius: 8px; padding: 6px;")
        else:
            container.setStyleSheet("background-color: #24273A; border: 1px solid #313244; border-radius: 8px; padding: 6px;")

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(10, 6, 10, 8)
        vbox.setSpacing(6)

        header_row = QHBoxLayout()
        header = QLabel("🤖 Assistant", container)
        header.setStyleSheet("color: #198754; font-size: 11px; font-weight: bold;" if self.current_theme == "light" else "color: #A6E3A1; font-size: 11px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()

        copy_btn = create_copy_button(lambda: full_text, tooltip="전체 응답 복사")
        header_row.addWidget(copy_btn)
        vbox.addLayout(header_row)

        code_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        last_idx = 0

        for match in code_pattern.finditer(full_text):
            start, end = match.span()
            pre_text = full_text[last_idx:start].strip()
            if pre_text:
                txt_lbl = QLabel(pre_text, container)
                txt_lbl.setTextFormat(Qt.MarkdownText)
                txt_lbl.setWordWrap(True)
                txt_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                txt_lbl.setStyleSheet("font-size: 13px; line-height: 1.4;")
                vbox.addWidget(txt_lbl)

            lang = match.group(1) or "python"
            code_content = match.group(2)
            code_widget = CodeBlockWidget(code_content, language=lang, parent=container)
            vbox.addWidget(code_widget)
            last_idx = end

        remaining = full_text[last_idx:].strip()
        if remaining:
            txt_lbl = QLabel(remaining, container)
            txt_lbl.setTextFormat(Qt.MarkdownText)
            txt_lbl.setWordWrap(True)
            txt_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            txt_lbl.setStyleSheet("font-size: 13px; line-height: 1.4;")
            vbox.addWidget(txt_lbl)

        # 하단 토큰 사용량 / 소요 시간 및 우측 [🗑️ 삭제] 버튼
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)

        metrics_str = ""
        if elapsed_sec is not None or tokens is not None:
            metrics_str = "⏱️ "
            if elapsed_sec is not None:
                metrics_str += f"{elapsed_sec:.2f}s"
            if tokens is not None and tokens > 0:
                metrics_str += f"  |  🔤 ~{tokens} tokens"

        metrics_lbl = QLabel(metrics_str, container)
        metrics_lbl.setStyleSheet("color: #6C7086; font-size: 10px;")
        bottom_row.addWidget(metrics_lbl)

        bottom_row.addStretch()

        if msg_index is not None:
            del_set_btn = QPushButton("🗑️ 삭제", container)
            del_set_btn.setToolTip("이 질문-응답 세트를 대화 기록에서 삭제합니다")
            del_set_btn.setCursor(Qt.PointingHandCursor)
            del_set_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #6C7086;
                    border: 1px solid rgba(128, 128, 128, 0.2);
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: rgba(243, 139, 168, 0.2);
                    color: #F38BA8;
                    border: 1px solid #F38BA8;
                }
            """)
            del_set_btn.clicked.connect(lambda _, idx=msg_index: self._delete_message_set(idx))
            bottom_row.addWidget(del_set_btn)

        vbox.addLayout(bottom_row)

        self._insert_widget_to_chat(container)

    def _add_system_message(self, text: str):
        lbl = QLabel(f"<i>{text}</i>", self.chat_content)
        lbl.setTextFormat(Qt.RichText)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #6C7086; font-size: 11px; margin: 8px 0px;")
        self._insert_widget_to_chat(lbl)

    def _insert_widget_to_chat(self, widget: QWidget):
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(max(0, count - 1), widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QApplication.processEvents()
        v_bar = self.chat_scroll.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())

    # ==========================================
    # 14. 에이전트 초기화 & 메시지 스트리밍
    # ==========================================
    def _set_status(self, text: str, state: str = "normal"):
        """헤더 상태 라벨 텍스트 및 배경 투명 스타일 설정"""
        self.status_label.setText(text)
        if state == "online":
            c = "#15803D" if self.current_theme == "light" else "#A6E3A1"
            fw = "bold"
        elif state == "thinking":
            c = "#2563EB" if self.current_theme == "light" else "#89B4FA"
            fw = "normal"
        elif state == "tool":
            c = "#B45309" if self.current_theme == "light" else "#F9E2AF"
            fw = "normal"
        elif state == "offline":
            c = "#DC2626" if self.current_theme == "light" else "#F38BA8"
            fw = "bold"
        else:
            c = "#475569" if self.current_theme == "light" else "#BAC2DE"
            fw = "normal"

        self.status_label.setStyleSheet(f"background-color: transparent; color: {c}; font-size: 12px; font-weight: {fw};")

    def _init_agent(self):
        if self.init_worker and self.init_worker.isRunning():
            self.init_worker.quit()
            self.init_worker.wait(500)

        self._set_status("⏳ 에이전트 초기화 중...", "tool")

        current_prompt = self.current_data.get("system_prompt", self.app_config.get("SYSTEM_PROMPT", "당신은 유능하고 친절한 AI 어시스턴트입니다."))
        self.init_worker = AgentInitWorker(self.active_mcp_servers, self.temperature, system_prompt=current_prompt)
        self.init_worker.success.connect(self._on_agent_init_success)
        self.init_worker.failed.connect(self._on_agent_init_failed)
        self.init_worker.start()

    def _on_agent_init_success(self, agent, tools, server_tools_map):
        self.agent = agent
        self.tools = tools
        self.server_tools_map = server_tools_map

        mcp_status = f"{len(tools)}개 도구" if tools else "MCP 비활성"
        self._set_status(f"● 온라인 ({mcp_status} | {self.app_config.get('MODEL_NAME', 'gemma')} | T:{self.temperature:.1f})", "online")
        self.send_btn.setEnabled(True)

    def _on_agent_init_failed(self, error_msg: str):
        self._set_status("● 오프라인 (연결 실패)", "offline")
        self._add_system_message(f"❌ 에이전트 초기화 실패: {error_msg}")

    def _on_send_click(self):
        if self.is_busy or not self.agent:
            return

        user_text = self.chat_input.toPlainText().strip()
        if not user_text:
            return

        self.chat_input.clear()
        self._render_user_bubble(user_text)

        self.current_data["messages"].append({"role": "user", "content": user_text})
        ConversationManager.save_conversation(self.current_title, self.current_data)

        self.is_busy = True
        self._set_status("🧠 생각 중...", "thinking")
        self.send_btn.setEnabled(False)

        self.current_ai_raw_text = ""
        self._prepare_ai_streaming_bubble()

        thread_id = self.current_data.get("thread_id", str(uuid.uuid4()))
        self.stream_worker = AgentStreamWorker(self.agent, user_text, thread_id)
        self.stream_worker.token_chunk.connect(self._on_token_chunk)
        self.stream_worker.tool_started.connect(self._on_tool_started)
        self.stream_worker.tool_finished.connect(self._on_tool_finished)
        self.stream_worker.stream_complete.connect(self._on_stream_complete)
        self.stream_worker.error_occurred.connect(self._on_stream_error)
        self.stream_worker.start()

    def _prepare_ai_streaming_bubble(self):
        self.stream_container = QFrame(self.chat_content)
        self.stream_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if self.current_theme == "light":
            self.stream_container.setStyleSheet("background-color: #FFFFFF; border: 1px solid #DEE2E6; border-radius: 8px; padding: 6px;")
        else:
            self.stream_container.setStyleSheet("background-color: #24273A; border: 1px solid #313244; border-radius: 8px; padding: 6px;")

        vbox = QVBoxLayout(self.stream_container)
        vbox.setContentsMargins(10, 6, 10, 8)
        vbox.setSpacing(4)

        header_row = QHBoxLayout()
        header = QLabel("🤖 Assistant", self.stream_container)
        header.setStyleSheet("color: #198754; font-size: 11px; font-weight: bold;" if self.current_theme == "light" else "color: #A6E3A1; font-size: 11px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()

        copy_btn = create_copy_button(lambda: self.current_ai_raw_text, tooltip="응답 복사")
        header_row.addWidget(copy_btn)
        vbox.addLayout(header_row)

        self.current_ai_bubble = QLabel("", self.stream_container)
        self.current_ai_bubble.setWordWrap(True)
        self.current_ai_bubble.setTextFormat(Qt.MarkdownText)
        self.current_ai_bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_ai_bubble.setStyleSheet("font-size: 13px; line-height: 1.4;")
        vbox.addWidget(self.current_ai_bubble)

        self._insert_widget_to_chat(self.stream_container)

    def _on_token_chunk(self, chunk: str):
        self.current_ai_raw_text += chunk
        if self.current_ai_bubble:
            self.current_ai_bubble.setText(self.current_ai_raw_text)
            self._scroll_to_bottom()

    def _on_tool_started(self, name: str, args: str):
        self._set_status(f"⚡ 도구 실행: {name}", "tool")

        is_light = (self.current_theme == "light")
        self.current_tool_card = ToolAccordionWidget(name, args, is_light=is_light, parent=self.chat_content)
        self._insert_widget_to_chat(self.current_tool_card)

        ai_msg = self._get_or_create_last_ai_message()
        if "tool_steps" not in ai_msg:
            ai_msg["tool_steps"] = []
        ai_msg["tool_steps"].append({
            "type": "tool_call",
            "name": name,
            "args": json.loads(args) if args.startswith("{") else args,
        })

    def _on_tool_finished(self, name: str, result: str):
        if self.current_tool_card:
            self.current_tool_card.set_result(result)

        ai_msg = self._get_or_create_last_ai_message()
        if "tool_steps" in ai_msg and ai_msg["tool_steps"]:
            ai_msg["tool_steps"][-1]["result"] = result

    def _on_stream_complete(self, final_text: str, elapsed_sec: float, estimated_tokens: int):
        self.is_busy = False
        mcp_status = f"{len(self.tools)}개 도구" if self.tools else "MCP 비활성"
        self._set_status(f"● 온라인 ({mcp_status} | {self.app_config.get('MODEL_NAME', 'gemma')} | T:{self.temperature:.1f})", "online")
        self.send_btn.setEnabled(True)
        self.chat_input.setFocus()

        ans_text = final_text or self.current_ai_raw_text
        ai_msg = self._get_or_create_last_ai_message()
        ai_msg["content"] = ans_text
        ai_msg["elapsed_sec"] = elapsed_sec
        ai_msg["tokens"] = estimated_tokens
        ConversationManager.save_conversation(self.current_title, self.current_data)

        if self.stream_container:
            self.stream_container.deleteLater()

        last_idx = len(self.current_data["messages"]) - 1
        self._render_ai_response_blocks(ans_text, elapsed_sec=elapsed_sec, tokens=estimated_tokens, msg_index=last_idx)

    def _delete_message_set(self, assistant_index: int):
        """사용자 질문 - Assistant 응답 1개 세트 삭제"""
        if self.is_busy:
            QMessageBox.warning(self, "알림", "에이전트가 응답 중일 때는 대화를 삭제할 수 없습니다.")
            return

        msgs = self.current_data.get("messages", [])
        if assistant_index < 0 or assistant_index >= len(msgs):
            return

        reply = QMessageBox.question(
            self,
            "대화 세트 삭제",
            "이 질문-응답 세트를 대화 기록에서 삭제하시겠습니까?\n(사용자 질문과 AI 응답이 함께 삭제됩니다)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            # 직전 메시지가 user인 경우 사용자 질문과 답변 세트 모두 삭제
            if assistant_index > 0 and msgs[assistant_index - 1].get("role") == "user":
                del msgs[assistant_index]
                del msgs[assistant_index - 1]
            else:
                del msgs[assistant_index]

            ConversationManager.save_conversation(self.current_title, self.current_data)
            self._load_session_to_ui(self.current_title)

    def _on_stream_error(self, error_msg: str):
        self.is_busy = False
        self._set_status("❌ 오류 발생", "offline")
        self._add_system_message(f"❌ 오류: {error_msg}")
        self.send_btn.setEnabled(True)
        self.chat_input.setFocus()

    def _get_or_create_last_ai_message(self) -> Dict[str, Any]:
        msgs = self.current_data.get("messages", [])
        if not msgs or msgs[-1].get("role") != "assistant":
            ai_entry = {"role": "assistant", "content": "", "tool_steps": []}
            msgs.append(ai_entry)
            return ai_entry
        return msgs[-1]


# ==========================================
# 실행 진입점
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(create_emoji_icon("✨"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
