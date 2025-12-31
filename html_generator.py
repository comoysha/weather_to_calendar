#!/usr/bin/env python3
import argparse
import calendar
import json
import os
import re
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Generate chart.html from weather_history JSON files.")
    parser.add_argument("--input-dir", default="weather_history", help="Directory containing JSON history files.")
    parser.add_argument("--output", default="chart.html", help="Output HTML file path.")
    return parser.parse_args()

def load_history(input_dir):
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.json$")
    data = {}
    hours = {6, 12, 20}

    if not os.path.isdir(input_dir):
        return data

    for name in os.listdir(input_dir):
        match = pattern.match(name)
        if not match:
            continue
        date_str, hour_str, minute_str = match.groups()
        hour = int(hour_str)
        if hour not in hours:
            continue

        path = os.path.join(input_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            live = payload["lives"][0]
            temperature = live["temperature"]
            humidity = live.get("humidity")
            weather = live.get("weather", "")
            temp_value = float(temperature)
            hum_value = float(humidity) if humidity not in (None, "") else None
        except Exception:
            continue

        entry = data.setdefault(date_str, {}).setdefault(hour, {})
        entry["temperature"] = temp_value
        entry["humidity"] = hum_value
        entry["weather"] = weather

    return data

def build_chart_data(history):
    years = sorted({date[:4] for date in history})
    include_leap = any(date[5:] == "02-29" for date in history)
    labels = []
    label_index = {}
    base_year = 2000 if include_leap else 2001

    for month in range(1, 13):
        days = calendar.monthrange(base_year, month)[1]
        for day in range(1, days + 1):
            md = f"{month:02d}-{day:02d}"
            label_index[md] = len(labels)
            labels.append(md)

    hours = ["6", "12", "20"]
    temp_series = {year: {hour: [None] * len(labels) for hour in hours} for year in years}
    hum_series = {year: {hour: [None] * len(labels) for hour in hours} for year in years}
    weather_series = {year: {hour: [""] * len(labels) for hour in hours} for year in years}

    for date, hours_data in history.items():
        year = date[:4]
        md = date[5:]
        idx = label_index.get(md)
        if idx is None or year not in temp_series:
            continue
        for hour, entry in hours_data.items():
            hour_key = str(hour)
            if hour_key not in temp_series[year]:
                continue
            temp_series[year][hour_key][idx] = entry.get("temperature")
            hum_series[year][hour_key][idx] = entry.get("humidity")
            weather_series[year][hour_key][idx] = entry.get("weather", "")

    return labels, years, base_year, temp_series, hum_series, weather_series

def render_html(labels, years, base_year, temp_series, hum_series, weather_series, output_path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    latest_year = years[-1] if years else ""
    counts = {}
    if latest_year:
        counts = {hour: sum(1 for v in temp_series[latest_year][hour] if v is not None) for hour in temp_series[latest_year]}
    year_controls = "\n".join(
        f"<label class=\"year-chip\"><input type=\"checkbox\" value=\"{year}\"{' checked' if year == latest_year else ''}><span>{year}</span></label>"
        for year in years
    )

    html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>杭州天气折线图</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
  <link href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600&family=ZCOOL+XiaoWei&display=swap\" rel=\"stylesheet\" />
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    :root {{
      --bg-start: #f6f0e7;
      --bg-end: #d7e6f2;
      --card-bg: rgba(255, 255, 255, 0.85);
      --text-main: #1b1f23;
      --text-muted: #5a6670;
      --line-6: #f06b42;
      --line-12: #2b7bb9;
      --line-20: #3a9c6f;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: \"IBM Plex Sans\", system-ui, sans-serif;
      color: var(--text-main);
      background: radial-gradient(circle at top left, #fff7eb, transparent 40%),
                  radial-gradient(circle at top right, #e1f0ff, transparent 45%),
                  linear-gradient(135deg, var(--bg-start), var(--bg-end));
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px 20px;
    }}

    .card {{
      width: min(1100px, 100%);
      background: var(--card-bg);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(36, 44, 60, 0.18);
      padding: 28px 32px 36px;
      backdrop-filter: blur(12px);
      animation: rise 0.7s ease-out;
    }}

    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(18px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }}

    h1 {{
      margin: 0;
      font-family: \"ZCOOL XiaoWei\", serif;
      font-weight: 400;
      font-size: clamp(28px, 3.2vw, 40px);
      letter-spacing: 0.5px;
    }}

    .meta {{
      font-size: 14px;
      color: var(--text-muted);
      line-height: 1.6;
    }}

    .meta span {{
      display: inline-block;
      margin-right: 16px;
    }}

    .toolbar {{
      display: inline-flex;
      gap: 12px;
      padding: 6px;
      border-radius: 999px;
      background: rgba(27, 31, 35, 0.08);
      margin: 8px 0 18px;
    }}

    .range-filter {{
      display: inline-flex;
      gap: 10px;
      padding: 6px;
      border-radius: 999px;
      background: rgba(27, 31, 35, 0.08);
      margin: 0 0 18px;
    }}

    .tab {{
      border: none;
      background: transparent;
      color: var(--text-main);
      font-size: 14px;
      padding: 8px 16px;
      border-radius: 999px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .tab.is-active {{
      background: #1b1f23;
      color: #fff;
      box-shadow: 0 10px 20px rgba(27, 31, 35, 0.2);
    }}

    .year-filter {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: var(--text-muted);
      margin: 6px 0 18px;
    }}

    .year-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 999px;
      background: rgba(27, 31, 35, 0.08);
      color: var(--text-main);
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .year-chip input {{
      appearance: none;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      border: 2px solid #1b1f23;
      display: inline-block;
      position: relative;
    }}

    .year-chip input:checked {{
      background: #1b1f23;
    }}

    .chart-wrap {{
      position: relative;
      height: 480px;
    }}

    canvas {{
      width: 100% !important;
      height: 100% !important;
    }}

    @media (max-width: 720px) {{
      .card {{ padding: 22px; }}
      .chart-wrap {{ height: 360px; }}
    }}
  </style>
</head>
<body>
  <div class=\"card\">
    <header>
      <h1>杭州天气温度记录</h1>
      <div class=\"meta\">
        <span>更新于: {now_str}</span>
        <span>06:00 记录 {counts.get('6', 0)} 条</span>
        <span>12:00 记录 {counts.get('12', 0)} 条</span>
        <span>20:00 记录 {counts.get('20', 0)} 条</span>
      </div>
    </header>
    <div class=\"year-filter\">
      <span>年份</span>
      {year_controls}
    </div>
    <div class=\"range-filter\">
      <button class=\"tab is-active\" data-range=\"full\">全年</button>
      <button class=\"tab\" data-range=\"first-half\">上半年</button>
      <button class=\"tab\" data-range=\"second-half\">下半年</button>
      <button class=\"tab\" data-range=\"last-3-months\">最近 3 个月</button>
    </div>
    <div class=\"toolbar\">
      <button class=\"tab is-active\" data-mode=\"temperature\">温度</button>
      <button class=\"tab\" data-mode=\"humidity\">湿度</button>
    </div>
    <div class=\"chart-wrap\">
      <canvas id=\"weatherChart\"></canvas>
    </div>
  </div>

  <script>
    const labels = {json.dumps(labels, ensure_ascii=False)};
    const labelMonths = labels.map((label) => Number(label.split('-')[0]));
    const labelDays = labels.map((label) => Number(label.split('-')[1]));
    const years = {json.dumps(years)};
    const latestYear = {json.dumps(latest_year)};
    const baseYear = {base_year};
    const tempByYear = {json.dumps(temp_series)};
    const humByYear = {json.dumps(hum_series)};
    const weatherByYear = {json.dumps(weather_series, ensure_ascii=False)};
    const hours = ['6', '12', '20'];
    const hourLabels = {{ '6': '06:00', '12': '12:00', '20': '20:00' }};

    const ctx = document.getElementById('weatherChart');
    const baseColors = {{
      '6': getComputedStyle(document.documentElement).getPropertyValue('--line-6').trim(),
      '12': getComputedStyle(document.documentElement).getPropertyValue('--line-12').trim(),
      '20': getComputedStyle(document.documentElement).getPropertyValue('--line-20').trim(),
    }};
    const dashStyles = [[0, 0], [8, 5], [2, 3], [12, 6, 2, 6]];

    const modeData = {{
      temperature: {{
        source: tempByYear,
        yTitle: '温度 (°C)',
        suffix: '°C',
      }},
      humidity: {{
        source: humByYear,
        yTitle: '湿度 (%)',
        suffix: '%',
      }}
    }};

    const buildDatasets = (mode, selectedYears) => {{
      const datasets = [];
      selectedYears.forEach((year, yearIndex) => {{
        hours.forEach((hour) => {{
          const color = baseColors[hour];
          datasets.push({{
            label: `${{hourLabels[hour]}} · ${{year}}`,
            data: modeData[mode].source?.[year]?.[hour] ?? [],
            borderColor: color,
            backgroundColor: color,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointHitRadius: 12,
            spanGaps: false,
            fill: false,
            borderWidth: 2,
            borderDash: dashStyles[yearIndex % dashStyles.length],
            _year: year,
            _hour: hour,
          }});
        }});
      }});
      return datasets;
    }};

    const updateTabs = (mode) => {{
      document.querySelectorAll('.toolbar .tab').forEach((tab) => {{
        tab.classList.toggle('is-active', tab.dataset.mode === mode);
      }});
    }};

    const updateRangeTabs = (range) => {{
      document.querySelectorAll('.range-filter .tab').forEach((tab) => {{
        tab.classList.toggle('is-active', tab.dataset.range === range);
      }});
    }};

    const chart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels,
        datasets: buildDatasets('temperature', latestYear ? [latestYear] : [])
      }},
      options: {{
        maintainAspectRatio: false,
        interaction: {{
          mode: 'nearest',
          intersect: true,
        }},
        scales: {{
          y: {{
            title: {{
              display: true,
              text: '温度 (°C)'
            }},
            grid: {{
              color: 'rgba(120, 130, 140, 0.18)'
            }},
            ticks: {{
              callback: (value) => value
            }}
          }},
          x: {{
            grid: {{
              display: false
            }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{
              usePointStyle: true,
              pointStyle: 'circle'
            }}
          }},
          tooltip: {{
            callbacks: {{
              title: (items) => {{
                if (!items.length) return '';
                const year = items[0].dataset._year || '';
                return year ? `${{year}}-${{items[0].label}}` : items[0].label;
              }},
              label: (context) => {{
                const suffix = modeData[chart.$mode].suffix;
                const value = context.parsed.y ?? '无数据';
                return ` ${{context.dataset.label}}: ${{value}}${{suffix}}`;
              }},
              afterLabel: (context) => {{
                const idx = chart.$indexMap?.[context.dataIndex] ?? context.dataIndex;
                const year = context.dataset._year;
                const hour = context.dataset._hour;
                const humidity = humByYear?.[year]?.[hour]?.[idx];
                const humText = humidity === null || humidity === undefined ? '无数据' : `${{humidity}}%`;
                const weather = weatherByYear?.[year]?.[hour]?.[idx] || '未知';
                return ` 湿度: ${{humText}}  天气: ${{weather}}`;
              }}
            }}
          }}
        }},
        animation: {{
          duration: 1200,
          easing: 'easeOutQuart'
        }}
      }}
    }});

    chart.$mode = 'temperature';
    chart.$range = 'full';
    const selectedYears = new Set(latestYear ? [latestYear] : []);

    const dayOfYear = (year, month, day) => {{
      const date = new Date(year, month - 1, day);
      const start = new Date(year, 0, 1);
      return Math.floor((date - start) / 86400000) + 1;
    }};

    const labelDayOfYear = labels.map((label, idx) => dayOfYear(baseYear, labelMonths[idx], labelDays[idx]));

    const rangeIndices = (range) => {{
      if (range === 'full') {{
        return labels.map((_, idx) => idx);
      }}
      if (range === 'first-half') {{
        return labelMonths.map((m, idx) => m <= 6 ? idx : null).filter((v) => v !== null);
      }}
      if (range === 'second-half') {{
        return labelMonths.map((m, idx) => m >= 7 ? idx : null).filter((v) => v !== null);
      }}
      if (range === 'last-3-months') {{
        const today = new Date();
        const start = new Date(today);
        start.setMonth(start.getMonth() - 3);

        const endDoy = dayOfYear(baseYear, today.getMonth() + 1, today.getDate());
        const startDoy = dayOfYear(baseYear, start.getMonth() + 1, start.getDate());

        if (startDoy <= endDoy) {{
          return labelDayOfYear.map((doy, idx) => (doy >= startDoy && doy <= endDoy) ? idx : null).filter((v) => v !== null);
        }}
        return labelDayOfYear.map((doy, idx) => (doy >= startDoy || doy <= endDoy) ? idx : null).filter((v) => v !== null);
      }}
      return labels.map((_, idx) => idx);
    }};

    const applyRange = (range) => {{
      const idxs = rangeIndices(range);
      chart.$indexMap = idxs;
      chart.data.labels = idxs.map((idx) => labels[idx]);
      chart.data.datasets.forEach((dataset) => {{
        if (!dataset._fullData) {{
          dataset._fullData = dataset.data;
        }}
        dataset.data = idxs.map((idx) => dataset._fullData[idx]);
      }});
      chart.update();
      updateRangeTabs(range);
    }};

    const setMode = (mode) => {{
      chart.$mode = mode;
      const yearsList = Array.from(selectedYears);
      chart.data.datasets = buildDatasets(mode, yearsList);
      chart.data.datasets.forEach((dataset) => {{
        dataset._fullData = dataset.data;
      }});
      chart.options.scales.y.title.text = modeData[mode].yTitle;
      chart.options.scales.y.ticks.callback = (value) => mode === 'humidity' ? `${{value}}%` : value;
      chart.update();
      updateTabs(mode);
      applyRange(chart.$range);
    }};

    document.querySelectorAll('.toolbar .tab').forEach((tab) => {{
      tab.addEventListener('click', () => setMode(tab.dataset.mode));
    }});

    updateTabs('temperature');
    updateRangeTabs('full');

    document.querySelectorAll('.year-chip input').forEach((input) => {{
      input.addEventListener('change', () => {{
        if (input.checked) {{
          selectedYears.add(input.value);
        }} else {{
          selectedYears.delete(input.value);
        }}
        const yearsList = Array.from(selectedYears);
        chart.data.datasets = buildDatasets(chart.$mode, yearsList);
        chart.data.datasets.forEach((dataset) => {{
          dataset._fullData = dataset.data;
        }});
        applyRange(chart.$range);
      }});
    }});

    document.querySelectorAll('.range-filter .tab').forEach((tab) => {{
      tab.addEventListener('click', () => {{
        chart.$range = tab.dataset.range;
        applyRange(chart.$range);
      }});
    }});

    applyRange('full');
  </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    args = parse_args()
    history = load_history(args.input_dir)
    labels, years, base_year, temp_series, hum_series, weather_series = build_chart_data(history)
    render_html(labels, years, base_year, temp_series, hum_series, weather_series, args.output)


if __name__ == "__main__":
    main()
