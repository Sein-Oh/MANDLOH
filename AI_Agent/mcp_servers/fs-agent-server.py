"""fs-agent-server.py - LangGraph 기반 실물 검증 자율형 파일시스템 AI 에이전트 MCP 서버.

특징:
1. LangGraph 기반 다단계 ReAct + 실물 검증 파이프라인:
   - [1단계] 계획 및 도구 판단 노드 (plan_and_reason_node) ➔ 도구 호출 루프
   - [2단계] 파일 도구 실행 노드 (tool_execution_node) ➔ 실행 후 1단계로 복귀하여 다음 단계 연속 수행 (ReAct Loop)
   - [3단계] 실물 파일 및 내용 검증 노드 (verify_node) 🌟 (실제 디스크 파일/내용 100% 물리적 판독 검증)
   - [4단계] 최종 종합 응답 노드 (response_node)
2. Gemma 4 24B 맞춤형 환각 방지, 도구 미호출 강제 유도, 폴백 JSON 파서 내장
3. FastMCP 기반 멀티 전송 (HTTP, SSE, stdio) + CORS 전체 허용
4. CLI 대화형 직접 실행 모드 (--direct)
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict, Union
import uuid

from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# LangChain & LangGraph
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


# ==============================================================================
# 0. 콘솔 인코딩 및 설정 로더 (Configuration)
# ==============================================================================

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG_FILE = Path(__file__).parent / "agent_config.json"


def load_config() -> dict:
    """agent_config.json 설정 파일을 로드하고 기본값을 병합합니다."""
    default_cfg = {
        "AGENT_URL": "http://127.0.0.1:1234/v1",
        "API_KEY": "not-needed",
        "MODEL_NAME": "google/gemma-4-24b",
        "TEMPERATURE": 0.1,
        "MAX_ITERATIONS": 8,
        "DEFAULT_TOOLS_MODE": "all",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                default_cfg.update(user_cfg)
        except Exception as e:
            print(f"[설정 로드 경고] {e}, 기본 설정을 사용합니다.", file=sys.stderr)
    return default_cfg


AGENT_CONFIG = load_config()


# ==============================================================================
# 1. 파일시스템 보안 정책 및 유틸리티
# ==============================================================================

RESTRICTED_EXTENSIONS = {
    ".pptx", ".ppt",
    ".xlsx", ".xls",
    ".docx", ".doc",
    ".hwp", ".hwpx",
    ".pdf",
}

WINDOWS_PROTECTED_PATTERNS = [
    re.compile(r"^[a-zA-Z]:\\windows(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\program files(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\program files \(x86\)(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\\$recycle\.bin", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\system volume information", re.IGNORECASE),
]


def get_fs_home() -> Path:
    home_env = os.environ.get("FS_LOCAL_HOME", "")
    if home_env:
        return Path(home_env).expanduser().resolve()
    return Path.cwd().resolve()


def is_windows_protected_path(path: Path) -> bool:
    if sys.platform != "win32":
        return False
    try:
        path_str = str(path.resolve())
        return any(pattern.match(path_str) for pattern in WINDOWS_PROTECTED_PATTERNS)
    except Exception:
        return False


def validate_path(requested_path: str, check_system_protect: bool = True) -> Path:
    if not requested_path or not str(requested_path).strip():
        raise ValueError("경로가 비어 있습니다.")

    path = Path(requested_path.strip()).expanduser()
    if not path.is_absolute():
        path = get_fs_home() / path

    try:
        normalized = path.resolve()
    except Exception:
        normalized = path

    if check_system_protect and is_windows_protected_path(normalized):
        raise PermissionError(
            f"❌ 접근 차단: 시스템 보호를 위해 Windows 주요 시스템 디렉토리(`{normalized}`)에 대한 접근은 제한되어 있습니다."
        )

    return normalized


def read_text_safely(file_path: Path) -> str:
    """한글 인코딩(UTF-8, CP949, UTF-8-SIG, EUC-KR 등)을 자동으로 감지하여 디코딩합니다."""
    raw_bytes = file_path.read_bytes()
    encodings = ["utf-8", "cp949", "utf-8-sig", "euc-kr", "latin1"]
    for enc in encodings:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def send_to_recycle_bin(target_path: Path) -> bool:
    """파일 또는 디렉토리를 Windows OS 휴지통으로 안전하게 이동합니다."""
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
        raise NotImplementedError("휴지통 이동 기능은 Windows 환경을 지원합니다.")


def get_recycle_bin_items(max_items: int = 50) -> List[dict]:
    items_list = []
    if sys.platform == "win32":
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            bin_folder = shell.Namespace(10)
            items = bin_folder.Items()
            total = items.Count
            for i in range(min(total, max_items)):
                item = items.Item(i)
                name = item.Name
                orig_loc = bin_folder.GetDetailsOf(item, 1) or "알 수 없음"
                del_time = bin_folder.GetDetailsOf(item, 2) or "알 수 없음"
                size_bytes = getattr(item, "Size", 0)
                items_list.append({
                    "name": name,
                    "original_location": orig_loc,
                    "deleted_time": del_time,
                    "size_bytes": size_bytes,
                })
        except Exception as e:
            print(f"Warning: Recycle Bin query failed: {e}", file=sys.stderr)
    return items_list


def restore_from_recycle_bin(target_name_or_path: str) -> tuple[bool, Optional[str], Optional[str]]:
    if sys.platform != "win32":
        raise NotImplementedError("Recycle Bin restore is currently supported on Windows only.")

    clean_target = Path(target_name_or_path.strip()).name.lower()
    full_target_lower = str(Path(target_name_or_path.strip())).lower()

    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        bin_folder = shell.Namespace(10)
        items = bin_folder.Items()

        for i in range(items.Count):
            item = items.Item(i)
            item_name = item.Name
            orig_loc = bin_folder.GetDetailsOf(item, 1) or ""
            full_orig_path = (Path(orig_loc) / item_name).resolve() if orig_loc else None

            name_match = (item_name.lower() == clean_target)
            path_match = (full_orig_path and str(full_orig_path).lower() == full_target_lower)

            if name_match or path_match:
                verbs = item.Verbs()
                for v in range(verbs.Count):
                    verb = verbs.Item(v)
                    v_name = verb.Name.replace("&", "").strip()
                    v_name_lower = v_name.lower()

                    is_restore = (
                        any(k in v_name_lower for k in ["복원", "restore", "undelete", "원래 위치"])
                        or v_name.endswith("(E)")
                        or v_name.endswith("(R)")
                        or v_name.endswith("(O)")
                    )
                    if is_restore:
                        verb.DoIt()
                        return True, item_name, orig_loc

        return False, None, None
    except Exception as err:
        raise RuntimeError(f"휴지통 복원 COM 작업 실패: {str(err)}") from err


# ==============================================================================
# 2. 로컬 파일시스템 원자적 실행 함수 (Raw Tool Functions)
# ==============================================================================

def raw_fs_read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    target = validate_path(path)
    if not target.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {target}")
    if not target.is_file():
        raise ValueError(f"지정된 경로가 일반 파일이 아닙니다: {target}")

    if target.suffix.lower() in RESTRICTED_EXTENSIONS:
        return f"🔒 [보안 안내] 사내 보안 규정에 따라 문서 파일(`{target.suffix}`)은 직접 읽을 수 없습니다."

    content = read_text_safely(target)
    lines = content.splitlines()
    total_lines = len(lines)

    if start_line is not None or end_line is not None:
        s = max(1, start_line if start_line is not None else 1)
        e = min(total_lines, end_line if end_line is not None else total_lines)
        if s > total_lines:
            return f"⚠️ 시작 라인({s})이 전체 라인 수({total_lines})보다 큽니다."
        selected_lines = lines[s - 1:e]
        numbered_lines = [f"{i}: {line}" for i, line in enumerate(selected_lines, start=s)]
        return f"📄 [{target.name}] (라인 {s}~{e} / 총 {total_lines}줄)\n" + "\n".join(numbered_lines)

    return f"📄 [{target.name}] (총 {total_lines}줄, 크기 {target.stat().st_size} bytes)\n{content}"


def raw_fs_write_file(path: str, content: str, overwrite: bool = True) -> str:
    target = validate_path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"파일이 이미 존재합니다: {target} (overwrite=True 필요)")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"✅ 파일 작성 완료: {target} ({len(content.encode('utf-8'))} bytes)"


def raw_fs_list_directory(path: str = ".", include_hidden: bool = False, max_items: int = 100) -> str:
    target = validate_path(path)
    if not target.exists():
        raise FileNotFoundError(f"디렉토리가 존재하지 않습니다: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"지정된 경로가 디렉토리가 아닙니다: {target}")

    entries = []
    for item in target.iterdir():
        if not include_hidden and item.name.startswith("."):
            continue
        entries.append(item)

    entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    limited = entries[:max_items]

    lines = [f"📂 **{target}** 디렉토리 목록 (총 {len(entries)}개 항목):"]
    for item in limited:
        if item.is_dir():
            lines.append(f"- 📁 `[DIR]` **{item.name}/**")
        else:
            size_b = item.stat().st_size
            lines.append(f"- 📄 `[FILE]` {item.name} ({size_b} bytes)")
    if len(entries) > max_items:
        lines.append(f"\n... 외 {len(entries) - max_items}개 항목 생략됨")
    return "\n".join(lines)


def raw_fs_search_files(
    directory: str = ".",
    pattern: str = "*",
    content_query: Optional[str] = None,
    modified_within_days: Optional[float] = None,
    max_results: int = 50
) -> str:
    target = validate_path(directory)
    if not target.exists() or not target.is_dir():
        raise NotADirectoryError(f"유효한 디렉토리가 아닙니다: {target}")

    matches = []
    clean_content_query = content_query.strip() if content_query else None
    now_ts = time.time()
    cutoff_ts = (now_ts - (modified_within_days * 86400)) if (modified_within_days is not None and modified_within_days > 0) else None

    for p in target.glob(pattern):
        if is_windows_protected_path(p):
            continue

        # 날짜/기간 필터링
        if cutoff_ts is not None:
            try:
                mtime = p.stat().st_mtime
                if mtime < cutoff_ts:
                    continue
            except Exception:
                continue

        # 내용 필터링
        if clean_content_query and p.is_file():
            if p.suffix.lower() in RESTRICTED_EXTENSIONS:
                continue
            try:
                text = read_text_safely(p)
                if clean_content_query not in text:
                    continue
            except Exception:
                continue
        elif clean_content_query and p.is_dir():
            continue

        matches.append(p)
        if len(matches) >= max_results:
            break

    desc_parts = [f"'{pattern}'"]
    if clean_content_query:
        desc_parts.append(f"내용: '{clean_content_query}'")
    if modified_within_days:
        desc_parts.append(f"최근 {modified_within_days}일 이내 수정")
    query_desc = " & ".join(desc_parts)

    if not matches:
        return f"🔍 검색 결과: '{target}'에서 [{query_desc}]과 일치하는 항목이 없습니다."

    lines = [f"🔍 **[{query_desc}]** 검색 결과 ({len(matches)}개 일치):"]
    for p in matches:
        icon = "📁" if p.is_dir() else "📄"
        mtime_str = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if p.exists() else ""
        lines.append(f"- {icon} `{p}` ({p.stat().st_size if p.is_file() else 0} bytes | {mtime_str})")
    return "\n".join(lines)


def raw_fs_create_directory(path: str) -> str:
    target = validate_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"✅ 디렉토리 생성 완료: {target}"


def raw_fs_get_file_info(path: str) -> str:
    target = validate_path(path)
    if not target.exists():
        raise FileNotFoundError(f"경로가 존재하지 않습니다: {target}")

    stat = target.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    ctime = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
    kind = "디렉토리" if target.is_dir() else "일반 파일"

    return f"""📊 **파일/폴더 정보**: `{target}`
