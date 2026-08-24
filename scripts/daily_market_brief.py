#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日股市六法简报生成器
====================
数据源（自动降级）:
  大盘指数/行业/涨停/龙虎榜 : 扶摇官方API (主) -> 腾讯(指数降级)
  宽基ETF/国债ETF           : 腾讯批量 (不封IP)
  商品期货主力              : 新浪
  财联社快讯                : cls.cn v1 (本地签名零key)

输出: reports/market/YYYY-MM-DD.md
用法: python3 scripts/daily_market_brief.py [--push]
"""
import sys, io, os, json, time, random, hashlib, argparse
import urllib.request
import requests
from datetime import datetime, date

# 脚本可独立运行(无包依赖)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.expanduser("~/claude/apikey/tonghuashun.txt")
FUYAO_BASE = "https://fuyao.aicubes.cn"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE = "https://fumolan.github.io/my-bot"

SOURCES_OK, SOURCES_FAIL = [], []

def log_ok(src): SOURCES_OK.append(src)
def log_fail(src, why=""): SOURCES_FAIL.append(f"{src}({why})")

# ────────────────────────── 扶摇官方 API ──────────────────────────
def fuyao_key():
    try:
        return open(KEY_FILE).read().strip()
    except Exception:
        return os.environ.get("FUYAO_API_KEY", "")

def fuyao_get(path, params=None):
    key = fuyao_key()
    if not key:
        raise RuntimeError("no fuyao key")
    url = f"{FUYAO_BASE}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url)
    req.add_header("X-api-key", key)
    req.add_header("User-Agent", UA)
    d = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if d.get("code") != 0:
        raise RuntimeError(d.get("message", "api error"))
    return d.get("data", {})

# ────────────────────────── 腾讯批量行情 ──────────────────────────
def tencent_batch(codes):
    prefixed = []
    for c in codes:
        if c.startswith(("5", "6", "9")):
            prefixed.append(f"sh{c}")
        else:
            prefixed.append(f"sz{c}")
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    d = urllib.request.urlopen(req, timeout=15).read().decode("gbk")
    out = {}
    for line in d.strip().split(";"):
        if "=" not in line or '"' not in line:
            continue
        code = line.split("=")[0].split("_")[-1][2:]
        v = line.split('"')[1].split("~")
        if len(v) < 47:
            continue
        try:
            out[code] = {"name": v[1], "price": float(v[3] or 0),
                         "chg": float(v[32] or 0),
                         "amount_yi": float(v[37] or 0) / 10000}
        except Exception:
            continue
    return out

# ────────────────────────── 新浪期货 ──────────────────────────
FUT = {"RB0": "螺纹钢", "HC0": "热卷", "I0": "铁矿石", "CU0": "沪铜", "AL0": "沪铝",
       "AU0": "沪金", "AG0": "沪银", "M0": "豆粕", "Y0": "豆油", "TA0": "PTA",
       "MA0": "甲醇", "SC0": "原油", "FU0": "燃油", "SA0": "纯碱", "FG0": "玻璃"}

def fetch_futures():
    codes = ",".join(f"nf_{k}" for k in FUT)
    req = urllib.request.Request(f"https://hq.sinajs.cn/list={codes}")
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://finance.sina.com.cn")
    d = urllib.request.urlopen(req, timeout=15).read().decode("gbk")
    rows = []
    for line in d.strip().split(";"):
        if '"' not in line or "=" not in line:
            continue
        var = line.split("=")[0].replace("var hq_str_", "").strip()
        f = line.split('"')[1].split(",")
        if len(f) < 11 or not f[8]:
            continue
        try:
            last, settle = float(f[8]), float(f[10])
            if last > 0 and settle > 0:
                rows.append((FUT.get(var.replace("nf_", ""), var), last,
                             (last / settle - 1) * 100))
        except Exception:
            continue
    rows.sort(key=lambda x: -x[2])
    return rows

# ────────────────────────── 财联社快讯 ──────────────────────────
def fetch_cls(n=10):
    params = {"appName": "CailianpressWeb", "os": "web", "sv": "7.7.5",
              "last_time": "", "refresh_type": "1", "rn": str(n)}
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    sign = hashlib.md5(hashlib.sha1(qs.encode()).hexdigest().encode()).hexdigest()
    url = f"https://www.cls.cn/v1/roll/get_roll_list?{qs}&sign={sign}"
    r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://www.cls.cn/"},
                     timeout=10)
    items = r.json().get("data", {}).get("roll_data", []) or []
    out = []
    for it in items[:n]:
        ts = it.get("ctime")
        t = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else ""
        title = it.get("title", "") or (it.get("brief", "") or "")[:50]
        lvl = it.get("level", "")
        mark = "🔴" if lvl == "A" else ("🟠" if lvl == "B" else "·")
        out.append(f"- {mark} {t} {title[:60]}")
    return out

# ────────────────────────── 行业指数(881xxx一级行业) ──────────────────────────
INDUSTRY = {
    "881101.TI": "种植业与林业", "881102.TI": "养殖业", "881103.TI": "农产品加工",
    "881105.TI": "煤炭开采加工", "881107.TI": "油气开采及服务", "881108.TI": "化学原料",
    "881109.TI": "化学制品", "881112.TI": "钢铁", "881114.TI": "金属新材料",
    "881115.TI": "建筑材料", "881116.TI": "建筑装饰", "881117.TI": "通用设备",
    "881118.TI": "专用设备", "881121.TI": "半导体", "881122.TI": "光学光电子",
    "881123.TI": "其他电子", "881124.TI": "消费电子", "881125.TI": "汽车整车",
    "881126.TI": "汽车零部件", "881129.TI": "通信设备", "881130.TI": "计算机设备",
    "881131.TI": "白色家电", "881133.TI": "饮料制造", "881134.TI": "食品加工制造",
    "881135.TI": "纺织制造", "881136.TI": "服装家纺", "881140.TI": "化学制药",
    "881141.TI": "中药", "881142.TI": "生物制品", "881143.TI": "医药商业",
    "881144.TI": "医疗器械", "881145.TI": "电力", "881146.TI": "燃气",
    "881148.TI": "港口航运", "881149.TI": "公路铁路运输", "881152.TI": "物流",
    "881153.TI": "房地产", "881155.TI": "银行", "881156.TI": "保险", "881157.TI": "证券",
    "881158.TI": "零售", "881160.TI": "旅游及酒店", "881164.TI": "文化传媒",
    "881166.TI": "军工装备", "881167.TI": "非金属材料", "881168.TI": "工业金属",
    "881169.TI": "贵金属", "881170.TI": "小金属", "881171.TI": "自动化设备",
    "881173.TI": "小家电", "881175.TI": "医疗服务", "881177.TI": "互联网电商",
    "881180.TI": "石油加工贸易", "881263.TI": "农化制品", "881267.TI": "能源金属",
    "881268.TI": "工程机械", "881270.TI": "元件", "881271.TI": "IT服务",
    "881272.TI": "软件开发", "881273.TI": "白酒", "881275.TI": "游戏",
    "881276.TI": "军工电子", "881278.TI": "电网设备", "881279.TI": "光伏设备",
    "881280.TI": "风电设备", "881281.TI": "电池", "881283.TI": "多元金融",
}

IDX_NAME = {"000001.SH": "上证指数", "399001.SZ": "深证成指", "399006.SZ": "创业板指",
            "000300.SH": "沪深300", "000905.SH": "中证500", "000688.SH": "科创50",
            "000016.SH": "上证50"}

BROAD_ETF = ["510300", "510050", "510500", "512100", "588000", "159915"]
BOND_ETF = ["511010", "511260", "511090", "511520"]
DIVIDEND_ETF = {"510880": "红利ETF", "512880": "证券ETF"}

# ────────────────────────── 主流程 ──────────────────────────
def generate(out_date=None):
    out_date = out_date or date.today().strftime("%Y-%m-%d")
    lines = []
    A = lines.append

    A(f"# 📊 股市六法简报 · {out_date}")
    A("")
    A(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    A("> 数据源：同花顺扶摇API · 腾讯 · 新浪 · 财联社（自动降级）")
    A("")

    # ① 大盘指数
    try:
        data = fuyao_get("/api/a-share-index/prices/snapshot",
                         {"thscodes": ",".join(IDX_NAME)})
        A("## 一、大盘指数")
        A("")
        A("| 指数 | 收盘 | 涨跌幅 |")
        A("|------|------|--------|")
        for it in data.get("item", []):
            nm = IDX_NAME.get(it["thscode"], it["thscode"])
            A(f"| {nm} | {it['last_price']:.2f} | {it['price_change_ratio_pct']:+.2f}% |")
        log_ok("扶摇指数")
    except Exception as e:
        log_fail("扶摇指数", str(e)[:30])
    A("")

    # ② 行业涨跌
    try:
        codes = list(INDUSTRY)
        results = []
        for i in range(0, len(codes), 45):
            batch = codes[i:i + 45]
            data = fuyao_get("/api/a-share-index/prices/snapshot",
                             {"thscodes": ",".join(batch)})
            for it in data.get("item", []):
                results.append((INDUSTRY.get(it["thscode"], it["thscode"]),
                                it.get("price_change_ratio_pct", 0)))
        results.sort(key=lambda x: -x[1])
        up = sum(1 for _, c in results if c > 0)
        A("## 二、行业板块（同花顺一级行业）")
        A("")
        A(f"**涨跌比：{up} 涨 / {len(results) - up} 跌**")
        A("")
        A("🔺 涨幅前8：")
        for nm, c in results[:8]:
            A(f"- {nm} **{c:+.2f}%**")
        A("")
        A("🔻 跌幅前8：")
        for nm, c in results[-8:]:
            A(f"- {nm} **{c:+.2f}%**")
        log_ok("扶摇行业")
    except Exception as e:
        log_fail("扶摇行业", str(e)[:30])
    A("")

    # ③ ETF
    try:
        q = tencent_batch(BROAD_ETF + BOND_ETF + list(DIVIDEND_ETF))
        A("## 三、ETF 温度计")
        A("")
        A("| ETF | 价格 | 涨跌 |")
        A("|-----|------|------|")
        for c in BROAD_ETF:
            if c in q:
                A(f"| {q[c]['name']} | {q[c]['price']:.3f} | {q[c]['chg']:+.2f}% |")
        for c, nm in DIVIDEND_ETF.items():
            if c in q:
                A(f"| {nm} | {q[c]['price']:.3f} | **{q[c]['chg']:+.2f}%** |")
        for c in BOND_ETF:
            if c in q:
                A(f"| {q[c]['name']} | {q[c]['price']:.3f} | {q[c]['chg']:+.3f}% |")
        log_ok("腾讯ETF")
    except Exception as e:
        log_fail("腾讯ETF", str(e)[:30])
    A("")

    # ④ 商品期货
    try:
        rows = fetch_futures()
        A("## 四、商品期货主力")
        A("")
        if rows:
            top = [f"{n} {c:+.2f}%" for n, _, c in rows[:4]]
            bot = [f"{n} {c:+.2f}%" for n, _, c in rows[-3:]]
            A(f"🔺 最强：{' ｜ '.join(top)}")
            A("")
            A(f"🔻 最弱：{' ｜ '.join(bot)}")
        log_ok("新浪期货")
    except Exception as e:
        log_fail("新浪期货", str(e)[:30])
    A("")

    # ⑤ 涨停池
    try:
        data = fuyao_get("/api/a-share/special-data/limit-up-pool",
                         {"sort_field": "continue_day_cnt", "sort_dir": "desc",
                          "size": "10"})
        items = data.get("item", [])
        total = data.get("pagination", {}).get("total", len(items))
        A(f"## 五、涨停题材（共{total}家）")
        A("")
        for it in items:
            A(f"- **{it['name']}**（{it['continue_day_text']}）：{it.get('limit_up_reason', '')}")
        log_ok("扶摇涨停")
    except Exception as e:
        log_fail("扶摇涨停", str(e)[:30])
    A("")

    # ⑥ 龙虎榜
    try:
        data = fuyao_get("/api/a-share/special-data/dragon-tiger-list",
                         {"board_type": "all"})
        items = data.get("stock_items", [])
        seen = set()
        rows = []
        for it in items:
            if it["thscode"] in seen or it.get("range_days") != 1:
                continue
            seen.add(it["thscode"])
            rows.append(it)
        rows.sort(key=lambda x: -(x.get("net_value") or 0))
        A(f"## 六、龙虎榜净买入 TOP（{data.get('trade_date', '')}）")
        A("")
        for it in rows[:6]:
            nv = (it.get("net_value") or 0) / 1e8
            A(f"- **{it['name']}** 净买 {nv:+.2f}亿（{(it.get('change') or 0)*100:+.1f}%）")
        log_ok("扶摇龙虎榜")
    except Exception as e:
        log_fail("扶摇龙虎榜", str(e)[:30])
    A("")

    # ⑦ 财联社快讯
    try:
        news = fetch_cls(10)
        A("## 七、财联社快讯")
        A("")
        lines.extend(news)
        log_ok("财联社")
    except Exception as e:
        log_fail("财联社", str(e)[:30])
    A("")

    # ⑧ 六法速评（规则化生成）
    A("## 八、股市六法速评")
    A("")
    try:
        idx_data = fuyao_get("/api/a-share-index/prices/snapshot",
                             {"thscodes": "399006.SZ,000688.SH,000016.SH"})
        chg = {it["thscode"]: it["price_change_ratio_pct"] for it in idx_data.get("item", [])}
        cyb = chg.get("399006.SZ", 0)
        kc50 = chg.get("000688.SH", 0)
        sz50 = chg.get("000016.SH", 0)
        A(f"**一法·大跌买指数**：创业板 {cyb:+.2f}%、科创50 {kc50:+.2f}%。"
          + ("跌幅超-2.5%，进入分批建仓区（首笔1/4）。" if min(cyb, kc50) < -2.5
             else "未到恐慌阈值，继续等。" if min(cyb, kc50) < -1
             else "无大跌信号。"))
        A("")
        div = q.get("510880", {}).get("chg", 0) if q else 0
        A(f"**三法·攒股收股息**：红利ETF {div:+.2f}%。"
          + ("红利逆势走强，防御共识，继续持有定投。" if div > 0.5
             else ("红利平淡。" if abs(div) <= 0.5 else "红利回调，攒息者可逢低补。")))
        A("")
        A("**四法·周期反向**：见上方行业涨跌榜——领跌板块若基本面未恶化，缩量企稳3日后是反向观察点。")
        A("")
        A("**五法·龙头打折**：关注今晚财报预增但板块下跌的错杀股（见财联社快讯）。")
        A("")
        A("**六法·赚成长的钱**：涨停池题材+商品周期指向的主线，等深度回调分批，不追连板。")
    except Exception as e:
        A("(六法速评生成失败)")
    A("")
    A("---")
    A("*数据仅供参考，不构成投资建议。由 AI Agent 自动生成。*")

    # 数据源健康度
    if SOURCES_FAIL:
        A("")
        A(f"⚠️ 数据源降级：{', '.join(SOURCES_FAIL)}")

    out_dir = os.path.join(REPO, "reports", "market")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{out_date}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 简报已生成: {out_path}")
    print(f"   数据源: OK={SOURCES_OK} FAIL={SOURCES_FAIL}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYY-MM-DD")
    args = ap.parse_args()
    generate(args.date)
