"""skills-mcp-server.py - 표준 디렉토리 기반 FastMCP 스킬 관리 서버.

Antigravity / Claude 표준 스킬 구조(skills/<skill_name>/SKILL.md)를 지원하며,
YAML Frontmatter 기반 메타데이터 파싱 및 스킬 조회, 등록/수정, 안전 삭제를 제공합니다.

[제공 도구]
1. skills_smart_run - [추천] 사용자 요청을 입력하면 최적의 스킬을 자동 연결하는 원스톱 실행 도구
2. skills_get - 특정 스킬의 SKILL.md 전체 지침 전문 로드
3. skills_list - 등록된 모든 스킬의 이름 및 요약 설명 조회
4. skills_create_or_update - 표준 YAML Frontmatter 형식의 스킬 생성 및 수정
5. skills_delete_to_trash - 스킬 폴더를 OS 휴지통으로 안전하게 이동 (Safe Delete)
"""

import argparse
import asyncio
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# UTF-8 콘솔 인코딩 설정 (Windows 대응)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# FastMCP 서버 인스턴스 초기화
mcp = FastMCP("Skills-MCP-Server")


# ==============================================================================
# 1. 데이터 모델 및 스킬 디렉토리 설정
# ==============================================================================

class SkillMetadata(BaseModel):
    name: str = Field(description="스킬 고유 식별자 (폴더명 및 식별자)")
    description: str = Field(description="스킬의 주요 목적과 기능 요약")
    category: str = Field(default="General", description="스킬 분류 카테고리")
    triggers: List[str] = Field(default_factory=list, description="스킬 자동 활성화 키워드 목록")


def get_skills_dir() -> Path:
    """스킬들이 저장된 루트 디렉토리 경로를 반환합니다."""
    env_path = os.environ.get("SKILLS_DIR")
    if env_path:
        target = Path(env_path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target

    # 스크립트 디렉토리 기준 'skills' 폴더
    script_dir = Path(__file__).parent.resolve()
    target = script_dir / "skills"
    if target.exists():
        return target

    # 현재 작업 디렉토리 기준 'skills' 폴더
    cwd_target = Path.cwd().resolve() / "skills"
    if cwd_target.exists():
        return cwd_target

    target.mkdir(parents=True, exist_ok=True)
    return target


# ==============================================================================
# 2. YAML Frontmatter 파싱 및 저장 유틸리티
# ==============================================================================

def parse_yaml_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """마크다운 텍스트에서 YAML Frontmatter와 본문(Markdown Body)을 파싱합니다."""
    metadata: Dict[str, Any] = {}
    body = content

    # --- 로 둘러싸인 YAML Frontmatter 검출
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return metadata, body

    raw_yaml, body = match.group(1), match.group(2)
    
    # 순수 파이썬 라인 단위 YAML 파서 (PyYAML 의존성 없이도 견고하게 동작)
    current_list_key = None
    for line in raw_yaml.splitlines():
        line_str = line.strip()
        if not line_str or line_str.startswith("#"):
            continue

        if line_str.startswith("- ") and current_list_key:
            item_val = line_str[2:].strip().strip("\"'")
            if isinstance(metadata.get(current_list_key), list):
                metadata[current_list_key].append(item_val)
            continue

        if ":" in line_str:
            key, val = line_str.split(":", 1)
            key = key.strip()
            val = val.strip().strip("\"'")
            if not val:
                metadata[key] = []
                current_list_key = key
            else:
                metadata[key] = val
                current_list_key = None

    return metadata, body.strip()


def format_skill_markdown(
    name: str,
    description: str,
    instructions: str,
    category: str = "General",
    triggers: Optional[List[str]] = None,
) -> str:
    """표준 YAML Frontmatter + Markdown 포맷 문자열을 생성합니다."""
    triggers = triggers or []
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"category: {category}",
    ]

    if triggers:
        lines.append("triggers:")
        for t in triggers:
            lines.append(f"  - {t}")
    else:
        lines.append("triggers: []")

    lines.append("---")
    lines.append("")

    # Markdown Body
    if not instructions.startswith("#"):
        lines.append(f"# {name.replace('-', ' ').replace('_', ' ').title()} Skill")
        lines.append("")
        lines.append("## 실행 지침 (Instructions)")
        lines.append(instructions.strip())
    else:
        lines.append(instructions.strip())

    return "\n".join(lines).strip() + "\n"


