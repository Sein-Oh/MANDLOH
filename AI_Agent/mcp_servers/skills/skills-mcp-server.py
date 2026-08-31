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
# 2. YAML Frontmatter 파싱 및 유틸리티
# ==============================================================================

def parse_yaml_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """마크다운 텍스트에서 YAML Frontmatter와 본문(Markdown Body)을 파싱합니다 (오류 내구성 강화)."""
    metadata: Dict[str, Any] = {}
    if not content or not content.strip():
        return metadata, ""

    body = content.strip()

    # --- 로 둘러싸인 YAML Frontmatter 검출
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        # Frontmatter가 없는 일반 마크다운인 경우 첫 줄의 # 제목을 이름 후보로 파싱
        first_line = content.strip().splitlines()[0] if content.strip() else ""
        if first_line.startswith("#"):
            metadata["name"] = first_line.lstrip("#").strip().lower().replace(" ", "-")
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
    """폴더나 파일을 Windows OS 휴지통으로 안전하게 이동합니다 (Windows Native Safe Delete)."""
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
        FOF_ALLOWUNDO = 0x0040  # 휴지통 보관 플래그
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
        raise NotImplementedError("휴지통 이동 기능은 Windows 환경을 기본 지원합니다.")


def load_all_skills_registry() -> List[Dict[str, Any]]:
    """등록된 모든 스킬의 메타데이터와 파일 정보를 스캔하여 반환합니다."""
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return []

    registry = []
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir():
            skill_file = item / "SKILL.md"
            if skill_file.exists():
                try:
                    raw_text = skill_file.read_text(encoding="utf-8")
                    meta, instructions = parse_yaml_frontmatter(raw_text)
                    s_name = meta.get("name") or item.name
                    s_desc = meta.get("description") or "설명 없음"
                    s_cat = meta.get("category") or "General"
                    s_trig = meta.get("triggers") or []
                    if isinstance(s_trig, str):
                        s_trig = [t.strip() for t in s_trig.split(",") if t.strip()]

                    registry.append({
                        "name": str(s_name).strip(),
                        "dir_name": item.name,
                        "description": str(s_desc).strip(),
                        "category": str(s_cat).strip(),
                        "triggers": s_trig,
                        "file_path": skill_file,
                        "instructions": instructions,
                        "raw_content": raw_text,
                    })
                except Exception as e:
                    print(f"Warning: Failed to load skill in {item}: {e}", file=sys.stderr)
    return registry


# ==============================================================================
# 3. 표준 FastMCP 도구 정의 (Enhanced Triggering & One-Stop Execution)
# ==============================================================================

