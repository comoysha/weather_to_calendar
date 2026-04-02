#!/bin/bash
set -euo pipefail

export TZ="Asia/Shanghai"

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_TEMPLATE="$BASE_DIR/com.xiayue.weather-to-calendar.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_TARGET="$LAUNCH_AGENTS_DIR/com.xiayue.weather-to-calendar.plist"
LOG_DIR="$BASE_DIR/logs"

if [ ! -f "$PLIST_TEMPLATE" ]; then
  echo "缺少模板文件: $PLIST_TEMPLATE" >&2
  exit 1
fi

mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$LOG_DIR"

cp "$PLIST_TEMPLATE" "$PLIST_TARGET"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/com.xiayue.weather-to-calendar"
launchctl kickstart -k "gui/$(id -u)/com.xiayue.weather-to-calendar"

echo "已安装并启动: $PLIST_TARGET"
echo "标准输出日志: $LOG_DIR/weather_to_calendar.stdout.log"
echo "错误日志: $LOG_DIR/weather_to_calendar.stderr.log"
launchctl print "gui/$(id -u)/com.xiayue.weather-to-calendar" | sed -n '1,80p'
