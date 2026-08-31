# ⚡ Skills FastMCP 서버 사용 가이드 (`SKILLS_GUIDE.md`)

본 문서는 **Antigravity 및 Claude 표준 스킬 구조(`SKILL.md`)를 지원하는 Skills FastMCP 서버 (`skills-mcp-server.py`)**의 아키텍처, 5개 도구 목록, 스킬 제작 규칙 및 활용법을 안내합니다.

---

## 🌟 1. 시스템 핵심 아키텍처

스킬 서버는 각 스킬을 독립된 서브 디렉토리와 표준 마크다운 파일(`SKILL.md`)로 관리합니다.

```text
MCP_Servers/
├── skills-mcp-server.py      # LLM 연동 FastMCP 서버 (HTTP/SSE/stdio 지원, 포트 8002)
└── skills/                   # 스킬 저장소 디렉토리
    ├── prompt-optimizer/     # 🎯 프롬프트 개선 스킬
    │   └── SKILL.md
    ├── python-pro/           # 🐍 파이썬 고급 프로그래밍 스킬
    │   └── SKILL.md
    └── web-scraper/          # 🌐 웹 데이터 수집 스킬
        └── SKILL.md
```

* **표준 호환성**: Antigravity / Claude의 표준 스킬 규격을 100% 준수하여 다른 환경과 상호 호환됩니다.
* **원스톱 지능형 라우팅 (`skills_smart_run`)**: 사용자의 의도를 분석하여 적절한 스킬을 스스로 찾아 실행 지침을 반환합니다.

---

## 📦 2. 파이썬 필수 라이브러리 설치 (Prerequisites)

```bash
# 스킬 FastMCP 서버 구동에 필요한 핵심 패키지
pip install fastmcp uvicorn starlette pydantic
```

> **참고 (기본 내장 라이브러리)**:
> Windows 휴지통 연동(`ctypes`), 파일 시스템 스캔(`pathlib`), 정규표현식(`re`), 비동기 처리(`asyncio`) 등은 **파이썬 3.10+ 기본 표준 라이브러리**에 포함되어 있어 추가 설치가 필요 없습니다.

---

## 🛠️ 3. 제공되는 스킬 도구 목록 (총 5개)

| 도구명 | 설명 | 사용 예시 |
| :--- | :--- | :--- |
| **`skills_smart_run`** | **[추천 원스톱 도구]** 사용자 요청을 입력하면 최적의 스킬을 자동 매칭하여 실행 가이드 반환 | `skills_smart_run(prompt="이 프롬프트 좀 고도화해줘")` |
| **`skills_list`** | 등록된 모든 스킬의 이름, 카테고리, 설명 요약 목록 조회 | `skills_list(category="Engineering")` |
| **`skills_get`** | 특정 스킬의 `SKILL.md` 전체 지침 및 상세 프롬프트 로드 | `skills_get(name="prompt-optimizer")` |
| **`skills_create_or_update`** | 표준 YAML Frontmatter 형식의 새 스킬 생성 또는 기존 스킬 갱신 | `skills_create_or_update(name="sql-helper", description="...", content="...")` |
| **`skills_delete_to_trash`** | 스킬 폴더를 영구 삭제하지 않고 OS 휴지통으로 안전하게 이동 (Safe Delete) | `skills_delete_to_trash(name="old-skill")` |

---

## 📝 4. 표준 스킬(`SKILL.md`) 작성 규칙

스킬 문서는 상단의 **YAML Frontmatter**와 하단의 **상세 프롬프트/지침(Markdown Body)**으로 구성됩니다:

```markdown
---
name: "prompt-optimizer"
description: "사용자가 작성한 프롬프트를 고품질의 구조화된 프롬프트로 고도화해주는 전문 스킬입니다."
category: "Productivity"
triggers: ["프롬프트개선", "프롬프트 최적화", "prompt optimize"]
---

# 🎯 Prompt Optimizer Skill Guide

## 1. 역할 및 목표
당신은 최고의 프롬프트 엔지니어링 전문가입니다.

## 2. 최적화 단계
1. **역할(Role) 정의**: 명확한 페르소나 부여
2. **맥락(Context) 구체화**: 필수 배경 지식 주입
3. **출력 형식(Output Format) 지정**: 마크다운 테이블, 코드 블록 등 지정
```

---

## 🚀 5. 서버 실행 및 NeuJS 앱 연동

1. **스킬 서버 기동 (기본 8002 포트)**:
   ```bash
   python MCP_Servers/skills-mcp-server.py --port 8002
   ```
2. **NeuJS 앱 연결**:
   * 앱의 **`⚙️ 환경 설정 > MCP 서버`** 탭에서 **`스킬 (http://127.0.0.1:8002/mcp)`** 스위치를 켜면 즉시 모든 스킬 도구가 활성화됩니다.
