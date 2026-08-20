"""Standalone FastMCP Server for File System Operations.

This server provides File System tools using FastMCP,
independent of Django or pyhub internal frameworks.
"""

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
from fnmatch import fnmatch
import os
from pathlib import Path
import re
from typing import List, Optional

from fastmcp import FastMCP
from pydantic import Field

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
    """Validate and normalize a file path against allowed directories.

    Args:
        requested_path: The path to validate (str or Path)

    Returns:
        Path: The normalized absolute path if valid

    Raises:
        ValueError: If path is outside allowed directories
    """
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
            raise ValueError(
                f"Access denied - path outside allowed directories: {normalized_requested}"
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
# Helper Data Structures & Utilities
# ==============================================================================

@dataclass
class EditOperation:
    """File edit operation."""
    old_text: str
    new_text: str


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to \n."""
    return text.replace("\r\n", "\n")


def create_unified_diff(original_content: str, new_content: str, filepath: Path) -> str:
    """Create a unified diff between original and new content."""
    original = normalize_line_endings(original_content)
    modified = normalize_line_endings(new_content)

    filepath_str = str(filepath)
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=filepath_str,
        tofile=filepath_str,
        fromfiledate="original",
        tofiledate="modified",
    )
    return "".join(diff)


def apply_file_edits(
    file_path: Path,
    edits: list[EditOperation],
    dry_run: bool = False,
) -> str:
    """Apply edits to a file and return the diff."""
    with file_path.open("r", encoding="utf-8") as f:
        content = normalize_line_endings(f.read())

    modified_content = content
    for edit in edits:
        old_text = normalize_line_endings(edit.old_text)
        new_text = normalize_line_endings(edit.new_text)

        # Try exact match first
        if old_text in modified_content:
            modified_content = modified_content.replace(old_text, new_text)
            continue

        # Try line-by-line matching with whitespace flexibility
        old_lines = old_text.split("\n")
        content_lines = modified_content.split("\n")
        match_found = False

        for i in range(len(content_lines) - len(old_lines) + 1):
            potential_match = content_lines[i : i + len(old_lines)]

            is_match = all(
                old_line.strip() == content_line.strip()
                for old_line, content_line in zip(old_lines, potential_match, strict=False)
            )

            if is_match:
                original_indent = content_lines[i].replace(content_lines[i].lstrip(), "")
                new_lines = []

                for j, line in enumerate(new_text.split("\n")):
                    if j == 0:
                        new_lines.append(original_indent + line.lstrip())
                    else:
                        old_indent = old_lines[j].replace(old_lines[j].lstrip(), "")
                        new_indent = line.replace(line.lstrip(), "")
                        if old_indent and new_indent:
                            relative_indent = len(new_indent) - len(old_indent)
                            new_lines.append(original_indent + " " * max(0, relative_indent) + line.lstrip())
                        else:
                            new_lines.append(line)

                content_lines[i : i + len(old_lines)] = new_lines
                modified_content = "\n".join(content_lines)
                match_found = True
                break

        if not match_found:
            raise ValueError(f"Could not find exact match for edit:\n{edit.old_text}")

    diff = create_unified_diff(content, modified_content, file_path)

    num_backticks = 3
    while "`" * num_backticks in diff:
        num_backticks += 1
    formatted_diff = f"{'`' * num_backticks}diff\n{diff}{'`' * num_backticks}\n\n"

    if not dry_run:
        with file_path.open("w", encoding="utf-8") as f:
            f.write(modified_content)

    return formatted_diff


# ==============================================================================
# MCP Tools - File System Operations
# ==============================================================================

@mcp.tool()
async def fs_read_file(
    path: str = Field(
        description="Path to the file to read",
        examples=["data.txt", "~/documents/notes.md"],
    ),
) -> str:
    """Read the complete contents of a file from the file system."""
    def _run():
        valid_path = validate_path(path)
        try:
            with open(valid_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError as e:
            raise ValueError(f"File {path} is not a valid text file") from e
        except IOError as e:
            raise ValueError(f"Error reading file {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_read_multiple_files(
    paths: list[str] = Field(
        description="List of file paths to read",
        examples=[
            ["data1.txt", "data2.txt"],
            ["~/documents/notes.md", "./config.json"],
        ],
    ),
) -> str:
    """Read the contents of multiple files simultaneously (returned as Base64 encoded strings)."""
    def _run():
        results = []
        for file_path in paths:
            try:
                valid_path = validate_path(file_path)
                with open(valid_path, "rb") as f:
                    content = base64.b64encode(f.read()).decode("utf-8")
                results.append(f"{file_path}: {content}")
            except (ValueError, IOError) as e:
                results.append(f"{file_path}: Error - {str(e)}")
        return "\n".join(results)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_write_file(
    path: str = Field(
        description="Path where to write the file",
        examples=["output.txt", "~/documents/notes.md"],
    ),
    text_content: str = Field(
        default="",
        description=(
            "Text Content to write to the file. If both text_content and base64_content are provided, "
            "text_content takes precedence."
        ),
        examples=["Hello World", "{'key': 'value'}"],
    ),
    base64_content: str = Field(
        default="",
        description=(
            "Base64 encoded binary content to write to the file. "
            "This is used only when text_content is empty. The content will be decoded from base64 before writing."
        ),
        examples=["SGVsbG8gV29ybGQ=", "eydrZXknOiAndmFsdWUnfQ=="],
    ),
    text_encoding: str = Field(default="utf-8", description="Encoding of text_content"),
) -> str:
    """Create a new file or completely overwrite an existing file with new content."""
    def _run():
        valid_path = validate_path(path)
        parent_dir = valid_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        try:
            if text_content:
                with open(valid_path, "wt", encoding=text_encoding) as f:
                    f.write(text_content)
            elif base64_content:
                try:
                    binary_content = base64.b64decode(base64_content)
                    with open(valid_path, "wb") as f:
                        f.write(binary_content)
                except Exception as e:
                    raise ValueError(f"Invalid base64 content: {str(e)}") from e
            else:
                raise ValueError("No content to write")

            return f"Successfully wrote to {valid_path}"
        except IOError as e:
            raise ValueError(f"Error writing to file {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_edit_file(
    path: str = Field(
        description="Path to the file to edit",
        examples=["script.py", "~/documents/notes.md"],
    ),
    edits: list[dict[str, str]] = Field(
        description="List of edit operations. Each edit should have 'old_text' and 'new_text'",
        examples=[
            [
                {"old_text": "def old_name", "new_text": "def new_name"},
                {"old_text": "print('hello')", "new_text": "print('world')"},
            ]
        ],
    ),
    dry_run: bool = Field(
        default=False,
        description="Preview changes using git-style diff format without applying them",
    ),
) -> str:
    """Make line-based edits to a text file and return a git-style unified diff."""
    def _run():
        valid_path = validate_path(path)
        edit_operations = [
            EditOperation(old_text=edit["old_text"], new_text=edit["new_text"]) for edit in edits
        ]
        return apply_file_edits(valid_path, edit_operations, dry_run)

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_create_directory(
    path: str = Field(
        description="Path of the directory to create",
        examples=["new_folder", "~/documents/project/src"],
    ),
) -> str:
    """Create a new directory or ensure a directory exists."""
    def _run():
        valid_path = validate_path(path)
        try:
            valid_path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory {path}"
        except IOError as e:
            raise ValueError(f"Error creating directory {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_list_directory(
    path: str = Field(
        default=".",
        description="Path of the directory to list",
        examples=[".", "~/documents", "project/src"],
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
    """Get a detailed listing of files and directories in a specified path."""
    def _run():
        valid_path = validate_path(path)
        try:
            if not recursive:
                entries = []
                for entry in valid_path.iterdir():
                    prefix = "[DIR]" if entry.is_dir() else "[FILE]"
                    entries.append(f"{prefix} {entry.name}")
                return "\n".join(sorted(entries))

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

            return "\n".join(sorted(entries))
        except IOError as e:
            raise ValueError(f"Error listing directory {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_move_file(
    source: str = Field(
        description="Source path of file or directory to move",
        examples=["old_name.txt", "~/documents/old_folder"],
    ),
    destination: str = Field(
        description="Destination path where to move the file or directory",
        examples=["new_name.txt", "~/documents/new_folder"],
    ),
) -> str:
    """Move or rename files and directories."""
    def _run():
        valid_source = validate_path(source)
        valid_dest = validate_path(destination)
        try:
            if not valid_source.exists():
                raise ValueError(f"Source does not exist: {source}")
            if not valid_source.is_file():
                raise ValueError(f"Source must be a file: {source}")

            if valid_dest.exists() and valid_dest.is_dir():
                valid_dest = valid_dest / valid_source.name
            elif valid_dest.exists():
                raise ValueError(f"Destination already exists: {valid_dest}")

            if valid_dest.parent:
                valid_dest.parent.mkdir(parents=True, exist_ok=True)

            valid_source.rename(valid_dest)
            return f"Successfully moved {source} to {valid_dest}"
        except IOError as e:
            raise ValueError(f"Error moving {source} to {valid_dest}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_find_files(
    path: str = Field(
        default=".",
        description="Base directory path to start search from",
        examples=[".", "~/documents", "project/src"],
    ),
    name_pattern: str = Field(
        default="",
        description="Pattern to match filenames (supports wildcards like *.py)",
        examples=["*.py", "test*", "*.{jpg,png}"],
    ),
    exclude_patterns: str = Field(
        default="",
        description="Comma-separated patterns to exclude from search (e.g., '*.pyc, .git/**')",
        examples=["*.pyc, .git/**", "node_modules/**, *.tmp"],
    ),
    max_depth: int = Field(
        default=0,
        description="Maximum depth to traverse (0 for unlimited)",
        examples=[1, 2, 3],
    ),
) -> str:
    """Recursively search for files matching patterns."""
    def _run():
        valid_path = validate_path(path)
        excludes = [s.strip() for s in exclude_patterns.split(",") if s.strip()]
        results = []

        try:
            for root, _, files in os.walk(valid_path):
                root_path = Path(root)
                try:
                    relative_root = root_path.relative_to(valid_path)
                    current_depth = len(relative_root.parts)

                    if max_depth > 0 and current_depth > max_depth:
                        continue

                    for file in files:
                        file_path = root_path / file
                        try:
                            validate_path(str(file_path))
                            relative_path = file_path.relative_to(valid_path)

                            should_exclude = any(
                                fnmatch(str(relative_path), exclude_pattern) for exclude_pattern in excludes
                            )
                            if should_exclude:
                                continue

                            if name_pattern and not fnmatch(file, name_pattern):
                                continue

                            results.append(str(file_path))
                        except ValueError:
                            continue

                except ValueError:
                    continue

            if not results:
                return "No matches found"

            return "\n".join(sorted(results))
        except IOError as e:
            raise ValueError(f"Error searching in {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_get_file_info(
    path: str = Field(
        description="Path to the file or directory to get info about",
        examples=["script.py", "~/documents/project"],
    ),
) -> str:
    """Retrieve detailed metadata about a file or directory."""
    def _run():
        valid_path = validate_path(path)
        try:
            stats = os.stat(valid_path)
            created = datetime.fromtimestamp(stats.st_ctime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            modified = datetime.fromtimestamp(stats.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            accessed = datetime.fromtimestamp(stats.st_atime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            type_ = "directory" if valid_path.is_dir() else "file"
            permissions = oct(stats.st_mode)[-3:]

            info = {
                "size": f"{stats.st_size:,} bytes",
                "created": created,
                "modified": modified,
                "accessed": accessed,
                "type": type_,
                "permissions": permissions,
            }

            return "\n".join(f"{key}: {value}" for key, value in info.items())
        except IOError as e:
            raise ValueError(f"Error getting info for {path}: {str(e)}") from e

    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_list_allowed_directories() -> str:
    """Returns the list of directories that this server is allowed to access."""
    return "Allowed directories:\n" + "\n".join(map(str, get_allowed_directories()))


# ==============================================================================
# Server Entry Point
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="File System FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport type: stdio, sse, or http (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address for HTTP/SSE (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP/SSE (default: 8001)")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
