# 📊 股市六法简报 · 每日盘面 × 六法推演

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-上线-brightgreen)](https://fumolan.github.io/my-market-bot/)
[![RSS](https://img.shields.io/badge/RSS-订阅-orange)](https://fumolan.github.io/my-market-bot/rss.xml)

由 AI Agent 每天早上自动生成的 A 股盘面简报，按「投资心法·股市六法」框架推演当日机会。

## 📡 RSS 订阅

复制以下地址到任意 RSS 阅读器（NetNewsWire / Reeder / Follow / Inoreader / Feedly）：

```
https://fumolan.github.io/my-market-bot/rss.xml
```

## 🧭 股市六法

| 法 | 心法 | 用法 |
|----|------|------|
| 一 | 大跌买指数 | 恐慌大跌时分批买入宽基指数 |
| 二 | 专注一两只做波段 | 只做看得懂的主线龙头 |
| 三 | 攒股收股息 | 高股息资产长期定投 |
| 四 | 看懂周期反向布局 | 领跌板块缩量企稳后反向介入 |
| 五 | 价值投资等龙头打折 | 好公司遇板块错杀时买入 |
| 六 | 赚企业成长的钱 | 主线成长股深度回调分批 |

## 📦 数据源（自动降级）

| 数据 | 主源 | 降级 |
|------|------|------|
| 大盘指数/行业/涨停/龙虎榜 | 同花顺扶摇官方API | 腾讯行情 |
| 宽基ETF/国债ETF | 腾讯批量 | — |
| 商品期货主力 | 新浪 | — |
| 财联社快讯 | cls.cn v1（零key本地签名） | — |

## 📁 结构

```
my-market-bot/
├── index.html                    # 静态站点（GitHub Pages）
├── rss.xml                       # RSS 2.0 feed
├── reports.json                  # 简报索引（自动生成）
├── scripts/
│   ├── daily_market_brief.py     # 简报生成器（数据采集+六法速评）
│   ├── build_rss.py              # RSS 生成器
│   └── update_index.py           # reports.json 重建器
└── reports/market/YYYY-MM-DD.md  # 每日简报
```

## ⚙️ 每日流程

1. **07:30**（crontab 触发）`daily_market_brief.py` 拉取多源数据生成当日简报
2. `update_index.py` 重建 reports.json
3. `build_rss.py` 刷新 rss.xml
4. `git commit + push` → GitHub Pages 自动发布
5. RSS 订阅者的阅读器自动收到更新

## ⚠️ 免责声明

所有数据与分析由程序自动生成，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。

---

*Built with ❤️ by ZCode AI Agent*
