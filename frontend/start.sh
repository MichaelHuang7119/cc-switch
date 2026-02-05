#!/bin/bash

# CC Switch - 前端启动脚本

# 函数：加载.env文件
load_env() {
    # 先尝试加载frontend目录的.env
    local frontend_env="./.env"
    # 如果没有，再加载项目根目录的.env
    local root_env="../.env"

    # 加载frontend的.env
    if [ -f "$frontend_env" ]; then
        echo "📄 加载环境变量: $frontend_env"
        set -a
        source "$frontend_env"
        set +a
    # 加载项目根目录的.env
    elif [ -f "$root_env" ]; then
        echo "📄 加载环境变量: $root_env"
        set -a
        source "$root_env"
        set +a
    fi
}

# 确保在 frontend 目录
cd "$(dirname "$0")" || { echo "❌ 无法进入脚本目录"; exit 1; }

# 加载环境变量
load_env

if [ ! -f "package.json" ]; then
    echo "❌ 错误: 未找到 package.json，请确保在 frontend 目录运行此脚本"
    exit 1
fi

# 检查是否包含 --dev 参数
DEV_MODE=false
for arg in "$@"; do
    if [[ "$arg" == "--dev" ]]; then
        DEV_MODE=true
        break
    fi
done

echo "🚀 CC Switch - 启动前端服务器..."
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "📦 Node.js 版本: $(node --version)"
echo "📦 npm 版本: $(npm --version)"
echo ""

# 检查依赖
NEED_INSTALL=false
if [ ! -d "node_modules" ]; then
    NEED_INSTALL=true
elif [ ! -f "node_modules/.bin/vite" ]; then
    echo "⚠️  依赖不完整，将重新安装..."
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo "🛠️  安装依赖..."
    if grep -q "patch-package" package.json; then
        echo "📦 预安装 patch-package..."
        npm install --no-save patch-package &>/dev/null || true
    fi

    if ! npm install; then
        echo "⚠️  尝试使用 --legacy-peer-deps..."
        if ! npm install --legacy-peer-deps; then
            echo "❌ 依赖安装失败"
            echo "💡 建议: rm -rf node_modules package-lock.json && npm install"
            exit 1
        fi
    fi
    echo ""
fi

if [ ! -f "node_modules/.bin/vite" ]; then
    echo "❌ vite 未安装成功"
    exit 1
fi

# 生成 SvelteKit 配置
if [ ! -d ".svelte-kit" ] || [ ! -f ".svelte-kit/tsconfig.json" ]; then
    echo "📝 生成 SvelteKit 配置..."
    npx svelte-kit sync &>/dev/null || true
fi

# 解析参数（支持 --polling）
VITE_ARGS=()
USE_POLLING=false

for arg in "$@"; do
    if [[ "$arg" == "--polling" ]]; then
        USE_POLLING=true
    elif [[ "$arg" == "--dev" ]]; then
        # 忽略 --dev 参数，由环境变量控制
        :
    else
        VITE_ARGS+=("$arg")
    fi
done

# 确定是否启用轮询：环境变量 > CLI 参数 > 自动检测
if [ -n "${VITE_USE_POLLING}" ]; then
    USE_POLLING="${VITE_USE_POLLING}"
elif [ "$USE_POLLING" = false ] && [ "$(uname)" = "Linux" ]; then
    # 自动为 Linux 启用轮询（兼容 WSL/Docker）
    USE_POLLING=true
    echo "ℹ️  自动启用轮询模式（Linux 环境）"
fi

# 设置环境变量给 Vite
if [ "$USE_POLLING" = true ]; then
    export VITE_USE_POLLING=true
    export CHOKIDAR_USEPOLLING=true  # 兼容旧工具
fi

# 函数：检查端口是否可用
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    else
        if nc -z localhost $port 2>/dev/null; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    fi
}

# 函数：查找可用端口（只输出端口号到stdout）
find_available_port() {
    local start_port=$1
    local max_attempts=${2:-10}
    local port=$start_port

    for ((i=0; i<max_attempts; i++)); do
        if check_port $port; then
            if [ $i -gt 0 ]; then
                echo "✅ 端口 $port 可用（已尝试 $i 个端口）" >&2
            fi
            echo "$port"
            return 0
        fi

        if [ $i -eq 0 ]; then
            echo "⚠️  端口 $port 被占用，正在查找可用端口..." >&2
        fi
        ((port++))
    done

    echo "❌ 无法找到可用端口（已尝试 $max_attempts 个端口）" >&2
    return 1
}

# 获取后端端口（优先使用环境变量）
echo "🔍 检查后端端口..."
if [ -n "$BACKEND_PORT" ]; then
    # 如果环境变量有后端端口，直接使用
    # 如果被占用，说明后端正在运行，这是正常的
    if ! check_port $BACKEND_PORT 2>/dev/null; then
        echo "✅ 后端端口: $BACKEND_PORT (后端服务已运行)"
    else
        echo "✅ 后端端口: $BACKEND_PORT"
    fi
else
    # 没有环境变量时检测
    BACKEND_PORT=$(find_available_port 8000 10)
    if ! [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]]; then
        echo "❌ 无法找到可用的后端端口，使用默认 8000"
        BACKEND_PORT=8000
    fi
    echo "✅ 后端端口: $BACKEND_PORT"
fi

# 获取前端端口（优先使用环境变量，如果没有则自动检测）
echo "🔍 检查前端端口..."
FRONTEND_PORT=${EXPOSE_PORT:-5173}
if ! check_port $FRONTEND_PORT 2>/dev/null; then
    echo "⚠️  端口 $FRONTEND_PORT 被占用，正在查找可用端口..."
    FRONTEND_PORT=$(find_available_port 5173 10)
    if ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]]; then
        echo "❌ 无法找到可用的前端端口，使用默认 5173"
        FRONTEND_PORT=5173
    fi
else
    echo "✅ 前端端口: $FRONTEND_PORT"
fi

if [ "$DEV_MODE" = true ]; then
    echo "🌐 启动前端开发服务器..."
    echo "📖 代理后端: http://localhost:$BACKEND_PORT"
    echo "🔗 访问地址: http://localhost:$FRONTEND_PORT"
    echo "🔄 HMR (热重载): 已启用"
else
    echo "🌐 启动前端服务器..."
    echo "📖 代理后端: http://localhost:$BACKEND_PORT"
    echo "🔗 访问地址: http://localhost:$FRONTEND_PORT"
    echo "🔄 HMR (热重载): 已禁用"
fi

if [ "$USE_POLLING" = true ]; then
    echo "📡 文件监听: 轮询模式 (Polling) — 兼容 WSL/Docker"
else
    echo "📡 文件监听: 原生模式 (Native)"
fi
echo "💡 按 Ctrl+C 停止服务"
echo ""

echo "🔧 接收到的原始参数: $*"
echo "🔧 传递给 Vite 的参数: ${VITE_ARGS[*]}"

# 设置Vite端口
export VITE_PORT=$FRONTEND_PORT

# 启动 Vite
npx vite dev --port $FRONTEND_PORT "${VITE_ARGS[@]}"