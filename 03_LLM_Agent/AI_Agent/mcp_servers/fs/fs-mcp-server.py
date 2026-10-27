"""fs-mcp-server.py - 개인 환경 최적화 FastMCP 파일시스템 서버.

제공 도구 (총 12개):
1. fs_read_file - 파일 내용 읽기 (한글 인코딩 자동 처리, 라인 범위 지원, 오피스/한글/PDF 보안 제외)
2. fs_write_file - 파일 쓰기 및 덮어쓰기
3. fs_list_directory - 디렉토리 파일 및 서브폴더 목록 조회
4. fs_search_files - 파일/디렉토리 패턴 검색 (Glob)
5. fs_create_directory - 새 디렉토리(폴더) 생성
6. fs_get_file_info - 파일/폴더 크기 및 메타데이터 정보 조회
7. fs_rename_file - 파일 또는 폴더 이름 변경
8. fs_move_file - 파일 또는 폴더 이동
9. fs_copy_file - 파일 또는 폴더 복사
10. fs_delete_to_trash - 영구 삭제 대신 OS 휴지통으로 안전 이동 (Safe Delete)
11. fs_restore_from_trash - OS 휴지통에서 파일/폴더를 원래 위치로 복원 (Restore)
12. fs_list_trash - OS 휴지통에 들어있는 파일/폴더 목록 확인
"""

import asyncio
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import sys
from typing import List, Optional

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
mcp = FastMCP("FileSystem-MCP-Server")


# ==============================================================================
# 1. 보안 및 경로 정책 설정 (Security & Allowed Paths)
# ==============================================================================

# [사내 보안 정책] 열람이 제한된 문서 확장자 목록 (MS Office, 한글, PDF)
RESTRICTED_EXTENSIONS = {
    ".pptx", ".ppt",
    ".xlsx", ".xls",
    ".docx", ".doc",
    ".hwp", ".hwpx",
    ".pdf",
}

# [시스템 보호] 윈도우11 주요 핵심 시스템 디렉토리 보호 패턴
WINDOWS_PROTECTED_PATTERNS = [
    re.compile(r"^[a-zA-Z]:\\windows(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\program files(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\program files \(x86\)(?:\\[^\\]*)*$", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\\$recycle\.bin", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\system volume information", re.IGNORECASE),
]


def get_fs_home() -> Path:
    """상대 경로 해석을 위한 기본 루트 디렉토리를 반환합니다."""
    home_env = os.environ.get("FS_LOCAL_HOME", "")
    if home_env:
        return Path(home_env).expanduser().resolve()
    return Path.cwd().resolve()


def is_windows_protected_path(path: Path) -> bool:
    """경로가 윈도우 주요 보호 시스템 디렉토리 내에 있는지 확인합니다."""
    if sys.platform != "win32":
        return False
    try:
        path_str = str(path.resolve())
        return any(pattern.match(path_str) for pattern in WINDOWS_PROTECTED_PATTERNS)
    except Exception:
        return False


def validate_path(requested_path: str, check_system_protect: bool = True) -> Path:
    """경로를 정규화하고 윈도우 핵심 시스템 폴더 보호를 검증합니다 (C:, D: 등 일반 드라이브 전체 허용)."""
    if not requested_path or not str(requested_path).strip():
        raise ValueError("경로가 비어 있습니다.")

    path = Path(requested_path.strip()).expanduser()

    # 상대 경로인 경우 기본 작업 디렉토리 기준 절대 경로로 확장
    if not path.is_absolute():
        path = get_fs_home() / path

    try:
        normalized = path.resolve()
    except Exception:
        normalized = path

    # 윈도우 핵심 시스템 폴더 보호 검사
    if check_system_protect and is_windows_protected_path(normalized):
        raise PermissionError(
            f"❌ 접근 차단: 시스템 보호를 위해 Windows 주요 시스템 디렉토리(`{normalized}`)에 대한 접근은 제한되어 있습니다."
        )

    return normalized


def read_text_safely(file_path: Path) -> str:
    """한글 인코딩(UTF-8, CP949, EUC-KR 등)을 자동으로 감지하여 텍스트 깨짐 없이 안전하게 디코딩합니다."""
    raw_bytes = file_path.read_bytes()

    # 순차적 인코딩 디코딩 시도
    encodings = ["utf-8", "cp949", "utf-8-sig", "euc-kr", "latin1"]
    for enc in encodings:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    # 모두 실패 시 에러 무시 대체
    return raw_bytes.decode("utf-8", errors="replace")


