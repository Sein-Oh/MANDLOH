"""Standalone FastMCP Server for File System Operations.

Essential File System tools:
1. fs_list_directory - 경로에 있는 파일목록 조회
2. fs_rename_file - 파일명 수정
3. fs_move_file - 파일 이동
4. fs_copy_file - 파일 복사
5. fs_write_file - 파일 쓰기
6. fs_delete_to_trash - 영구 삭제 대신 OS 휴지통으로 안전 이동
"""

import asyncio
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

# Initialize FastMCP Server
mcp = FastMCP("FileSystem-MCP-Server")


# ==============================================================================
# Configuration & Security Settings
# ==============================================================================

def get_fs_home() -> Path:
    """Retrieve home directory for relative path resolution."""
    home_env = os.environ.get("FS_LOCAL_HOME", "")
    if home_env:
        return Path(home_env).expanduser().resolve()
    return Path.cwd().resolve()


def get_allowed_directories() -> List[Path]:
    """Retrieve list of allowed directories from environment or default."""
    allowed_env = os.environ.get("FS_LOCAL_ALLOWED_DIRECTORIES", "")
    if allowed_env:
        return [
            Path(p.strip()).expanduser().resolve()
            for p in re.split(r"[,;]", allowed_env)
            if p.strip()
        ]
    # Default allowed directories: current working directory & user home
    return [get_fs_home(), Path.home().resolve()]


def validate_path(requested_path: str) -> Path:
    """Validate and normalize a file path against allowed directories."""
    path = Path(requested_path).expanduser()

    # Relative path handling
    if not path.is_absolute():
        path = get_fs_home() / path

    allowed_local_directories = get_allowed_directories()

    if len(allowed_local_directories) == 0:
        raise ValueError("No allowed local directories are set")

    try:
        normalized_requested = path.resolve()

        # Check if path is within allowed directories
        is_allowed = any(
            str(normalized_requested).startswith(str(local_path))
            for local_path in allowed_local_directories
        )
        if not is_allowed:
            allowed_str = ", ".join(str(d) for d in allowed_local_directories)
            raise ValueError(
                f"Access denied - path '{normalized_requested}' is outside allowed directories ({allowed_str}). "
                f"Please specify a path inside one of the allowed directories."
            )
        return normalized_requested
    except FileNotFoundError as e:
        # For new files that don't exist yet, verify parent directory
        parent_dir = path.parent
        try:
            real_parent_path = parent_dir.resolve()
            is_parent_allowed = any(
                str(real_parent_path).startswith(str(dir_.resolve()))
                for dir_ in allowed_local_directories
            )
            if not is_parent_allowed:
                raise ValueError("Access denied - parent directory outside allowed directories") from e
            return path
        except FileNotFoundError as err:
            raise ValueError(f"Parent directory does not exist: {parent_dir}") from err


# ==============================================================================
# Helper Utilities (Safe Delete)
# ==============================================================================


def send_to_recycle_bin(target_path: Path) -> bool:
    """Move file or directory to OS Recycle Bin (Trash) safely."""
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
        FOF_ALLOWUNDO = 0x0040  # Preserve in Recycle Bin
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
        raise NotImplementedError("Recycle Bin operation is only supported on Windows in this environment.")


# ==============================================================================
# MCP Tools (Essential File System Operations)
# ==============================================================================

