#!/bin/bash
# start.sh - 一键启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}  量化交易平台 Docker 启动脚本     ${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    print_message "Docker 环境检查通过"
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."
    mkdir -p data logs nginx/ssl
    print_message "目录创建完成"
}

# 生成默认配置文件
generate_configs() {
    print_message "生成配置文件..."

    # 生成 nginx.conf
    if [ ! -f nginx/nginx.conf ]; then
        cat > nginx/nginx.conf << 'NGINXEOF'
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;

        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location / {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
NGINXEOF
    fi

    # 生成 .env 文件
    if [ ! -f .env ]; then
        cat > .env << 'ENVEOF'
# 后端配置
DATABASE_URL=sqlite:///./db/quant_trading.db
REDIS_URL=redis://redis:6379
PYTHONPATH=/app
LOG_LEVEL=INFO

# 前端配置
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development

# 端口配置
FRONTEND_PORT=3000
BACKEND_PORT=8000
REDIS_PORT=6379
NGINX_PORT=80
ENVEOF
    fi

    print_message "配置文件生成完成"
}

# 停止现有服务
stop_services() {
    print_message "停止现有服务..."
    docker-compose down || true
    docker system prune -f || true
}

# 构建并启动服务
start_services() {
    print_message "构建并启动服务..."
    docker-compose up --build -d

    print_message "等待服务启动..."
    sleep 10
}

# 检查服务状态
check_services() {
    print_message "检查服务状态..."

    # 检查各个服务
    services=("redis" "backend" "frontend")

    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "${service}.*Up"; then
            print_message "$service 服务运行正常"
        else
            print_error "$service 服务启动失败"
            docker-compose logs $service
            return 1
        fi
    done
}

# 显示访问信息
show_access_info() {
    print_header
    echo -e "${GREEN}🎉 量化交易平台启动成功！${NC}"
    echo ""
    echo -e "${BLUE}服务访问地址：${NC}"
    echo -e "  • 前端应用: ${YELLOW}http://localhost:3000${NC}"
    echo -e "  • 后端API:  ${YELLOW}http://localhost:8000${NC}"
    echo -e "  • API文档:  ${YELLOW}http://localhost:8000/docs${NC}"
    echo -e "  • Redis:    ${YELLOW}localhost:6379${NC}"
    echo ""
    echo -e "${BLUE}管理命令：${NC}"
    echo -e "  • 查看日志: ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  • 停止服务: ${YELLOW}docker-compose down${NC}"
    echo -e "  • 重启服务: ${YELLOW}docker-compose restart${NC}"
    echo -e "  • 进入容器: ${YELLOW}docker-compose exec backend bash${NC}"
    echo ""
}

# 主函数
main() {
    print_header

    # 检查参数
    case "${1:-start}" in
        start)
            check_docker
            create_directories
            generate_configs
            stop_services
            start_services
            check_services
            show_access_info
            ;;
        stop)
            docker-compose down
            print_message "服务已停止"
            ;;
        restart)
            docker-compose restart
            print_message "服务已重启"
            ;;
        logs)
            docker-compose logs -f
            ;;
        status)
            docker-compose ps
            ;;
        clean)
            print_warning "这将删除所有容器、镜像和数据卷"
            read -p "确认删除? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker-compose down -v --rmi all
                docker system prune -af
                print_message "清理完成"
            fi
            ;;
        *)
            echo "用法: $0 {start|stop|restart|logs|status|clean}"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
