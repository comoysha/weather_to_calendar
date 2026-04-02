#!/bin/bash
set -euo pipefail

export TZ="Asia/Shanghai"

PLIST_TARGET="$HOME/Library/LaunchAgents/com.xiayue.weather-to-calendar.plist"
LABEL="com.xiayue.weather-to-calendar"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl disable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

if [ -f "$PLIST_TARGET" ]; then
  rm -f "$PLIST_TARGET"
fi

echo "已卸载: $PLIST_TARGET"
launchctl print-disabled "gui/$(id -u)" 2>/dev/null | grep "$LABEL" || true