@mcp.tool()
async def skills_smart_run(
    user_request: str = Field(
        description="사용자의 원본 작업 요청 내용 (예: '보안공지 메일 써줘', '다음 Python 코드 리뷰해줘', '프롬프트 최적화해줘')",
        examples=[
            "8월 보안공지 메일 작성해줘",
            "다음 Python 코드를 리뷰하고 최적화해줘",
            "영어 번역을 잘 해주는 LLM 프롬프트 만들어줘",
        ],
    ),
    skill_name: Optional[str] = Field(
        default=None,
        description="특정 스킬을 직접 지정하려는 경우 스킬 식별자 입력 (예: 'code-reviewer', 'security-notice' 등). 비워두면 요청 내용을 분석하여 최적의 스킬을 자동 선택합니다.",
        examples=["security-notice", "code-reviewer", "prompt-optimizer", None],
    ),
) -> str:
    """[RECOMMENDED / ONE-STOP SKILL RUNNER] 사용자가 '스킬'을 언급하거나 특정 전문 작업(코드 분석, 프롬프트 최적화, 보안공지 등)을 요청했을 때, 직접 자체 지식으로 답변하기 전에 반드시 최우선으로 호출해야 하는 필수 도구입니다.
    
    등록된 모든 스킬의 triggers, description, name을 실시간으로 스캔하여 최적의 스킬 지침을 자동 연결하고 2단계 연쇄 실행을 수행합니다.
    """
    def _run():
        skills = load_all_skills_registry()
        if not skills:
            return "❌ 등록된 스킬이 없습니다. `skills_create_or_update` 도구로 새 스킬을 먼저 등록해주세요."

        selected_skill = None
        req_text = user_request if isinstance(user_request, str) else str(user_request or "")

        # 1. 스킬 이름이 명시적으로 전달된 경우
        target_name = skill_name if isinstance(skill_name, str) and skill_name.strip() else None
        if target_name:
            clean_target = target_name.strip().lower().replace("_", "-")
            for sk in skills:
                if sk["name"].lower() == clean_target or sk["dir_name"].lower() == clean_target:
                    selected_skill = sk
                    break

        # 2. 동적 트리거 및 유사도 기반 자동 매칭 (Dynamic Auto-Routing)
        if not selected_skill:
            req_lower = req_text.lower()
            best_score = 0
            best_skill = None

            for sk in skills:
                score = 0
                # (a) triggers 키워드 매칭 (가장 높은 가중치)
                for trig in sk["triggers"]:
                    t_lower = str(trig).lower()
                    if t_lower and t_lower in req_lower:
                        score += 15 + len(t_lower)

                # (b) 스킬 이름 매칭
                s_name_lower = sk["name"].lower()
                if s_name_lower in req_lower or s_name_lower.replace("-", " ") in req_lower:
                    score += 10

                # (c) 설명(description) 키워드 매칭
                for word in re.findall(r"[\w가-힣]{2,}", sk["description"].lower()):
                    if word in req_lower:
                        score += 2

                # (d) 카테고리 매칭
                if sk["category"].lower() in req_lower:
                    score += 2

                if score > best_score:
                    best_score = score
                    best_skill = sk

            if best_score > 0:
                selected_skill = best_skill

        # 3. 매칭 실패 시 안내 반환
        if not selected_skill:
            available_names = [f"`{sk['name']}`" for sk in skills]
            return (
                f"ℹ️ 요청('{req_text}')과 완벽히 일치하는 스킬을 자동 감지하지 못했습니다.\n"
                f"사용 가능한 스킬 목록: {', '.join(available_names)}\n"
                f"원하는 스킬을 `skills_smart_run(user_request, skill_name='스킬명')`으로 지정해 호출해주세요."
            )

        s_name = selected_skill["name"]
        s_desc = selected_skill["description"]
        s_cat = selected_skill["category"]
        instructions = selected_skill["instructions"] or selected_skill["raw_content"]

        workflow = [
            f"🎯 **[전문 스킬 가이드 활성화: `{s_name}`]**",
            f"- **설명**: {s_desc}",
            f"- **카테고리**: {s_cat}",
            "",
            "---",
            "### 📌 [스킬 표준 실행 지침 (Instructions)]:",
            instructions,
            "---",
            "",
            "⚡ **[AI 어시스턴트 필수 연쇄 실행 지침 (MANDATORY 2-STEP WORKFLOW)]**:",
            f"당신은 위 `{s_name}` 스킬 지침을 기반으로 다음 2단계를 반드시 순서대로 모두 수행하여 완성형 최종 답변을 제공해야 합니다:",
            "",
            f"🏷️ **[필수 말머리 규칙]**: 최종 답변을 시작할 때, 반드시 최상단 첫 줄에 **`### 🎯 [적용 스킬: {s_name}]`** 말머리를 붙여서 어떤 스킬이 적용되었는지 사용자에게 명시하십시오.",
            "",
            "▶ **1단계 [스킬 적용 및 분석/계획]**:",
            f"- `{s_name}` 스킬 실행 지침에 맞춰 사용자의 원본 요청을 분석하고, 필요한 양식이나 기준을 도출하세요.",
            "",
            "▶ **2단계 [최종 작업 직접 수행 및 완성]**:",
            "- 1단계에서 도출된 기준과 지침을 바탕으로, 사용자가 최종적으로 얻고자 하는 **실제 완성형 결과물(예: 완성된 메일 본문, 분석 보고서, 완성 소스 코드 등)을 완벽하게 작성**하세요.",
            "",
            "⚠️ **중요 주의사항**: 1단계(계획이나 뼈대)만 출력하고 멈추지 마십시오. 반드시 최상단 말머리부터 2단계(실제 완성된 최종 결과물)까지 한 번의 응답에서 완전하게 출력해야 합니다.",
        ]
        return "\n".join(workflow)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_list(
    category: Optional[str] = Field(
        default=None,
        description="특정 카테고리만 필터링하여 조회하려는 경우 입력 (예: 'Development', 'Communication', 'Prompt Engineering'). 비워두면 전체 카테고리별로 그룹핑하여 조회합니다.",
        examples=["Development", "Communication", None],
    ),
) -> str:
    """[MANDATORY TOOL & SKILL LISTER] 현재 시스템에 연결된 모든 AI 스킬 및 도구 목록을 카테고리별로 깔끔하게 그룹핑하여 조회합니다. 사용자가 '연결된 도구 목록', '도구 목록', '스킬 목록', '사용 가능한 기능', '무슨 도구가 있어?' 등을 묻거나 도구 현황을 파악하고자 할 때 반드시 1순위로 호출해야 하는 도구입니다."""
    def _run():
        skills = load_all_skills_registry()
        if not skills:
            return "ℹ️ 등록된 스킬이 없습니다."

        skills_dir = get_skills_dir()

        # 카테고리 필터링
        cat_filter = category if isinstance(category, str) and category.strip() else None
        if cat_filter:
            cat_clean = cat_filter.strip().lower()
            skills = [s for s in skills if s["category"].lower() == cat_clean]
            if not skills:
                return f"ℹ️ 카테고리 '{cat_filter}'에 속한 스킬이 없습니다."

        # 카테고리별 그룹핑
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for s in skills:
            cat = s["category"] or "General"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(s)

        output_lines = [
            f"📋 **등록된 AI 스킬 목록 (총 {len(skills)}개)**",
            f"📁 저장 위치: `{skills_dir}`",
            "",
        ]

        for cat_name, items in sorted(grouped.items()):
            output_lines.append(f"### 📂 [{cat_name}]")
            for item in items:
                trig_str = f" *(트리거: {', '.join(item['triggers'])})*" if item['triggers'] else ""
                output_lines.append(f"- **`{item['name']}`**: {item['description']}{trig_str}")
            output_lines.append("")

        output_lines.append("💡 특정 스킬의 세부 지침을 확인하려면 `skills_get(name)`을 호출하세요.")
        return "\n".join(output_lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_search(
    query: str = Field(
        description="검색할 키워드 또는 주제 (예: '보안', '코드', '프롬프트', 'email', 'python')",
        examples=["보안", "코드", "프롬프트", "이메일"],
    ),
) -> str:
    """[스킬 검색] 키워드나 주제를 입력하여 관련된 AI 스킬을 빠르게 검색합니다."""
    def _run():
        skills = load_all_skills_registry()
        if not skills:
            return "ℹ️ 등록된 스킬이 없습니다."

        q_text = query if isinstance(query, str) else str(query or "")
        q_lower = q_text.strip().lower()
        matched = []

        for s in skills:
            # 이름, 설명, 카테고리, 트리거에서 검색
            in_name = q_lower in s["name"].lower()
            in_desc = q_lower in s["description"].lower()
            in_cat = q_lower in s["category"].lower()
            in_trig = any(q_lower in str(t).lower() for t in s["triggers"])

            if in_name or in_desc or in_cat or in_trig:
                matched.append(s)

        if not matched:
            return f"🔍 '{q_text}' 검색어와 일치하는 스킬을 찾지 못했습니다. `skills_list()`로 전체 목록을 확인해보세요."

        lines = [
            f"🔍 **'{q_text}' 관련 스킬 검색 결과 (총 {len(matched)}개)**",
            "",
        ]
        for s in matched:
            trig_str = f" *(트리거: {', '.join(s['triggers'])})*" if s['triggers'] else ""
            lines.append(f"- **`{s['name']}`** [{s['category']}]: {s['description']}{trig_str}")

        lines.append("")
        lines.append("💡 스킬을 실행하려면 `skills_smart_run(user_request, skill_name)`을 호출하세요.")
        return "\n".join(lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_get(
    name: str = Field(
        description="로드할 스킬의 식별자 이름 (예: 'code-reviewer', 'security-notice', 'prompt-optimizer')",
    ),
) -> str:
    """[MANDATORY SKILL LOADER] 특정 스킬의 전체 지침 전문(SKILL.md)을 로드합니다. 사용자가 스킬 관련 작업을 요구할 때 먼저 호출하여 지침을 가져옵니다."""
    def _run():
        skills = load_all_skills_registry()
        clean_name = name.strip().lower().replace("_", "-")

        target_skill = None
        for s in skills:
            if s["name"].lower() == clean_name or s["dir_name"].lower() == clean_name:
                target_skill = s
                break

        if not target_skill:
            available = [s["name"] for s in skills]
            return f"❌ 스킬 '{name}'을(를) 찾을 수 없습니다.\n사용 가능한 스킬 목록: {available}"

        s_name = target_skill["name"]
        raw_content = target_skill["raw_content"]

        return (
            f"{raw_content}\n\n---\n"
            f"⚡ **[AI 어시스턴트 지침]**: 답변을 작성할 때 반드시 최상단 첫 줄에 "
            f"`### 🎯 [적용 스킬: {s_name}]` 말머리를 붙이고 위 지침에 따라 최종 답변을 완성하십시오."
        )

    return await asyncio.to_thread(_run)


@mcp.tool()
async def skills_create_or_update(
    name: str = Field(
        description="스킬 고유 식별자 (영문, 소문자, 하이픈 권장. 예: security-notice, code-reviewer)",
        examples=["security-notice", "prompt-optimizer", "git-commit-helper"],
    ),
    description: str = Field(
        description="스킬의 주요 목적과 기능에 대한 요약 설명",
        examples=["매월 정기 보안공지 메일을 작성합니다."],
    ),
    instructions: str = Field(
        description="스킬 실행 시 에이전트가 준수해야 할 상세 마크다운 가이드/지침",
    ),
    category: str = Field(
        default="General",
        description="스킬 분류 카테고리 (예: Development, Communication, Prompt Engineering, Utility)",
    ),
    triggers: str = Field(
        default="",
        description="스킬 자동 활성화 키워드 목록 (쉼표 구분. 예: 보안공지, 보안 공지, 보안메일)",
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
        skills = load_all_skills_registry()
        clean_name = name.strip().lower().replace("_", "-")

        target_skill = None
        for s in skills:
            if s["name"].lower() == clean_name or s["dir_name"].lower() == clean_name:
                target_skill = s
                break

        if not target_skill:
            return f"❌ 삭제 대상 스킬 폴더를 찾을 수 없습니다: '{name}'"

        target_dir = target_skill["file_path"].parent

        try:
            send_to_recycle_bin(target_dir)
            return f"🗑️ 스킬 `{target_skill['name']}` 폴더를 OS 휴지통으로 안전하게 이동했습니다 (경로: `{target_dir}`)."
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
