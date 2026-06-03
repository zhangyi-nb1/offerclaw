#!/bin/bash
# setup_openclaw_cron.sh — 一键创建 OfferClaw 的 3 个定时任务（默认禁用）
#
# 前置：需先在 OpenClaw 面板批准 CLI 的 cron 管理权限（scope upgrade）。
#       若运行报 "pairing required / scope upgrade pending approval"，
#       去 OpenClaw 控制台批准设备权限后再跑本脚本。
#
# 任务默认 --disabled，创建后用 `openclaw cron enable <name>` 开启。
# 调试单次立即运行：`openclaw cron run <name>`
#
# 用法：bash scripts/setup_openclaw_cron.sh

set -e

echo "创建 offerclaw-morning（工作日 09:00 推送今日建议）..."
openclaw cron add --name "offerclaw-morning" \
  --cron "0 9 * * 1-5" \
  --message "用 OfferClaw 技能生成今天的求职/学习建议（运行 offerclaw_cli.py today），用简洁中文发给我，重点说今天最该做的事。" \
  --announce --channel last --disabled \
  --description "工作日早间推送今日建议"

echo "创建 offerclaw-evening（每日 22:00 留痕/复盘提醒）..."
openclaw cron add --name "offerclaw-evening" \
  --cron "0 22 * * *" \
  --message "提醒我用 OfferClaw 记录今天的学习留痕（log）；如果今天还没复盘，建议我说一句就帮我复盘（review）。简短友好。" \
  --announce --channel last --disabled \
  --description "每日晚间留痕/复盘提醒"

echo "创建 offerclaw-weekly（周日 21:00 周度复盘）..."
openclaw cron add --name "offerclaw-weekly" \
  --cron "0 21 * * 0" \
  --message "用 OfferClaw 做本周复盘（运行 offerclaw_cli.py review，并回顾最近一周 daily），总结本周进展和下周建议，发给我。" \
  --announce --channel last --disabled \
  --description "周日晚间周度复盘"

echo ""
echo "已创建（默认禁用）。下一步："
echo "  openclaw cron list                 # 查看"
echo "  openclaw cron run offerclaw-morning  # 立即测试一次（会真的发到微信）"
echo "  openclaw cron enable offerclaw-morning  # 满意后开启"
