# 📖 LLM-Native Wiki 지식 베이스 & 인덱서 사용 가이드

본 문서는 **FastMCP 기반 LLM Wiki 서버** 및 **스마트 지식 그래프 인덱서(Indexer)**의 구조와 활용법을 안내합니다.

---

## 🌟 1. 시스템 핵심 아키텍처

```text
MCP_Servers/
├── wiki-mcp-server.py       # LLM 연동 FastMCP 서버 (HTTP/SSE/stdio 지원, 포트 8003)
├── wiki_indexer.py          # 지식 그래프 색인 및 00_INDEX.md 자동 빌더
└── wiki_data/               # 로컬 마크다운(.md) 지식 저장소
    ├── 00_INDEX.md          # 📊 전체 지식 대시보드 (자동 갱신)
    ├── 📁 14_CFR_Part33/    # ✈️ 항공 엔진 감항 기준 규정 조항들
    │   ├── 33.28_Engine_Control_Systems.md
    │   ├── 33.75_Safety_Analysis.md
    │   └── ...
    └── 📁 Development/      # 💻 개발 팁 및 엔지니어링 가이드
        └── FMEA_Python_Guide.md
```

* **사람에게는**: 분야별 폴더로 깔끔하게 정리된 마크다운 노트 (옵시디언, 메모장 완벽 호환).
* **AI에게는**: 폴더 위치와 상관없이 `[[문서명]]`으로 전역 연결되는 단일 지식 그래프.

---

## 📦 2. 파이썬 필수 라이브러리 설치 (Prerequisites)

위키 서버 및 인덱서를 구동하기 위해 아래 라이브러리들을 설치해야 합니다:

```bash
# 위키 FastMCP 서버 구동에 필요한 핵심 패키지
pip install fastmcp uvicorn starlette pydantic
```

### 📋 주요 패키지 상세 안내
* **`fastmcp`**: LLM 모델과 통신하는 고성능 MCP 서버 프레임워크
* **`uvicorn`**: HTTP 및 SSE 통신을 서빙하는 비동기 웹 서버 (ASGI)
* **`starlette`**: 브라우저 통신을 위한 CORS 미들웨어 처리
* **`pydantic`**: 도구 파라미터 유효성 검증 및 스키마 생성

> **참고 (기본 내장 라이브러리)**:
> Windows 휴지통 연동(`ctypes`), 파일 탐색(`pathlib`), 정규표현식(`re`), 비동기(`asyncio`) 등은 **파이썬 3.10+ 기본 표준 라이브러리**에 포함되어 있어 별도 설치가 필요 없습니다.

---

## 🛠️ 3. 제공되는 MCP 도구 목록 (총 7개)

| 도구명 | 설명 | 사용 예시 |
| :--- | :--- | :--- |
| **`wiki_read`** | 문서 내용 + ➡️ **참조 링크** + ⬅️ **역링크(Backlinks) 동시 조회** | `wiki_read(title="33.28_Engine_Control_Systems")` |
| **`wiki_create_or_update`** | 문서 생성/갱신 (카테고리 서브폴더 자동 생성, 덮어쓰기/덧붙이기 지원) | `wiki_create_or_update(title="v2_로드맵", content="...", category="Project")` |
| **`wiki_search`** | 키워드, 태그, 분야(서브폴더) 기반 고속 통합 검색 | `wiki_search(query="FADEC", tag="Part33")` |
| **`wiki_list_all`** | 전체 문서 목차를 분야별 계층 트리 뷰로 확인 | `wiki_list_all(category="14_CFR_Part33")` |
| **`wiki_backlinks`** | 특정 조항을 참조하고 있는 모든 상위/연관 조항 역추적 | `wiki_backlinks(title="33.75_Safety_Analysis")` |
| **`wiki_rebuild_index`** | **[NEW]** 전체 지식 그래프 색인 재구축 & `00_INDEX.md` 대시보드 갱신 | `wiki_rebuild_index(auto_link=True)` |
| **`wiki_delete_to_trash`** | 문서를 영구 삭제하지 않고 OS 휴지통으로 안전 이동 | `wiki_delete_to_trash(title="임시메모")` |

---

## ⚡ 4. 인덱서(Indexer) 사용법

### 1) 대화창에서 AI에게 요청하기
채팅창에서 아래와 같이 말씀하시면 AI가 `wiki_rebuild_index` 도구를 실행합니다:
* *"위키 인덱서 돌려서 대시보드 최신화해줘."*
* *"본문 안의 조항들을 위키 링크로 자동 연결(`auto_link`)해서 색인 다시 빌드해줘."*

### 2) 터미널(CLI)에서 직접 실행하기
대량의 문서를 폴더에 복사해 넣은 후, 터미널에서 1초 만에 전체 색인을 완료할 수 있습니다:

```bash
# 기본 색인 및 00_INDEX.md 생성
python MCP_Servers/wiki_indexer.py

# 본문 내 키워드를 감지하여 [[문서명]] 링크로 자동 변환하며 색인
python MCP_Servers/wiki_indexer.py --auto-link
```

---

## 📝 5. 마크다운 문서 작성 규칙 (Tip)

### 1) 양방향 위키 링크 문법
문서 본문에서 다른 조항이나 문서를 인용할 때는 **대괄호 두 개 `[[문서명]]`**을 사용합니다.
* 서브폴더 경로를 적지 않고 파일명만 적어도 AI가 알아서 찾아냅니다.
* 예시: `FADEC 제어 로직은 [[33.75_Safety_Analysis]]의 안전성 분석 요건을 준수해야 합니다.`

### 2) YAML Frontmatter (자동 관리됨)
AI가 도구로 문서를 생성할 때 상단 메타데이터를 자동으로 채워줍니다:
```yaml
---
title: "14 CFR § 33.28 - Engine Control Systems"
category: "14_CFR_Part33"
tags: ["CFR", "Part33", "FADEC", "제어시스템"]
created_at: "2026-08-31 22:46:25"
updated_at: "2026-09-01 00:01:27"
---
```

---

## 🚀 6. 서버 실행 및 NeuJS 앱 연동

1. **위키 서버 기동**:
   ```bash
   python MCP_Servers/wiki-mcp-server.py --port 8003
   ```
2. **NeuJS 앱 연결**:
   * 앱의 **`⚙️ 환경 설정 > MCP 서버`** 탭에서 **`위키 (http://127.0.0.1:8003/mcp)`** 스위치를 켜면 즉시 모든 위키 도구가 활성화됩니다.
