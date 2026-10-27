"""wiki-mcp-server.py - 계층형 서브폴더(분야별) 및 양방향 링크를 지원하는 LLM-Native Wiki FastMCP 서버.

주요 특징:
1. 분야별 서브폴더(예: `14_CFR_Part33/`, `Development/`, `General/`) 구조 자동 관리
2. `rglob("*.md")` 재귀 스캔을 통한 도메인 융합 양방향 위키 링크(`[[문서명]]`) 및 역링크(Backlinks) 통합 그래프
3. 사람(탐색기/옵시디언)에게는 깔끔한 폴더 구조, AI에게는 단일 통합 지식 그래프 제공
4. Windows 네이티브 휴지통 안전 삭제 (Safe Delete)
5. CORS 전체 허용 및 HTTP / SSE / stdio 전송 방식 지원 (기본 포트: 8003)

제공 도구 (총 6개):
1. wiki_read - 위키 문서 본문 및 링크/역링크(Backlinks) 통합 조회 (하위 모든 폴더 자동 탐색)
2. wiki_create_or_update - 위키 문서 생성 또는 내용 갱신 (카테고리별 서브폴더 자동 분류 저장)
3. wiki_search - 키워드, 태그, 카테고리(서브폴더) 기반 위키 지식 통합 검색
4. wiki_list_all - 전체 위키 문서 목차 및 서브폴더(카테고리)별 트리 구조 색인
5. wiki_backlinks - 특정 문서를 참조하고 있는 모든 연관 문서(역링크) 역추적
6. wiki_delete_to_trash - 위키 문서를 OS 휴지통으로 안전하게 이동
"""

import asyncio
from datetime import datetime
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from fastmcp import FastMCP
from pydantic import Field
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
mcp = FastMCP("Wiki-Knowledge-MCP-Server")

# 위키 마크다운 파일 저장소 디렉토리 결정 (절대 경로 보장)
def get_wiki_dir() -> Path:
    env_dir = os.environ.get("WIKI_DATA_DIR", "")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    default_p = (Path(__file__).resolve().parent / "wiki_data").resolve()
    default_p.mkdir(parents=True, exist_ok=True)
    return default_p

WIKI_DIR = get_wiki_dir()


# ==============================================================================
# 1. 헬퍼 유틸리티 (YAML 파서, 위키 링크 파서, 계층형 파일 관리, 휴지통)
# ==============================================================================

def ensure_wiki_dir() -> Path:
    """위키 데이터 루트 디렉토리를 생성하고 반환합니다."""
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    return WIKI_DIR


def sanitize_filename(name: str) -> str:
    """파일명 또는 폴더명으로 사용할 수 없는 특수문자를 언더스코어로 안전하게 치환합니다."""
    clean = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', name).strip()
    return clean if clean else "untitled"


def extract_wiki_links(text: str) -> List[str]:
    """본문 내의 [[문서명]] 패턴을 찾아 링크 목록을 추출합니다."""
    if not text:
        return []
    matches = re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text)
    cleaned = [m.strip() for m in matches if m.strip()]
    return list(dict.fromkeys(cleaned))