def send_to_recycle_bin(target_path: Path) -> bool:
    """파일 또는 디렉토리를 Windows OS 휴지통으로 안전하게 이동합니다 (Windows Native Safe Delete)."""
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


def get_recycle_bin_items(max_items: int = 50) -> List[dict]:
    """OS 휴지통에 있는 파일/폴더 목록을 조회합니다."""
    items_list = []
    if sys.platform == "win32":
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            bin_folder = shell.Namespace(10)  # 10 = ssfBITBUCKET
            items = bin_folder.Items()
            total = items.Count
            for i in range(min(total, max_items)):
                item = items.Item(i)
                name = item.Name
                orig_loc = bin_folder.GetDetailsOf(item, 1) or "알 수 없음"
                del_time = bin_folder.GetDetailsOf(item, 2) or "알 수 없음"
                items_list.append({
                    "name": name,
                    "original_location": orig_loc,
                    "deleted_time": del_time,
                })
        except Exception as e:
            print(f"Warning: win32com Recycle Bin query failed: {e}", file=sys.stderr)
    return items_list


def restore_from_recycle_bin(target_name_or_path: str) -> tuple[bool, Optional[str], Optional[str]]:
    """OS 휴지통에서 특정 파일 또는 폴더를 찾아 원래 위치로 복원합니다."""
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

            # 1. 파일명 일치 또는 원래 전체 경로 일치 확인
            name_match = (item_name.lower() == clean_target)
            path_match = (full_orig_path and str(full_orig_path).lower() == full_target_lower)

            if name_match or path_match:
                verbs = item.Verbs()
                for v in range(verbs.Count):
                    verb = verbs.Item(v)
                    v_name = verb.Name.replace("&", "").strip()
                    v_name_lower = v_name.lower()

                    # 한글/영문 Windows 복원 Verb 감지
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
# 2. FastMCP 도구 정의 (10개 필수 파일시스템 도구)
# ==============================================================================

