#!/bin/bash
# 启动脚本 - 同时启动视频流传输器和可视化功能

# 设置默认参数
PORT=${PORT:-5000}
HOST=${HOST:-localhost}
WEB_PORT=${WEB_PORT:-5001}
CHART_PORT=${CHART_PORT:-5002}
RS485_PORT=${RS485_PORT:-/dev/ttyTHS1}
RS485_BAUD=${RS485_BAUD:-9600}
LUX_SENSOR_ADDR=${LUX_SENSOR_ADDR:-0x0B}
LIGHT_CONTROL_ADDR=${LIGHT_CONTROL_ADDR:-0x01}
DESCRIPTION_INTERVAL=${DESCRIPTION_INTERVAL:-10}
MODEL=${MODEL:-gemma3:4b}
VIDEO_SOURCE=${VIDEO_SOURCE:-0}
VLLM_URL=${VLLM_URL:-http://localhost:11434/v1/completions}

# 显示使用说明
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "启动VLM Demo系统"
    echo ""
    echo "选项:"
    echo "  --port PORT              UDP端口 (默认: 5000)"
    echo "  --host HOST              主机地址 (默认: localhost)"
    echo "  --web-port WEB_PORT      Web界面端口 (默认: 5001)"
    echo "  --chart-port CHART_PORT  图表数据端口 (默认: 5002)"
    echo "  --rs485-port RS485_PORT  RS485串口设备 (默认: /dev/ttyTHS1)"
    echo "  --rs485-baud RS485_BAUD  RS485波特率 (默认: 9600)"
    echo "  --lux-sensor-addr ADDR   光照传感器地址 (默认: 0x0B)"
    echo "  --light-control-addr ADDR 灯光控制地址 (默认: 0x01)"
    echo "  --description-interval SECONDS 分析间隔 (默认: 10)"
    echo "  --model MODEL            Ollama模型名称 (默认: gemma3:4b)"
    echo "  --video-source SOURCE    视频源 (默认: 0)"
    echo "  --vllm-url URL           vLLM API URL (默认: http://localhost:11434/v1/completions)"
    echo "  --no-rs485               禁用RS485设备支持"
    echo "  --help                   显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  PORT, HOST, WEB_PORT, CHART_PORT, RS485_PORT, RS485_BAUD, LUX_SENSOR_ADDR, LIGHT_CONTROL_ADDR"
    echo "  DESCRIPTION_INTERVAL, MODEL, VIDEO_SOURCE, VLLM_URL"
    echo ""
    echo "示例:"
    echo "  $0"
    echo "  $0 --port 5005 --web-port 5006"
    echo "  PORT=5005 WEB_PORT=5006 $0"
    echo "  $0 --no-rs485"
    echo "  $0 --video-source /path/to/video.mp4"
    exit 1
}

# 解析命令行参数
ENABLE_RS485=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --web-port)
            WEB_PORT="$2"
            shift 2
            ;;
        --chart-port)
            CHART_PORT="$2"
            shift 2
            ;;
        --rs485-port)
            RS485_PORT="$2"
            shift 2
            ;;
        --rs485-baud)
            RS485_BAUD="$2"
            shift 2
            ;;
        --lux-sensor-addr)
            LUX_SENSOR_ADDR="$2"
            shift 2
            ;;
        --light-control-addr)
            LIGHT_CONTROL_ADDR="$2"
            shift 2
            ;;
        --description-interval)
            DESCRIPTION_INTERVAL="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --video-source)
            VIDEO_SOURCE="$2"
            shift 2
            ;;
        --vllm-url)
            VLLM_URL="$2"
            shift 2
            ;;
        --no-rs485)
            ENABLE_RS485=false
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "未知选项: $1"
            usage
            ;;
    esac
done

echo "Starting VLM Demo System..."

# 启动Web UI (从指定端口接收数据，在指定Web端口显示UI)
echo "Starting Web UI..."
python3 web_ui.py --port $PORT --host $HOST --web-port $WEB_PORT --chart-port $CHART_PORT &
WEB_UI_PID=$!

# 等待几秒确保Web UI启动
sleep 3

# 检查Web UI是否成功启动
if ! kill -0 $WEB_UI_PID 2>/dev/null; then
    echo "Error: Failed to start Web UI"
    exit 1
fi

# 启动主应用
echo "Starting main application..."
if [ "$ENABLE_RS485" = true ]; then
    echo "Starting with direct RS485 support..."
    python3 app.py \
        --enable-rs485-direct \
        --rs485-port $RS485_PORT \
        --rs485-baud $RS485_BAUD \
        --lux-sensor-addr $LUX_SENSOR_ADDR \
        --light-control-addr $LIGHT_CONTROL_ADDR \
        --port $PORT \
        --host $HOST \
        --description-interval $DESCRIPTION_INTERVAL \
        --model $MODEL \
        --video-source $VIDEO_SOURCE \
        --vllm-url $VLLM_URL &
else
    echo "Starting without RS485 support..."
    python3 app.py \
        --port $PORT \
        --host $HOST \
        --description-interval $DESCRIPTION_INTERVAL \
        --model $MODEL \
        --video-source $VIDEO_SOURCE \
        --vllm-url $VLLM_URL &
fi

APP_PID=$!

# 等待一段时间确保应用启动
sleep 2

# 检查应用是否成功启动
if ! kill -0 $APP_PID 2>/dev/null; then
    echo "Error: Failed to start main application"
    kill $WEB_UI_PID 2>/dev/null
    exit 1
fi

# 显示访问信息
echo ""
echo "=========================================="
echo "VLM Demo System Started!"
echo "Web interface is available at: http://localhost:$WEB_PORT"
echo "UDP Port: $PORT"
echo "Chart Port: $CHART_PORT"
if [ "$ENABLE_RS485" = true ]; then
    echo "RS485 Port: $RS485_PORT"
    echo "RS485 Baud: $RS485_BAUD"
fi
echo "Press Ctrl+C to stop all services"
echo "=========================================="
echo ""

# 等待用户中断
trap 'echo "Stopping all services..."; kill $WEB_UI_PID $APP_PID 2>/dev/null; exit' INT TERM

# 等待任一进程结束
wait $WEB_UI_PID $APP_PID