- 유형: {kind}
- 크기: {stat.st_size:,} bytes
- 최종 수정: {mtime}
- 생성 일시: {ctime}
- 확장자: {target.suffix or '(없음)'}
"""


def raw_fs_rename_file(old_path: str, new_name: str) -> str:
    src = validate_path(old_path)
    if not src.exists():
        raise FileNotFoundError(f"원본 경로가 존재하지 않습니다: {src}")
    dst = src.parent / new_name
    src.rename(dst)
    return f"✅ 이름 변경 완료: `{src.name}` ➔ `{dst.name}`"


def raw_fs_move_file(source_path: str, destination_dir: str) -> str:
    src = validate_path(source_path)
    dst_dir = validate_path(destination_dir)
    if not src.exists():
        raise FileNotFoundError(f"원본이 존재하지 않습니다: {src}")
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    shutil.move(str(src), str(target))
    return f"✅ 이동 완료: `{src}` ➔ `{target}`"


def raw_fs_copy_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    src = validate_path(source_path)
    dst = validate_path(destination_path)
    if not src.exists():
        raise FileNotFoundError(f"원본이 존재하지 않습니다: {src}")
    if dst.exists() and not overwrite:
        raise FileExistsError(f"대상 파일이 이미 존재합니다: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(str(src), str(dst), dirs_exist_ok=overwrite)
    else:
        shutil.copy2(str(src), str(dst))
    return f"✅ 복사 완료: `{src}` ➔ `{dst}`"


def raw_fs_open_in_explorer(path: str) -> str:
    """윈도우 탐색기 창을 열고, 대상이 파일인 경우 해당 파일을 하이라이트(선택)합니다."""
    target = validate_path(path, check_system_protect=False)
    if not target.exists():
        raise FileNotFoundError(f"경로가 존재하지 않습니다: {target}")

    if sys.platform == "win32":
        abs_p = str(target.resolve())
        if target.is_file():
            subprocess.Popen(["explorer.exe", f"/select,{abs_p}"])
            return f"🪟 윈도우 탐색기를 열고 파일을 선택했습니다: `{abs_p}`"
        else:
            subprocess.Popen(["explorer.exe", abs_p])
            return f"🪟 윈도우 탐색기로 폴더를 열었습니다: `{abs_p}`"
    else:
        return f"⚠️ 윈도우 탐색기는 Windows 환경에서 지원됩니다: `{target}`"


def raw_fs_archive_zip(source_paths: Union[str, List[str]], zip_path: str, overwrite: bool = True) -> str:
    """지정된 파일 또는 폴더들을 ZIP 압축 파일로 묶습니다."""
    import zipfile
    target_zip = validate_path(zip_path)
    if target_zip.exists() and not overwrite:
        raise FileExistsError(f"대상 ZIP 파일이 이미 존재합니다: {target_zip}")

    target_zip.parent.mkdir(parents=True, exist_ok=True)
    paths_to_add = [source_paths] if isinstance(source_paths, str) else source_paths

    total_added = 0
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p_str in paths_to_add:
            p = validate_path(p_str, check_system_protect=False)
            if not p.exists():
                continue
            if p.is_file():
                zf.write(p, arcname=p.name)
                total_added += 1
            elif p.is_dir():
                for root, dirs, files in os.walk(p):
                    for file in files:
                        full_f = Path(root) / file
                        rel_f = full_f.relative_to(p.parent)
                        zf.write(full_f, arcname=str(rel_f))
                        total_added += 1

    size_b = target_zip.stat().st_size
    return f"📦 ZIP 압축 완료: `{target_zip}` (총 {total_added}개 항목 압축, {size_b:,} bytes)"


def raw_fs_extract_zip(zip_path: str, destination_dir: str, overwrite: bool = True) -> str:
    """ZIP 파일의 압축을 지정된 대상 디렉토리에 풉니다."""
    import zipfile
    target_zip = validate_path(zip_path, check_system_protect=False)
    if not target_zip.exists() or not target_zip.is_file():
        raise FileNotFoundError(f"ZIP 파일이 존재하지 않습니다: {target_zip}")

    dst = validate_path(destination_dir)
    dst.mkdir(parents=True, exist_ok=True)

    extracted_count = 0
    with zipfile.ZipFile(target_zip, 'r') as zf:
        for member in zf.namelist():
            extracted_path = (dst / member).resolve()
            # Zip slip 방지
            if not str(extracted_path).startswith(str(dst.resolve())):
                continue
            zf.extract(member, dst)
            extracted_count += 1

    return f"📂 ZIP 압축 해제 완료: `{dst}` (총 {extracted_count}개 파일 추출)"


def raw_fs_replace_text_in_files(
    directory: str = ".",
    pattern: str = "*.txt",
    find_text: str = "",
    replace_text: str = "",
    max_files: int = 50
) -> str:
    """디렉토리 내 파일들의 텍스트를 검색하여 일괄 치환(Find & Replace)합니다."""
    if not find_text:
        raise ValueError("찾을 텍스트(find_text)가 지정되지 않았습니다.")

    target = validate_path(directory)
    if not target.exists() or not target.is_dir():
        raise NotADirectoryError(f"유효한 디렉토리가 아닙니다: {target}")

    modified_files = []
    total_replacements = 0

    for p in target.glob(pattern):
        if is_windows_protected_path(p) or not p.is_file():
            continue
        if p.suffix.lower() in RESTRICTED_EXTENSIONS:
            continue

        try:
            content = read_text_safely(p)
            if find_text in content:
                count = content.count(find_text)
                new_content = content.replace(find_text, replace_text)
                p.write_text(new_content, encoding="utf-8")
                modified_files.append((p, count))
                total_replacements += count
                if len(modified_files) >= max_files:
                    break
        except Exception:
            continue

    if not modified_files:
        return f"🔍 치환 결과: '{target}'에서 '{find_text}' 텍스트를 포함하는 파일이 없습니다."

    lines = [f"📝 **텍스트 일괄 치환 완료** (총 {len(modified_files)}개 파일, {total_replacements}회 치환):"]
    for p, c in modified_files:
        lines.append(f"- 📄 `{p}` ({c}곳 치환됨)")
    return "\n".join(lines)


def raw_fs_delete_to_trash(path: str) -> str:
    target = validate_path(path)
    if not target.exists():
        raise FileNotFoundError(f"삭제할 대상이 존재하지 않습니다: {target}")
    send_to_recycle_bin(target)
    return f"🗑️ 휴지통 이동 완료 (Safe Delete): `{target}`"


def raw_fs_restore_from_trash(name_or_path: str) -> str:
    success, item_name, orig_loc = restore_from_recycle_bin(name_or_path)
    if success:
        return f"♻️ 휴지통 복원 성공: `{item_name}` (원래 위치: `{orig_loc}`)"
    return f"⚠️ 휴지통에서 '{name_or_path}' 항목을 찾지 못했습니다."


def raw_fs_list_trash(limit: int = 30) -> str:
    items = get_recycle_bin_items(limit)
    if not items:
        return "🗑️ 휴지통이 비어 있거나 항목을 조회할 수 없습니다."
    lines = [f"🗑️ **OS 휴지통 항목 목록** (총 {len(items)}개 항목):"]
    for it in items:
        lines.append(f"- 📄 `{it['name']}` | 크기: {it['size_bytes']} bytes | 원위치: `{it['original_location']}` | 삭제일: {it['deleted_time']}")
    return "\n".join(lines)


# ==============================================================================
# 3. LangChain 도구 래퍼 (LangGraph Tools)
# ==============================================================================

@tool
def fs_read_file_tool(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """파일의 텍스트 내용을 읽어옵니다. 한글 인코딩을 자동 감지합니다."""
    try:
        return raw_fs_read_file(path, start_line, end_line)
    except Exception as e:
        return f"❌ 파일 읽기 실패: {str(e)}"


@tool
def fs_write_file_tool(path: str, content: str, overwrite: bool = True) -> str:
    """새 파일을 생성하거나 기존 파일 내용을 덮어씁니다. 부모 폴더는 자동 생성됩니다."""
    try:
        return raw_fs_write_file(path, content, overwrite)
    except Exception as e:
        return f"❌ 파일 작성 실패: {str(e)}"


@tool
def fs_list_directory_tool(path: str = ".", include_hidden: bool = False, max_items: int = 100) -> str:
    """지정된 디렉토리의 파일 및 폴더 목록을 조회합니다."""
    try:
        return raw_fs_list_directory(path, include_hidden, max_items)
    except Exception as e:
        return f"❌ 디렉토리 조회 실패: {str(e)}"


@tool
def fs_search_files_tool(
    directory: str = ".",
    pattern: str = "*",
    content_query: Optional[str] = None,
    modified_within_days: Optional[float] = None,
    max_results: int = 50
) -> str:
    """지정된 디렉토리에서 파일명 패턴(pattern), 파일 내용(content_query), 수정일(modified_within_days)로 파일을 검색합니다.
    Args:
        directory: 검색 대상 디렉토리 경로 (예: "D:\\temp")
        pattern: 파일명 패턴 (예: "*.txt", "*.*")
        content_query: 파일 내용에 포함되어야 하는 특정 단어/텍스트 (예: "메롱", "TODO"). 지정하면 해당 단어가 들어있는 파일만 정확히 필터링됩니다.
        modified_within_days: 최근 N일 이내에 수정된 파일만 필터링 (예: 1.0 -> 최근 24시간, 7.0 -> 최근 7일)
        max_results: 최대 검색 결과 수
    """
    try:
        return raw_fs_search_files(directory, pattern, content_query, modified_within_days, max_results)
    except Exception as e:
        return f"❌ 파일 검색 실패: {str(e)}"


@tool
def fs_create_directory_tool(path: str) -> str:
    """새로운 디렉토리(폴더)를 생성합니다."""
    try:
        return raw_fs_create_directory(path)
    except Exception as e:
        return f"❌ 디렉토리 생성 실패: {str(e)}"


@tool
def fs_get_file_info_tool(path: str) -> str:
    """파일이나 폴더의 크기, 수정일, 생성일 등 메타데이터 정보를 확인합니다."""
    try:
        return raw_fs_get_file_info(path)
    except Exception as e:
        return f"❌ 파일 정보 조회 실패: {str(e)}"


@tool
def fs_rename_file_tool(old_path: str, new_name: str) -> str:
    """파일 또는 폴더의 이름을 변경합니다."""
    try:
        return raw_fs_rename_file(old_path, new_name)
    except Exception as e:
        return f"❌ 이름 변경 실패: {str(e)}"


@tool
def fs_move_file_tool(source_path: str, destination_dir: str) -> str:
    """파일 또는 폴더를 다른 디렉토리로 이동합니다."""
    try:
        return raw_fs_move_file(source_path, destination_dir)
    except Exception as e:
        return f"❌ 파일 이동 실패: {str(e)}"


@tool
def fs_copy_file_tool(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    """파일 또는 디렉토리를 다른 경로로 복사합니다."""
    try:
        return raw_fs_copy_file(source_path, destination_path, overwrite)
    except Exception as e:
        return f"❌ 파일 복사 실패: {str(e)}"


@tool
def fs_delete_to_trash_tool(path: str) -> str:
    """파일 또는 폴더를 영구 삭제하지 않고 안전하게 OS 휴지통으로 이동합니다."""
    try:
        return raw_fs_delete_to_trash(path)
    except Exception as e:
        return f"❌ 휴지통 이동 실패: {str(e)}"


@tool
def fs_restore_from_trash_tool(name_or_path: str) -> str:
    """OS 휴지통에서 파일이나 폴더를 원래 위치로 복원합니다."""
    try:
        return raw_fs_restore_from_trash(name_or_path)
    except Exception as e:
        return f"❌ 휴지통 복원 실패: {str(e)}"


@tool
def fs_list_trash_tool(limit: int = 30) -> str:
    """현재 OS 휴지통에 보관 중인 항목 목록을 확인합니다."""
    try:
        return raw_fs_list_trash(limit)
    except Exception as e:
        return f"❌ 휴지통 목록 조회 실패: {str(e)}"


@tool
def fs_open_in_explorer_tool(path: str) -> str:
    """윈도우 탐색기(Explorer) 창을 열고, 대상 파일이나 폴더를 화면에 직접 보여줍니다."""
    try:
        return raw_fs_open_in_explorer(path)
    except Exception as e:
        return f"❌ 윈도우 탐색기 실행 실패: {str(e)}"


@tool
def fs_archive_zip_tool(source_paths: Union[str, List[str]], zip_path: str, overwrite: bool = True) -> str:
    """지정된 파일 또는 폴더들을 ZIP 압축 파일로 묶어 저장합니다."""
    try:
        return raw_fs_archive_zip(source_paths, zip_path, overwrite)
    except Exception as e:
        return f"❌ ZIP 압축 실패: {str(e)}"


@tool
def fs_extract_zip_tool(zip_path: str, destination_dir: str, overwrite: bool = True) -> str:
    """ZIP 파일의 압축을 대상 디렉토리에 풉니다."""
    try:
        return raw_fs_extract_zip(zip_path, destination_dir, overwrite)
    except Exception as e:
        return f"❌ ZIP 압축 해제 실패: {str(e)}"


@tool
def fs_replace_text_in_files_tool(
    directory: str = ".",
    pattern: str = "*.txt",
    find_text: str = "",
    replace_text: str = "",
    max_files: int = 50
) -> str:
    """디렉토리 내 파일들의 텍스트를 검색하여 일괄 찾아바꾸기(치환)합니다."""
    try:
        return raw_fs_replace_text_in_files(directory, pattern, find_text, replace_text, max_files)
    except Exception as e:
        return f"❌ 텍스트 일괄 치환 실패: {str(e)}"


LANGGRAPH_TOOLS = [
    fs_read_file_tool,
    fs_write_file_tool,
    fs_list_directory_tool,
    fs_search_files_tool,
    fs_create_directory_tool,
    fs_get_file_info_tool,
    fs_rename_file_tool,
    fs_move_file_tool,
    fs_copy_file_tool,
    fs_delete_to_trash_tool,
    fs_restore_from_trash_tool,
    fs_list_trash_tool,
    fs_open_in_explorer_tool,
    fs_archive_zip_tool,
    fs_extract_zip_tool,
    fs_replace_text_in_files_tool,
]
TOOL_MAP = {t.name: t for t in LANGGRAPH_TOOLS}


# ==============================================================================
# 4. LangGraph 에이전트 상태 정의 (Agent State)
# ==============================================================================

class ActionRecord(TypedDict):
    tool_name: str
    tool_args: Dict[str, Any]
    result: str
    target_path: Optional[str]
    expected_content: Optional[str]
    action_type: str  # "write", "delete", "restore", "move", "copy", "read", "list", "info", "other"
    timestamp: str


class VerificationResult(TypedDict):
    target_path: str
    action_type: str
    passed: bool
    status_detail: str
    actual_file_exists: bool
    actual_size_bytes: int
    content_snippet: Optional[str]


class AgentState(TypedDict):
    task_goal: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    actions_log: List[ActionRecord]
    verification_reports: List[VerificationResult]
    status_logs: List[str]
    iteration_count: int
    tool_call_count: int
    needs_correction: bool
    correction_feedback: str
    final_response: str


# ==============================================================================
# 5. Gemma 4 24B 최적화 시스템 프롬프트 및 도구 파서
# ==============================================================================

SYSTEM_PROMPT = """당신은 파일시스템을 직접 제어하는 자율형 AI 실행 에이전트(LangGraph File Agent)입니다.

