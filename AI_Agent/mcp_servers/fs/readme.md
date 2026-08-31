# 📁 FileSystem FastMCP 서버 사용 가이드 (`FS_GUIDE.md`)

본 문서는 **개인 작업 환경에 최적화된 파일시스템 FastMCP 서버 (`fs-mcp-server.py`)**의 보안 정책, 12개 도구 목록, 휴지통 복원 기능 및 활용법을 안내합니다.

---

## 🌟 1. 주요 특징 및 보안/권한 정책

1. **사용자 친화적 권한 개방 & 윈도우11 보호**:
   * **C: 드라이브 및 D: 드라이브 전체 경로에 대한 자유로운 접근 허용** (개인 작업 편의성 극대화).
   * 운영체제 핵심 손상을 방지하기 위해 `C:\Windows`, `C:\Program Files`, `$Recycle.Bin`, `System Volume Information` 등 **핵심 시스템 디렉토리는 안전하게 쓰기/삭제 차단**.

2. **사내 보안 정책 준수 (민감 문서 사전 차단)**:
   * 보안 규정상 LLM이 직접 열람할 수 없는 문서 확장자는 `fs_read_file`에서 자동으로 접근이 차단되며 안전한 보안 안내 메시지가 반환됩니다.
   * **차단 확장자**: `.pptx`, `.ppt`, `.xlsx`, `.xls`, `.docx`, `.doc`, `.hwp`, `.hwpx`, `.pdf`

3. **한글 인코딩 4단계 자동 감지 & 복원**:
   * 텍스트 파일 읽기 시 `UTF-8` ➔ `CP949` ➔ `UTF-8-SIG` ➔ `EUC-KR` 순으로 자동 시도하여 **한글 깨짐 현상을 원천 방지**합니다.

4. **안전 삭제 & 100% 원위치 복원 (Safe Delete & Restore)**:
   * 파일을 영구 삭제하지 않고 Windows 네이티브 `Shell.Application` API를 통해 **OS 휴지통으로 이동**합니다.
   * 휴지통에 들어간 파일을 원래 위치로 다시 꺼내오는 **`fs_restore_from_trash`** 기능을 완벽 지원합니다.

---

## 📦 2. 파이썬 필수 라이브러리 설치 (Prerequisites)

```bash
# 파일시스템 FastMCP 서버 구동에 필요한 패키지
pip install fastmcp uvicorn starlette pydantic
```

> **참고 (기본 내장 라이브러리)**:
> Windows 휴지통 연동(`ctypes`), 휴지통 복원 COM 인터페이스(`win32com` 대신 파이썬 내장 `ctypes`), 파일 조작(`shutil`, `pathlib`) 등은 **파이썬 3.10+ 표준 라이브러리**를 사용하므로 추가 외부 의존성이 없습니다.

---

## 🛠️ 3. 제공되는 파일시스템 도구 목록 (총 12개)

| 도구명 | 설명 | 사용 예시 |
| :--- | :--- | :--- |
| **`fs_read_file`** | 텍스트 파일 내용 읽기 (한글 인코딩 자동 처리, 라인 범위 지원, 오피스/한글/PDF 보안 제외) | `fs_read_file(path="C:/work/test.py", start_line=1, end_line=50)` |
| **`fs_write_file`** | 파일 쓰기 및 덮어쓰기 (부모 폴더 자동 생성) | `fs_write_file(path="C:/work/output.txt", content="Hello", overwrite=True)` |
| **`fs_list_directory`** | 디렉토리 내 파일 및 폴더 목록 조회 (크기, 수정일, 숨김파일 필터) | `fs_list_directory(path="C:/Users/JooJoo/Desktop")` |
| **`fs_search_files`** | 파일/폴더 패턴 검색 (Glob 패턴 지원) | `fs_search_files(directory="C:/work", pattern="*.json", max_results=20)` |
| **`fs_create_directory`** | 새 디렉토리(폴더) 생성 (계층 구조 지원) | `fs_create_directory(path="C:/work/new_project/src")` |
| **`fs_get_file_info`** | 파일/폴더 상세 메타데이터 정보(크기, 생성일, 권한 등) 확인 | `fs_get_file_info(path="C:/work/data.csv")` |
| **`fs_rename_file`** | 파일 또는 폴더 이름 변경 | `fs_rename_file(old_path="C:/work/old.txt", new_name="new.txt")` |
| **`fs_move_file`** | 파일 또는 폴더를 다른 디렉토리로 이동 | `fs_move_file(source_path="C:/work/a.txt", destination_dir="C:/archive")` |
| **`fs_copy_file`** | 파일 또는 디렉토리 복사 (덮어쓰기 옵션 지원) | `fs_copy_file(source_path="C:/work/a.txt", destination_path="C:/work/b.txt")` |
| **`fs_delete_to_trash`** | 영구 삭제 대신 **OS 휴지통으로 안전 이동 (Safe Delete)** | `fs_delete_to_trash(path="C:/work/temp.log")` |
| **`fs_restore_from_trash`** | **[강력 추천]** 휴지통에 있는 파일/폴더를 원래 경로로 완벽 복원 | `fs_restore_from_trash(original_file_name="temp.log")` |
| **`fs_list_trash`** | 현재 OS 휴지통에 보관 중인 삭제된 항목 목록 확인 | `fs_list_trash(limit=30)` |

---

## 🚀 4. 서버 실행 및 NeuJS 앱 연동

1. **파일시스템 서버 기동 (기본 8001 포트)**:
   ```bash
   python MCP_Servers/fs-mcp-server.py --port 8001
   ```
2. **NeuJS 앱 연결**:
   * 앱의 **`⚙️ 환경 설정 > MCP 서버`** 탭에서 **`파일시스템 (http://127.0.0.1:8001/mcp)`** 스위치를 켜면 즉시 모든 파일시스템 도구가 활성화됩니다.