@mcp.tool()
async def fs_read_file(
    path: str = Field(
        description="읽을 파일의 경로 (예: 'config.json', 'src/main.py', 'C:/Users/사용자/notes.txt')",
        examples=["config.json", "src/app.py", "README.md"],
    ),
    start_line: int = Field(
        default=1,
        description="읽기를 시작할 라인 번호 (1부터 시작)",
    ),
    end_line: Optional[int] = Field(
        default=None,
        description="읽기를 종료할 라인 번호 (포함). 비워두면 끝까지 읽습니다.",
    ),
) -> str:
    """[파일 내용 읽기] 텍스트 파일의 내용을 읽어옵니다. (한글 깨짐 자동 방지, 라인 범위 지정 지원, MS Office/한글/PDF 보안 제외)"""
    def _run():
        if not path or not str(path).strip():
            return "❌ 읽을 파일 경로를 지정해주세요."

        # [사내 보안 정책] MS Office, 한글, PDF 파일 열람 사전 제한 검사
        raw_ext = Path(str(path).strip()).suffix.lower()
        if raw_ext in RESTRICTED_EXTENSIONS:
            return (
                f"🛡️ **[사내 보안 정책 안내]**: 사내 보안 및 정책상 MS Office 문서(`{raw_ext}`: pptx, xlsx, docx 등), "
                f"한글 문서(`{raw_ext}`: hwp, hwpx), PDF 문서(`{raw_ext}`)의 본문 읽기는 제한되어 있습니다."
            )

        try:
            valid_path = validate_path(str(path).strip())
        except Exception as err:
            return str(err)

        if not valid_path.exists():
            return f"❌ 파일이 존재하지 않습니다: `{valid_path}`"
        if not valid_path.is_file():
            return f"❌ 디렉토리는 읽을 수 없습니다 (파일을 지정해주세요): `{valid_path}`"

        ext = valid_path.suffix.lower()
        if ext in RESTRICTED_EXTENSIONS:
            return (
                f"🛡️ **[사내 보안 정책 안내]**: 사내 보안 및 정책상 MS Office 문서(`{ext}`: pptx, xlsx, docx 등), "
                f"한글 문서(`{ext}`: hwp, hwpx), PDF 문서(`{ext}`)의 본문 읽기는 제한되어 있습니다."
            )

        try:
            full_text = read_text_safely(valid_path)
            lines = full_text.splitlines(keepends=True)
            total_lines = len(lines)

            s_line = int(start_line) if isinstance(start_line, int) else 1
            e_line = int(end_line) if isinstance(end_line, int) else None

            s_idx = max(1, s_line)
            e_idx = min(total_lines, e_line) if e_line and e_line > 0 else total_lines

            if s_idx > total_lines:
                return f"ℹ️ 파일의 총 라인 수({total_lines}줄)보다 시작 라인({s_idx})이 큽니다."

            selected_lines = lines[s_idx - 1 : e_idx]
            body = "".join(selected_lines)

            header = f"📄 **[`{valid_path.name}` 파일 내용]** (총 {total_lines}줄 중 {s_idx}~{e_idx}줄):\n```\n"
            footer = "\n```"
            return f"{header}{body}{footer}"
        except Exception as e:
            return f"❌ 파일 읽기 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_write_file(
    path: str = Field(
        description="생성하거나 덮어쓸 파일의 경로",
        examples=["output.txt", "src/main.py", "notes.md"],
    ),
    content: str = Field(
        description="파일에 작성할 텍스트 내용",
        examples=["print('Hello World')", "설정 데이터"],
    ),
    encoding: str = Field(
        default="utf-8",
        description="파일 저장 인코딩 (기본값: utf-8)",
    ),
) -> str:
    """[파일 쓰기] 새 파일을 생성하거나 기존 파일 내용을 덮어씁니다."""
    def _run():
        try:
            valid_path = validate_path(str(path).strip())
        except Exception as err:
            return str(err)

        parent_dir = valid_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        enc = str(encoding) if isinstance(encoding, str) and encoding.strip() else "utf-8"
        text_content = str(content) if content is not None else ""

        try:
            with open(valid_path, "w", encoding=enc) as f:
                f.write(text_content)
            return f"✅ 파일이 성공적으로 저장되었습니다: `{valid_path}` (크기: {len(text_content)}자)"
        except Exception as e:
            return f"❌ 파일 쓰기 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_list_directory(
    path: str = Field(
        default=".",
        description="조회할 디렉토리 경로 (예: '.', 'src', 'C:/Users/사용자/Desktop')",
    ),
    recursive: bool = Field(
        default=False,
        description="하위 서브 디렉토리까지 재귀적으로 조회할지 여부",
    ),
    max_depth: int = Field(
        default=0,
        description="재귀 조회 시 최대 깊이 제한 (0은 무제한)",
    ),
) -> str:
    """[디렉토리 목록 조회] 지정한 폴더 내의 파일 및 서브 디렉토리 목록을 조회합니다."""
    def _run():
        target_str = str(path).strip() if path and isinstance(path, str) else "."
        try:
            valid_path = validate_path(target_str)
        except Exception as err:
            return str(err)

        if not valid_path.exists():
            return f"❌ 디렉토리가 존재하지 않습니다: `{valid_path}`"
        if not valid_path.is_dir():
            return f"❌ 디렉토리가 아닙니다 (파일 경로): `{valid_path}`"

        is_rec = bool(recursive) if isinstance(recursive, bool) else False
        depth_limit = int(max_depth) if isinstance(max_depth, int) else 0

        try:
            if not is_rec:
                entries = []
                for entry in sorted(valid_path.iterdir()):
                    prefix = "📁 [DIR] " if entry.is_dir() else "📄 [FILE]"
                    entries.append(f"{prefix} {entry.name}")
                if not entries:
                    return f"ℹ️ 디렉토리가 비어 있습니다: `{valid_path}`"
                return f"📁 **[`{valid_path}` 디렉토리 목록 (총 {len(entries)}개)]**:\n" + "\n".join(entries)

            entries = []
            for entry in valid_path.rglob("*"):
                try:
                    if depth_limit > 0:
                        relative_path = entry.relative_to(valid_path)
                        if len(relative_path.parts) > depth_limit:
                            continue

                    prefix = "📁 [DIR] " if entry.is_dir() else "📄 [FILE]"
                    relative_path = entry.relative_to(valid_path)
                    entries.append(f"{prefix} {relative_path}")
                except ValueError:
                    continue

            if not entries:
                return f"ℹ️ 디렉토리가 비어 있습니다: `{valid_path}`"
            return f"📁 **[`{valid_path}` 재귀 목록 (총 {len(entries)}개)]**:\n" + "\n".join(sorted(entries))
        except Exception as e:
            return f"❌ 디렉토리 목록 조회 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_search_files(
    directory: str = Field(
        default=".",
        description="검색을 시작할 기준 디렉토리 경로",
        examples=[".", "src", "C:/Users/사용자/Desktop"],
    ),
    pattern: str = Field(
        default="*.*",
        description="검색할 파일/폴더 Glob 패턴 (예: '*.py', '*config*', '*.json', '*.md')",
        examples=["*.py", "*.json", "*config*", "*.md"],
    ),
    recursive: bool = Field(
        default=True,
        description="하위 디렉토리까지 재귀적으로 검색할지 여부",
    ),
    max_results: int = Field(
        default=50,
        description="최대 검색 결과 개수 제한 (기본값: 50)",
    ),
) -> str:
    """[파일 검색] 패턴(Glob)이나 키워드를 사용하여 조건에 맞는 파일을 빠르게 검색합니다."""
    def _run():
        try:
            valid_path = validate_path(directory)
        except Exception as err:
            return str(err)

        if not valid_path.exists() or not valid_path.is_dir():
            return f"❌ 검색 대상 디렉토리가 올바르지 않습니다: `{valid_path}`"

        try:
            matched = []
            generator = valid_path.rglob(pattern) if recursive else valid_path.glob(pattern)

            for item in generator:
                try:
                    rel = item.relative_to(valid_path)
                    prefix = "📁 [DIR] " if item.is_dir() else "📄 [FILE]"
                    matched.append(f"{prefix} {rel}")
                    if len(matched) >= max_results:
                        break
                except ValueError:
                    continue

            if not matched:
                return f"🔍 `{valid_path}` 내에서 패턴 `{pattern}`과(와) 일치하는 파일을 찾지 못했습니다."

            header = [
                f"🔍 **[`{valid_path}` 내 '{pattern}' 검색 결과 (총 {len(matched)}개)]**",
                "",
                *matched,
            ]
            if len(matched) >= max_results:
                header.append(f"\n*(최대 {max_results}개까지만 표시되었습니다)*")
            return "\n".join(header)
        except Exception as e:
            return f"❌ 파일 검색 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_create_directory(
    path: str = Field(
        description="생성할 디렉토리 경로 (상위 폴더가 없으면 자동 생성)",
        examples=["new_folder", "src/components", "backup/2026-08"],
    ),
) -> str:
    """[디렉토리 생성] 새 폴더(디렉토리)를 생성합니다. 상위 경로가 없으면 자동으로 함께 생성합니다."""
    def _run():
        try:
            valid_path = validate_path(path)
        except Exception as err:
            return str(err)

        if valid_path.exists():
            return f"ℹ️ 이미 존재하는 디렉토리입니다: `{valid_path}`"

        try:
            valid_path.mkdir(parents=True, exist_ok=True)
            return f"✅ 디렉토리가 성공적으로 생성되었습니다: `{valid_path}`"
        except Exception as e:
            return f"❌ 디렉토리 생성 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_get_file_info(
    path: str = Field(
        description="정보를 확인할 파일 또는 디렉토리 경로",
        examples=["config.json", "src", "README.md"],
    ),
) -> str:
    """[파일 정보 조회] 파일/폴더의 크기, 생성일, 최종 수정일, 속성 등 상세 정보를 조회합니다."""
    def _run():
        try:
            valid_path = validate_path(path)
        except Exception as err:
            return str(err)

        if not valid_path.exists():
            return f"❌ 대상이 존재하지 않습니다: `{valid_path}`"

        try:
            stat = valid_path.stat()
            is_dir = valid_path.is_dir()
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            ctime = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

            info_lines = [
                f"ℹ️ **[`{valid_path.name}` 메타데이터 정보]**",
                f"- **유형**: {'📁 디렉토리 (Folder)' if is_dir else '📄 파일 (File)'}",
                f"- **전체 경로**: `{valid_path}`",
                f"- **크기**: {size_str} ({size_bytes:,} bytes)" if not is_dir else f"- **크기**: (디렉토리)",
                f"- **최종 수정일**: {mtime}",
                f"- **생성일**: {ctime}",
            ]
            if not is_dir:
                info_lines.append(f"- **확장자**: `{valid_path.suffix.lower() or '(없음)'}`")
            return "\n".join(info_lines)
        except Exception as e:
            return f"❌ 정보 조회 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_rename_file(
    path: str = Field(
        description="이름을 변경할 파일 또는 폴더 경로",
        examples=["notes.txt", "src/old_name.py"],
    ),
    new_name: str = Field(
        description="새로운 이름 (경로가 아닌 파일명만 입력)",
        examples=["new_notes.txt", "new_name.py"],
    ),
) -> str:
    """[이름 변경] 파일 또는 폴더의 이름을 변경합니다."""
    def _run():
        try:
            valid_source = validate_path(path)
        except Exception as err:
            return str(err)

        if not valid_source.exists():
            return f"❌ 대상 파일/폴더가 존재하지 않습니다: `{valid_source}`"

        cleaned_name = Path(new_name).name
        if not cleaned_name:
            return "❌ 올바른 새 이름을 입력해주세요."

        destination = valid_source.parent / cleaned_name
        try:
            valid_dest = validate_path(str(destination))
        except Exception as err:
            return str(err)

        if valid_dest.exists():
            return f"❌ 동일한 이름의 파일/폴더가 이미 존재합니다: `{valid_dest}`"

        try:
            valid_source.rename(valid_dest)
            return f"✅ 이름이 성공적으로 변경되었습니다: `{valid_source.name}` ➔ `{cleaned_name}`"
        except Exception as e:
            return f"❌ 이름 변경 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_move_file(
    source: str = Field(
        description="이동할 원본 파일 또는 폴더 경로",
        examples=["old_dir/test.txt", "temp_folder"],
    ),
    destination: str = Field(
        description="이동할 목적지 경로",
        examples=["new_dir/test.txt", "archive/temp_folder"],
    ),
) -> str:
    """[파일 이동] 파일 또는 폴더를 다른 위치로 이동합니다."""
    def _run():
        try:
            valid_source = validate_path(source)
            valid_dest = validate_path(destination)
        except Exception as err:
            return str(err)

        if not valid_source.exists():
            return f"❌ 원본 대상이 존재하지 않습니다: `{valid_source}`"

        try:
            if valid_dest.exists() and valid_dest.is_dir():
                final_dest = valid_dest / valid_source.name
            else:
                final_dest = valid_dest

            if final_dest.exists():
                return f"❌ 목적지에 동일한 파일/폴더가 이미 존재합니다: `{final_dest}`"

            if final_dest.parent:
                final_dest.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(valid_source), str(final_dest))
            return f"✅ 성공적으로 이동되었습니다: `{valid_source}` ➔ `{final_dest}`"
        except Exception as e:
            return f"❌ 이동 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_copy_file(
    source: str = Field(
        description="복사할 원본 파일 또는 폴더 경로",
        examples=["template.py", "assets_folder"],
    ),
    destination: str = Field(
        description="복사될 목적지 경로",
        examples=["template_copy.py", "assets_backup"],
    ),
) -> str:
    """[파일 복사] 파일 또는 폴더를 지정한 목적지 경로로 복사합니다."""
    def _run():
        try:
            valid_source = validate_path(source)
            valid_dest = validate_path(destination)
        except Exception as err:
            return str(err)

        if not valid_source.exists():
            return f"❌ 원본 대상이 존재하지 않습니다: `{valid_source}`"

        try:
            if valid_dest.exists() and valid_dest.is_dir() and valid_source.is_file():
                final_dest = valid_dest / valid_source.name
            else:
                final_dest = valid_dest

            if final_dest.parent:
                final_dest.parent.mkdir(parents=True, exist_ok=True)

            if valid_source.is_dir():
                shutil.copytree(str(valid_source), str(final_dest), dirs_exist_ok=True)
                return f"✅ 디렉토리가 성공적으로 복사되었습니다: `{valid_source}` ➔ `{final_dest}`"
            else:
                shutil.copy2(str(valid_source), str(final_dest))
                return f"✅ 파일이 성공적으로 복사되었습니다: `{valid_source}` ➔ `{final_dest}`"
        except Exception as e:
            return f"❌ 복사 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_delete_to_trash(
    path: str = Field(
        description="OS 휴지통으로 안전하게 이동할 파일 또는 폴더 경로",
        examples=["temp.txt", "old_folder", "build/output.log"],
    ),
) -> str:
    """[휴지통 이동] 파일 또는 폴더를 영구 삭제하지 않고 OS 휴지통으로 안전하게 이동합니다 (Safe Delete)."""
    def _run():
        try:
            valid_path = validate_path(path)
        except Exception as err:
            return str(err)

        if not valid_path.exists():
            return f"❌ 삭제 대상이 존재하지 않습니다: `{valid_path}`"

        try:
            send_to_recycle_bin(valid_path)
            item_type = "디렉토리" if valid_path.is_dir() else "파일"
            return f"🗑️ {item_type}을(를) OS 휴지통으로 안전하게 이동했습니다: `{valid_path}`"
        except Exception as e:
            return f"❌ 휴지통 이동 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_restore_from_trash(
    name_or_path: str = Field(
        description="휴지통에서 원래 위치로 복원할 파일 또는 폴더 이름(또는 원래 전체 경로)",
        examples=["notes.txt", "project_backup", "C:/Users/사용자/Desktop/important.py"],
    ),
) -> str:
    """[휴지통 복원] OS 휴지통에 있는 파일 또는 폴더를 찾아 원래 있던 위치로 복원합니다 (Restore)."""
    def _run():
        target = str(name_or_path).strip() if name_or_path else ""
        if not target:
            return "❌ 복원할 파일 또는 폴더 이름을 지정해주세요."

        try:
            success, item_name, orig_loc = restore_from_recycle_bin(target)
            if success:
                loc_str = f" (원래 위치: `{orig_loc}`)" if orig_loc else ""
                return f"♻️ 휴지통에서 `{item_name}`을(를) 성공적으로 원래 위치로 복원했습니다!{loc_str}"
            else:
                return (
                    f"ℹ️ 휴지통에서 `{target}` 항목을 찾지 못했습니다.\n"
                    f"`fs_list_trash()` 도구로 현재 휴지통에 보관된 파일 목록을 먼저 확인해보세요."
                )
        except Exception as e:
            return f"❌ 휴지통 복원 실패: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_list_trash(
    max_items: int = Field(
        default=50,
        description="조회할 최대 휴지통 항목 개수 (기본값: 50)",
    ),
) -> str:
    """[휴지통 목록 조회] 현재 OS 휴지통에 보관 중인 파일 및 폴더 목록(이름, 원래 위치, 삭제일시)을 조회합니다."""
    def _run():
        limit = int(max_items) if isinstance(max_items, int) else 50
        try:
            items = get_recycle_bin_items(max_items=limit)
            if not items:
                return "ℹ️ 현재 OS 휴지통이 비어 있습니다."

            lines = [
                f"🗑️ **[OS 휴지통 보관 목록 (총 {len(items)}개)]**",
                "",
            ]
            for it in items:
                lines.append(f"- 📄 **`{it['name']}`** | 원래 위치: `{it['original_location']}` | 삭제일시: {it['deleted_time']}")

            lines.append("")
            lines.append("💡 복원하려면 `fs_restore_from_trash(name_or_path='파일명')` 도구를 호출하세요.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ 휴지통 목록 조회 실패: {str(e)}"

    return await asyncio.to_thread(_run)


# ==============================================================================
# 3. 서버 실행 진입점 (HTTP / SSE / stdio)
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced File System FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["http", "sse", "stdio"],
        default="http",
        help="전송 방식: http, sse, stdio (기본값: http)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE 호스트 주소 (기본값: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="HTTP/SSE 포트 번호 (기본값: 8001)")
    args = parser.parse_args()

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
        print(f"🚀 FileSystem FastMCP HTTP Server 시작 (CORS 전체 허용): http://{args.host}:{args.port}", file=sys.stderr)
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )
    elif args.transport == "sse":
        print(f"🚀 FileSystem FastMCP SSE Server 시작 (CORS 전체 허용): http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            allowed_origins=["*"],
            allowed_hosts=["*"],
            middleware=cors_middleware,
        )


