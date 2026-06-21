#!/bin/bash
set -e

# ============================================================
#       Soft-Ripe Timezone AI Lover -- One-Click Start (Linux)
# ============================================================

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8765

PYTHON_CMD="python3"
NPM_CMD="npm"

# 清理函数
cleanup() {
    echo ""
    echo "Stopping server..."
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
    fi
    echo "[OK] Server stopped"
    echo ""
    exit 0
}

trap cleanup SIGINT SIGTERM

clear

echo "============================================================"
echo "      Soft-Ripe Timezone AI Lover -- One-Click Start"
echo "============================================================"
echo ""

# ---- [1/5] 环境检查 ----
echo "[1/5] Checking environment..."

# 检查 Python
if ! command -v python3 &>/dev/null; then
    if ! command -v python &>/dev/null; then
        echo "[ERROR] Python not found. Please install Python 3.10+"
        exit 1
    fi
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "[OK] $PYTHON_VERSION"

# 检查 Python 版本 >= 3.10
$PYTHON_CMD -c "import sys; sys.exit(0) if sys.version_info >= (3,10) else sys.exit(1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

# 检查 Node.js / npm
if ! command -v npm &>/dev/null; then
    echo "[ERROR] npm not found. Please install Node.js 16+"
    exit 1
fi
NPM_VERSION=$(npm --version 2>&1)
echo "[OK] npm v$NPM_VERSION"

echo ""

# ---- [2/5] 安装后端依赖 ----
echo "[2/5] Installing backend dependencies..."
cd "$BACKEND_DIR"
pip install -r requirements.txt -q --disable-pip-version-check 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[OK] Backend dependencies ready"
else
    echo "[WARN] pip install failed, retrying..."
    pip install -r requirements.txt --disable-pip-version-check
fi
echo ""

# ---- [3/5] 构建前端 ----
echo "[3/5] Building frontend..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "    Installing frontend dependencies..."
    npm install --silent
fi
echo "    Building production frontend..."
npm run build
if [ $? -eq 0 ]; then
    echo "[OK] Frontend build completed"
else
    echo "[WARN] Frontend build failed. Run 'npm run build' manually."
fi
echo ""

# ---- [4/5] 清理端口占用 ----
echo "[4/5] Cleaning up existing processes on port $BACKEND_PORT..."
PID=$(lsof -ti :$BACKEND_PORT 2>/dev/null || fuser $BACKEND_PORT/tcp 2>/dev/null | awk '{print $1}')
if [ -n "$PID" ]; then
    echo "    Killing process on port $BACKEND_PORT PID: $PID"
    kill -9 $PID 2>/dev/null
fi
sleep 1
echo "[OK] Port cleaned"
echo ""

# ---- [5/5] 启动服务 ----
echo "[5/5] Starting server..."
echo ""

cd "$BACKEND_DIR"
echo "[START] Server (backend + frontend, port $BACKEND_PORT)..."
echo ""
echo "============================================================"
echo "               SERVER STARTING..."
echo ""
echo "  The browser will open automatically when ready."
echo ""
echo "  To stop: Press Ctrl+C"
echo "============================================================"
echo ""

# 后台启动 Python 服务
$PYTHON_CMD main.py &
SERVER_PID=$!

# 等待服务就绪后打开浏览器
sleep 2
if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$BACKEND_PORT" 2>/dev/null &
elif command -v open &>/dev/null; then
    open "http://localhost:$BACKEND_PORT" 2>/dev/null &
fi

# 等待服务进程结束
wait $SERVER_PID