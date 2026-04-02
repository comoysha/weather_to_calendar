#!/bin/bash

set -euo pipefail

export TZ="Asia/Shanghai"

CALENDAR_NAME="杭州天气存档"
START_DATE="2026-02-06"
END_DATE="$(date "+%Y-%m-%d")"
OUTPUT_DIR="weather_history"
CITY_CODE="330110"
CITY_NAME="杭州"
PROVINCE_NAME="浙江"

usage() {
    cat <<EOF
用法: $0 [选项]

选项:
  --calendar NAME      日历名称，默认: 杭州天气存档
  --start-date DATE    开始日期，格式: YYYY-MM-DD，默认: 2026-02-06
  --end-date DATE      结束日期，格式: YYYY-MM-DD，默认: 今天（Asia/Shanghai）
  --output-dir DIR     输出目录，默认: weather_history
  --overwrite          覆盖已存在的 JSON
  -h, --help           显示帮助

说明:
  从 Calendar 读取事件标题，例如 “13°C，雾，89%”，回填缺失的天气 JSON。
  默认只创建缺失文件，不覆盖已有文件。
EOF
}

OVERWRITE="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --calendar)
            CALENDAR_NAME="$2"
            shift 2
            ;;
        --start-date)
            START_DATE="$2"
            shift 2
            ;;
        --end-date)
            END_DATE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --overwrite)
            OVERWRITE="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            usage
            exit 1
            ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

tmp_output="$(mktemp)"
osascript <<APPLESCRIPT > "$tmp_output"
on pad2(n)
    return text -2 thru -1 of ("0" & (n as string))
end pad2

on fmtDate(d)
    set y to year of d as integer
    set m to month of d as integer
    set dd to day of d as integer
    set hh to hours of d as integer
    set mm to minutes of d as integer
    return (y as string) & "-" & my pad2(m) & "-" & my pad2(dd) & " " & my pad2(hh) & ":" & my pad2(mm)
end fmtDate

tell application "Calendar"
    set targetCalendar to first calendar whose name is "$CALENDAR_NAME"
    set startDate to date "$START_DATE 00:00:00"
    set endDate to date "$END_DATE 23:59:59"
    set eventList to every event of targetCalendar whose start date is greater than or equal to startDate and start date is less than or equal to endDate

    set outLines to {}
    repeat with e in eventList
        set end of outLines to (my fmtDate(start date of e) & "|" & (summary of e))
    end repeat

    set oldTIDs to AppleScript's text item delimiters
    set AppleScript's text item delimiters to "\n"
    set outText to outLines as string
    set AppleScript's text item delimiters to oldTIDs
    return outText
end tell
APPLESCRIPT

output="$(cat "$tmp_output")"
rm -f "$tmp_output"

if [ -z "$output" ]; then
    echo "未获取到任何事件"
    exit 0
fi

created=0
skipped_existing=0
skipped_parse=0

while IFS= read -r line; do
    [ -z "$line" ] && continue

    start_time="${line%%|*}"
    summary="${line#*|}"

    date_part="${start_time%% *}"
    time_part="${start_time#* }"
    hour="${time_part%%:*}"
    minute="${time_part#*:}"
    filename="${OUTPUT_DIR}/${date_part}_${hour}${minute}.json"

    if [ -f "$filename" ] && [ "$OVERWRITE" != "true" ]; then
        skipped_existing=$((skipped_existing + 1))
        continue
    fi

    temperature="$(printf "%s" "$summary" | sed -nE 's/^(-?[0-9]+)°C，.*$/\1/p')"
    weather="$(printf "%s" "$summary" | sed -nE 's/^-?[0-9]+°C，([^，]+)，[0-9]+%$/\1/p')"
    humidity="$(printf "%s" "$summary" | sed -nE 's/^.*，([0-9]+)%$/\1/p')"

    if [ -z "$temperature" ] || [ -z "$weather" ] || [ -z "$humidity" ]; then
        echo "跳过无法解析的事件: $start_time | $summary"
        skipped_parse=$((skipped_parse + 1))
        continue
    fi

    report_time="${date_part} ${hour}:${minute}:00"

    CITY_CODE="$CITY_CODE" \
    CITY_NAME="$CITY_NAME" \
    PROVINCE_NAME="$PROVINCE_NAME" \
    TEMPERATURE="$temperature" \
    WEATHER="$weather" \
    HUMIDITY="$humidity" \
    REPORT_TIME="$report_time" \
    python3 - <<'PY' > "$filename"
import json
import os

payload = {
    "status": "1",
    "count": "1",
    "info": "OK",
    "infocode": "10000",
    "lives": [{
        "province": os.environ["PROVINCE_NAME"],
        "city": os.environ["CITY_NAME"],
        "adcode": os.environ["CITY_CODE"],
        "weather": os.environ["WEATHER"],
        "temperature": os.environ["TEMPERATURE"],
        "winddirection": "",
        "windpower": "",
        "humidity": os.environ["HUMIDITY"],
        "reporttime": os.environ["REPORT_TIME"],
    }],
}
print(json.dumps(payload, ensure_ascii=False))
PY

    echo "已生成: $filename"
    created=$((created + 1))
done <<< "$output"

echo "完成: 新建 $created 个, 已存在跳过 $skipped_existing 个, 解析失败跳过 $skipped_parse 个"