def parse_frontmatter_and_content(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """마크다운 파일에서 YAML Frontmatter와 순수 본문을 분리하여 파싱합니다."""
    rel_parent = file_path.parent.relative_to(WIKI_DIR) if file_path.parent != WIKI_DIR else None
    default_cat = str(rel_parent).replace("\\", "/") if rel_parent and str(rel_parent) != "." else "일반"

    meta: Dict[str, Any] = {
        "title": file_path.stem,
        "tags": [],
        "category": default_cat,
        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except Exception:
        raw_text = file_path.read_text(encoding="cp949", errors="replace")

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body_text = parts[2].strip()

            for line in fm_text.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "title" and v:
                    meta["title"] = v.strip("'\"")
                elif k == "category" and v:
                    meta["category"] = v.strip("'\"")
                elif k == "created_at" and v:
                    meta["created_at"] = v.strip("'\"")
                elif k == "updated_at" and v:
                    meta["updated_at"] = v.strip("'\"")
                elif k == "tags":
                    if v.startswith("[") and v.endswith("]"):
                        items = [t.strip().strip("'\"") for t in v[1:-1].split(",") if t.strip()]
                        meta["tags"] = items
                    elif v:
                        meta["tags"] = [t.strip() for t in v.split(",") if t.strip()]

            return meta, body_text

    return meta, raw_text.strip()


def build_markdown_document(title: str, content: str, tags: Optional[List[str]] = None, category: str = "일반", created_at: Optional[str] = None) -> str:
    """메타데이터와 본문을 결합하여 표준 위키 마크다운 문서를 생성합니다."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c_time = created_at or now_str
    tag_list = tags if tags else []

    fm_lines = [
        "---",
        f"title: \"{title}\"",
        f"category: \"{category}\"",
        f"tags: [{', '.join(f'\"{t}\"' for t in tag_list)}]",
        f"created_at: \"{c_time}\"",
        f"updated_at: \"{now_str}\"",
        "---",
        "",
    ]
    return "\n".join(fm_lines) + content.strip() + "\n"


def get_all_wiki_files() -> List[Path]:
    """저장소 내의 모든 서브폴더 마크다운 위키 파일 목록을 재귀적으로 반환합니다 (rglob)."""
    ensure_wiki_dir()
    return sorted(WIKI_DIR.rglob("*.md"))


def find_wiki_file(name_or_title: str) -> Optional[Path]:
    """파일명, 상대경로 또는 문서 제목을 기준으로 하위 모든 서브폴더에서 대상 파일을 찾습니다."""
    files = get_all_wiki_files()
    clean_target = sanitize_filename(Path(name_or_title).stem).lower()
    target_path_clean = str(Path(name_or_title)).replace("\\", "/").lower()

    # 1. 파일명 정확 일치 (stem 일치)
    for f in files:
        if f.stem.lower() == clean_target:
            return f

    # 2. 상대 경로 일치 (예: 14_CFR_Part33/33.28)
    for f in files:
        rel_str = str(f.relative_to(WIKI_DIR)).replace("\\", "/").lower()
        if target_path_clean in rel_str or rel_str.startswith(target_path_clean):
            return f

    # 3. 문서 제목(title) 메타데이터 일치
    for f in files:
        meta, _ = parse_frontmatter_and_content(f)
        if meta.get("title", "").lower() == name_or_title.strip().lower():
            return f

    # 4. 부분 일치 검색
    for f in files:
        if clean_target in f.stem.lower():
            return f

    return None


def build_backlinks_index() -> Dict[str, Set[str]]:
    """전체 위키 서브폴더를 스캔하여 대상 문서별 역링크(이 문서를 참조하는 문서들) 색인을 생성합니다."""
    backlinks: Dict[str, Set[str]] = {}
    files = get_all_wiki_files()

    for f in files:
        source_name = f.stem
        meta, body = parse_frontmatter_and_content(f)
        outgoing_links = extract_wiki_links(body)

        for target in outgoing_links:
            target_clean = sanitize_filename(Path(target).stem).lower()
            if target_clean not in backlinks:
                backlinks[target_clean] = set()
            backlinks[target_clean].add(meta.get("title") or source_name)

    return backlinks


def send_to_recycle_bin(target_path: Path) -> bool:
    """Windows 네이티브 휴지통으로 안전 삭제합니다."""
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
        raise NotImplementedError("휴지통 이동 기능은 Windows 환경을 기본 지원합니다.")


# ==============================================================================
# 2. 초기 샘플 데이터 시딩 (분야별 서브폴더 구조: 14_CFR_Part33)
# ==============================================================================

def init_sample_cfr_data():
    """분야별 서브폴더(14_CFR_Part33)에 14 CFR Part 33 감항 기준 샘플 위키 문서를 기본 생성합니다."""
    ensure_wiki_dir()
    cfr_dir = WIKI_DIR / "14_CFR_Part33"
    cfr_dir.mkdir(parents=True, exist_ok=True)

    sample_files = list(WIKI_DIR.rglob("*.md"))
    if sample_files:
        # 혹시 기존 루트에 플랫하게 남아있는 샘플 파일이 있다면 서브폴더로 이동 정리
        for f in WIKI_DIR.glob("33.*.md"):
            dest = cfr_dir / f.name
            if not dest.exists():
                f.rename(dest)
        return

    # 1. 33.28 엔진 제어 시스템
    doc_33_28 = """# 14 CFR § 33.28 - Engine Control Systems (엔진 제어 시스템)

## 1. 개요 및 요구조건
엔진 제어 시스템(FADEC 등)은 모든 정상 및 비정상 운용 조건에서 엔진이 승인된 제한치 내에서 안전하게 작동하도록 설계되어야 합니다.

## 2. 상호 참조 및 필수 연계 조항 (Cross-References)
- **안전성 분석 연계**: 제어 시스템의 고장 모드 및 영향 분석(FMEA)은 반드시 [[33.75_Safety_Analysis]]의 감항 요건을 충족해야 합니다.
- **내구성 시험 검증**: 제어 시스템의 기능 및 소프트웨어/하드웨어 신뢰성은 [[33.87_Endurance_Test]]에서 규정하는 가혹 시험 조건에서 검증되어야 합니다.
- **연료 시스템 인터페이스**: 전기/전자 제어 장치는 [[33.67_Fuel_System]]과의 압력 및 유량 제어 인터페이스가 정합되어야 합니다.

## 3. 고장 안전(Fail-Safe) 요구사항
단일 고장이 발생하더라도 엔진 추력의 위험한 급변(LOTC: Loss of Thrust Control)이 발생해서는 안 됩니다.
"""
    f1 = cfr_dir / "33.28_Engine_Control_Systems.md"
    f1.write_text(build_markdown_document("14 CFR § 33.28 - Engine Control Systems", doc_33_28, ["CFR", "Part33", "FADEC", "제어시스템"], "14_CFR_Part33"), encoding="utf-8")

    # 2. 33.75 안전성 분석
    doc_33_75 = """# 14 CFR § 33.75 - Safety Analysis (엔진 안전성 분석)

## 1. 개요
엔진 시스템 전반에 걸쳐 발생 가능한 잠재적 고장을 분석하고 위험도를 평가해야 합니다.

## 2. 고장 중대성 분류
1. **극히 희박한 고장(Extremely Improbable)**: 파국적 결과(Catastrophic)를 초래하는 고장은 $10^{-9}$ / flight hour 이하이어야 함.
2. **주요 고장(Hazardous Engine Effects)**: 화재, 비격납 파손, 제어 불능 등.

## 3. 연계 하위 시스템
- [[33.28_Engine_Control_Systems]]의 소프트웨어/전자 고장 확률 분석
- [[33.67_Fuel_System]]의 누유 및 연료 차단 밸브 신뢰성 분석
"""
    f2 = cfr_dir / "33.75_Safety_Analysis.md"
    f2.write_text(build_markdown_document("14 CFR § 33.75 - Safety Analysis", doc_33_75, ["CFR", "Part33", "Safety", "안전성평가"], "14_CFR_Part33"), encoding="utf-8")

    # 3. 33.87 내구성 시험
    doc_33_87 = """# 14 CFR § 33.87 - Endurance Test (엔진 내구성 블록 시험)

## 1. 개요
엔진이 극한의 출력, 온도, 진동 조건에서 최소 요구 운용 수명을 충족하는지 입증하기 위한 가혹 시험(통상 150시간 블록 테스트)입니다.

## 2. 필수 시험 연계 항목
- [[33.28_Engine_Control_Systems]]: 최대 이륙 추력(Takeoff Rating) 및 OEI(One Engine Inoperative) 조건에서의 제어 응답성 입증.
- 과열 및 과회전 방지 계통 동작 검증.
"""
    f3 = cfr_dir / "33.87_Endurance_Test.md"
    f3.write_text(build_markdown_document("14 CFR § 33.87 - Endurance Test", doc_33_87, ["CFR", "Part33", "Endurance", "내구성시험"], "14_CFR_Part33"), encoding="utf-8")


# ==============================================================================
# 3. FastMCP 도구 정의 (총 6개)
# ==============================================================================

@mcp.tool()
async def wiki_read(
    title: str = Field(
        description="읽을 위키 문서의 제목 또는 파일명 (서브폴더 경로 또는 파일명만 입력 가능. 예: '33.28_Engine_Control_Systems', '14_CFR_Part33/33.75_Safety_Analysis')",
        examples=["33.28_Engine_Control_Systems", "33.75_Safety_Analysis", "FastMCP_Tips"],
    ),
) -> str:
    """[위키 문서 읽기] 하위 모든 서브폴더를 자동 탐색하여 문서 본문과 함께, 본문이 참조하는 링크 및 이 문서를 참조하는 역링크(Backlinks) 목록을 통합 반환합니다."""
    def _run():
        ensure_wiki_dir()
        t_str = str(title).strip() if title and isinstance(title, str) else ""
        if not t_str:
            return "❌ 읽을 위키 문서 제목을 지정해주세요."

        target_file = find_wiki_file(t_str)
        if not target_file or not target_file.exists():
            return f"❌ 위키 문서 `{t_str}`을(를) 찾을 수 없습니다.\n`wiki_list_all()` 또는 `wiki_search()`로 사용 가능한 문서 목록을 확인하세요."

        meta, body = parse_frontmatter_and_content(target_file)
        outgoing_links = extract_wiki_links(body)

        backlinks_idx = build_backlinks_index()
        current_title_key = target_file.stem.lower()
        incoming_links = sorted(list(backlinks_idx.get(current_title_key, set())))

        rel_path = target_file.relative_to(WIKI_DIR)

        header_lines = [
            f"# 📖 {meta.get('title', target_file.stem)}",
            f"- **저장 경로**: `{rel_path}`",
            f"- **분야(카테고리)**: {meta.get('category', '일반')}",
            f"- **태그**: {', '.join(meta.get('tags', [])) if meta.get('tags') else '(없음)'}",
            f"- **최종 수정일**: {meta.get('updated_at', '알 수 없음')}",
            "",
            "---",
            "",
            body,
            "",
            "---",
            "### 🔗 연결 관계망 (Knowledge Graph)",
        ]

        if outgoing_links:
            header_lines.append(f"- ➡️ **이 문서가 참조하는 조항/문서 (Outgoing Links)**: {', '.join(f'[[{l}]]' for l in outgoing_links)}")
        else:
            header_lines.append("- ➡️ **이 문서가 참조하는 조항/문서**: (없음)")

        if incoming_links:
            header_lines.append(f"- ⬅️ **이 문서를 참조하고 있는 상위/연관 조항 (Backlinks)**: {', '.join(f'[[{l}]]' for l in incoming_links)}")
        else:
            header_lines.append("- ⬅️ **이 문서를 참조하고 있는 조항**: (없음)")

        return "\n".join(header_lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_create_or_update(
    title: str = Field(
        description="위키 문서의 제목 (파일명으로 사용됨)",
        examples=["33.67_Fuel_System", "NeuJS_아키텍처", "FMEA_신뢰도_계산"],
    ),
    content: str = Field(
        description="문서의 마크다운 본문 내용 (다른 문서를 인용할 때는 [[문서명]] 형태로 작성)",
        examples=["# 14 CFR § 33.67\n연료 펌프 및 제어는 [[33.28_Engine_Control_Systems]]와 연동됩니다."],
    ),
    tags: Optional[List[str]] = Field(
        default=None,
        description="문서 분류 태그 목록 (예: ['CFR', 'Part33', '연료계통'])",
    ),
    category: str = Field(
        default="일반",
        description="문서가 속할 분야/서브폴더명 (예: '14_CFR_Part33', 'Development', 'General')",
    ),
    append_mode: bool = Field(
        default=False,
        description="True인 경우 기존 문서 내용을 덮어쓰지 않고 하단에 덧붙입니다 (기본값: False)",
    ),
) -> str:
    """[위키 문서 생성/갱신] 분야별 서브폴더를 자동 생성하여 문서를 작성하거나 기존 문서를 보강 및 갱신합니다."""
    def _run():
        ensure_wiki_dir()
        t_str = str(title).strip() if title and isinstance(title, str) else ""
        if not t_str:
            return "❌ 위키 문서 제목을 지정해주세요."

        clean_name = sanitize_filename(Path(t_str).stem)
        cat_folder_name = sanitize_filename(category) if category and str(category).strip() else "일반"

        # 서브폴더 생성
        target_dir = WIKI_DIR / cat_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # 기존 파일 검색 (다른 폴더에 이미 존재할 수도 있음)
        existing_file = find_wiki_file(clean_name)
        target_file = existing_file if existing_file else (target_dir / f"{clean_name}.md")

        created_at = None
        c_text = str(content) if content is not None else ""
        final_content = c_text
        final_tags = tags if isinstance(tags, list) else []
        cat_str = str(category).strip() if isinstance(category, str) and category.strip() else "일반"
        is_append = bool(append_mode) if isinstance(append_mode, bool) else False

        if target_file.exists():
            old_meta, old_body = parse_frontmatter_and_content(target_file)
            created_at = old_meta.get("created_at")
            if not final_tags and old_meta.get("tags"):
                final_tags = old_meta["tags"]
            if cat_str == "일반" and old_meta.get("category"):
                category_val = old_meta["category"]
            else:
                category_val = cat_str

            if is_append:
                final_content = f"{old_body}\n\n## 갱신 내역 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n{c_text}"
            action_desc = "덧붙여 갱신" if is_append else "덮어써서 갱신"
        else:
            category_val = cat_str
            action_desc = "신규 생성"

        doc_text = build_markdown_document(clean_name, final_content, final_tags, category_val, created_at)
        target_file.write_text(doc_text, encoding="utf-8")

        extracted_links = extract_wiki_links(final_content)
        links_info = f" (포함된 위키 링크: {', '.join(f'[[{l}]]' for l in extracted_links)})" if extracted_links else ""
        rel_path = target_file.relative_to(WIKI_DIR)

        return f"✅ 위키 문서 `{clean_name}`이(가) 성공적으로 {action_desc}되었습니다!{links_info}\n저장 위치: `{rel_path}`"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_search(
    query: str = Field(
        description="검색할 키워드 (제목, 본문 내용, 태그)",
        examples=["FADEC", "안전성", "내구성", "제어"],
    ),
    tag: Optional[str] = Field(
        default=None,
        description="특정 태그로 필터링할 경우 지정 (예: 'Part33')",
    ),
    category: Optional[str] = Field(
        default=None,
        description="특정 분야/서브폴더로 필터링할 경우 지정 (예: '14_CFR_Part33', 'Development')",
    ),
) -> str:
    """[위키 지식 검색] 모든 서브폴더를 대상으로 키워드, 태그, 카테고리를 기준으로 관련된 위키 문서들을 통합 검색합니다."""
    def _run():
        files = get_all_wiki_files()
        if not files:
            return "ℹ️ 현재 위키 지식 베이스에 등록된 문서가 없습니다."

        q_lower = str(query).lower().strip() if query and isinstance(query, str) else ""
        tag_filter = str(tag).strip().lower() if tag and isinstance(tag, str) else None
        cat_filter = str(category).strip().lower() if category and isinstance(category, str) else None
        results = []

        for f in files:
            meta, body = parse_frontmatter_and_content(f)
            title = meta.get("title", f.stem)
            cat = meta.get("category", "일반")
            tags_list = meta.get("tags", [])
            rel_path = str(f.relative_to(WIKI_DIR)).replace("\\", "/")

            if tag_filter and tag_filter not in [t.lower() for t in tags_list]:
                continue
            if cat_filter and cat_filter not in cat.lower() and cat_filter not in rel_path.lower():
                continue

            match_score = 0
            match_reasons = []

            if q_lower:
                if q_lower in title.lower():
                    match_score += 10
                    match_reasons.append("제목 일치")
                if any(q_lower in t.lower() for t in tags_list):
                    match_score += 5
                    match_reasons.append("태그 일치")
                if q_lower in cat.lower() or q_lower in rel_path.lower():
                    match_score += 3
                    match_reasons.append("폴더/카테고리 일치")
                if q_lower in body.lower():
                    match_score += 2
                    match_reasons.append("본문 포함")

                if match_score == 0:
                    continue
            else:
                match_score = 1

            snippet = body.replace("\n", " ").strip()
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."

            results.append({
                "score": match_score,
                "title": title,
                "name": f.stem,
                "path": rel_path,
                "category": cat,
                "tags": tags_list,
                "snippet": snippet,
                "reasons": match_reasons,
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        if not results:
            return f"🔍 검색어 `{query}`에 일치하는 위키 문서를 찾지 못했습니다."

        lines = [
            f"🔍 **[위키 지식 검색 결과 (총 {len(results)}건)]**",
            "",
        ]
        for idx, r in enumerate(results, 1):
            reasons_str = f" ({', '.join(r['reasons'])})" if r['reasons'] else ""
            tags_str = f" `[{', '.join(r['tags'])}]`" if r['tags'] else ""
            lines.append(f"{idx}. 📄 **`{r['name']}`** (`{r['path']}`){reasons_str}")
            lines.append(f"   - 분야: `{r['category']}`{tags_str}")
            lines.append(f"   - 미리보기: *\"{r['snippet']}\"*")
            lines.append("")

        lines.append("💡 문서를 자세히 읽으려면 `wiki_read(title='문서명')` 도구를 호출하세요.")
        return "\n".join(lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_list_all(
    category: Optional[str] = Field(
        default=None,
        description="특정 서브폴더(카테고리)의 문서만 조회하려면 카테고리명을 지정하세요",
    ),
) -> str:
    """[위키 전체 목차 조회] 모든 서브폴더(분야)별 계층 트리 형태로 지식 문서 색인을 조회합니다."""
    def _run():
        files = get_all_wiki_files()
        if not files:
            return "ℹ️ 현재 위키 지식 베이스가 비어 있습니다."

        cat_filter = str(category).strip().lower() if category and isinstance(category, str) else None
        categories: Dict[str, List[Dict[str, Any]]] = {}
        all_tags: Set[str] = set()

        for f in files:
            meta, body = parse_frontmatter_and_content(f)
            cat = meta.get("category", "기타")
            rel_path = str(f.relative_to(WIKI_DIR)).replace("\\", "/")

            if cat_filter and cat_filter not in cat.lower() and cat_filter not in rel_path.lower():
                continue

            links = extract_wiki_links(body)
            tags = meta.get("tags", [])
            all_tags.update(tags)

            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": f.stem,
                "path": rel_path,
                "title": meta.get("title", f.stem),
                "tags": tags,
                "links_count": len(links),
                "updated_at": meta.get("updated_at", ""),
            })

        lines = [
            f"📚 **[LLM Wiki 계층형 전체 목차 색인 (총 {len(files)}개 문서)]**",
            "",
        ]

        for cat_name, doc_list in sorted(categories.items()):
            lines.append(f"📁 **[{cat_name}]** ({len(doc_list)}개)")
            for d in sorted(doc_list, key=lambda x: x["name"]):
                tags_badge = f" `[{', '.join(d['tags'])}]`" if d['tags'] else ""
                links_badge = f" (연결 링크: {d['links_count']}개)" if d['links_count'] > 0 else ""
                lines.append(f"  └── 📄 **`{d['name']}`** - {d['title']}{tags_badge}{links_badge}")
            lines.append("")

        if all_tags:
            lines.append(f"🏷️ **등록된 주요 태그**: {', '.join(sorted(all_tags))}")

        return "\n".join(lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_backlinks(
    title: str = Field(
        description="역링크(이 문서를 참조하고 있는 문서들)를 추적할 대상 문서명",
        examples=["33.75_Safety_Analysis", "33.87_Endurance_Test"],
    ),
) -> str:
    """[역링크 추적] 서브폴더 위치와 무관하게 특정 위키 문서를 참조([[링크]])하고 있는 모든 상위/연관 문서를 역추적합니다."""
    def _run():
        t_str = str(title).strip() if title and isinstance(title, str) else ""
        if not t_str:
            return "❌ 역링크를 추적할 대상 문서명을 지정해주세요."

        clean_target = sanitize_filename(Path(t_str).stem).lower()
        backlinks_idx = build_backlinks_index()

        referencing_docs = backlinks_idx.get(clean_target, set())

        if not referencing_docs:
            return (
                f"ℹ️ 문서 `{t_str}`을(를) 참조하고 있는 다른 위키 문서가 아직 없습니다.\n"
                f"(다른 문서 본문에 `[[{t_str}]]` 링크를 추가하면 자동으로 역링크가 연결됩니다.)"
            )

        lines = [
            f"⬅️ **[`{t_str}`을(를) 참조하고 있는 연관/상위 문서 목록 (총 {len(referencing_docs)}건)]**",
            "",
        ]
        for doc in sorted(referencing_docs):
            lines.append(f"- 📄 **`{doc}`** ──(참조)──▶ `[[{t_str}]]`")

        lines.append("")
        lines.append("💡 해당 문서를 확인하려면 `wiki_read(title='문서명')`을 실행하세요.")
        return "\n".join(lines)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_delete_to_trash(
    title: str = Field(
        description="휴지통으로 안전하게 이동할 위키 문서의 제목 또는 파일명",
        examples=["임시메모", "old_draft"],
    ),
) -> str:
    """[위키 문서 안전 삭제] 지정한 위키 문서를 영구 삭제하지 않고 OS 휴지통으로 안전하게 이동합니다."""
    def _run():
        ensure_wiki_dir()
        t_str = str(title).strip() if title and isinstance(title, str) else ""
        if not t_str:
            return "❌ 삭제할 위키 문서 제목을 지정해주세요."

        target_file = find_wiki_file(t_str)
        if not target_file or not target_file.exists():
            return f"❌ 삭제할 위키 문서 `{t_str}`이(가) 존재하지 않습니다."

        try:
            send_to_recycle_bin(target_file)
            rel_path = target_file.relative_to(WIKI_DIR)
            return f"🗑️ 위키 문서 `{rel_path}`을(를) OS 휴지통으로 안전하게 이동했습니다 (Safe Delete)."
        except Exception as e:
            return f"❌ 휴지통 이동 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def wiki_rebuild_index(
    auto_link: bool = Field(
        default=False,
        description="True인 경우 본문 내 일반 텍스트 조항/키워드를 [[문서명]] 링크로 자동 변환합니다 (기본값: False)",
    ),
) -> str:
    """[위키 색인 재구축 & 대시보드 갱신] 전체 위키 문서를 분석하여 00_INDEX.md 대시보드를 생성하고 최다 인용 허브/연결 건강도를 보고합니다."""
    def _run():
        try:
            import importlib
            import wiki_indexer
            importlib.reload(wiki_indexer)
            res = wiki_indexer.scan_and_rebuild_index(auto_link=bool(auto_link))
        except Exception as e:
            return f"❌ 색인 빌드 중 오류 발생: {str(e)}"

        if not res.get("success"):
            return f"❌ 색인 실패: {res.get('message')}"

        top_hubs_str = ", ".join([f"[[{h[0]}]] ({h[1]}회)" for h in res.get("top_hubs", []) if h[1] > 0]) or "(아직 인용된 문서 없음)"

        lines = [
            "✅ **[LLM Wiki 지식 그래프 색인 재구축 완료]**",
            f"- 📊 **총 등록 문서 수**: **{res['total_docs']}개**",
            f"- 📁 **분야(서브폴더) 수**: **{res['total_categories']}개**",
            f"- 🏷️ **등록 태그 수**: **{res['total_tags']}개**",
            f"- 🏆 **핵심 허브(Hub) 문서 Top 3**: {top_hubs_str}",
            f"- 🔍 **지식 건강도**: 끊어진 링크 **{res['broken_links_count']}건**, 고아 문서 **{res['orphan_count']}건**",
        ]
        if auto_link and res.get("auto_linked_count", 0) > 0:
            lines.append(f"- ⚡ **자동 연결된 위키 링크**: {res['auto_linked_count']}개")

        lines.append(f"- 📄 **대시보드 파일**: `00_INDEX.md` (저장 완료)")
        lines.append("\n💡 전체 대시보드 요약을 확인하려면 `wiki_read(title='00_INDEX')`를 호출하세요.")
        return "\n".join(lines)

    return await asyncio.to_thread(_run)


# ==============================================================================
# 4. 서버 기동 진입점 (HTTP / SSE / stdio)
# ==============================================================================

if __name__ == "__main__":
    import argparse

    init_sample_cfr_data()

    parser = argparse.ArgumentParser(description="LLM Wiki Knowledge Base FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["http", "sse", "stdio"],
        default="http",
        help="전송 방식: http, sse, stdio (기본값: http)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE 호스트 주소 (기본값: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8003, help="HTTP/SSE 포트 번호 (기본값: 8003)")
    args = parser.parse_args()

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
        print(f"🚀 Wiki Knowledge FastMCP HTTP Server 시작: http://{args.host}:{args.port}", file=sys.stderr)
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
    elif args.transport == "sse":
        print(f"🚀 Wiki Knowledge FastMCP SSE Server 시작: http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )

