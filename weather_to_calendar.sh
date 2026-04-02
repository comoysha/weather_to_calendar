#!/bin/bash
set -u

export TZ="Asia/Shanghai"

# 天气查询并添加到日历的脚本
# 作者: 自动生成
# 功能: 查询高德天气API，解析数据并创建日历事件

# 配置参数
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$BASE_DIR/weather_config.sh"
if [ -f "$CONFIG_FILE" ]; then
    # shellcheck source=/dev/null
    . "$CONFIG_FILE"
else
    echo "错误: 未找到配置文件 $CONFIG_FILE" >&2
    exit 1
fi

timestamp_now() {
    date "+%Y-%m-%d %H:%M:%S %Z"
}

log_info() {
    echo "[$(timestamp_now)] $*" >&2
}

log_error() {
    echo "[$(timestamp_now)] $*" >&2
}

fail() {
    log_error "$*"
    exit 1
}

# 获取当前时间作为默认值
CURRENT_HOUR=$(date "+%H")  # 当前小时
CURRENT_MINUTE=$(date "+%M")  # 当前分钟

START_HOUR="$CURRENT_HOUR"  # 默认开始时间（当前小时）
START_MINUTE="$CURRENT_MINUTE"  # 默认开始时间（当前分钟）
END_HOUR="$CURRENT_HOUR"    # 默认结束时间（当前小时）
END_MINUTE="$CURRENT_MINUTE"  # 默认结束时间（当前分钟）

# 获取当前日期和时间
CURRENT_DATE=$(date "+%Y-%m-%d")
CURRENT_TIMESTAMP=$(date "+%Y-%m-%d_%H%M")

HISTORY_DIR="$BASE_DIR/weather_history"
CHART_GENERATOR="$BASE_DIR/html_generator.py"
CHART_OUTPUT="$BASE_DIR/chart.html"

# 函数：构建时间字符串
build_time_strings() {
    START_TIME="$CURRENT_DATE $START_HOUR:$START_MINUTE:00"
    END_TIME="$CURRENT_DATE $END_HOUR:$END_MINUTE:00"
}

# 函数：查询天气信息
get_weather_info() {
    local api_url="https://restapi.amap.com/v3/weather/weatherInfo?Key=${API_KEY}&city=${CITY_CODE}&"
    
    log_info "正在查询天气信息..."
    
    # 调用API并获取响应
    local response=$(curl -s --location --request GET "$api_url")
    
    if [ $? -ne 0 ]; then
        fail "无法连接到天气API"
    fi
    
    echo "$response"
}

