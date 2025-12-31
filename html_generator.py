#!/usr/bin/env python3
import argparse
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
    labels = sorted(history.keys())
    hours = [6, 12, 20]
    temp_series = {hour: [] for hour in hours}
    hum_series = {hour: [] for hour in hours}
    weather_series = {hour: [] for hour in hours}

    for date in labels:
        for hour in hours:
            entry = history.get(date, {}).get(hour)
            if entry is None:
                temp_series[hour].append(None)
                hum_series[hour].append(None)
                weather_series[hour].append("")
                continue
            temp_series[hour].append(entry.get("temperature"))
            hum_series[hour].append(entry.get("humidity"))
            weather_series[hour].append(entry.get("weather", ""))

    return labels, temp_series, hum_series, weather_series

def render_html(labels, temp_series, hum_series, weather_series, output_path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    counts = {hour: sum(1 for v in temp_series[hour] if v is not None) for hour in temp_series}

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
        <span>06:00 记录 {counts[6]} 条</span>
        <span>12:00 记录 {counts[12]} 条</span>
        <span>20:00 记录 {counts[20]} 条</span>
      </div>
    </header>
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
    const temp06 = {json.dumps(temp_series[6])};
    const temp12 = {json.dumps(temp_series[12])};
    const temp20 = {json.dumps(temp_series[20])};
    const hum06 = {json.dumps(hum_series[6])};
    const hum12 = {json.dumps(hum_series[12])};
    const hum20 = {json.dumps(hum_series[20])};
    const weather06 = {json.dumps(weather_series[6], ensure_ascii=False)};
    const weather12 = {json.dumps(weather_series[12], ensure_ascii=False)};
    const weather20 = {json.dumps(weather_series[20], ensure_ascii=False)};

    const ctx = document.getElementById('weatherChart');
    const baseDatasets = [
      {{
        label: '06:00',
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--line-6').trim(),
        backgroundColor: 'rgba(240, 107, 66, 0.18)',
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 6,
        spanGaps: false,
      }},
      {{
        label: '12:00',
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--line-12').trim(),
        backgroundColor: 'rgba(43, 123, 185, 0.18)',
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 6,
        spanGaps: false,
      }},
      {{
        label: '20:00',
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--line-20').trim(),
        backgroundColor: 'rgba(58, 156, 111, 0.18)',
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 6,
        spanGaps: false,
      }}
    ];

    const modeData = {{
      temperature: {{
        datasets: [temp06, temp12, temp20],
        yTitle: '温度 (°C)',
      }},
      humidity: {{
        datasets: [hum06, hum12, hum20],
        yTitle: '湿度 (%)',
      }}
    }};

    const humidityLookup = {{
      '06:00': hum06,
      '12:00': hum12,
      '20:00': hum20,
    }};

    const weatherLookup = {{
      '06:00': weather06,
      '12:00': weather12,
      '20:00': weather20,
    }};

    const buildDatasets = (mode) => baseDatasets.map((base, idx) => ({{ ...base, data: modeData[mode].datasets[idx] }}));

    const updateTabs = (mode) => {{
      document.querySelectorAll('.tab').forEach((tab) => {{
        tab.classList.toggle('is-active', tab.dataset.mode === mode);
      }});
    }};

    const chart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels,
        datasets: buildDatasets('temperature')
      }},
      options: {{
        maintainAspectRatio: false,
        interaction: {{
          mode: 'index',
          intersect: false,
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
              label: (context) => {{
                const suffix = chart.$mode === 'humidity' ? '%' : '°C';
                const value = context.parsed.y ?? '无数据';
                return ` ${{context.dataset.label}}: ${{value}}${{suffix}}`;
              }},
              afterLabel: (context) => {{
                const label = context.dataset.label;
                const idx = context.dataIndex;
                const humidity = humidityLookup[label]?.[idx];
                const humText = humidity === null || humidity === undefined ? '无数据' : `${{humidity}}%`;
                const weather = weatherLookup[label]?.[idx] || '未知';
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

    const setMode = (mode) => {{
      chart.$mode = mode;
      chart.data.datasets = buildDatasets(mode);
      chart.options.scales.y.title.text = modeData[mode].yTitle;
      chart.options.scales.y.ticks.callback = (value) => mode === 'humidity' ? `${{value}}%` : value;
      chart.update();
      updateTabs(mode);
    }};

    document.querySelectorAll('.tab').forEach((tab) => {{
      tab.addEventListener('click', () => setMode(tab.dataset.mode));
    }});

    updateTabs('temperature');
  </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    args = parse_args()
    history = load_history(args.input_dir)
    labels, temp_series, hum_series, weather_series = build_chart_data(history)
    render_html(labels, temp_series, hum_series, weather_series, args.output)


if __name__ == "__main__":
    main()