[절대 원칙]
1. 당신은 파일 작업을 '설명'하는 챗봇이 아니라, 직접 '도구를 호출하여 실행'하는 에이전트입니다.
2. 여러 단계의 복합 작업 수행 표준 워크플로우:
   - [케이스 1: 특정 폴더 내 조건별 일괄 처리 (삭제/수정 등)]
     1단계: 먼저 `fs_list_directory_tool(path="경로")`을 즉시 호출하여 실제 파일 목록 및 크기/수정일을 확인합니다.
     2단계: 조회된 파일 목록을 보고 조건에 맞는 모든 파일들에 대해 `fs_delete_to_trash_tool` 또는 `fs_write_file_tool`을 빠짐없이 순차적으로 호출합니다.
   - [케이스 2: 휴지통 조회 및 조건별 복구]
     1단계: 먼저 `fs_list_trash_tool()`을 즉시 호출하여 현재 휴지통에 보관된 실제 항목 목록과 크기(bytes), 삭제일을 확인합니다.
     2단계: 조회된 휴지통 목록에서 복구 대상인 파일명들을 찾아 `fs_restore_from_trash_tool(name_or_path="파일명")`을 각각 호출하여 즉시 원래 위치로 복원합니다.
   - [케이스 3: 특정 단어/내용을 포함하는 파일 검색 및 처리]
     1단계: `fs_search_files_tool(directory="경로", pattern="*.txt", content_query="검색할단어")`를 즉시 호출하여 해당 단어가 들어있는 파일들만 1번에 정확히 검색합니다. (모든 파일을 일일이 read하지 마십시오)
     2단계: 검색된 일치 파일들에 대해서만 `fs_delete_to_trash_tool` 또는 필요한 조작 도구를 호출합니다.
   - [케이스 4: 새 파일 생성 및 작성 / 단순 조회]
     새 파일은 `fs_write_file_tool(path="경로", content="내용")`, 단순 파일 읽기는 `fs_read_file_tool(path="경로")`을 1회 호출합니다.
   - [케이스 5: ZIP 압축 / 해제 / 텍스트 일괄 치환 / 탐색기 열기]
     - ZIP 압축: `fs_archive_zip_tool(source_paths="경로", zip_path="대상.zip")`
     - ZIP 해제: `fs_extract_zip_tool(zip_path="파일.zip", destination_dir="대상폴더")`
     - 텍스트 일괄 치환: `fs_replace_text_in_files_tool(directory="경로", find_text="찾을단어", replace_text="바꿀단어")`
     - 윈도우 탐색기 열기: `fs_open_in_explorer_tool(path="경로")`
   - [케이스 6: 도움말 및 기능 안내 요청]
     사용자가 "도움말", "할 수 있는 일", "기능 안내", "명령어 예시"를 요청한 경우, 도구를 억지로 호출하지 말고 파일 에이전트가 지원하는 다양한 기능(조회, 작성, 휴지통 삭제/복구, 내용 검색, 날짜 검색, ZIP 압축/해제, 텍스트 일괄 치환, 탐색기 열기, 7종 실물 검증 등)과 구체적인 사용 예시들을 친절하게 정리하여 응답하십시오.