# 函数：解析JSON数据
parse_weather_data() {
    local json_data="$1"
    
    # 检查API响应状态
    local status=$(echo "$json_data" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$status" != "1" ]; then
        log_error "API返回状态异常"
        log_error "响应内容: $json_data"
        exit 1
    fi
    
    # 提取天气数据
    local temperature=$(echo "$json_data" | grep -o '"temperature":"[^"]*"' | cut -d'"' -f4)
    local weather=$(echo "$json_data" | grep -o '"weather":"[^"]*"' | cut -d'"' -f4)
    local humidity=$(echo "$json_data" | grep -o '"humidity":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$temperature" ] || [ -z "$weather" ] || [ -z "$humidity" ]; then
        log_error "无法解析天气数据"
        log_error "响应内容: $json_data"
        exit 1
    fi
    
    # 构建事件标题
    EVENT_TITLE="${temperature}°C，${weather}，${humidity}%"
    
    log_info "解析成功: 温度 ${temperature}°C, 天气 ${weather}, 湿度 ${humidity}%, 事件标题 ${EVENT_TITLE}"
}

# 函数：保存原始天气响应
save_weather_history() {
    local json_data="$1"
    local output_dir="$HISTORY_DIR"
    local output_file="${output_dir}/${CURRENT_TIMESTAMP}.json"

    mkdir -p "$output_dir" || fail "创建目录失败: $output_dir"
    printf "%s" "$json_data" > "$output_file" || fail "保存天气原始数据失败: $output_file"

    log_info "已保存原始天气数据: $output_file"
}

# 函数：创建日历事件
create_calendar_event() {
    log_info "正在创建日历事件..."
    
    # 构建AppleScript
    local apple_script="
tell application \"Calendar\"
    set targetCalendar to first calendar whose name is \"$CALENDAR_NAME\"
    
    set startDate to (date \"$START_TIME\")
    set endDate to (date \"$END_TIME\")
    
    tell targetCalendar
        make new event with properties {summary:\"$EVENT_TITLE\", start date:startDate, end date:endDate, description:\"天气信息 - $CURRENT_DATE\"}
    end tell
end tell
"
    
    # 执行AppleScript
    echo "$apple_script" | osascript
    
    if [ $? -eq 0 ]; then
        log_info "日历事件创建成功: $EVENT_TITLE, 时间 ${START_TIME}"
    else
        fail "日历事件创建失败"
    fi
}

# 函数：生成折线图
generate_chart() {
    if [ -f "$CHART_GENERATOR" ]; then
        python3 "$CHART_GENERATOR" --input-dir "$HISTORY_DIR" --output "$CHART_OUTPUT"
        if [ $? -eq 0 ]; then
            log_info "chart.html 已更新"
        else
            fail "chart.html 生成失败"
        fi
    else
        fail "未找到图表生成脚本: $CHART_GENERATOR"
    fi
}

# 函数：显示帮助信息
show_help() {
    echo "天气信息日历脚本"
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -c, --city CODE         设置城市代码 (默认: 330110)"
    echo "  -k, --key KEY           设置API密钥"
    echo "  -n, --calendar NAME     设置日历名称 (默认: 收件箱)"
    echo "  -s, --start-time HH:MM  设置开始时间 (默认: 07:00)"
    echo "  -e, --end-time HH:MM    设置结束时间 (默认: 07:00)"
    echo "  -h, --help              显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                                    # 使用默认设置"
    echo "  $0 -c 110000 -n \"工作日历\"             # 指定城市和日历"
    echo "  $0 -s 08:30 -e 09:00                  # 设置时间为8:30-9:00"
    echo "  $0 -s 07:00 -e 07:30 -n \"天气提醒\"    # 完整自定义设置"
}

# 函数：验证时间格式
validate_time_format() {
    local time_str="$1"
    local param_name="$2"
    
    if [[ ! $time_str =~ ^[0-2][0-9]:[0-5][0-9]$ ]]; then
        fail "$param_name 格式不正确，应为 HH:MM 格式 (如: 08:30)"
    fi
    
    local hour=$(echo "$time_str" | cut -d':' -f1)
    local minute=$(echo "$time_str" | cut -d':' -f2)
    
    if [ "$hour" -gt 23 ]; then
        fail "$param_name 小时数不能超过23"
    fi
    
    if [ "$minute" -gt 59 ]; then
        fail "$param_name 分钟数不能超过59"
    fi
}

# 函数：解析时间参数
parse_time_param() {
    local time_str="$1"
    local is_start="$2"
    
    validate_time_format "$time_str" "$([ "$is_start" = "true" ] && echo "开始时间" || echo "结束时间")"
    
    local hour=$(echo "$time_str" | cut -d':' -f1)
    local minute=$(echo "$time_str" | cut -d':' -f2)
    
    if [ "$is_start" = "true" ]; then
        START_HOUR="$hour"
        START_MINUTE="$minute"
    else
        END_HOUR="$hour"
        END_MINUTE="$minute"
    fi
}

# 主函数
main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--city)
                CITY_CODE="$2"
                shift 2
                ;;
            -k|--key)
                API_KEY="$2"
                shift 2
                ;;
            -n|--calendar)
                CALENDAR_NAME="$2"
                shift 2
                ;;
            -s|--start-time)
                parse_time_param "$2" "true"
                shift 2
                ;;
            -e|--end-time)
                parse_time_param "$2" "false"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 构建时间字符串
    build_time_strings
    
    # 检查必要参数
    if [ -z "$API_KEY" ]; then
        fail "请设置API密钥"
    fi
    
    log_info "=== 天气信息日历脚本 ==="
    log_info "城市代码: $CITY_CODE"
    log_info "日历名称: $CALENDAR_NAME"
    log_info "日期: $CURRENT_DATE"
    log_info "开始时间: $START_TIME"
    log_info "结束时间: $END_TIME"
    
    # 执行主要流程
    local weather_data=$(get_weather_info)
    save_weather_history "$weather_data"
    parse_weather_data "$weather_data"
    generate_chart
    create_calendar_event
    
    log_info "脚本执行完成"
}

# 执行主函数
main "$@"
