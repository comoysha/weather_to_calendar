#!/usr/bin/env python3
import argparse
import calendar
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")
TRACKED_HOURS = (6, 12, 20)
TRACKED_SLOT_MINUTES = tuple(hour * 60 for hour in TRACKED_HOURS)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate chart assets from weather_history JSON files.")
    parser.add_argument("--input-dir", default="weather_history", help="Directory containing JSON history files.")
    parser.add_argument("--output", default="chart.html", help="Output HTML file path.")
    return parser.parse_args()


def load_history(input_dir):
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.json$")
    history = {}
    input_path = Path(input_dir)

    if not input_path.is_dir():
        return history

    for item in sorted(input_path.iterdir()):
        match = pattern.match(item.name)
        if not match:
            continue

        try:
            payload = load_json_payload(item)
            live = payload["lives"][0]
            temperature = float(live["temperature"])
            humidity_raw = live.get("humidity")
            humidity = float(humidity_raw) if humidity_raw not in (None, "") else None
            weather = live.get("weather", "")
            report_time_raw = live.get("reporttime", "")
        except Exception:
            continue

        date_str, hour_str, minute_str = match.groups()
        normalized = normalize_slot(date_str, hour_str, minute_str, report_time_raw)
        if normalized is None:
            continue

        normalized_date, normalized_hour, distance_minutes, is_exact_match = normalized
        entry = history.setdefault(normalized_date, {})
        candidate = {
            "temperature": temperature,
            "humidity": humidity,
            "weather": weather,
            "_priority": build_priority(is_exact_match, distance_minutes, item.name),
        }
        current = entry.get(normalized_hour)
        if current is None or candidate["_priority"] > current["_priority"]:
            entry[normalized_hour] = candidate

    return history


def load_json_payload(path):
    raw_text = path.read_text(encoding="utf-8")
    candidate = raw_text.lstrip()
    if candidate.startswith("{"):
        return json.loads(candidate)

    json_start = raw_text.find("{")
    json_end = raw_text.rfind("}")
    if json_start == -1 or json_end == -1 or json_end < json_start:
        raise ValueError(f"No JSON object found in {path}")

    return json.loads(raw_text[json_start:json_end + 1])


def normalize_slot(date_str, hour_str, minute_str, report_time_raw):
    report_dt = parse_reporttime(report_time_raw)
    if report_dt is not None:
        date_str = report_dt.strftime("%Y-%m-%d")
        total_minutes = report_dt.hour * 60 + report_dt.minute
    else:
        total_minutes = int(hour_str) * 60 + int(minute_str)

    slot_minutes, distance_minutes = min(
        ((slot, abs(slot - total_minutes)) for slot in TRACKED_SLOT_MINUTES),
        key=lambda item: item[1],
    )
    if distance_minutes > 240:
        return None

    normalized_hour = slot_minutes // 60
    is_exact_match = total_minutes == slot_minutes
    return date_str, normalized_hour, distance_minutes, is_exact_match


def parse_reporttime(report_time_raw):
    if not report_time_raw:
        return None

    try:
        return datetime.strptime(report_time_raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ASIA_SHANGHAI)
    except ValueError:
        return None


def build_priority(is_exact_match, distance_minutes, source_name):
    return (
        1 if is_exact_match else 0,
        -distance_minutes,
        source_name,
    )


def build_payload(history):
    years = sorted({date[:4] for date in history})
    include_leap = any(date[5:] == "02-29" for date in history)
    base_year = 2000 if include_leap else 2001

    labels = []
    label_index = {}
    for month in range(1, 13):
        days = calendar.monthrange(base_year, month)[1]
        for day in range(1, days + 1):
            month_day = f"{month:02d}-{day:02d}"
            label_index[month_day] = len(labels)
            labels.append(month_day)

    series_template = {str(hour): [None] * len(labels) for hour in TRACKED_HOURS}
    weather_template = {str(hour): [""] * len(labels) for hour in TRACKED_HOURS}
    temperature = {year: {hour: values[:] for hour, values in series_template.items()} for year in years}
    humidity = {year: {hour: values[:] for hour, values in series_template.items()} for year in years}
    weather = {year: {hour: values[:] for hour, values in weather_template.items()} for year in years}

    for date_str, hour_map in history.items():
        year = date_str[:4]
        idx = label_index.get(date_str[5:])
        if idx is None or year not in temperature:
            continue

        for hour, entry in hour_map.items():
            hour_key = str(hour)
            if hour_key not in temperature[year]:
                continue
            temperature[year][hour_key][idx] = entry["temperature"]
            humidity[year][hour_key][idx] = entry["humidity"]
            weather[year][hour_key][idx] = entry["weather"]

    latest_year = years[-1] if years else ""
    preferred_years = [year for year in ("2025", "2026") if year in years]
    default_years = preferred_years or ([latest_year] if latest_year else [])
    counts = {
        str(hour): sum(1 for value in temperature.get(latest_year, {}).get(str(hour), []) if value is not None)
        for hour in TRACKED_HOURS
    } if latest_year else {}

    return {
        "title": "杭州天气温度记录",
        "generatedAt": datetime.now(ASIA_SHANGHAI).strftime("%Y-%m-%d %H:%M"),
        "timezone": "Asia/Shanghai (UTC+8)",
        "baseYear": base_year,
        "years": years,
        "defaultYears": default_years,
        "latestYear": latest_year,
        "counts": counts,
        "labels": labels,
        "hours": [str(hour) for hour in TRACKED_HOURS],
        "hourLabels": {
            "6": "06:00",
            "12": "12:00",
            "20": "20:00",
        },
        "series": {
            "temperature": temperature,
            "humidity": humidity,
            "weather": weather,
        },
    }


def build_html_document():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>杭州天气折线图</title>
  <link rel="stylesheet" href="assets/chart.css" />
</head>
<body>
  <div class="card">
    <header class="header">
      <h1 id="pageTitle">杭州天气温度记录</h1>
      <div id="metaInfo" class="meta"></div>
    </header>
    <div id="yearFilter" class="year-filter"></div>
    <div class="control-row">
      <div id="rangeFilter" class="range-filter"></div>
      <div id="modeFilter" class="toolbar"></div>
    </div>
    <div class="chart-wrap">
      <svg id="weatherChart" aria-label="天气趋势图"></svg>
      <div id="chartTooltip" class="chart-tooltip"></div>
      <div id="chartEmpty" class="chart-empty">当前筛选范围内暂无可绘制数据</div>
    </div>
  </div>

  <script src="chart_data.js"></script>
  <script src="assets/chart_app.js"></script>
</body>
</html>
"""


def write_output_files(output_path, payload):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_document(), encoding="utf-8")

    data_path = output_path.with_name("chart_data.js")
    data_script = "window.WEATHER_CHART_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    data_path.write_text(data_script, encoding="utf-8")


def main():
    args = parse_args()
    history = load_history(args.input_dir)
    payload = build_payload(history)
    write_output_files(Path(args.output), payload)


if __name__ == "__main__":
    main()
