"""wiki_indexer.py - LLM Wiki 지식 그래프 색인기 및 자동 링크 빌더.

주요 기능:
1. 전체 서브폴더 스캔 및 양방향 링크(Backlinks) 지식 그래프 분석
2. 총괄 대시보드 마크다운(00_INDEX.md) 자동 생성/갱신
3. 허브(Hub) 문서 분석 (가장 많이 인용된 핵심 조항 Top N)
4. 끊어진 링크(Broken Links) 및 고아 문서(Orphan Notes) 탐지
5. 스마트 자동 링크 연결기(--auto-link): 본문 내 키워드/조항명을 [[문서명]]으로 자동 변환
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

WIKI_DIR = Path(__file__).resolve().parent / "wiki_data"


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', name).strip()
    return clean if clean else "untitled"


def extract_wiki_links(text: str) -> List[str]:
    if not text:
        return []
    matches = re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text)
    cleaned = [m.strip() for m in matches if m.strip()]
    return list(dict.fromkeys(cleaned))


def parse_frontmatter_and_content(file_path: Path) -> Tuple[Dict[str, Any], str]:
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


def scan_and_rebuild_index(auto_link: bool = False) -> Dict[str, Any]:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    all_files = [f for f in WIKI_DIR.rglob("*.md") if f.name != "00_INDEX.md"]

    if not all_files:
        return {"success": False, "message": "위키 저장소에 등록된 문서가 없습니다."}

    doc_registry: Dict[str, Dict[str, Any]] = {}
    name_to_stem_map: Dict[str, str] = {}

    for f in all_files:
        stem = f.stem
        meta, body = parse_frontmatter_and_content(f)
        outgoing = extract_wiki_links(body)
        rel_path = str(f.relative_to(WIKI_DIR)).replace("\\", "/")

        doc_registry[stem] = {
            "path": f,
            "rel_path": rel_path,
            "meta": meta,
            "body": body,
            "outgoing": outgoing,
            "incoming": set(),
        }
        name_to_stem_map[stem.lower()] = stem
        if meta.get("title"):
            name_to_stem_map[meta["title"].lower()] = stem

    broken_links: Dict[str, List[str]] = {}

    for stem, info in doc_registry.items():
        for target in info["outgoing"]:
            t_raw = target[:-3] if target.lower().endswith(".md") else target
            target_clean = sanitize_filename(t_raw).lower()
            if target_clean in name_to_stem_map:
                actual_target_stem = name_to_stem_map[target_clean]
                doc_registry[actual_target_stem]["incoming"].add(stem)
            else:
                if target not in broken_links:
                    broken_links[target] = []
                broken_links[target].append(stem)

    auto_linked_count = 0
    if auto_link:
        known_keywords = sorted(
            [(k, stem) for k, stem in name_to_stem_map.items() if len(k) >= 3],
            key=lambda x: len(x[0]),
            reverse=True
        )

        for stem, info in doc_registry.items():
            content = info["body"]
            modified = False

            for kw, target_stem in known_keywords:
                if target_stem == stem:
                    continue

                pattern = re.compile(rf'(?<!\[\[)(?<!\w)({re.escape(kw)})(?!\w)(?!\]\])', re.IGNORECASE)
                if pattern.search(content):
                    content = pattern.sub(f'[[{target_stem}]]', content)
                    modified = True
                    auto_linked_count += 1

            if modified:
                new_doc = build_markdown_document(
                    info["meta"].get("title", stem),
                    content,
                    info["meta"].get("tags", []),
                    info["meta"].get("category", "일반"),
                    info["meta"].get("created_at")
                )
                info["path"].write_text(new_doc, encoding="utf-8")
                info["body"] = content
                info["outgoing"] = extract_wiki_links(content)

    categories: Dict[str, List[Dict[str, Any]]] = {}
    all_tags: Set[str] = set()
    orphan_docs: List[str] = []

    for stem, info in doc_registry.items():
        cat = info["meta"].get("category", "기타")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "stem": stem,
            "title": info["meta"].get("title", stem),
            "rel_path": info["rel_path"],
            "tags": info["meta"].get("tags", []),
            "outgoing_count": len(info["outgoing"]),
            "incoming_count": len(info["incoming"]),
        })
        all_tags.update(info["meta"].get("tags", []))

        if len(info["outgoing"]) == 0 and len(info["incoming"]) == 0:
            orphan_docs.append(stem)

    ranked_hubs = sorted(
        doc_registry.items(),
        key=lambda x: len(x[1]["incoming"]),
        reverse=True
    )[:5]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dash_lines = [
        "---",
        "title: \"00_INDEX (위키 총괄 색인 및 지식 대시보드)\"",
        "category: \"시스템\"",
        "tags: [\"Index\", \"Dashboard\", \"Overview\"]",
        f"updated_at: \"{now_str}\"",
        "---",
        "",
        "# 📚 LLM Wiki 총괄 지식 대시보드",
        f"> **최종 색인 갱신 일시**: `{now_str}`  ",
        f"> **총 등록 문서 수**: **{len(all_files)}개** | **분류 분야**: **{len(categories)}개** | **등록 태그**: **{len(all_tags)}개**",
        "",
        "---",
        "",
        "## 🌟 핵심 허브(Hub) 조항 / 인기 문서 Top 5",
        "*(다른 문서들로부터 가장 많은 참조 및 인용을 받고 있는 핵심 문서 목록)*",
        "",
    ]

    for rank, (h_stem, h_info) in enumerate(ranked_hubs, 1):
        in_cnt = len(h_info["incoming"])
        if in_cnt > 0:
            dash_lines.append(f"{rank}. 🏆 **[[{h_stem}]]** - `{h_info['meta'].get('title', h_stem)}` (참조 인용: **{in_cnt}회**)")
        else:
            dash_lines.append(f"{rank}. 📄 **[[{h_stem}]]** - `{h_info['meta'].get('title', h_stem)}`")

    dash_lines.extend([
        "",
        "---",
        "",
        "## 📂 분야(서브폴더)별 전체 문서 목차",
        "",
    ])

    for cat_name, items in sorted(categories.items()):
        dash_lines.append(f"### 📁 [{cat_name}] ({len(items)}개 문서)")
        for it in sorted(items, key=lambda x: x["stem"]):
            tag_badges = f" `[{', '.join(it['tags'])}]`" if it['tags'] else ""
            link_stats = f" *(연계: ➡️ {it['outgoing_count']}개 / ⬅️ {it['incoming_count']}개)*"
            dash_lines.append(f"- 📄 **[[{it['stem']}]]** - {it['title']}{tag_badges}{link_stats}")
        dash_lines.append("")

    if all_tags:
        dash_lines.extend([
            "---",
            "## 🏷️ 전체 태그 색인",
            ", ".join(f"`#{t}`" for t in sorted(all_tags)),
            "",
        ])

    dash_lines.extend([
        "---",
        "## 🔍 지식 네트워크 건강도 분석",
        "",
    ])

    if broken_links:
        dash_lines.append(f"### ⚠️ 끊어진 링크(Broken Links) ({len(broken_links)}건)")
        dash_lines.append("*(본문에서 인용되었으나 아직 생성되지 않은 대상 문서 목록)*")
        for missing, sources in broken_links.items():
            dash_lines.append(f"- ❓ `[[{missing}]]` ➔ 참조 조항: {', '.join(f'[[{s}]]' for s in sources)}")
        dash_lines.append("")
    else:
        dash_lines.append("✅ **끊어진 링크 없음**: 모든 `[[링크]]`가 실제 존재하는 문서와 100% 정상 연결되어 있습니다.\n")

    if orphan_docs:
        dash_lines.append(f"### 🏝️ 고아 문서(Orphan Documents) ({len(orphan_docs)}건)")
        dash_lines.append("*(다른 문서와 아무런 링크도 주고받지 않은 독립 문서 목록)*")
        for orph in orphan_docs:
            dash_lines.append(f"- 📄 [[{orph}]]")
        dash_lines.append("")
    else:
        dash_lines.append("✅ **고아 문서 없음**: 모든 문서가 지식 그래프에 유기적으로 연결되어 있습니다.\n")

    index_file = WIKI_DIR / "00_INDEX.md"
    index_file.write_text("\n".join(dash_lines), encoding="utf-8")

    return {
        "success": True,
        "total_docs": len(all_files),
        "total_categories": len(categories),
        "total_tags": len(all_tags),
        "top_hubs": [(h[0], len(h[1]["incoming"])) for h in ranked_hubs],
        "broken_links_count": len(broken_links),
        "orphan_count": len(orphan_docs),
        "auto_linked_count": auto_linked_count,
        "index_path": str(index_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Wiki Knowledge Indexer & Graph Builder")
    parser.add_argument(
        "--auto-link", "-a",
        action="store_true",
        help="본문 내 키워드/조항명을 감지하여 [[문서명]] 위키 링크로 자동 연결합니다.",
    )
    args = parser.parse_args()

    print("🚀 LLM Wiki 지식 그래프 색인 작업을 시작합니다...", file=sys.stderr)
    res = scan_and_rebuild_index(auto_link=args.auto_link)

    if res["success"]:
        print("=" * 60)
        print(f"✅ 위키 총괄 색인 및 00_INDEX.md 생성 완료!")
        print(f"- 📊 총 문서 수: {res['total_docs']}개")
        print(f"- 📁 총 분야(서브폴더) 수: {res['total_categories']}개")
        print(f"- 🏷️ 등록 태그 수: {res['total_tags']}개")
        print(f"- 🏆 최다 인용 허브 Top 3: {res['top_hubs'][:3]}")
        print(f"- ⚠️ 끊어진 링크: {res['broken_links_count']}건 | 고아 문서: {res['orphan_count']}건")
        if args.auto_link:
            print(f"- ⚡ 자동 생성된 위키 링크: {res['auto_linked_count']}개")
        print(f"- 📄 색인 파일 위치: {res['index_path']}")
        print("=" * 60)
    else:
        print(f"❌ 색인 실패: {res['message']}", file=sys.stderr)
