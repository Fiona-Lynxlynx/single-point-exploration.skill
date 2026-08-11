#!/usr/bin/env python3
"""
單點外展狀科學探索精神 - 引文外延輔助工具
以一篇論文為起點，沿參考文獻網絡向外展開（點式外延）。

用法：
    python3 explore.py <DOI或標題> [--depth 2] [--branch 5]

依賴：requests
數據源：Crossref API（開放學術元數據）
"""
import sys
import json
import argparse
import requests

CROSSREF = "https://api.crossref.org/works/"


def fetch_by_doi(doi):
    r = requests.get(CROSSREF + doi, timeout=30)
    r.raise_for_status()
    return r.json()["message"]


def fetch_by_title(title):
    r = requests.get(CROSSREF, params={"query.bibliographic": title, "rows": 1}, timeout=30)
    r.raise_for_status()
    items = r.json()["message"]["items"]
    return items[0] if items else None


def extract_refs(msg):
    """提取參考文獻列表（Crossref 的 reference 字段）。"""
    refs = []
    for ref in msg.get("reference", []):
        refs.append({
            "title": ref.get("article-title", ref.get("unstructured", "")[:120]),
            "author": ref.get("author", ""),
            "year": ref.get("year", ""),
            "doi": ref.get("DOI", ""),
            "container": ref.get("journal-title", ""),
            "key": ref.get("key", ""),
        })
    return refs


def summarize(msg):
    return {
        "title": msg.get("title", [""])[0],
        "author": ", ".join(
            f"{a.get('family','')} {a.get('given','')}" for a in msg.get("author", [])[:3]
        ),
        "year": msg.get("issued", {}).get("date-parts", [[None]])[0][0],
        "container": msg.get("container-title", [""])[0],
        "doi": msg.get("DOI", ""),
        "abstract": (msg.get("abstract", "") or "")[:300],
    }


def explore(node, depth, branch, max_depth, visited, out):
    """遞歸外延：每個節點展開其參考文獻。"""
    if depth > max_depth:
        return
    doi = node.get("doi", "")
    if not doi or doi in visited:
        return
    visited.add(doi)
    try:
        msg = fetch_by_doi(doi)
    except Exception:
        return
    refs = extract_refs(msg)
    level = out.setdefault(f"L{depth}", [])
    level.append({
        "node": summarize(msg),
        "refs_count": len(refs),
        "refs": refs[:branch],
    })
    # 向下展開前 branch 個有 DOI 的參考文獻
    expanded = 0
    for ref in refs:
        if expanded >= branch:
            break
        if ref["doi"]:
            explore(ref, depth + 1, branch, max_depth, visited, out)
            expanded += 1


def main():
    ap = argparse.ArgumentParser(description="點式外延科學探索")
    ap.add_argument("query", help="DOI 或標題")
    ap.add_argument("--depth", type=int, default=2, help="外延深度（默認2）")
    ap.add_argument("--branch", type=int, default=5, help="每層展開點數（默認5）")
    args = ap.parse_args()

    try:
        msg = fetch_by_doi(args.query)
    except Exception:
        msg = fetch_by_title(args.query)
    if not msg:
        print("未找到論文"); sys.exit(1)

    print(f"# 出發論文：{summarize(msg)['title']}")
    print(f"  作者：{summarize(msg)['author']} | {summarize(msg)['year']} | DOI: {summarize(msg)['doi']}")

    out = {}
    visited = set()
    # 根節點
    root_refs = extract_refs(msg)
    out["L0"] = [{"node": summarize(msg), "refs_count": len(root_refs), "refs": root_refs[:args.branch]}]
    visited.add(msg.get("DOI", ""))

    expanded = 0
    for ref in root_refs:
        if expanded >= args.branch:
            break
        if ref["doi"]:
            explore(ref, 1, args.branch, args.depth, visited, out)
            expanded += 1

    print("\n## 外延樹")
    for level in sorted(out.keys()):
        print(f"\n### {level}")
        for item in out[level]:
            n = item["node"]
            print(f"- {n['title'][:80]} ({n['year']}) — 引用數：{item['refs_count']}")
            for ref in item["refs"][:3]:
                print(f"    ↳ {ref['title'][:60]} {ref['year']} DOI:{ref['doi'][:40] or '無'}")


if __name__ == "__main__":
    main()
