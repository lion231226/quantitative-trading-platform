#!/bin/bash

# 本地部署脚本 - 不依赖Docker
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}   量化交易平台本地部署脚本        ${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

# 启动后端服务
start_backend() {
    print_message "启动后端服务..."
    cd backend
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_message "创建Python虚拟环境..."
        python -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    print_message "安装Python依赖..."
    pip install -r requirements.txt
    
    # 启动后端服务
    print_message "启动FastAPI服务..."
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
    
    cd ..
    print_message "后端服务已启动: http://localhost:8000"
}

# 启动前端服务
start_frontend() {
    print_message "启动前端服务..."
    cd frontend
    
    # 安装依赖
    if [ ! -d "node_modules" ]; then
        print_message "安装Node.js依赖..."
        npm install
    fi
    
    # 启动前端服务
    print_message "启动Next.js服务..."
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    
    cd ..
    print_message "前端服务已启动: http://localhost:3000"
}

# 检查服务状态
check_services() {
    print_message "检查服务状态..."
    sleep 5
    
    # 检查后端
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_message "✓ 后端服务正常"
    else
        print_message "⚠ 后端服务启动中..."
    fi
    
    # 检查前端
    if curl -f http://localhost:3000 &> /dev/null; then
        print_message "✓ 前端服务正常"
    else
        print_message "⚠ 前端服务启动中..."
    fi
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
    echo -e "  • 查看日志: ${YELLOW}tail -f logs/backend.log${NC}"
    echo -e "  • 停止服务: ${YELLOW}pkill -f uvicorn${NC} && ${YELLOW}pkill -f next-server${NC}"
    echo ""
}

# 主函数
main() {
    print_header
    
    # 创建日志目录
    mkdir -p logs
    
    case "${1:-start}" in
        start)
            start_backend
            start_frontend
            check_services
            show_info
            ;;
        stop)
            pkill -f uvicorn || true
            pkill -f next-server || true
            print_message "服务已停止"
            ;;
        status)
            ps aux | grep -E "(uvicorn|next-server)" | grep -v grep
            ;;
        *)
            echo "用法: $0 {start|stop|status}"
            exit 1
            ;;
    esac
}

main "$@"
