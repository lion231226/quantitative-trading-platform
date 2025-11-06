#!/bin/bash

# 完整部署脚本 - 包含环境检查 - 修复版
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}  量化交易平台一键部署脚本          ${NC}"
    echo -e "${BLUE}  Enhanced Linux/Mac Launcher      ${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

# 检查必需环境
check_environment() {
    print_message "检查运行环境..."

    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_message "✓ Python 版本: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        print_message "✓ Python 版本: $PYTHON_VERSION"
    else
        print_error "✗ Python 3 未安装，请先安装 Python 3.11+"
        exit 1
    fi

    # 检查Python版本
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        print_error "✗ Python 版本过低，需要 3.11+，当前版本: $PYTHON_VERSION"
        exit 1
    fi

    # 检查 Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_message "✓ Node.js 版本: $NODE_VERSION"
    else
        print_error "✗ Node.js 未安装，请先安装 Node.js 18+"
        exit 1
    fi

    # 检查 npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        print_message "✓ npm 版本: $NPM_VERSION"
    else
        print_error "✗ npm 未安装"
        exit 1
    fi

    # 检查项目文件
    if [ ! -f "backend/requirements.txt" ]; then
        print_error "✗ backend/requirements.txt 不存在"
        print_error "请确保在正确的项目目录中运行此脚本"
        exit 1
    fi

    if [ ! -f "frontend/package.json" ]; then
        print_error "✗ frontend/package.json 不存在"
        print_error "请确保在正确的项目目录中运行此脚本"
        exit 1
    fi

    print_message "✅ 环境检查通过"
}

# 启动后端服务
start_backend() {
    print_message "启动后端服务..."

    # 确保在正确的目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"

    # 创建必要目录
    mkdir -p data logs temp

    cd backend

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_message "创建Python虚拟环境..."
        if command -v python3 &> /dev/null; then
            python3 -m venv venv
        else
            python -m venv venv
        fi

        if [ $? -ne 0 ]; then
            print_error "创建虚拟环境失败"
            print_error "请检查Python安装是否正确"
            exit 1
        fi
        print_message "✓ 虚拟环境创建成功"
    fi

    # 激活虚拟环境
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_message "✓ 虚拟环境激活成功"
    else
        print_error "无法激活虚拟环境"
        exit 1
    fi

    # 升级pip
    print_message "升级pip..."
    pip install --upgrade pip --quiet
    if [ $? -ne 0 ]; then
        print_warning "pip升级失败，继续使用现有版本"
    fi

    # 安装依赖
    print_message "安装Python依赖..."
    print_warning "首次安装可能需要几分钟，请耐心等待..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "Python依赖安装失败"
        print_error "请检查网络连接和Python版本"
        exit 1
    fi
    print_message "✓ Python依赖安装完成"

    # 创建环境变量文件
    if [ ! -f ".env" ]; then
        print_message "创建后端环境配置..."
        cat > .env << EOF
# 后端配置
DATABASE_URL=sqlite:///./../data/quant_trading.db
PYTHONPATH=$(pwd)
LOG_LEVEL=INFO

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# AKShare配置
AKSHARE_TIMEOUT=30
AKSHARE_RETRY=3
EOF
        print_message "✓ 环境配置创建完成"
    fi

    # 启动后端服务
    print_message "启动FastAPI服务..."
    print_message "后端服务地址: http://localhost:8000"
    print_message "API文档地址: http://localhost:8000/docs"

    # 后台启动后端服务
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID" > ../logs/backend.pid

    cd ..
    print_message "后端服务启动中: http://localhost:8000"
}

