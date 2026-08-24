#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reports.json 索引重建器
======================
扫描 reports/ 目录, 重建 reports.json (兼容原有 categories/months/items 结构)

用法: python3 scripts/update_index.py
"""
import os, re, json
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAT_META = [
    {"slug": "market", "name": "股市六法简报", "icon": "📊"},
]

DATE_RE = re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})")

def extract_date(name):
    m = DATE_RE.search(name)
    if not m:
        return None, None
    d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    label = re.sub(r"\.md$", "", name)
    return d, label

def main():
    categories = []
    for cat in CAT_META:
        cat_dir = os.path.join(REPO, "reports", cat["slug"])
        if not os.path.isdir(cat_dir):
            continue
        by_month = {}
        total = 0
        latest = ""
        for fn in sorted(os.listdir(cat_dir)):
            if not fn.endswith(".md"):
                continue
            d, label = extract_date(fn)
            if not d:
                d, label = "1970-01-01", fn[:-3]
            mk = d[:7]
            by_month.setdefault(mk, []).append({
                "name": fn,
                "path": f"reports/{cat['slug']}/{fn}",
                "date": d,
                "label": label,
            })
            total += 1
            latest = max(latest, d)
        months = []
        for mk in sorted(by_month, reverse=True):
            items = sorted(by_month[mk], key=lambda x: x["date"], reverse=True)
            months.append({
                "key": mk,
                "label": f"{mk[:4]}年{mk[5:7]}月",
                "items": items,
            })
        categories.append({
            "slug": cat["slug"],
            "name": cat["name"],
            "icon": cat["icon"],
            "total": total,
            "latest_date": latest,
            "months": months,
        })
        print(f"  {cat['slug']}: {total} 篇, 最新 {latest}")

    out = {
        "updated": datetime.now().isoformat(),
        "categories": categories,
    }
    idx_path = os.path.join(REPO, "reports.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ reports.json 已重建 (categories={[c['slug'] for c in categories]})")

if __name__ == "__main__":
    main()
