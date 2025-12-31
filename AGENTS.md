# AGENTS.md

本文件用于指导自动化代理在本仓库内的改动与协作方式。

## 项目概览
- 目的: 定时获取高德天气并写入 Apple Calendar, 同时本地留存数据并生成折线图。
- 运行环境: macOS (依赖 Calendar.app 与 osascript)。
- 定时点: 每天 06:00 / 12:00 / 20:00 执行脚本。

## 关键文件
- weather_to_calendar.sh: 获取天气并创建日历事件的主脚本。
- 需求.md: 当前需求说明与变更方向。
- 计划新增:
  - weather_history/: 本地 JSON 数据存档目录。
  - html_generator.py: 从 weather_history 生成 chart.html。
  - chart.html: 天气折线图输出。
  - 临时历史提取脚本: 从 Calendar 导出历史数据到 weather_history。

## 重要约束
- 不要修改用户已有的日历数据或删除事件。
- 修改脚本时保持兼容现有自动化调用方式。
- 尽量保持输出与目录命名可预测、可读。

## 数据存档约定 (待确认)
- 每次调用 weather_to_calendar.sh 时将完整天气响应保存为 JSON。
- 文件名使用可读时间戳 (例如 YYYYMMDD_HHMMSS.json)。
- 存放目录: weather_history/。

## 图表生成
- html_generator.py 负责扫描 weather_history, 生成 chart.html。
- 生成的图表为三条折线: 06:00 / 12:00 / 20:00 的每日温度。
- 每次执行 weather_to_calendar.sh 后自动调用生成器。

## 历史数据导出
- 使用临时 sh 脚本从 Calendar 读取 2025-08-21 至今的天气事件。
- 解析事件标题, 还原温度/天气/湿度并写入 weather_history。

## 开发提示
- API Key 与城市代码在 weather_to_calendar.sh 中配置。
- Calendar 名称默认: "杭州天气存档"。
- 若需要调整结构或数据格式, 先更新 需求.md 再改代码。

## 运行/验证建议
- 手动执行: `./weather_to_calendar.sh`。
- 验证项: Calendar 事件创建成功 + weather_history 新 JSON + chart.html 更新。
