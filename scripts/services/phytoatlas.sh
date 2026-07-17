#!/usr/bin/env bash
set -euo pipefail

########## 0. params ##########
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="$ROOT_DIR/tmp/phytoatlas"
LOG_DIR="$ROOT_DIR/logs"
API_PID_FILE="$RUN_DIR/api.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
API_PORT="${PHYTOATLAS_API_PORT:-8000}"
WEB_PORT="${PHYTOATLAS_WEB_PORT:-4322}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
mkdir -p "$RUN_DIR" "$LOG_DIR"

########## 1. helpers ##########
is_running() {
    local pid_file="$1"
    [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_process() {
    local pid_file="$1"
    if ! is_running "$pid_file"; then
        rm -f "$pid_file"
        return
    fi
    local pid
    local process_group
    pid="$(cat "$pid_file")"
    process_group="$(ps -o pgid= -p "$pid" | tr -d '[:space:]')"
    if [ "$process_group" = "$pid" ]; then
        kill -- "-$pid"
    else
        kill "$pid"
    fi
    rm -f "$pid_file"
}

########## 2. start ##########
start_services() {
    if [ -f "$ROOT_DIR/apps/api/.env" ]; then
        set -a
        source "$ROOT_DIR/apps/api/.env"
        set +a
    fi
    if ! is_running "$API_PID_FILE"; then
        (
            cd "$ROOT_DIR/apps/api"
            nohup setsid "$PYTHON_BIN" -m uvicorn phytoatlas_api.main:app \
                --host 0.0.0.0 --port "$API_PORT" \
                > "$LOG_DIR/phytoatlas-api.log" 2>&1 &
            echo "$!" > "$API_PID_FILE"
        )
    fi
    if ! is_running "$WEB_PID_FILE"; then
        (
            cd "$ROOT_DIR/apps/web"
            nohup setsid npm run dev -- --port "$WEB_PORT" --strictPort \
                > "$LOG_DIR/phytoatlas-web.log" 2>&1 &
            echo "$!" > "$WEB_PID_FILE"
        )
    fi
}

########## 3. stop ##########
stop_services() {
    stop_process "$WEB_PID_FILE"
    stop_process "$API_PID_FILE"
}

########## 4. status ##########
show_status() {
    if is_running "$API_PID_FILE"; then
        echo "API running: http://localhost:$API_PORT"
    else
        echo "API stopped"
    fi
    if is_running "$WEB_PID_FILE"; then
        echo "Web running: http://localhost:$WEB_PORT"
    else
        echo "Web stopped"
    fi
}

########## 5. command ##########
case "${1:-status}" in
    start)
        start_services
        show_status
        ;;
    stop)
        stop_services
        show_status
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|status}" >&2
        exit 1
        ;;
esac