@mcp.tool()
async def fs_list_directory(
    path: str = Field(
        default=".",
        description="Path of the directory to list (e.g. '.', 'src', 'C:/Users/...')",
    ),
    recursive: bool = Field(
        default=False,
        description="Whether to recursively list subdirectories",
    ),
    max_depth: int = Field(
        default=0,
        description="Maximum depth for recursive listing (0 for unlimited)",
    ),
) -> str:
    """[경로 파일목록 조회] 지정한 디렉토리 내의 파일 및 서브 디렉토리 목록을 조회합니다."""
    def _run():
        valid_path = validate_path(path)
        if not valid_path.exists():
            return f"❌ Target directory does not exist: {valid_path}"
        if not valid_path.is_dir():
            return f"❌ Target path is not a directory: {valid_path}"

        try:
            if not recursive:
                entries = []
                for entry in valid_path.iterdir():
                    prefix = "[DIR]" if entry.is_dir() else "[FILE]"
                    entries.append(f"{prefix} {entry.name}")
                if not entries:
                    return f"ℹ️ Directory is empty: {valid_path}"
                return f"📁 Directory listing for `{valid_path}`:\n" + "\n".join(sorted(entries))

            entries = []
            for entry in valid_path.rglob("*"):
                try:
                    if max_depth > 0:
                        relative_path = entry.relative_to(valid_path)
                        if len(relative_path.parts) > max_depth:
                            continue

                    prefix = "[DIR]" if entry.is_dir() else "[FILE]"
                    relative_path = entry.relative_to(valid_path)
                    entries.append(f"{prefix} {relative_path}")
                except ValueError:
                    continue

            if not entries:
                return f"ℹ️ Directory is empty: {valid_path}"
            return f"📁 Recursive listing for `{valid_path}`:\n" + "\n".join(sorted(entries))
        except IOError as e:
            return f"❌ Error listing directory {path}: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_rename_file(
    path: str = Field(
        description="Path of the file or directory to rename",
        examples=["notes.txt", "src/old_name.py"],
    ),
    new_name: str = Field(
        description="New file or directory name (just the new name, not a full path)",
        examples=["new_notes.txt", "new_name.py"],
    ),
) -> str:
    """[파일명 수정] 지정한 파일 또는 폴더의 이름을 변경합니다."""
    def _run():
        valid_source = validate_path(path)
        if not valid_source.exists():
            return f"❌ Target path does not exist: {valid_source}"

        cleaned_name = Path(new_name).name
        if not cleaned_name:
            return "❌ Invalid new name provided."

        destination = valid_source.parent / cleaned_name
        valid_dest = validate_path(str(destination))

        if valid_dest.exists():
            return f"❌ Destination already exists: {valid_dest}"

        try:
            valid_source.rename(valid_dest)
            return f"✅ Successfully renamed '{valid_source.name}' to '{cleaned_name}' (Path: {valid_dest})"
        except IOError as e:
            return f"❌ Error renaming {path}: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_move_file(
    source: str = Field(
        description="Source path of file or directory to move",
        examples=["old_dir/test.txt", "temp_folder"],
    ),
    destination: str = Field(
        description="Destination path where to move the file or directory",
        examples=["new_dir/test.txt", "archive/temp_folder"],
    ),
) -> str:
    """[파일 이동] 파일 또는 디렉토리를 다른 경로로 이동합니다."""
    def _run():
        valid_source = validate_path(source)
        valid_dest = validate_path(destination)

        if not valid_source.exists():
            return f"❌ Source does not exist: {source}"

        try:
            if valid_dest.exists() and valid_dest.is_dir():
                final_dest = valid_dest / valid_source.name
            else:
                final_dest = valid_dest

            if final_dest.exists():
                return f"❌ Destination path already exists: {final_dest}"

            if final_dest.parent:
                final_dest.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(valid_source), str(final_dest))
            return f"✅ Successfully moved '{valid_source}' to '{final_dest}'"
        except Exception as e:
            return f"❌ Error moving {source} to {destination}: {str(e)}"

    return await asyncio.to_thread(_run)

@mcp.tool()
async def fs_copy_file(
    source: str = Field(
        description="Source path of file or directory to copy",
        examples=["template.py", "assets_folder"],
    ),
    destination: str = Field(
        description="Destination path where to copy the file or directory",
        examples=["template_copy.py", "assets_backup"],
    ),
) -> str:
    """[파일 복사] 파일 또는 디렉토리를 지정한 목적지 경로로 복사합니다."""
    def _run():
        valid_source = validate_path(source)
        valid_dest = validate_path(destination)

        if not valid_source.exists():
            return f"❌ Source does not exist: {source}"

        try:
            if valid_dest.exists() and valid_dest.is_dir() and valid_source.is_file():
                final_dest = valid_dest / valid_source.name
            else:
                final_dest = valid_dest

            if final_dest.parent:
                final_dest.parent.mkdir(parents=True, exist_ok=True)

            if valid_source.is_dir():
                shutil.copytree(str(valid_source), str(final_dest), dirs_exist_ok=True)
                return f"✅ Successfully copied directory '{valid_source}' to '{final_dest}'"
            else:
                shutil.copy2(str(valid_source), str(final_dest))
                return f"✅ Successfully copied file '{valid_source}' to '{final_dest}'"
        except Exception as e:
            return f"❌ Error copying {source} to {destination}: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_write_file(
    path: str = Field(
        description="Path of the file to create or overwrite",
        examples=["output.txt", "src/main.py", "notes.md"],
    ),
    content: str = Field(
        description="The text content to write to the file",
        examples=["Hello World\nLine 2", "print('hello')"],
    ),
    encoding: str = Field(
        default="utf-8",
        description="File encoding (default: utf-8)",
    ),
) -> str:
    """[파일 쓰기] 새 파일을 생성하거나 기존 파일 내용을 덮어씁니다."""
    def _run():
        valid_path = validate_path(path)
        parent_dir = valid_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(valid_path, "w", encoding=encoding) as f:
                f.write(content)
            return f"✅ Successfully wrote file: {valid_path} ({len(content)} characters)"
        except IOError as e:
            return f"❌ Failed to write file {path}: {str(e)}"

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_delete_to_trash(
    path: str = Field(
        description="Path of the file or directory to safely move to the OS Recycle Bin (Trash)",
        examples=["temp.txt", "old_folder", "build/output.log"],
    ),
) -> str:
    """[휴지통 이동] 파일 또는 폴더를 영구 삭제하지 않고 OS 휴지통으로 안전하게 이동합니다."""
    def _run():
        valid_path = validate_path(path)
        if not valid_path.exists():
            return f"❌ Target path does not exist: {valid_path}"

        try:
            send_to_recycle_bin(valid_path)
            item_type = "Directory" if valid_path.is_dir() else "File"
            return f"🗑️ Successfully moved {item_type.lower()} to Recycle Bin: '{valid_path}' (Safe Delete)."
        except Exception as e:
            return f"❌ Failed to move to Recycle Bin: {str(e)}"

    return await asyncio.to_thread(_run)


# ==============================================================================
# Server Entry Point
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="File System FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["http", "sse", "stdio"],
        default="http",
        help="Transport type: http, sse, or stdio (default: http)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address for HTTP/SSE (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP/SSE (default: 8001)")
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

