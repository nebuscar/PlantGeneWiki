#!/bin/bash
# PlantGeneWiki 服务管理脚本
# 用法：bash scripts/plantgenewiki.sh [start|stop|status]

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJ/logs"
mkdir -p "$LOG_DIR"

# 服务配置
AGENT_DIR="$PROJ/agent"
AGENT_PORT=8000
AGENT_NAME="chainlit"

show_status() {
    echo "========================================"
    echo "  PlantGeneWiki 服务状态"
    echo "========================================"

    local agent_pid=$(pgrep -f "chainlit run app.py" 2>/dev/null | head -1)
    if [ -n "$agent_pid" ]; then
        echo "  AI Agent    :${AGENT_PORT}  运行中 (PID: $agent_pid)"
        curl -s -o /dev/null -w "  HTTP状态  : %{http_code}\n" http://localhost:${AGENT_PORT}/ 2>/dev/null || echo "  HTTP状态  : 无响应"
    else
        echo "  AI Agent    :${AGENT_PORT}  未运行"
    fi
    echo "========================================"
}

stop_all() {
    echo "停止所有 PlantGeneWiki 服务..."
    pkill -f "chainlit run app.py" 2>/dev/null
    echo "已发送停止信号"
}

start_all() {
    # 检查环境
    if [ ! -d "$AGENT_DIR" ]; then
        echo "错误：agent 目录不存在"
        exit 1
    fi

    # 检查是否已运行
    if pgrep -f "chainlit run app.py" > /dev/null; then
        echo "AI Agent 已在运行中"
        show_status
        return
    fi

    # 加载环境变量
    if [ -f "$AGENT_DIR/.env" ]; then
        set -a; source "$AGENT_DIR/.env"; set +a
    fi

    echo "========================================"
    echo "  PlantGeneWiki 服务启动"
    echo "========================================"

    # 启动 AI Agent
    cd "$AGENT_DIR"
    conda run -n plantsdb chainlit run app.py --host 0.0.0.0 --port ${AGENT_PORT} \
        > "$LOG_DIR/agent.log" 2>&1 &
    local agent_pid=$!
    echo "  AI Agent    → http://localhost:${AGENT_PORT}   (PID: $agent_pid)"

    echo "========================================"
    echo ""
    echo "日志目录: $LOG_DIR"
    echo "停止服务: bash scripts/plantgenewiki.sh stop"
    echo ""

    # 等待服务就绪并自动打开浏览器
    echo "正在等待服务启动..."
    for i in {1..20}; do
        if curl -s -o /dev/null http://localhost:${AGENT_PORT}/ 2>/dev/null; then
            echo ""
            echo "========================================"
            echo "  服务已就绪！"
            echo "========================================"
            echo ""
            echo "  访问地址: http://localhost:${AGENT_PORT}"
            echo ""
            echo "  点击上述链接或等待自动打开浏览器..."
            echo "========================================"
            # 自动打开浏览器
            xdg-open http://localhost:${AGENT_PORT} &>/dev/null || \
            open http://localhost:${AGENT_PORT} &>/dev/null || \
            echo "（无法自动打开浏览器，请手动访问）"
            break
        fi
        sleep 1
    done

    if ! curl -s -o /dev/null http://localhost:${AGENT_PORT}/ 2>/dev/null; then
        echo ""
        echo "警告：服务启动超时，请检查日志: $LOG_DIR/agent.log"
    fi

    show_status
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    *)
               echo "用法: bash scripts/plantgenewiki.sh {start|stop|status}"
        echo ""
        echo "  start   启动所有服务"
        echo "  stop    停止所有服务"
        echo "  status  查看服务状态"
        exit 1
        ;;
esac