def send_to_recycle_bin(target_path: Path) -> bool:
    """폴더나 파일을 OS 휴지통으로 안전하게 이동합니다."""
    try:
        import send2trash
        send2trash.send2trash(str(target_path))
        return True
    except ImportError:
        pass

    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 0x0003
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004

        abs_path = str(target_path.resolve()) + "\0"
        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = None
        fileop.wFunc = FO_DELETE
        fileop.pFrom = abs_path
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        fileop.fAnyOperationsAborted = False
        fileop.hNameMappings = None
        fileop.lpszProgressTitle = None

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if res != 0 or fileop.fAnyOperationsAborted:
            raise RuntimeError(f"Windows Shell operation failed with code: {res}")
        return True
    else:
        raise NotImplementedError("Recycle Bin operation is only supported on Windows or with send2trash installed.")


# ==============================================================================
# 3. 표준 FastMCP 도구 정의 (Enhanced Triggering & One-Stop Execution)
# ==============================================================================

@mcp.tool()
async def skills_smart_run(
    user_request: str = Field(
        description="사용자의 원본 작업 요청 내용 (예: 'for i in range(0, 10): print(i) 코드 뜻 알려줘', '이 프롬프트 좀 개선해줘')",
        examples=[
            "for i in range(0, 10): print(i) 코드 뜻 알려줘",
            "다음 Python 코드를 리뷰하고 최적화해줘",
            "영어 번역을 잘 해주는 LLM 프롬프트 만들어줘",
        ],
    ),
    skill_name: Optional[str] = Field(
        default=None,
        description="특정 스킬을 지정하려는 경우 스킬 식별자 입력 ('code-reviewer', 'prompt-optimizer' 등). 비워두면 요청 내용 기반으로 최적의 스킬을 자동 선택합니다.",
        examples=["code-reviewer", "prompt-optimizer", None],
    ),
) -> str:
    """[RECOMMENDED / ONE-STOP SKILL RUNNER] 사용자가 '스킬'을 언급하거나 코드 분석, 코드 리뷰, 버그 검토, 프롬프트 개선/최적화 등 전문 작업을 요청했을 때, 직접 자체 지식으로 답변하기 전에 반드시 최우선으로 호출해야 하는 필수 도구입니다.
    
    사용자 요청에 가장 적합한 스킬(또는 지정된 skill_name)의 전문 지침(SKILL.md)을 자동으로 로드하여 최적화된 실행 워크플로우를 제공합니다.
    """
    def _run():
        skills_dir = get_skills_dir()
        if not skills_dir.exists():
            return f"❌ 스킬 디렉토리가 존재하지 않습니다: {skills_dir}"

        # 1. 대상 스킬 결정 (지정되었거나 키워드 기반 자동 감지)
        target_name = skill_name.strip().lower().replace("_", "-") if skill_name else None
        
        # 키워드 기반 자동 감지
        if not target_name:
            req_lower = user_request.lower()
            if any(k in req_lower for k in ["코드", "code", "python", "파이썬", "def ", "class ", "for ", "import ", "버그", "리뷰"]):
                target_name = "code-reviewer"
            elif any(k in req_lower for k in ["프롬프트", "prompt", "최적화", "페르소나", "system prompt"]):
                target_name = "prompt-optimizer"

        # 스킬 파일 검색
        skill_file = None
        if target_name:
            candidate = skills_dir / target_name / "SKILL.md"
            if candidate.exists():
                skill_file = candidate
            else:
                for item in skills_dir.iterdir():
                    if item.is_dir() and (item / "SKILL.md").exists():
                        meta, _ = parse_yaml_frontmatter((item / "SKILL.md").read_text(encoding="utf-8"))
                        if meta.get("name") == target_name or item.name.lower() == target_name:
                            skill_file = item / "SKILL.md"
                            break

        # 매칭된 스킬이 없을 경우 등록된 첫 번째 스킬 또는 목록 안내
        if not skill_file:
            all_skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
            return (
                f"ℹ️ 요청과 완벽히 일치하는 스킬을 자동 감지하지 못했습니다. "
                f"사용 가능한 스킬 목록: {all_skills}. "
                f"`skills_get(name)`으로 원하는 스킬을 직접 지정해 호출해주세요."
            )

        skill_content = skill_file.read_text(encoding="utf-8")
        meta, instructions = parse_yaml_frontmatter(skill_content)
        s_name = meta.get("name", skill_file.parent.name)

        workflow = [
            f"🎯 **[전문 스킬 가이드 활성화: `{s_name}`]**",
            f"- **설명**: {meta.get('description', '')}",
            f"- **카테고리**: {meta.get('category', 'General')}",
            "",
            "---",
            "### 📌 [스킬 표준 실행 지침 (Instructions)]:",
            instructions if instructions else skill_content,
            "---",
            "",
            "⚡ **[AI 어시스턴트 필수 연쇄 실행 지침 (MANDATORY 2-STEP WORKFLOW)]**:",
            f"당신은 위 `{s_name}` 스킬 지침을 기반으로 다음 2단계를 반드시 순서대로 모두 수행하여 완성형 최종 답변을 제공해야 합니다:",
            "",
            f"🏷️ **[필수 말머리 규칙]**: 최종 답변을 시작할 때, 반드시 최상단 첫 줄에 **`### 🎯 [적용 스킬: {s_name}]`** 말머리를 붙여서 어떤 스킬이 적용되었는지 사용자에게 명시하십시오.",
            "",
            "▶ **1단계 [스킬 적용 및 분석/최적화]**:",
            f"- `{s_name}` 스킬 실행 지침에 맞춰 사용자의 원본 요청을 분석하고, 최적화된 프롬프트나 분석 기준을 도출하세요.",
            "",
            "▶ **2단계 [최종 작업 직접 수행 및 완성]**:",
            "- 1단계에서 도출된 최적화 프롬프트/기준을 바탕으로, 사용자가 최종적으로 얻고자 하는 **실제 작업(예: 실제 분석 결과, 최종 추천안, 소스 코드 등)을 직접 수행하여 완성형 결과물을 함께 작성**하세요.",
            "",
            "⚠️ **중요 주의사항**: 1단계(최적화 프롬프트나 계획)만 출력하고 멈추지 마십시오. 반드시 최상단 말머리부터 2단계(실제 완성된 최종 결과물)까지 한 번의 응답에서 완성하여 출력해야 합니다.",
        ]
        return "\n".join(workflow)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_list() -> str:
    """[스킬 목록 조회] 등록된 모든 AI 에이전트 스킬의 식별자(name), 설명(description), 카테고리를 요약 조회합니다."""
    def _run():
        skills_dir = get_skills_dir()
        if not skills_dir.exists():
            return "ℹ️ 등록된 스킬 디렉토리가 없습니다."

        skill_entries = []
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    content = skill_file.read_text(encoding="utf-8")
                    meta, _ = parse_yaml_frontmatter(content)
                    s_name = meta.get("name", item.name)
                    s_desc = meta.get("description", "설명 없음")
                    s_cat = meta.get("category", "General")
                    s_trig = meta.get("triggers", [])
                    trig_str = f" *(트리거: {', '.join(s_trig)})*" if s_trig else ""
                    skill_entries.append(f"- **`{s_name}`** [{s_cat}]: {s_desc}{trig_str}")

        if not skill_entries:
            return f"ℹ️ `{skills_dir}`에 등록된 스킬이 없습니다."

        header = [
            f"📋 **등록된 AI 스킬 목록 (총 {len(skill_entries)}개)**",
            f"📁 저장 위치: `{skills_dir}`",
            "",
            *skill_entries,
            "",
            "💡 특정 스킬의 세부 지침을 확인하려면 `skills_get(name)`을 호출하세요.",
        ]
        return "\n".join(header)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_get(
    name: str = Field(
        description="로드할 스킬 이름. 사용 가능한 대표 스킬: 'code-reviewer' (코드 분석, 파이썬/JS 리뷰, 버그 검토), 'prompt-optimizer' (프롬프트 개선, 구조화 프롬프트 작성)",
        examples=["code-reviewer", "prompt-optimizer"],
    ),
) -> str:
    """[MANDATORY SKILL LOADER] 특정 스킬의 전체 지침 전문(SKILL.md)을 로드합니다. 사용자가 코드 분석, 프롬프트 최적화 또는 '스킬' 관련 작업을 요구할 때 반드시 먼저 호출하여 지침을 가져옵니다."""
    def _run():
        skills_dir = get_skills_dir()
        cleaned_name = name.strip().lower().replace("_", "-")
        
        target_dir = skills_dir / cleaned_name
        skill_file = target_dir / "SKILL.md"

        if not skill_file.exists():
            for item in skills_dir.iterdir():
                if item.is_dir():
                    candidate = item / "SKILL.md"
                    if candidate.exists():
                        meta, _ = parse_yaml_frontmatter(candidate.read_text(encoding="utf-8"))
                        meta_name = str(meta.get("name", "")).strip().lower().replace("_", "-")
                        if meta_name == cleaned_name or item.name.lower() == cleaned_name:
                            skill_file = candidate
                            break

        if not skill_file.exists():
            available = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
            return f"❌ 스킬 '{name}'을(를) 찾을 수 없습니다.\n사용 가능한 스킬 목록: {available}"

        skill_content = skill_file.read_text(encoding="utf-8")
        meta, _ = parse_yaml_frontmatter(skill_content)
        s_name = meta.get("name", skill_file.parent.name)

        return (
            f"{skill_content}\n\n---\n"
            f"⚡ **[AI 어시스턴트 지침]**: 답변을 작성할 때 반드시 최상단 첫 줄에 "
            f"`### 🎯 [적용 스킬: {s_name}]` 말머리를 붙이고 위 지침에 따라 최종 답변을 완성하십시오."
        )

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_create_or_update(
    name: str = Field(
        description="스킬 고유 식별자 (영문, 소문자, 하이픈 권장. 예: prompt-optimizer, code-reviewer)",
        examples=["prompt-optimizer", "git-commit-helper"],
    ),
    description: str = Field(
        description="스킬의 주요 목적과 기능에 대한 요약 설명",
        examples=["사용자의 프롬프트를 체계적으로 최적화합니다."],
    ),
    instructions: str = Field(
        description="스킬 실행 시 에이전트가 준수해야 할 상세 마크다운 가이드/지침",
    ),
    category: str = Field(
        default="General",
        description="스킬 분류 카테고리 (예: Development, Prompt Engineering, Utility)",
    ),
    triggers: str = Field(
        default="",
        description="스킬 자동 활성화 키워드 목록 (쉼표 구분. 예: 프롬프트 개선, 프롬프트 최적화)",
    ),
) -> str:
    """[스킬 등록/수정] 새로운 스킬을 등록하거나 기존 스킬을 표준 SKILL.md 파일로 영구 저장합니다."""
    def _run():
        skills_dir = get_skills_dir()
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", name.strip()).strip("-").lower()
        if not clean_name:
            return "❌ 유효한 스킬 이름을 입력해주세요 (영문, 숫자, 하이픈 권장)."

        target_dir = skills_dir / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        trigger_list = [t.strip() for t in re.split(r"[,;]", triggers) if t.strip()]
        formatted_content = format_skill_markdown(
            name=clean_name,
            description=description.strip(),
            instructions=instructions.strip(),
            category=category.strip() or "General",
            triggers=trigger_list,
        )

        is_new = not skill_file.exists()
        skill_file.write_text(formatted_content, encoding="utf-8")
        action = "신규 등록" if is_new else "수정(업데이트)"
        return f"✅ 스킬 `{clean_name}`이(가) 성공적으로 {action}되었습니다! (경로: `{skill_file}`)"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_delete_to_trash(
    name: str = Field(
        description="삭제할 스킬의 고유 식별자(name)",
        examples=["prompt-optimizer", "old-skill"],
    ),
) -> str:
    """[스킬 휴지통 삭제] 지정한 스킬 폴더를 영구 삭제하지 않고 OS 휴지통으로 안전하게 이동합니다."""
    def _run():
        skills_dir = get_skills_dir()
        clean_name = name.strip().lower().replace("_", "-")
        target_dir = skills_dir / clean_name

        if not target_dir.exists():
            for item in skills_dir.iterdir():
                if item.is_dir():
                    candidate = item / "SKILL.md"
                    if candidate.exists():
                        meta, _ = parse_yaml_frontmatter(candidate.read_text(encoding="utf-8"))
                        if meta.get("name") == clean_name or item.name.lower() == clean_name:
                            target_dir = item
                            break

        if not target_dir.exists() or not target_dir.is_dir():
            return f"❌ 삭제 대상 스킬 폴더를 찾을 수 없습니다: '{name}'"

        try:
            send_to_recycle_bin(target_dir)
            return f"🗑️ 스킬 `{name}` 폴더를 OS 휴지통으로 안전하게 이동했습니다 (경로: `{target_dir}`)."
        except Exception as e:
            return f"❌ 스킬 삭제 실패: {str(e)}"

    return await asyncio.to_thread(_run)