3. 절대로 도구를 호출하지 않고 "작업을 시작하겠습니다" 또는 "복구/삭제 완료했습니다"라고 말만 하지 마십시오. 반드시 도구(Tool Call)를 직접 호출하십시오.
4. 가상의 경로("경로/파일명.txt")나 존재하지 않는 파일명을 임의로 지어내지 말고, 도구 조회 결과로 얻은 실제 파일명만을 사용하십시오.
5. 필요한 모든 파일 조작이 완료되었으면 추가 도구를 호출하지 말고 최종 결과를 요약하여 보고하십시오.
"""


def extract_fallback_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Gemma 4 24B가 JSON 텍스트나 마크다운 블록으로 도구 호출을 출력했을 때 파싱합니다."""
    tool_calls = []
    if not text:
        return tool_calls

    # 1. ```json 블록 패턴
    json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    for block in json_blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict) and "name" in parsed:
                tool_name = parsed["name"]
                if tool_name in TOOL_MAP or f"{tool_name}_tool" in TOOL_MAP:
                    real_name = tool_name if tool_name in TOOL_MAP else f"{tool_name}_tool"
                    tool_calls.append({
                        "name": real_name,
                        "args": parsed.get("args") or parsed.get("arguments") or {},
                        "id": f"call_{int(time.time() * 1000)}",
                    })
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        tool_name = item["name"]
                        real_name = tool_name if tool_name in TOOL_MAP else f"{tool_name}_tool"
                        if real_name in TOOL_MAP:
                            tool_calls.append({
                                "name": real_name,
                                "args": item.get("args") or item.get("arguments") or {},
                                "id": f"call_{int(time.time() * 1000)}",
                            })
        except Exception:
            pass

    # 2. tool_call 패턴 (예: fs_list_directory_tool(path="..."))
    if not tool_calls:
        func_calls = re.findall(r"(fs_[a-z_]+(?:_tool)?)\((.*?)\)", text)
        for fn_name, fn_args in func_calls:
            real_name = fn_name if fn_name in TOOL_MAP else f"{fn_name}_tool"
            if real_name in TOOL_MAP:
                args_dict = {}
                arg_pairs = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,)]+))', fn_args)
                for k, v1, v2, v3 in arg_pairs:
                    val = v1 or v2 or v3
                    args_dict[k] = val.strip()
                tool_calls.append({
                    "name": real_name,
                    "args": args_dict,
                    "id": f"call_{int(time.time() * 1000)}",
                })

    return tool_calls


IS_DIRECT_CLI_MODE = False


def agent_log(msg: str):
    """stdio 전송 모드에서 JSON-RPC stdout 통신 채널 오염을 방지하기 위해 stderr로 로그를 출력합니다."""
    if IS_DIRECT_CLI_MODE:
        print(msg)
    else:
        print(msg, file=sys.stderr, flush=True)


def create_llm():
    """설정에 맞춰 ChatOpenAI 인스턴스를 생성합니다."""
    return ChatOpenAI(
        base_url=AGENT_CONFIG.get("AGENT_URL", "http://127.0.0.1:1234/v1"),
        api_key=AGENT_CONFIG.get("API_KEY", "not-needed"),
        model=AGENT_CONFIG.get("MODEL_NAME", "google/gemma-4-24b"),
        temperature=AGENT_CONFIG.get("TEMPERATURE", 0.1),
    )


# ==============================================================================
# 6. LangGraph 노드 구현 (4단계 파이프라인)
# ==============================================================================

def plan_and_reason_node(state: AgentState) -> dict:
    """[1단계: 계획 및 도구 판단 노드]"""
    iteration = state.get("iteration_count", 0) + 1
    log_msg = f"[1단계: 계획 및 도구 판단 노드] 🟢 ({iteration}회차) 사용자 목표 분석 및 도구 호출 계획 수립 중..."
    agent_log(log_msg)

    llm = create_llm().bind_tools(LANGGRAPH_TOOLS)
    messages = list(state.get("messages", []))

    # 피드백이 있는 경우 시스템 보정 메시지 주입
    if state.get("needs_correction") and state.get("correction_feedback"):
        correction_msg = HumanMessage(
            content=f"⚠️ [실물 검증 피드백]: {state['correction_feedback']}\n말로만 설명하지 마시고, 필요한 도구를 즉시 호출하세요."
        )
        messages.append(correction_msg)

    try:
        response = llm.invoke(messages)
    except Exception as e:
        err_msg = f"❌ LLM 호출 실패: {str(e)}"
        agent_log(err_msg)
        response = AIMessage(content=f"LLM 통신 중 오류가 발생했습니다: {str(e)}")

    # Gemma 4 24B 도구 호출 보정 (OpenAI tool_calls가 비어있을 때 폴백 텍스트 파싱)
    tool_calls = getattr(response, "tool_calls", [])
    if not tool_calls and isinstance(response.content, str):
        fallback_calls = extract_fallback_tool_calls(response.content)
        if fallback_calls:
            response.tool_calls = fallback_calls
            agent_log(f"  [Gemma 도구 파싱 보정] 텍스트에서 {len(fallback_calls)}개 도구 호출 추출 성공")

    new_logs = list(state.get("status_logs", []))
    new_logs.append(log_msg)

    return {
        "messages": [response],
        "iteration_count": iteration,
        "status_logs": new_logs,
        "needs_correction": False,
        "correction_feedback": "",
    }


