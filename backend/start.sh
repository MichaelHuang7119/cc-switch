#!/bin/bash

# CC Switch - 后端启动脚本

# 函数：加载.env文件
load_env() {
    # 先尝试加载backend目录的.env
    local backend_env="./.env"
    # 如果没有，再加载项目根目录的.env
    local root_env="../.env"

    # 加载backend的.env
    if [ -f "$backend_env" ]; then
        echo "📄 加载环境变量: $backend_env"
        set -a
        source "$backend_env"
        set +a
    # 加载项目根目录的.env
    elif [ -f "$root_env" ]; then
        echo "📄 加载环境变量: $root_env"
        set -a
        source "$root_env"
        set +a
    fi
}

# 确保在 backend 目录
cd "$(dirname "$0")" || { echo "❌ 无法进入脚本所在目录"; exit 1; }

# 加载环境变量
load_env

# 检查是否在正确的目录
if [ ! -f "start_proxy.py" ]; then
    echo "❌ 错误: 未找到 start_proxy.py，请确保在 backend 目录运行此脚本"
    echo "   当前目录: $(pwd)"
    exit 1
fi

# 检查 Python 3 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查是否包含 --dev 或 --reload 参数
DEV_MODE=false
RELOAD_PARAM=""
LOG_LEVEL="info"  # 默认日志级别为 info

for arg in "$@"; do
    if [[ "$arg" == "--dev" ]] || [[ "$arg" == "--reload" ]]; then
        DEV_MODE=true
        RELOAD_PARAM="--reload"
        LOG_LEVEL="debug"  # 开发模式使用 debug 日志级别
        break
    fi
done

# 设置日志级别环境变量
export LOG_LEVEL

echo "🚀 CC Switch - 启动后端服务..."
echo ""

# 使用环境变量中的端口（如果设置了）
if [ -n "$BACKEND_PORT" ]; then
    export PORT=$BACKEND_PORT
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv || { echo "❌ 虚拟环境创建失败"; exit 1; }
fi

# 激活虚拟环境
source venv/bin/activate || { echo "❌ 无法激活虚拟环境"; exit 1; }

# 升级 pip（可选但推荐）
python -m pip install --upgrade pip -q

# 安装依赖
if [ -f "requirements.txt" ]; then
    echo "📥 安装或更新依赖..."
    pip install -q -r requirements.txt || { echo "❌ 依赖安装失败"; exit 1; }
else
    echo "⚠️  警告: 未找到 requirements.txt，跳过依赖安装"
fi

echo ""

# 根据模式显示不同信息
if [ "$DEV_MODE" = true ]; then
    echo "🔧 开发模式 - 启用自动重载 + DEBUG 日志"
    echo "   日志级别: DEBUG (详细日志)"
    echo "   使用 --no-reload 禁用重载"
else
    echo "🔧 生产模式 - 禁用自动重载 + INFO 日志"
    echo "   日志级别: INFO (仅重要信息)"
    echo "   使用 --dev 或 --reload 启用热重载和 DEBUG 日志"
fi

# 获取实际使用的端口
FINAL_PORT=${PORT:-8000}
echo "   服务地址: http://localhost:$FINAL_PORT"
echo "   API 文档: http://localhost:$FINAL_PORT/docs"
echo "   日志级别: $LOG_LEVEL"
echo "   按 Ctrl+C 停止服务"
echo ""

# 处理参数，移除 --dev 参数，保留其他参数
FINAL_ARGS=()
for arg in "$@"; do
    if [[ "$arg" != "--dev" ]]; then
        FINAL_ARGS+=("$arg")
    fi
done

# 添加日志级别参数
FINAL_ARGS+=("--log-level")
FINAL_ARGS+=("$LOG_LEVEL")

# 将参数传递给 Python 启动脚本
exec python start_proxy.py "${FINAL_ARGS[@]}"