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
    type: str = Field(default="direct", description="스킬 유형: 'direct' (직접 변환형) 또는 'chain' (연쇄 확장형)")
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

    script_dir = Path(__file__).parent.resolve()
    target = script_dir / "skills"
    if target.exists():
        return target

    # CWD 기준 후보 탐색
    cwd = Path.cwd().resolve()
    for candidate in [cwd / "skills", cwd / "MCP_Servers" / "skills"]:
        if candidate.exists():
            return candidate

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
    skill_type: str = "direct",
    category: str = "General",
    triggers: Optional[List[str]] = None,
) -> str:
    """표준 YAML Frontmatter + Markdown 포맷 문자열을 생성합니다."""
    triggers = triggers or []
    lines = [
        "---",
        f"name: {name}",
        f"type: {skill_type}",
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
                    s_type = meta.get("type") or ("chain" if any(k in str(s_name).lower() for k in ["optimizer", "refine", "planner", "research"]) else "direct")
                    s_trig = meta.get("triggers") or []
                    if isinstance(s_trig, str):
                        s_trig = [t.strip() for t in s_trig.split(",") if t.strip()]

                    registry.append({
                        "name": str(s_name).strip(),
                        "dir_name": item.name,
                        "type": str(s_type).strip(),
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

@mcp.tool(name="skills_smart_run")
async def skills_smart_run(
    user_request: str = Field(
        description="사용자의 작업 요청 내용 (예: '프롬프트 개선해줘', '보안공지 써줘', 'Python 코드 리뷰해줘')",
        examples=[
            "8월 보안공지 메일 작성해줘",
            "다음 Python 코드를 리뷰하고 최적화해줘",
            "영어 번역을 잘 해주는 LLM 프롬프트 만들어줘",
        ],
    ),
    skill_name: Optional[str] = Field(
        default=None,
        description="특정 스킬을 직접 지정할 때 스킬 식별자 입력 (예: 'prompt-optimizer', 'security-notice', 'code-reviewer'). 비워두면 요청 내용을 분석하여 최적의 스킬을 자동 선택합니다.",
        examples=["prompt-optimizer", "security-notice", "code-reviewer", None],
    ),
) -> str:
    """[원스톱 AI 스킬 실행 도구] 사용자의 요청을 분석하여 등록된 최적의 전문가 스킬(SKILL.md)을 매칭하고, 프롬프트 개선·코드 리뷰·보안공지 등의 표준 지침을 온디맨드로 로드합니다."""
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

        # 2. 동적 트리거 및 유사도 기반 자동 매칭 (한국어 공백 무시 비교 지원)
        if not selected_skill:
            req_lower = req_text.lower()
            req_no_space = re.sub(r"\s+", "", req_lower)
            best_score = 0
            best_skill = None

            for sk in skills:
                score = 0
                # (a) triggers 키워드 매칭 (가장 높은 가중치 + 공백 무시 비교)
                for trig in sk["triggers"]:
                    t_lower = str(trig).lower()
                    t_no_space = re.sub(r"\s+", "", t_lower)
                    if t_lower and (t_lower in req_lower or t_no_space in req_no_space):
                        score += 25 + len(t_lower)

                # (b) 스킬 이름 매칭
                s_name_lower = sk["name"].lower()
                s_name_no_space = re.sub(r"[_\-\s]+", "", s_name_lower)
                if s_name_lower in req_lower or s_name_no_space in req_no_space:
                    score += 15

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
            "⚡ **[AI 어시스턴트 최종 답변 지침 (Gemma 4 준수 표준)]**:",
            f"1. 최상단 첫 줄: `### 🎯 [적용 스킬: {s_name}]`",
            "2. '이 템플릿을 복사해서 AI에게 다시 질문하세요' 같은 불필요한 메타 설명은 일체 배제하십시오.",
            "3. 사용자가 요청한 질문에 대해, 위 스킬 지침으로 **최적화/개선된 전문가 기준을 즉시 적용하여 완성된 최종 결과물 본문만을 곧바로 작성**하여 제공하십시오.",
        ]
        return "\n".join(workflow)

    return await asyncio.to_thread(_run)


@mcp.tool(name="skills_list")
async def skills_list(
    category: Optional[str] = Field(
        default=None,
        description="특정 카테고리만 필터링하여 조회하려는 경우 입력 (예: 'Development', 'Communication', 'Prompt Engineering'). 비워두면 전체 카테고리별로 그룹핑하여 조회합니다.",
        examples=["Development", "Communication", None],
    ),
) -> str:
    """현재 시스템에 등록된 모든 AI 스킬 목록을 카테고리 및 유형(direct vs chain)별로 조회합니다."""
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
                type_tag = "⚡ [직접 변환형]" if item.get("type") == "direct" else "🔄 [연쇄 확장형]"
                trig_str = f" *(트리거: {', '.join(item['triggers'][:4])})*" if item['triggers'] else ""
                output_lines.append(f"- **`{item['name']}`** `{type_tag}`: {item['description']}{trig_str}")
            output_lines.append("")

        output_lines.append("💡 스킬을 실행하려면 `skills_smart_run(user_request)`를 호출하세요.")
        output_lines.append("💡 새 스킬을 만들려면 `skills_smart_create(topic_or_idea)`를 호출하세요.")
        return "\n".join(output_lines)

    return await asyncio.to_thread(_run)


@mcp.tool(name="skills_search")
async def skills_search(
    query: str = Field(
        description="검색할 키워드 또는 주제 (예: '보안', '코드', '프롬프트', 'email', 'python')",
        examples=["보안", "코드", "프롬프트", "이메일"],
    ),
) -> str:
    """키워드나 주제를 입력하여 관련된 AI 스킬을 빠르게 검색합니다."""
    def _run():
        skills = load_all_skills_registry()
        if not skills:
            return "ℹ️ 등록된 스킬이 없습니다."

        q_text = query if isinstance(query, str) else str(query or "")
        q_lower = q_text.strip().lower()
        matched = []

        for s in skills:
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
            type_tag = "⚡ 직접 변환" if s.get("type") == "direct" else "🔄 연쇄 확장"
            trig_str = f" *(트리거: {', '.join(s['triggers'][:4])})*" if s['triggers'] else ""
            lines.append(f"- **`{s['name']}`** `[{type_tag}]`: {s['description']}{trig_str}")

        lines.append("")
        lines.append("💡 스킬을 실행하려면 `skills_smart_run(user_request, skill_name)`을 호출하세요.")
        return "\n".join(lines)

    return await asyncio.to_thread(_run)


@mcp.tool(name="skills_get")
async def skills_get(
    name: str = Field(
        description="로드할 스킬의 식별자 이름 (예: 'code-reviewer', 'security-notice', 'prompt-optimizer')",
    ),
) -> str:
    """특정 스킬의 전체 지침 전문(SKILL.md)을 로드합니다."""
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


@mcp.tool(name="skills_smart_create")
async def skills_smart_create(
    topic_or_idea: str = Field(
        description="만들고자 하는 스킬에 대한 자연어 설명이나 아이디어 (예: '사투리로 친절하게 설명해주는 스킬', '회의록 요약 스킬', '영문 비즈니스 메일 작성기')",
    ),
    skill_type: str = Field(
        default="auto",
        description="스킬 아키텍처 유형: 'direct' (Type 1 직접 변환형: 요청 ➔ 즉시 변환 응답), 'chain' (Type 2 연쇄 확장형: 요청 ➔ 프롬프트 고도화 ➔ 최종 응답), 'auto' (자동 판별)",
    ),
    name: Optional[str] = Field(
        default=None,
        description="스킬 고유 영문 식별자 (생략 시 아이디어에 맞춰 자동 작명. 예: saturi-explainer, meeting-summarizer)",
    ),
    category: Optional[str] = Field(
        default=None,
        description="스킬 카테고리 (생략 시 Communication, Development, Productivity, General 등 자동 분류)",
    ),
) -> str:
    """[원클릭 스마트 스킬 제작 도구] 사용자가 자연어로 아이디어만 말해도, 적합한 스킬 유형(direct: 직접 변환형 vs chain: 연쇄 확장형)을 자동 판별하여 고품질 SKILL.md 지침과 풍부한 트리거 키워드를 갖춘 완성형 스킬을 자동으로 생성 및 등록합니다."""
    def _run():
        skills_dir = get_skills_dir()
        topic = topic_or_idea.strip() if isinstance(topic_or_idea, str) else str(topic_or_idea or "").strip()
        if not topic:
            return "❌ 스킬로 제작할 아이디어 또는 설명을 입력해주세요."

        # 1. 스킬 유형 자동 판별 (direct vs chain)
        raw_type = skill_type.lower().strip() if isinstance(skill_type, str) else "auto"
        if raw_type not in ("direct", "chain"):
            if any(k in topic for k in ["프롬프트", "기획", "심층", "리서치", "연구", "설계", "고도화", "브레인스토밍", "아이디어", "캔버스"]):
                chosen_type = "chain"
            else:
                chosen_type = "direct"
        else:
            chosen_type = raw_type

        # 2. 영문 식별자(name) 자동 작명
        clean_name = name.strip().lower() if isinstance(name, str) and name.strip() else None
        if not clean_name:
            slug_candidates = []
            if "사투리" in topic: slug_candidates.append("saturi-converter")
            elif "회의" in topic: slug_candidates.append("meeting-summarizer")
            elif "이메일" in topic or "메일" in topic: slug_candidates.append("email-writer")
            elif "보고서" in topic: slug_candidates.append("report-generator")
            elif "번역" in topic: slug_candidates.append("smart-translator")
            elif "코드" in topic: slug_candidates.append("code-helper")
            elif "요약" in topic: slug_candidates.append("text-summarizer")
            else:
                words = re.findall(r"[a-zA-Z0-9]+", topic)
                if words:
                    slug_candidates.append("-".join(words[:3]).lower())
                else:
                    slug_candidates.append(f"custom-skill-{abs(hash(topic)) % 1000:03d}")
            clean_name = slug_candidates[0]

        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", clean_name).strip("-").lower()

        # 3. 카테고리 자동 분류
        chosen_cat = category.strip() if isinstance(category, str) and category.strip() else None
        if not chosen_cat:
            if any(k in topic for k in ["말투", "어조", "메일", "이메일", "방송", "공지", "스피치", "사투리"]):
                chosen_cat = "Communication"
            elif any(k in topic for k in ["코드", "프로그래밍", "버그", "파이썬", "리팩토링"]):
                chosen_cat = "Development"
            elif any(k in topic for k in ["회의", "보고서", "문서", "기획", "요약", "업무"]):
                chosen_cat = "Productivity"
            elif any(k in topic for k in ["프롬프트", "LLM", "최적화"]):
                chosen_cat = "Prompt Engineering"
            else:
                chosen_cat = "General"

        # 4. 풍부한 한국어 동의어 트리거 생성 (조사 자동 분리 및 어휘 확장)
        triggers = []
        raw_words = re.findall(r"[\w가-힣]{2,}", topic)
        clean_words = []
        for w in raw_words:
            # 주요 조사 제거
            cw = re.sub(r"(으로|로는|에게|에서|으로|로|를|을|에|의|은|는|이|가|과|와|도|만|처럼)$", "", w)
            if len(cw) >= 2 and cw not in clean_words:
                clean_words.append(cw)

        for w in clean_words:
            if w not in triggers:
                triggers.append(w)
                if chosen_type == "direct":
                    triggers.append(f"{w} 말투")
                    triggers.append(f"{w} 변환")
                else:
                    triggers.append(f"{w} 기획")
                    triggers.append(f"{w} 작성")
                triggers.append(f"{w} 해줘")
        if not triggers:
            triggers = [clean_name.replace("-", " "), clean_name]

        # 5. 고품질 SKILL.md 본문 자동 생성 (Gemma 4 최적화)
        if chosen_type == "direct":
            type_title = "Type 1: 직접 변환형 (Direct Transform)"
            instructions = f"""## 핵심 역할 및 변환 원칙
1. **불필요한 서론 생략**: "원문을 분석했습니다" 같은 메타 설명이나 잡담을 일체 배제하고, 변환된 완성 결과물 본문을 즉시 출력합니다.
2. **신뢰감과 명료성의 극대화**: 사용자의 요청 의도(`{topic}`)에 맞추어 전문적이고 일관된 어조 및 포맷으로 정제합니다.
3. **완성형 결과물 직행**: 사용자가 즉시 복사하여 활용할 수 있도록 군더더기 없는 완성본을 제공합니다.

## 표준 응답 포맷 (Gemma 4):
```markdown
### 🎯 [적용 스킬: {clean_name}]
> 💡 *사용자 요청을 '{topic}' 스킬 규칙에 따라 정제하여 작성된 결과입니다.*

(여기서부터 스킬 규칙이 적용된 완성형 결과물 본문을 곧바로 작성)
```"""
        else:
            type_title = "Type 2: 연쇄 확장형 (Refine-and-Execute Chain)"
            instructions = f"""## 핵심 역할 및 실행 원칙
1. **전문가 프레임워크 즉시 적용**: 사용자의 요청(`{topic}`)을 분석하여, 단순 단답형이 아닌 전문가 페르소나, 핵심 분석 기준표, 상황별 맞춤 추천 등 깊이 있는 구조로 최적화합니다.
2. **불필요한 메타 설명 배제**: "이 템플릿을 복사해서 다시 질문하세요" 같은 잡담이나 중간 복사용 템플릿을 늘어놓지 않습니다.
3. **완성형 결과물 즉시 도출**: 고도화된 프레임워크를 AI가 스스로 즉시 실행하여, 사용자가 실제로 얻고자 하는 **최종 심층 완성본**을 즉시 제공합니다.

## 표준 응답 포맷 (Gemma 4):
```markdown
### 🎯 [적용 스킬: {clean_name}]
> 💡 *사용자 요청을 전문가 심층 분석 및 최적화 프레임워크로 발전시켜 도출한 결과입니다.*

(여기서부터 고도화된 기준이 적용된 완성형 최종 결과물 본문을 곧바로 작성)
```"""

        formatted_content = format_skill_markdown(
            name=clean_name,
            description=f"{topic} 작업을 수행하는 전문 AI 스킬입니다.",
            instructions=instructions,
            skill_type=chosen_type,
            category=chosen_cat,
            triggers=triggers[:8],
        )

        target_dir = skills_dir / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"
        skill_file.write_text(formatted_content, encoding="utf-8")

        return f"""🎉 **스킬 `{clean_name}` 생성이 완벽하게 완료되었습니다!**

📁 **저장 경로**: `{skill_file}`
🏷️ **스킬 유형**: `{type_title}`
📂 **카테고리**: `{chosen_cat}`
🎯 **자동 활성화 키워드 (Triggers)**: {', '.join(f'`{t}`' for t in triggers[:6])}

💡 **테스트 방법**:
대화창에 `"{triggers[0]}"` 키워드를 포함하여 질문하시면, Gemma 4가 새로 만든 스킬을 자동으로 감지하여 완벽하게 답변합니다!"""

    return await asyncio.to_thread(_run)


@mcp.tool(name="skills_create_or_update")
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
    skill_type: str = Field(
        default="direct",
        description="스킬 유형: 'direct' (직접 변환형) 또는 'chain' (연쇄 확장형)",
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
    """[스킬 직접 등록/수정] 모든 필드를 직접 작성하여 표준 SKILL.md 파일로 영구 저장합니다."""
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
            skill_type=skill_type.strip() or "direct",
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
1. [스킬 실행]: 전문 작업(코드 분석, 프롬프트 개선, 번역, 톤 변환 등)을 요청받으면, 직접 추측하여 대답하지 말고 `skills_smart_run(user_request)`를 호출하십시오.
2. [스킬 생성]: 사용자가 새로운 스킬 생성을 요청했을 때, 스킬 유형이 명시되지 않았다면 다음 2가지 유형 중 어떤 것으로 제작할지 사용자에게 먼저 친절히 확인받으십시오:
   - 1️⃣ [Type 1: 직접 변환형 (요청 ➔ 직접 변환 응답)]: 입력된 문장을 해당 톤/스타일로 즉시 변환 (예: 아나운서 말투, 사투리 변환, 공지문 등)
   - 2️⃣ [Type 2: 연쇄 확장형 (요청 ➔ 프롬프트 고도화 ➔ 최종 응답)]: 질문을 전문가 프레임워크로 고도화한 뒤 최종 답변을 도출 (예: 프롬프트 최적화, 기획안 등)
   - 사용자가 선택하거나 확인하면 `skills_smart_create(topic_or_idea, skill_type='direct'|'chain')`을 호출하여 스킬을 즉시 생성하십시오.
3. 답변을 작성할 때는 반드시 최상단 첫 줄에 `### 🎯 [적용 스킬: <스킬명>]` 형식의 말머리를 명시하십시오."""


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
    parser.add_argument(
        "--direct",
        action="store_true",
        help="터미널에서 직접 스킬 매칭 및 실행 결과를 테스트하는 대화형 모드",
    )
    args = parser.parse_args()

    if args.skills_dir:
        os.environ["SKILLS_DIR"] = str(Path(args.skills_dir).expanduser().resolve())

    # 스킬 디렉토리 존재 확인
    skills_path = get_skills_dir()
    print(f"📂 Skills Root Directory: {skills_path}", file=sys.stderr)

    if args.direct:
        print("\n🚀 [Skills MCP Server 대화형 직접 테스트 모드]", file=sys.stderr)
        print("명령을 입력하면 적합한 스킬 매칭 및 실행 가이드라인을 출력합니다. ('exit' 종료)\n", file=sys.stderr)
        while True:
            try:
                user_input = input("User > ").strip()
                if not user_input or user_input.lower() in ("exit", "quit", "q"):
                    break
                res = asyncio.run(skills_smart_run(user_request=user_input))
                print(f"\n[Skills Output]\n{res}\n")
            except (KeyboardInterrupt, EOFError):
                break
        sys.exit(0)

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