# 启动前端服务
start_frontend() {
    print_message "启动前端服务..."
    cd frontend

    # 安装依赖
    if [ ! -d "node_modules" ]; then
        print_message "安装Node.js依赖..."
        print_warning "首次安装可能需要几分钟，请耐心等待..."
        npm install
        if [ $? -ne 0 ]; then
            print_error "Node.js依赖安装失败"
            print_error "请检查网络连接和Node.js版本"
            exit 1
        fi
        print_message "✓ Node.js依赖安装完成"
    fi

    # 创建环境变量文件
    if [ ! -f ".env.local" ]; then
        print_message "创建前端环境配置..."
        cat > .env.local << EOF
# 前端配置
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_NODE_ENV=development
NEXT_PUBLIC_APP_NAME=量化交易平台
NEXT_PUBLIC_APP_VERSION=1.0.0

# API配置
NEXT_PUBLIC_API_TIMEOUT=30000
NEXT_PUBLIC_API_RETRY=3
EOF
        print_message "✓ 前端环境配置创建完成"
    fi

    # 启动前端服务
    print_message "启动Next.js服务..."
    print_message "前端服务地址: http://localhost:3000"

    # 后台启动前端服务
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID" > ../logs/frontend.pid

    cd ..
    print_message "前端服务启动中: http://localhost:3000"
}

# 检查服务状态
check_services() {
    print_message "等待服务启动..."
    sleep 15

    # 检查后端
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_message "✓ 后端服务正常"
            break
        elif [ $i -eq 30 ]; then
            print_warning "⚠ 后端服务启动超时，请检查日志"
            print_error "请运行: tail -f logs/backend.log"
        else
            sleep 2
        fi
    done

    # 检查前端
    for i in {1..30}; do
        if curl -f http://localhost:3000 &> /dev/null; then
            print_message "✓ 前端服务正常"
            break
        elif [ $i -eq 30 ]; then
            print_warning "⚠ 前端服务启动超时，请检查日志"
            print_error "请运行: tail -f logs/frontend.log"
        else
            sleep 2
        fi
    done
}

# 显示访问信息
show_info() {
    print_header
    echo -e "${GREEN}🎉 量化交易平台启动成功！${NC}"
    echo ""
    echo -e "${BLUE}服务访问地址：${NC}"
    echo -e "  • 前端应用: ${YELLOW}http://localhost:3000${NC}"
    echo -e "  • 后端API:  ${YELLOW}http://localhost:8000${NC}"
    echo -e "  • API文档:  ${YELLOW}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${BLUE}管理命令：${NC}"
    echo -e "  • 查看后端日志: ${YELLOW}tail -f logs/backend.log${NC}"
    echo -e "  • 查看前端日志: ${YELLOW}tail -f logs/frontend.log${NC}"
    echo -e "  • 停止服务: ${YELLOW}./quick-start-fixed.sh stop${NC}"
    echo -e "  • 查看服务状态: ${YELLOW}./quick-start-fixed.sh status${NC}"
    echo ""
    echo -e "${YELLOW}注意: 首次启动可能需要较长时间来安装依赖${NC}"
    echo ""
}

# 停止服务
stop_services() {
    print_message "停止所有服务..."

    # 停止后端
    if [ -f "logs/backend.pid" ]; then
        BACKEND_PID=$(cat logs/backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID
            print_message "后端服务已停止"
        fi
        rm -f logs/backend.pid
    fi

    # 停止前端
    if [ -f "logs/frontend.pid" ]; then
        FRONTEND_PID=$(cat logs/frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            print_message "前端服务已停止"
        fi
        rm -f logs/frontend.pid
    fi

    # 强制停止相关进程
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true

    print_message "服务已停止"
}

# 显示服务状态
show_status() {
    print_message "检查服务状态..."

    # 检查后端进程
    if pgrep -f "uvicorn main:app" > /dev/null; then
        echo -e "${GREEN}✓ 后端服务运行中${NC}"
        echo -e "  访问地址: ${YELLOW}http://localhost:8000${NC}"
    else
        echo -e "${RED}✗ 后端服务未运行${NC}"
    fi

    # 检查前端进程
    if pgrep -f "next" > /dev/null; then
        echo -e "${GREEN}✓ 前端服务运行中${NC}"
        echo -e "  访问地址: ${YELLOW}http://localhost:3000${NC}"
    else
        echo -e "${RED}✗ 前端服务未运行${NC}"
    fi
}

# 主函数
main() {
    print_header

    case "${1:-start}" in
        start)
            check_environment
            start_backend
            start_frontend
            check_services
            show_info
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_backend
            start_frontend
            check_services
            show_info
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动所有服务"
            echo "  stop    - 停止所有服务"
            echo "  restart - 重启所有服务"
            echo "  status  - 查看服务状态"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"