# ==============================================================================
# 4. FastMCP 표준 Prompt 정의 (Agent System Prompt 자동 주입 지원)
# ==============================================================================

@mcp.prompt()
def agent_skills_guide() -> str:
    """AI 에이전트가 스킬 도구를 최적의 워크플로우로 호출하도록 돕는 표준 시스템 프롬프트입니다."""
    return """당신은 MCP 스킬 레지스트리를 활용하여 전문적인 답변을 생성하는 AI 어시스턴트입니다.
1. 사용자가 코드 분석, 코드 리뷰, 프롬프트 개선, 번역 등 전문적인 작업을 요청하거나 '스킬'을 언급하면, 직접 추측하여 대답하지 마십시오.
2. 반드시 먼저 `skills_smart_run(user_request)` 또는 `skills_get(name)` 도구를 호출하여 표준 지침을 로드하십시오.
3. 답변을 작성할 때는 반드시 최상단 첫 줄에 어떤 스킬을 적용했는지 `### 🎯 [적용 스킬: <스킬명>]` 형식의 말머리를 명시하고, 로드된 지침의 규칙과 포맷에 따라 최종 답변을 완벽하게 작성하십시오."""


# ==============================================================================
# 5. 서버 실행 진입점 (HTTP / SSE / stdio)
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standard Directory-based Skills FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["http", "sse", "stdio"],
        default="http",
        help="서빙 전송 방식 선택: http, sse, stdio (기본값: http)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP/SSE 서버 호스트 주소 (기본값: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="HTTP/SSE 서버 포트 번호 (기본값: 8002)",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="스킬 루트 디렉토리 경로 지정 (기본값: ./skills)",
    )
    args = parser.parse_args()

    if args.skills_dir:
        os.environ["SKILLS_DIR"] = str(Path(args.skills_dir).expanduser().resolve())

    # 스킬 디렉토리 존재 확인
    skills_path = get_skills_dir()
    print(f"📂 Skills Root Directory: {skills_path}", file=sys.stderr)

    # CORS 모든 접속 허용 미들웨어 설정
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
        print(f"🚀 Skills FastMCP HTTP Server 시작 (CORS 전체 허용): http://{args.host}:{args.port}", file=sys.stderr)
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
    elif args.transport == "sse":
        print(f"🚀 Skills FastMCP SSE Server 시작 (CORS 전체 허용): http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
