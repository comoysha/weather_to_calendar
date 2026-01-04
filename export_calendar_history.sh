# 临时脚本,用来把 mac calendar 里的 2025-08-21~2025-12-31 的信息拉到本地
# 后续如果有问题,可以把START_DATE改了重新运行

#!/bin/bash

set -euo pipefail

CALENDAR_NAME="杭州天气存档"
START_DATE="2026-01-01"
OUTPUT_DIR="weather_history"
CITY_CODE="330110"
CITY_NAME="杭州"

END_DATE=$(date "+%Y-%m-%d")

mkdir -p "$OUTPUT_DIR"

tmp_output=$(mktemp)
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

output=$(cat "$tmp_output")
rm -f "$tmp_output"

if [ -z "$output" ]; then
    echo "未获取到任何事件"
    exit 0
fi

while IFS= read -r line; do
    [ -z "$line" ] && continue
    start_time="${line%%|*}"
    summary="${line#*|}"

    date_part="${start_time%% *}"
    time_part="${start_time#* }"
    hour="${time_part%%:*}"
    minute="${time_part#*:}"

    temperature=$(printf "%s" "$summary" | sed -E 's/^([0-9]+).*/\1/')
    weather=$(printf "%s" "$summary" | sed -E 's/^[0-9]+°C，([^，]+)，.*/\1/')
    humidity=$(printf "%s" "$summary" | sed -E 's/^.*，([0-9]+)%.*/\1/')

    if [ -z "$temperature" ] || [ -z "$weather" ] || [ -z "$humidity" ]; then
        echo "跳过无法解析的事件: $summary"
        continue
    fi

    report_time="${date_part} ${hour}:${minute}:00"
    filename="${OUTPUT_DIR}/${date_part}_${hour}${minute}.json"

    CITY_CODE="$CITY_CODE" CITY_NAME="$CITY_NAME" \
    TEMPERATURE="$temperature" WEATHER="$weather" HUMIDITY="$humidity" REPORT_TIME="$report_time" \
    python3 -c "import json, os; payload={'status':'1','count':'1','info':'OK','infocode':'10000','lives':[{'province':'浙江','city':os.environ.get('CITY_NAME',''),'adcode':os.environ.get('CITY_CODE',''),'weather':os.environ.get('WEATHER',''),'temperature':os.environ.get('TEMPERATURE',''),'winddirection':'','windpower':'','humidity':os.environ.get('HUMIDITY',''),'reporttime':os.environ.get('REPORT_TIME','')}]}; print(json.dumps(payload, ensure_ascii=False))" > "$filename"

    echo "已生成: $filename"
done <<< "$output"