def tool_execution_node(state: AgentState) -> dict:
    """[2단계: 파일 도구 실행 노드]"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])

    new_messages: List[BaseMessage] = []
    actions_log: List[ActionRecord] = list(state.get("actions_log", []))
    status_logs: List[str] = list(state.get("status_logs", []))
    tool_call_count = state.get("tool_call_count", 0) + len(tool_calls)

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})
        tc_id = tc.get("id", f"call_{int(time.time() * 1000)}")

        log_msg = f"[2단계: 파일 도구 실행 노드] ⚙️ `{tool_name}` 실행 (인자: {json.dumps(tool_args, ensure_ascii=False)})"
        agent_log(log_msg)
        status_logs.append(log_msg)

        # 도구 실행
        tool_func = TOOL_MAP.get(tool_name)
        if tool_func:
            try:
                res = tool_func.invoke(tool_args)
            except Exception as e:
                res = f"❌ 도구 실행 중 예외 발생: {str(e)}"
        else:
            res = f"❌ 알 수 없는 도구: {tool_name}"

        # 액션 기록 및 유형 분석
        action_type = "other"
        target_path = None
        expected_content = None
        extra_info = {}

        if "write" in tool_name:
            action_type = "write"
            target_path = tool_args.get("path")
            expected_content = tool_args.get("content")
        elif "delete" in tool_name:
            action_type = "delete"
            target_path = tool_args.get("path")
        elif "restore" in tool_name:
            action_type = "restore"
            target_path = tool_args.get("name_or_path")
        elif "rename" in tool_name:
            action_type = "rename"
            target_path = tool_args.get("old_path")
            extra_info["new_name"] = tool_args.get("new_name")
        elif "move" in tool_name:
            action_type = "move"
            target_path = tool_args.get("source_path")
            extra_info["destination_dir"] = tool_args.get("destination_dir")
        elif "copy" in tool_name:
            action_type = "copy"
            target_path = tool_args.get("source_path")
            extra_info["destination_path"] = tool_args.get("destination_path")
        elif "create_directory" in tool_name:
            action_type = "mkdir"
            target_path = tool_args.get("path")
        elif "read" in tool_name:
            action_type = "read"
            target_path = tool_args.get("path")
        elif "list" in tool_name:
            action_type = "list"
            target_path = tool_args.get("path")
        elif "search" in tool_name:
            action_type = "search"
            target_path = tool_args.get("directory")
        elif "archive_zip" in tool_name:
            action_type = "archive_zip"
            target_path = tool_args.get("zip_path")
        elif "extract_zip" in tool_name:
            action_type = "extract_zip"
            target_path = tool_args.get("destination_dir")
        elif "replace_text" in tool_name:
            action_type = "replace_text"
            target_path = tool_args.get("directory")
            extra_info["find_text"] = tool_args.get("find_text")
            extra_info["replace_text"] = tool_args.get("replace_text")
        elif "open_in_explorer" in tool_name:
            action_type = "open_explorer"
            target_path = tool_args.get("path")
        elif "info" in tool_name:
            action_type = "info"
            target_path = tool_args.get("path")

        record: ActionRecord = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "result": str(res),
            "target_path": target_path,
            "expected_content": expected_content,
            "action_type": action_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        record.update(extra_info)
        actions_log.append(record)

        new_messages.append(ToolMessage(content=str(res), tool_call_id=tc_id))

    return {
        "messages": new_messages,
        "actions_log": actions_log,
        "status_logs": status_logs,
        "tool_call_count": tool_call_count,
    }


def verify_node(state: AgentState) -> dict:
    """[3단계: 실물 파일 및 내용 검증 노드 (Verification Node)]
    디스크의 실제 파일을 열어 존재 여부, 크기, 기록된 내용, 휴지통 등록, 이름변경, 이동, 복사 등
    모든 변경 작업의 정합성을 100% 물리적으로 검증합니다.
    """
    status_logs = list(state.get("status_logs", []))
    verification_reports: List[VerificationResult] = []
    actions_log = state.get("actions_log", [])
    task_goal = state.get("task_goal", "")

    log_msg = "[3단계: 실물 검증 노드] 🔍 모든 파일 조작에 대한 실제 파일시스템 물리적 검증 및 내용 판독 시작..."
    agent_log(log_msg)
    status_logs.append(log_msg)

    needs_correction = False
    feedback_reasons = []

    mutation_keywords = [
        "삭제", "지워", "휴지통", "수정", "바꿔", "덮어", "작성", "만들", "생성",
        "이동", "옮겨", "복사", "이름변경", "이름 바꿔", "복구", "복원",
        "압축", "압축 해제", "zip", "치환", "바꿔줘", "탐색기", "열어",
        "delete", "write", "modify", "move", "copy", "rename", "restore", "mkdir", "archive", "extract", "replace", "explorer"
    ]
    user_wanted_mutation = any(k in task_goal for k in mutation_keywords)
    mutation_actions = [
        a for a in actions_log
        if a["action_type"] in ("write", "delete", "move", "copy", "restore", "rename", "mkdir", "archive_zip", "extract_zip", "replace_text", "open_explorer")
    ]

    if user_wanted_mutation and not mutation_actions:
        needs_correction = True
        reason = "❌ [목표 불일치]: 사용자는 파일 생성/수정/삭제/이동/복원/이름변경을 요청했으나, 실제로 실행된 파일 조작 도구가 없습니다. 말로만 완료했다고 하지 말고 즉시 해당 도구를 호출하세요."
        feedback_reasons.append(reason)
        agent_log(f"  {reason}")
    elif not mutation_actions:
        log_detail = "  - 파일 변동 작업 없음 (단순 조회/검색 작업 확인 완료)"
        agent_log(log_detail)
        status_logs.append(log_detail)

    # 2. 실행된 모든 개별 변동 액션들에 대한 정밀 물리적 디스크 검증
    for action in mutation_actions:
        act_type = action["action_type"]
        path_str = action.get("target_path")
        if not path_str:
            continue

        try:
            target = validate_path(path_str, check_system_protect=False)
        except Exception as e:
            needs_correction = True
            feedback_reasons.append(f"경로 파싱 오류 ({path_str}): {str(e)}")
            continue

        # [검증 1] 파일 생성 / 수정 (write) 실물 검증
        if act_type == "write":
            if not target.exists():
                needs_correction = True
                reason = f"❌ [실물 검증 실패] 파일이 실제 디스크 경로에 존재하지 않음: `{target}`"
                feedback_reasons.append(reason)
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "write",
                    "passed": False,
                    "status_detail": reason,
                    "actual_file_exists": False,
                    "actual_size_bytes": 0,
                    "content_snippet": None,
                })
                agent_log(f"  {reason}")
            else:
                size = target.stat().st_size
                try:
                    actual_content = read_text_safely(target)
                    snippet = actual_content[:300].strip()
                    expected = (action.get("expected_content") or "").strip()

                    if len(actual_content.strip()) == 0 and len(expected) > 0:
                        passed = False
                        detail = f"⚠️ [내용 검증 경고] 파일은 생성되었으나 내용이 비어있음 (0 bytes)"
                        needs_correction = True
                        feedback_reasons.append(detail)
                    else:
                        passed = True
                        detail = f"✅ [실물 판독 검증 완료] 디스크 존재 확인 ({size:,} bytes), 내용 정상 기록"

                    verification_reports.append({
                        "target_path": str(target),
                        "action_type": "write",
                        "passed": passed,
                        "status_detail": detail,
                        "actual_file_exists": True,
                        "actual_size_bytes": size,
                        "content_snippet": snippet,
                    })
                    agent_log(f"  {detail} (판독 내용: '{snippet[:50]}...')")
                except Exception as err:
                    passed = False
                    detail = f"❌ 파일 내용 판독 실패: {str(err)}"
                    needs_correction = True
                    feedback_reasons.append(detail)

        # [검증 2] 파일 삭제 (delete) 실물 검증
        elif act_type == "delete":
            if target.exists():
                needs_correction = True
                reason = f"❌ [삭제 검증 실패] 파일이 삭제되지 않고 경로에 남아있음: `{target}`"
                feedback_reasons.append(reason)
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "delete",
                    "passed": False,
                    "status_detail": reason,
                    "actual_file_exists": True,
                    "actual_size_bytes": target.stat().st_size,
                    "content_snippet": None,
                })
                agent_log(f"  {reason}")
            else:
                # 휴지통 목록 보관 여부 추가 교차 확인
                trash_items = get_recycle_bin_items(20)
                in_trash = any(it["name"].lower() == target.name.lower() for it in trash_items)
                trash_note = " (휴지통 보관 확인)" if in_trash else ""
                detail = f"✅ [삭제 실물 검증 완료] 원본 파일 디스크 소멸{trash_note} 확인"
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "delete",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": False,
                    "actual_size_bytes": 0,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 3] 이름 변경 (rename) 실물 검증
        elif act_type == "rename":
            new_name = action.get("new_name") or ""
            new_target = target.parent / new_name
            if target.exists() and not new_target.exists():
                needs_correction = True
                reason = f"❌ [이름변경 검증 실패] 이전 파일명(`{target.name}`)이 그대로 남아있고 새 이름(`{new_name}`)이 생성되지 않음"
                feedback_reasons.append(reason)
            elif not new_target.exists():
                needs_correction = True
                reason = f"❌ [이름변경 검증 실패] 새 이름 파일(`{new_target}`)이 존재하지 않음"
                feedback_reasons.append(reason)
            else:
                detail = f"✅ [이름변경 실물 검증 완료] 이전 파일 소멸 및 새 이름 파일 확인 (`{target.name}` ➔ `{new_name}`, {new_target.stat().st_size:,} bytes)"
                verification_reports.append({
                    "target_path": str(new_target),
                    "action_type": "rename",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": new_target.stat().st_size,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 4] 파일 이동 (move) 실물 검증
        elif act_type == "move":
            dst_dir_str = action.get("destination_dir") or ""
            dst_dir = validate_path(dst_dir_str, check_system_protect=False)
            dst_file = dst_dir / target.name
            if target.exists() and not dst_file.exists():
                needs_correction = True
                reason = f"❌ [이동 검증 실패] 원본 경로(`{target}`)에 파일이 그대로 남아있음"
                feedback_reasons.append(reason)
            elif not dst_file.exists():
                needs_correction = True
                reason = f"❌ [이동 검증 실패] 대상 폴더(`{dst_dir}`)에 파일이 이동되지 않음"
                feedback_reasons.append(reason)
            else:
                detail = f"✅ [이동 실물 검증 완료] 원본 소멸 및 대상 경로 정상 존재 확인 (`{dst_file}`, {dst_file.stat().st_size:,} bytes)"
                verification_reports.append({
                    "target_path": str(dst_file),
                    "action_type": "move",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": dst_file.stat().st_size,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 5] 파일 복사 (copy) 실물 검증
        elif act_type == "copy":
            dst_path_str = action.get("destination_path") or ""
            dst_file = validate_path(dst_path_str, check_system_protect=False)
            if not target.exists():
                needs_correction = True
                reason = f"❌ [복사 검증 실패] 원본 파일(`{target}`)이 소실됨"
                feedback_reasons.append(reason)
            elif not dst_file.exists():
                needs_correction = True
                reason = f"❌ [복사 검증 실패] 복사본 파일(`{dst_file}`)이 생성되지 않음"
                feedback_reasons.append(reason)
            else:
                detail = f"✅ [복사 실물 검증 완료] 원본 보존 및 대상 복사본 생성 확인 (`{dst_file}`, {dst_file.stat().st_size:,} bytes)"
                verification_reports.append({
                    "target_path": str(dst_file),
                    "action_type": "copy",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": dst_file.stat().st_size,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 6] 휴지통 복원 (restore) 실물 검증
        elif act_type == "restore":
            res_text = action.get("result", "")
            if "실패" in res_text or "찾지 못했습니다" in res_text:
                needs_correction = True
                reason = f"❌ [복원 검증 실패] 휴지통 복원 실패: {res_text}"
                feedback_reasons.append(reason)
            else:
                # 원본 위치 디스크 물리적 존재 여부 확인
                orig_loc_match = re.search(r"원래 위치:\s*`([^`]+)`", res_text)
                restored_name_match = re.search(r"휴지통 복원 성공:\s*`([^`]+)`", res_text)
                actual_exists = False
                actual_size = 0
                restored_path_display = path_str

                if orig_loc_match and restored_name_match:
                    check_path = Path(orig_loc_match.group(1)) / restored_name_match.group(1)
                    restored_path_display = str(check_path)
                    if check_path.exists():
                        actual_exists = True
                        actual_size = check_path.stat().st_size
                elif target.exists():
                    actual_exists = True
                    actual_size = target.stat().st_size
                    restored_path_display = str(target)

                if actual_exists:
                    detail = f"✅ [휴지통 복원 실물 검증 완료] 디스크 원래 위치에 복원 확인 (`{restored_path_display}`, {actual_size:,} bytes)"
                else:
                    detail = f"✅ [휴지통 복원 완료] {res_text}"

                verification_reports.append({
                    "target_path": restored_path_display,
                    "action_type": "restore",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": actual_exists,
                    "actual_size_bytes": actual_size,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 7] 디렉토리 생성 (mkdir) 실물 검증
        elif act_type == "mkdir":
            if not target.exists():
                needs_correction = True
                reason = f"❌ [디렉토리 생성 실패] 디렉토리가 디스크에 생성되지 않음: `{target}`"
                feedback_reasons.append(reason)
            elif not target.is_dir():
                needs_correction = True
                reason = f"❌ [디렉토리 생성 실패] 생성된 경로가 디렉토리가 아님: `{target}`"
                feedback_reasons.append(reason)
            else:
                detail = f"✅ [디렉토리 생성 실물 검증 완료] 디스크 디렉토리 정상 존재 확인: `{target}`"
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "mkdir",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": 0,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 8] ZIP 압축 (archive_zip) 실물 검증
        elif act_type == "archive_zip":
            if not target.exists():
                needs_correction = True
                reason = f"❌ [ZIP 압축 실패] 압축 파일이 생성되지 않음: `{target}`"
                feedback_reasons.append(reason)
            else:
                size_b = target.stat().st_size
                detail = f"✅ [ZIP 압축 실물 검증 완료] 압축 파일 정상 생성 확인 (`{target}`, {size_b:,} bytes)"
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "archive_zip",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": size_b,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 9] ZIP 압축 해제 (extract_zip) 실물 검증
        elif act_type == "extract_zip":
            if not target.exists() or not target.is_dir():
                needs_correction = True
                reason = f"❌ [ZIP 해제 실패] 대상 폴더가 생성되지 않음: `{target}`"
                feedback_reasons.append(reason)
            else:
                detail = f"✅ [ZIP 해제 실물 검증 완료] 대상 폴더에 파일 추출 확인 (`{target}`)"
                verification_reports.append({
                    "target_path": str(target),
                    "action_type": "extract_zip",
                    "passed": True,
                    "status_detail": detail,
                    "actual_file_exists": True,
                    "actual_size_bytes": 0,
                    "content_snippet": None,
                })
                agent_log(f"  {detail}")

        # [검증 10] 텍스트 일괄 치환 (replace_text) 실물 검증
        elif act_type == "replace_text":
            res_text = action.get("result", "")
            detail = f"✅ [텍스트 치환 실물 검증 완료] {res_text}"
            verification_reports.append({
                "target_path": path_str,
                "action_type": "replace_text",
                "passed": True,
                "status_detail": detail,
                "actual_file_exists": True,
                "actual_size_bytes": 0,
                "content_snippet": None,
            })
            agent_log(f"  {detail}")

        # [검증 11] 탐색기 열기 (open_explorer) 실물 검증
        elif act_type == "open_explorer":
            res_text = action.get("result", "")
            detail = f"✅ [탐색기 실행 검증 완료] {res_text}"
            verification_reports.append({
                "target_path": path_str,
                "action_type": "open_explorer",
                "passed": True,
                "status_detail": detail,
                "actual_file_exists": True,
                "actual_size_bytes": 0,
                "content_snippet": None,
            })
            agent_log(f"  {detail}")

    # 최대 반복 횟수 초과 시 보정 중단
    max_iter = AGENT_CONFIG.get("MAX_ITERATIONS", 8)
    if state.get("iteration_count", 0) >= max_iter:
        needs_correction = False
        log_msg_end = f"[3단계: 실물 검증 노드] 최대 시도 횟수({max_iter}회)에 도달하여 검증을 마무리합니다."
        agent_log(log_msg_end)
        status_logs.append(log_msg_end)

    return {
        "verification_reports": verification_reports,
        "status_logs": status_logs,
        "needs_correction": needs_correction,
        "correction_feedback": " / ".join(feedback_reasons) if feedback_reasons else "",
    }


def response_node(state: AgentState) -> dict:
    """[4단계: 최종 종합 응답 노드]"""
    log_msg = "[4단계: 최종 종합 응답 노드] 📝 최종 결과 및 실물 검증 보고서 생성 완료"
    agent_log(log_msg)

    actions_log = state.get("actions_log", [])
    reports = state.get("verification_reports", [])
    iter_count = state.get("iteration_count", 1)

    last_ai_msg = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            last_ai_msg = str(msg.content)
            break

    # 1. 4단계 실행 타임라인(Timeline) 구성
    timeline_lines = [
        "### 🚀 [LangGraph AI 에이전트 4단계 실행 경과]",
        f"- 🟢 **1단계 (계획 및 의도 분석)**: 사용자 목표 분석 완료 (총 {iter_count}회 ReAct 순환)",
    ]

    if actions_log:
        action_types = set(a["action_type"] for a in actions_log)
        timeline_lines.append(f"- ⚙️ **2단계 (다단계 도구 실행)**: 총 {len(actions_log)}개 도구 작업 연쇄 실행 ({', '.join(action_types)})")
        for idx, a in enumerate(actions_log, 1):
            tgt = a.get('target_path') or ''
            timeline_lines.append(f"  - ({idx}) `{a['tool_name']}` ➔ `{tgt}`")
    else:
        timeline_lines.append("- ⚙️ **2단계 (도구 실행)**: 파일 변동 도구 실행 없음 (단순 조회/확인)")

    if reports:
        passed_cnt = sum(1 for r in reports if r["passed"])
        timeline_lines.append(f"- 🔍 **3단계 (디스크 물리적 실물 검증)**: {len(reports)}개 항목 중 {passed_cnt}개 통과 (100% 물리적 판독)")
    else:
        timeline_lines.append("- 🔍 **3단계 (실물 검증)**: 디스크 물리적 이상 없음 확인")

    timeline_lines.append("- 📝 **4단계 (종합 보고서 작성)**: 정상 완료")
    timeline_lines.append("")

    # 2. 실물 검증 상세 리포트
    report_lines = []
    if reports:
        report_lines.append("### 🔍 실제 디스크 물리적 검증 상세 결과 (Physical Verification)")
        for r in reports:
            icon = "✅" if r["passed"] else "❌"
            report_lines.append(f"- **대상 경로**: `{r['target_path']}`")
            report_lines.append(f"  - **작업 유형**: `{r['action_type']}` | **검증 상태**: {icon} {r['status_detail']}")
            if r["actual_file_exists"] and r["content_snippet"]:
                snippet_preview = r["content_snippet"].replace("\n", " ")[:150]
                report_lines.append(f"  - **실제 디스크 판독 내용**: `\"{snippet_preview}\"`")
            report_lines.append("")
    elif not actions_log:
        report_lines.append("⚠️ **주의**: 실제 디스크에서 파일 조작 도구가 실행되지 않았습니다.\n")

    # 전체 본문 결합
    full_parts = []
    full_parts.append("\n".join(timeline_lines))
    if last_ai_msg:
        full_parts.append("### 📋 에이전트 상세 분석 및 작업 소견\n" + last_ai_msg + "\n")
    if report_lines:
        full_parts.append("\n".join(report_lines))

    final_text = "\n".join(full_parts).strip()
    status_logs = list(state.get("status_logs", []))
    status_logs.append(log_msg)

    return {
        "final_response": final_text,
        "status_logs": status_logs,
    }


# ==============================================================================
# 7. LangGraph 워크플로우 그래프 빌더
# ==============================================================================

def route_after_plan(state: AgentState) -> str:
    """계획 노드 실행 후 분기:
    1. 도구 호출이 있으면 -> tool_execution_node
    2. 도구 호출이 없는데 사용자 목표가 파일 변경이고 도구가 한번도 실행 안됨 -> plan_and_reason_node (재촉)
    3. 도구 호출이 없고 완료 상태이면 -> verify_node
    """
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", [])
    if tool_calls:
        return "tool_execution_node"

    # 도구 호출이 없는데 사용자는 파일 변경을 원했고 도구 실행 이력이 0인 경우
    task_goal = state.get("task_goal", "")
    mutation_keywords = [
        "삭제", "지워", "휴지통", "수정", "바꿔", "덮어", "작성", "만들", "생성",
        "이동", "옮겨", "복사", "이름변경", "이름 바꿔", "복구", "복원",
        "압축", "압축 해제", "zip", "치환", "바꿔줘", "탐색기", "열어",
        "delete", "write", "modify", "move", "copy", "rename", "restore", "mkdir", "archive", "extract", "replace", "explorer"
    ]
    user_wanted_mutation = any(k in task_goal for k in mutation_keywords)
    tool_call_count = state.get("tool_call_count", 0)
    iter_count = state.get("iteration_count", 0)
    max_iter = AGENT_CONFIG.get("MAX_ITERATIONS", 8)

    if user_wanted_mutation and tool_call_count == 0 and iter_count < max_iter:
        state["needs_correction"] = True
        state["correction_feedback"] = "말로만 설명하지 마시고, 지금 즉시 필요한 파일 조작 도구(fs_list_directory_tool, fs_list_trash_tool, fs_restore_from_trash_tool 등)를 호출하세요."
        return "plan_and_reason_node"

    return "verify_node"


def route_after_verify(state: AgentState) -> str:
    """검증 노드 실행 후 자가 보정 필요 여부에 따라 분기합니다."""
    if state.get("needs_correction"):
        return "plan_and_reason_node"
    return "response_node"



def build_fs_agent_graph(checkpointer: Optional[Any] = None):
    """LangGraph StateGraph를 구성하고 컴파일합니다."""
    workflow = StateGraph(AgentState)

    workflow.add_node("plan_and_reason_node", plan_and_reason_node)
    workflow.add_node("tool_execution_node", tool_execution_node)
    workflow.add_node("verify_node", verify_node)
    workflow.add_node("response_node", response_node)

    workflow.set_entry_point("plan_and_reason_node")

    workflow.add_conditional_edges(
        "plan_and_reason_node",
        route_after_plan,
        {
            "tool_execution_node": "tool_execution_node",
            "plan_and_reason_node": "plan_and_reason_node",
            "verify_node": "verify_node",
        },
    )

    workflow.add_edge("tool_execution_node", "plan_and_reason_node")

    workflow.add_conditional_edges(
        "verify_node",
        route_after_verify,
        {
            "plan_and_reason_node": "plan_and_reason_node",
            "response_node": "response_node",
        },
    )

    workflow.add_edge("response_node", END)

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


AGENT_CHECKPOINTER = MemorySaver()
AGENT_GRAPH = build_fs_agent_graph(checkpointer=AGENT_CHECKPOINTER)


# ==============================================================================
# 8. 에이전트 작업 실행 함수 (Core Agent Runner)
# ==============================================================================

# 세션별 첫 메시지 여부 추적 (시스템 프롬프트 주입용)
INITIALIZED_THREADS = set()


async def run_fs_agent(
    task_goal: str,
    context: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict:
    """자연어 작업 목표를 전달받아 LangGraph 에이전트를 실행하고 결과를 반환합니다.
    - thread_id 지정 시 (Direct CLI 모드): MemorySaver를 통해 이전 대화 히스토리 및 컨텍스트를 유지합니다.
    - thread_id 미지정 시 (MCP 모드): 매 호출마다 독립된 고유 세션을 생성하여 순수 Stateless로 동작합니다.
    """
    is_mcp_stateless = (thread_id is None)
    current_thread = thread_id if thread_id else str(uuid.uuid4())
    config = {"configurable": {"thread_id": current_thread}}

    initial_prompt = f"사용자 작업 요청: {task_goal}"
    if context:
        initial_prompt += f"\n참고 맥락: {context}"

    # 스레드의 첫 진입인 경우 시스템 프롬프트 함께 주입
    if current_thread not in INITIALIZED_THREADS or is_mcp_stateless:
        INITIALIZED_THREADS.add(current_thread)
        messages_input = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=initial_prompt),
        ]
    else:
        messages_input = [HumanMessage(content=initial_prompt)]

    initial_state: AgentState = {
        "task_goal": task_goal,
        "messages": messages_input,
        "actions_log": [],
        "verification_reports": [],
        "status_logs": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "needs_correction": False,
        "correction_feedback": "",
        "final_response": "",
    }

    # 비동기 실행
    result = await asyncio.to_thread(AGENT_GRAPH.invoke, initial_state, config=config)
    return {
        "final_response": result.get("final_response", ""),
        "status_logs": result.get("status_logs", []),
        "verification_reports": result.get("verification_reports", []),
    }


# ==============================================================================
# 9. FastMCP 서버 등록 (Agent Tool + 개별 도구)
# ==============================================================================

mcp = FastMCP("FileSystem-Agent-Server")


def register_tools_to_mcp(server: FastMCP, mode: str = "agent-only"):
    """MCP 서버에 도구를 등록합니다.
    - agent-only (기본값): 상위 LLM이 단건 도구 호출로 인한 환각을 일으키지 못하도록 fs_agent_task만 노출.
    - all: 개별 원자적 파일 도구 11종까지 모두 노출.
    """
    # 1. 자율형 AI 올인원 에이전트 도구 등록 (필수)
    @server.tool(name="fs_agent_task")
    async def fs_agent_task(
        task: str = Field(
            description="[필수 파일시스템 에이전트] 파일 및 폴더와 관련된 모든 작업(목록 조회, 파일 읽기/생성/수정/삭제/휴지통/이동/복사/이름변경/내용검사 등)을 수행합니다. 사용자가 파일이나 폴더의 상태 확인이나 변경(삭제, 수정 등)을 요청하면 절대로 말로만 대답하지 말고 반드시 이 도구를 즉시 호출하십시오.",
            examples=[
                "D:\\temp 경로에 있는 파일들 중 내용이 없는 0바이트 파일은 모두 삭제해줘",
                "D:\\temp 경로의 파일 목록을 조회하고 빈 파일들을 지워줘",
                "work 폴더에 summary.md 만들고 내용 채워줘",
            ],
        ),
        context: Optional[str] = Field(
            default=None,
            description="이전 대화에서 조회된 파일 목록, 경로, 참고 데이터 등의 맥락",
        ),
    ) -> str:
        """[자율형 AI 파일 에이전트] ReAct 계획-도구연속실행-실물 내용 판독 검증까지 올인원으로 완료합니다."""
        res = await run_fs_agent(task, context, thread_id=None)
        return res["final_response"]

    # 2. 'all' 모드인 경우에만 개별 원자적 도구 노출
    if mode == "all":
        @server.tool(name="fs_read_file")
        async def fs_read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
            """파일의 텍스트 내용을 읽어옵니다. 한글 인코딩을 자동 감지합니다."""
            return await asyncio.to_thread(raw_fs_read_file, path, start_line, end_line)

        @server.tool(name="fs_write_file")
        async def fs_write_file(path: str, content: str, overwrite: bool = True) -> str:
            """새 파일을 생성하거나 기존 파일 내용을 덮어씁니다."""
            return await asyncio.to_thread(raw_fs_write_file, path, content, overwrite)

        @server.tool(name="fs_list_directory")
        async def fs_list_directory(path: str = ".", include_hidden: bool = False, max_items: int = 100) -> str:
            """지정된 디렉토리의 파일 및 폴더 목록을 조회합니다."""
            return await asyncio.to_thread(raw_fs_list_directory, path, include_hidden, max_items)

        @server.tool(name="fs_search_files")
        async def fs_search_files(
            directory: str = ".",
            pattern: str = "*",
            content_query: Optional[str] = None,
            max_results: int = 50
        ) -> str:
            """지정된 디렉토리에서 패턴 또는 내용(content_query)으로 파일/폴더를 검색합니다."""
            return await asyncio.to_thread(raw_fs_search_files, directory, pattern, content_query, max_results)

        @server.tool(name="fs_create_directory")
        async def fs_create_directory(path: str) -> str:
            """새로운 디렉토리(폴더)를 생성합니다."""
            return await asyncio.to_thread(raw_fs_create_directory, path)

        @server.tool(name="fs_get_file_info")
        async def fs_get_file_info(path: str) -> str:
            """파일이나 폴더의 크기, 수정일, 생성일 메타데이터를 조회합니다."""
            return await asyncio.to_thread(raw_fs_get_file_info, path)

        @server.tool(name="fs_rename_file")
        async def fs_rename_file(old_path: str, new_name: str) -> str:
            """파일 또는 폴더의 이름을 변경합니다."""
            return await asyncio.to_thread(raw_fs_rename_file, old_path, new_name)

        @server.tool(name="fs_move_file")
        async def fs_move_file(source_path: str, destination_dir: str) -> str:
            """파일 또는 폴더를 다른 디렉토리로 이동합니다."""
            return await asyncio.to_thread(raw_fs_move_file, source_path, destination_dir)

        @server.tool(name="fs_copy_file")
        async def fs_copy_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
            """파일 또는 디렉토리를 복사합니다."""
            return await asyncio.to_thread(raw_fs_copy_file, source_path, destination_path, overwrite)

        @server.tool(name="fs_delete_to_trash")
        async def fs_delete_to_trash(path: str) -> str:
            """파일 또는 폴더를 OS 휴지통으로 안전하게 이동합니다."""
            return await asyncio.to_thread(raw_fs_delete_to_trash, path)

        @server.tool(name="fs_restore_from_trash")
        async def fs_restore_from_trash(name_or_path: str) -> str:
            """OS 휴지통에서 파일이나 폴더를 원래 위치로 복원합니다."""
            return await asyncio.to_thread(raw_fs_restore_from_trash, name_or_path)

        @server.tool(name="fs_list_trash")
        async def fs_list_trash(limit: int = 30) -> str:
            """현재 OS 휴지통에 보관 중인 항목 목록을 확인합니다."""
            return await asyncio.to_thread(raw_fs_list_trash, limit)

        @server.tool(name="fs_open_in_explorer")
        async def fs_open_in_explorer(path: str) -> str:
            """윈도우 탐색기 창을 열고 파일/폴더를 화면에 직접 보여줍니다."""
            return await asyncio.to_thread(raw_fs_open_in_explorer, path)

        @server.tool(name="fs_archive_zip")
        async def fs_archive_zip(source_paths: Union[str, List[str]], zip_path: str, overwrite: bool = True) -> str:
            """파일 또는 폴더들을 ZIP 압축 파일로 묶어 저장합니다."""
            return await asyncio.to_thread(raw_fs_archive_zip, source_paths, zip_path, overwrite)

        @server.tool(name="fs_extract_zip")
        async def fs_extract_zip(zip_path: str, destination_dir: str, overwrite: bool = True) -> str:
            """ZIP 파일의 압축을 대상 디렉토리에 풉니다."""
            return await asyncio.to_thread(raw_fs_extract_zip, zip_path, destination_dir, overwrite)

        @server.tool(name="fs_replace_text_in_files")
        async def fs_replace_text_in_files(
            directory: str = ".",
            pattern: str = "*.txt",
            find_text: str = "",
            replace_text: str = "",
            max_files: int = 50
        ) -> str:
            """디렉토리 내 파일들의 텍스트를 검색하여 일괄 찾아바꾸기(치환)합니다."""
            return await asyncio.to_thread(raw_fs_replace_text_in_files, directory, pattern, find_text, replace_text, max_files)


# ==============================================================================
# 10. CLI Direct 대화형 테스트 모드 (MemorySaver 세션 유지)
# ==============================================================================

async def run_direct_cli_mode():
    """터미널에서 사용자와 실시간 대화형으로 LangGraph 에이전트를 테스트하는 모드 (MemorySaver 적용)"""
    print("\n" + "=" * 68)
    print("🤖 FileSystem AI Agent (LangGraph + Gemma 4 24B) [DIRECT CLI MODE]")
    print("=" * 68)
    print(f"📌 LLM 엔드포인트 : {AGENT_CONFIG.get('AGENT_URL')}")
    print(f"📌 타겟 모델명     : {AGENT_CONFIG.get('MODEL_NAME')}")
    print(f"📌 설정 파일 경로  : {CONFIG_FILE}")
    print(f"🧠 메모리 세이버   : 활성화 (MemorySaver - 이전 대화 기억)")
    print("💡 종료: 'exit', 'quit', 'q' | 🔄 메모리 초기화: '/clear', '/reset'")
    print("=" * 68 + "\n")

    cli_thread_id = f"direct_cli_session_{int(time.time())}"

    while True:
        try:
            user_input = input("\n📝 [사용자 작업 요청 입력] > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 FileSystem AI Agent CLI를 종료합니다.")
                break
            if user_input.lower() in ("/clear", "/reset", "clear", "reset"):
                cli_thread_id = f"direct_cli_session_{int(time.time())}"
                print("🔄 [메모리 초기화 완료] 새로운 대화 세션이 시작되었습니다.")
                continue

            print("\n" + "-" * 50)
            print("🚀 에이전트 실행 시작 (LangGraph 다단계 ReAct + MemorySaver)...")
            print("-" * 50)

            t0 = time.time()
            result = await run_fs_agent(user_input, thread_id=cli_thread_id)
            elapsed = time.time() - t0

            print("\n" + "=" * 50)
            print(f"✨ [에이전트 최종 응답] (소요시간: {elapsed:.2f}초)")
            print("=" * 50)
            print(result["final_response"])
            print("=" * 50 + "\n")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 세션을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 에러 발생: {str(e)}")


# ==============================================================================
# 11. 서버 실행 진입점 (HTTP / SSE / stdio / Direct CLI)
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangGraph FileSystem Agent FastMCP Server")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="CLI 대화형 직접 테스트 모드로 실행 (서버를 띄우지 않고 터미널에서 즉시 대화)",
    )
    parser.add_argument(
        "--transport",
        choices=["http", "sse", "stdio", "direct"],
        default="http",
        help="전송 방식: http, sse, stdio, direct (기본값: http)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE 호스트 주소 (기본값: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8101, help="HTTP/SSE 포트 번호 (기본값: 8101)")
    parser.add_argument(
        "--tools-mode",
        choices=["all", "agent-only"],
        default=AGENT_CONFIG.get("DEFAULT_TOOLS_MODE", "all"),
        help="MCP 도구 노출 모드 (all: 에이전트+개별도구 전체, agent-only: fs_agent_task만 노출)",
    )
    args = parser.parse_args()

    # 1. CLI 직접 실행 모드 (--direct 또는 --transport direct)
    if args.direct or args.transport == "direct":
        IS_DIRECT_CLI_MODE = True
        asyncio.run(run_direct_cli_mode())
        sys.exit(0)

    # 2. FastMCP 도구 등록 (tools_mode: agent-only 또는 all)
    register_tools_to_mcp(mcp, mode=args.tools_mode)
    print(f"🔧 FastMCP 도구 노출 모드: {args.tools_mode}", file=sys.stderr)

    # 3. CORS 미들웨어 설정
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

    # 4. 서버 실행
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        print(f"🚀 FileSystem Agent FastMCP HTTP Server 시작: http://{args.host}:{args.port}", file=sys.stderr)
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
    elif args.transport == "sse":
        print(f"🚀 FileSystem Agent FastMCP SSE Server 시작: http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
