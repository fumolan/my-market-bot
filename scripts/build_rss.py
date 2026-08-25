#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅生成器
=============
从 reports.json 生成 RSS 2.0 feed:
  rss.xml          — 全站聚合(各分类最新混排)
  rss/<slug>.xml   — 每分类独立 feed

用法: python3 scripts/build_rss.py
"""
import os, re, json, html
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://fumolan.github.io/my-market-bot"
CST = timezone(timedelta(hours=8))  # Asia/Shanghai

CAT_META = {
    "market":        {"name": "股市六法简报",   "icon": "📊"},
    "uzi":           {"name": "UZI深度报告",   "icon": "🎭"},
    "llm":           {"name": "大模型行业情报", "icon": "🤖"},
    "job-hunting":   {"name": "后端求职情报",   "icon": "🔍"},
    "interview-qa":  {"name": "每日面试题",     "icon": "📝"},
}

def esc(s):
    return html.escape(str(s), quote=True)

def parse_date(dstr):
    """'2026-08-24' / '2026-08-17' -> aware datetime (08:00 CST)"""
    try:
        return datetime.strptime(dstr[:10], "%Y-%m-%d").replace(
            hour=8, tzinfo=CST)
    except Exception:
        return None

def md_to_summary(md_path, limit=300):
    """提取 markdown 前N字符做摘要(剥掉语法符号)"""
    try:
        txt = open(md_path, encoding="utf-8").read()
    except Exception:
        return ""
    txt = re.sub(r"^#.*$", "", txt, flags=re.M)          # 标题
    txt = re.sub(r"\|.*\|", " ", txt)                    # 表格
    txt = re.sub(r"[*>`\[\]#-]", " ", txt)               # 语法符
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit] + ("…" if len(txt) > limit else "")

def build_channel(slug, name, items, out_file):
    """items: [(date, path, label)] 最新在前"""
    now = format_datetime(datetime.now(CST))
    entries = []
    for dstr, path, label in items[:40]:
        dt = parse_date(dstr)
        pub = format_datetime(dt) if dt else now
        url = f"{SITE}/{path}"
        md_abs = os.path.join(REPO, path)
        summary = md_to_summary(md_abs)
        entries.append(f"""    <item>
      <title>{esc(label)}</title>
      <link>{esc(url)}</link>
      <guid isPermaLink="true">{esc(url)}</guid>
      <pubDate>{pub}</pubDate>
      <description>{esc(summary)}</description>
    </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{esc('📊 ' + name + ' · 股市六法简报')}</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/{'rss/' + slug + '.xml' if slug != '_all' else 'rss.xml'}" rel="self" type="application/rss+xml"/>
    <description>{esc(name + ' — AI Agent 自动生成')}</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <generator>my-bot build_rss.py</generator>
{chr(10).join(entries)}
  </channel>
</rss>
"""
    os.makedirs(os.path.dirname(out_file), exist_ok=True) if os.path.dirname(out_file) else None
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✅ {out_file} ({len(entries)} items)")

def main():
    # 读索引
    idx_path = os.path.join(REPO, "reports.json")
    with open(idx_path, encoding="utf-8") as f:
        index = json.load(f)

    all_items = []  # (date, path, label, cat_name)
    for cat in index.get("categories", []):
        slug = cat["slug"]
        name = CAT_META.get(slug, {}).get("name", cat.get("name", slug))
        cat_items = []
        for month in cat.get("months", []):
            for it in month.get("items", []):
                cat_items.append((it["date"], it["path"], it.get("label", it["name"])))
        cat_items.sort(key=lambda x: x[0], reverse=True)
        for t in cat_items:
            all_items.append((*t, name))

    # 全站 feed(混排取最新40)
    all_items.sort(key=lambda x: x[0], reverse=True)
    all_items = [(d, p, f"[{n}] {l}") for d, p, l, n in all_items]
    build_channel("_all", "全站情报聚合", all_items,
                  os.path.join(REPO, "rss.xml"))

if __name__ == "__main__":
    main()
