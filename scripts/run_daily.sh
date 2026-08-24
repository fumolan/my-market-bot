#!/bin/bash
# 股市六法简报 · 每日自动生成+发布
# crontab: 30 7 * * 1-5  (工作日 07:30)
set -u
REPO="/home/fumolan/github/my-market-bot"
LOG="$REPO/logs/run_$(date +%Y%m%d).log"
mkdir -p "$REPO/logs"
cd "$REPO" || exit 1

echo "===== $(date '+%F %T') 开始 =====" >> "$LOG"

# ① 生成当日简报（交易日才需要，周末跳过）
DOW=$(date +%u)
if [ "$DOW" -ge 6 ]; then
    echo "周末，跳过" >> "$LOG"
    exit 0
fi

python3 scripts/daily_market_brief.py >> "$LOG" 2>&1
python3 scripts/update_index.py    >> "$LOG" 2>&1
python3 scripts/build_rss.py       >> "$LOG" 2>&1

# ② 有变化则提交推送（最多重试3次，应对网络抖动）
if ! git diff --quiet --ignore-submodules HEAD 2>/dev/null; then
    git add -A
    git commit -m "sync: 股市六法简报 $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    for i in 1 2 3; do
        if git push >> "$LOG" 2>&1; then
            echo "✅ 推送成功 (第${i}次尝试)" >> "$LOG"
            break
        fi
        echo "⚠️ 推送失败,重试 $i" >> "$LOG"
        sleep 20
    done
else
    echo "无变化,跳过推送" >> "$LOG"
fi

echo "===== $(date '+%F %T') 结束 =====" >> "$LOG"
