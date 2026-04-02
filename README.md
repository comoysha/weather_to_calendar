# weather_to_calendar

把杭州天气写入 Apple Calendar，并在本地保留历史 JSON，再生成一个可直接离线打开的趋势图页面。

## 文件结构

- [weather_to_calendar.sh](/Users/xiayue/raycast_script/weather_to_calendar/weather_to_calendar.sh): 拉取高德天气、写入 Calendar、保存历史、触发图表生成。
- [html_generator.py](/Users/xiayue/raycast_script/weather_to_calendar/html_generator.py): 扫描 `weather_history/`，输出 [chart.html](/Users/xiayue/raycast_script/weather_to_calendar/chart.html) 和 [chart_data.js](/Users/xiayue/raycast_script/weather_to_calendar/chart_data.js)。
- [assets/chart_app.js](/Users/xiayue/raycast_script/weather_to_calendar/assets/chart_app.js): 图表交互与 SVG 渲染逻辑。
- [assets/chart.css](/Users/xiayue/raycast_script/weather_to_calendar/assets/chart.css): 图表页面样式。
- [weather_history/](/Users/xiayue/raycast_script/weather_to_calendar/weather_history): 原始天气响应存档目录。
- [export_calendar_history.sh](/Users/xiayue/raycast_script/weather_to_calendar/export_calendar_history.sh): 从 Calendar 导出历史天气事件。
- [recover_missing_weather_history.sh](/Users/xiayue/raycast_script/weather_to_calendar/recover_missing_weather_history.sh): 从 Calendar 回填缺失的天气 JSON，默认不覆盖已有文件。

## 使用方式

先把 [weather_config.example.sh](/Users/xiayue/raycast_script/weather_to_calendar/weather_config.example.sh) 复制成 `weather_config.sh`，填入 API Key、城市代码和日历名称。

手动执行主流程：

```bash
TZ=Asia/Shanghai ./weather_to_calendar.sh
```

只重建图表：

```bash
TZ=Asia/Shanghai python3 html_generator.py --input-dir weather_history --output chart.html
```

安装 `launchd` 定时任务：

```bash
TZ=Asia/Shanghai ./install_launchd.sh
```

定时任务会在北京时间 `06:00`、`12:00`、`20:00` 触发。

卸载 `launchd` 定时任务：

```bash
TZ=Asia/Shanghai ./uninstall_launchd.sh
```

回填缺失的天气 JSON：

```bash
TZ=Asia/Shanghai ./recover_missing_weather_history.sh --start-date 2026-02-06 --end-date 2026-03-31
```

## 输出说明

- [chart.html](/Users/xiayue/raycast_script/weather_to_calendar/chart.html) 是一个很薄的页面壳。
- [chart_data.js](/Users/xiayue/raycast_script/weather_to_calendar/chart_data.js) 保存生成后的图表数据。
- 页面引用本地 CSS 和 JS，不依赖 `Chart.js`、Google Fonts 或其他外网资源，离线打开即可使用。
- 支持年份切换、全年/半年/最近 3 个月切换，以及温度/湿度切换。
- 图表生成会优先使用精确的 `06:00`、`12:00`、`20:00` 记录；对于从 Calendar 回填出的 `02:00`、`18:00`、`08:30`、`09:15` 这类历史异常时间，会按最近档位归一后再绘图。
- [weather_to_calendar.sh](/Users/xiayue/raycast_script/weather_to_calendar/weather_to_calendar.sh) 现在统一输出北京时间日志；保存 JSON、生成图表、创建目录等步骤失败时会立即退出，不再静默跳过。
- 历史文件应为纯 JSON；图表生成器会兼容旧文件中“日志行 + JSON”这种脏数据，但新写入文件不再混入日志。
- [com.xiayue.weather-to-calendar.plist](/Users/xiayue/raycast_script/weather_to_calendar/com.xiayue.weather-to-calendar.plist) 是 `launchd` 配置模板。
- [install_launchd.sh](/Users/xiayue/raycast_script/weather_to_calendar/install_launchd.sh) 会把配置安装到 `~/Library/LaunchAgents/` 并立即加载。
- [uninstall_launchd.sh](/Users/xiayue/raycast_script/weather_to_calendar/uninstall_launchd.sh) 会卸载并移除 `~/Library/LaunchAgents/` 中的对应任务。
- 运行日志会写到 [logs](/Users/xiayue/raycast_script/weather_to_calendar/logs) 目录。

## 验证项

- Calendar 中新增天气事件成功。
- `weather_history/` 下新增北京时间命名的 JSON。
- [chart.html](/Users/xiayue/raycast_script/weather_to_calendar/chart.html) 与 [chart_data.js](/Users/xiayue/raycast_script/weather_to_calendar/chart_data.js) 已刷新。
