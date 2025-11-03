#!/bin/bash

# 量化交易平台部署脚本
# 作者: 自动化部署系统
# 版本: 1.0.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置变量
PROJECT_NAME="quant-trading-platform"
BACKUP_DIR="/opt/backups/${PROJECT_NAME}"
LOG_FILE="/var/log/${PROJECT_NAME}/deploy.log"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 记录日志
exec > >(tee -a "$LOG_FILE")
exec 2>&1

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查端口占用
    local ports=(80 443 3000 8000 6379)
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warning "端口 $port 已被占用"
        fi
    done

    log_success "依赖检查完成"
}

# 环境配置
setup_environment() {
    log_info "设置部署环境..."

    # 创建必要的目录
    mkdir -p "$BACKUP_DIR"
    mkdir -p nginx/ssl
    mkdir -p data/{redis,backend,logs}

    # 设置权限
    chmod 755 nginx/ssl
    chmod 755 data

    # 创建环境变量文件（如果不存在）
    if [ ! -f "$ENV_FILE" ]; then
        log_info "创建环境变量文件..."
        cat > "$ENV_FILE" << EOF
# 应用配置
APP_NAME=量化交易平台
APP_VERSION=1.0.0
ENVIRONMENT=production

# 数据库配置
DATABASE_URL=sqlite:///./data/app.db

# Redis配置
REDIS_URL=redis://redis:6379/0

# 后端配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
LOG_LEVEL=info

# 前端配置
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=量化交易平台
NEXT_PUBLIC_APP_VERSION=1.0.0

# SSL配置（如果需要）
SSL_CERT_PATH=./nginx/ssl/cert.pem
SSL_KEY_PATH=./nginx/ssl/key.pem

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
EOF
        log_success "环境变量文件创建完成"
    fi

    log_success "环境设置完成"
}

# 备份现有数据
backup_data() {
    log_info "备份现有数据..."

    local backup_name="${PROJECT_NAME}_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$backup_path"

    # 备份数据库
    if [ -f "data/backend/app.db" ]; then
        cp data/backend/app.db "$backup_path/"
        log_info "数据库备份完成"
    fi

    # 备份配置文件
    if [ -f "$COMPOSE_FILE" ]; then
        cp "$COMPOSE_FILE" "$backup_path/"
    fi

    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$backup_path/"
    fi

    # 备份Nginx配置
    if [ -d "nginx" ]; then
        cp -r nginx "$backup_path/"
    fi

    log_success "数据备份完成: $backup_path"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."

    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t ${PROJECT_NAME}-backend:latest ./backend

    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -t ${PROJECT_NAME}-frontend:latest ./frontend

    log_success "镜像构建完成"
}

# 停止现有服务
stop_services() {
    log_info "停止现有服务..."

    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    fi

    log_success "服务停止完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 启动基础设施服务
    log_info "启动Redis服务..."
    docker-compose -f "$COMPOSE_FILE" up -d redis

    # 等待Redis启动
    log_info "等待Redis启动..."
    sleep 10

    # 启动后端服务
    log_info "启动后端服务..."
    docker-compose -f "$COMPOSE_FILE" up -d backend

    # 等待后端启动
    log_info "等待后端服务启动..."
    sleep 20

    # 检查后端健康状态
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "后端服务启动成功"
            break
        fi
        attempt=$((attempt + 1))
        log_info "等待后端服务启动... ($attempt/$max_attempts)"
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "后端服务启动失败"
        docker-compose -f "$COMPOSE_FILE" logs backend
        exit 1
    fi

    # 启动前端服务
    log_info "启动前端服务..."
    docker-compose -f "$COMPOSE_FILE" up -d frontend

    # 等待前端启动
    sleep 10

    # 启动Nginx
    log_info "启动Nginx服务..."
    docker-compose -f "$COMPOSE_FILE" up -d nginx

    log_success "所有服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    local services=("backend:8000" "frontend:3000" "nginx:80")
    local all_healthy=true

    for service in "${services[@]}"; do
        local service_name=$(echo $service | cut -d: -f1)
        local port=$(echo $service | cut -d: -f2)

        case $service_name in
            "backend")
                if curl -f http://localhost:$port/health &> /dev/null; then
                    log_success "$service_name 服务健康"
                else
                    log_error "$service_name 服务不健康"
                    all_healthy=false
                fi
                ;;
            "frontend"|"nginx")
                if curl -f http://localhost:$port &> /dev/null; then
                    log_success "$service_name 服务健康"
                else
                    log_error "$service_name 服务不健康"
                    all_healthy=false
                fi
                ;;
        esac
    done

    if [ "$all_healthy" = true ]; then
        log_success "所有服务健康检查通过"
    else
        log_error "健康检查失败"
        docker-compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# 清理资源
cleanup() {
    log_info "清理未使用的Docker资源..."

    # 清理未使用的镜像
    docker image prune -f

    # 清理未使用的容器
    docker container prune -f

    # 清理未使用的网络
    docker network prune -f

    log_success "清理完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose -f "$COMPOSE_FILE" ps

    echo ""
    log_info "服务访问地址:"
    echo "  前端应用: http://localhost"
    echo "  API接口: http://localhost/api/v1"
    echo "  健康检查: http://localhost/health"
}

# 主函数
main() {
    local start_time=$(date +%s)

    log_info "开始部署 ${PROJECT_NAME}..."
    echo "=================================================="

    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        log_warning "建议使用root用户运行此脚本"
    fi

    # 执行部署步骤
    check_dependencies
    setup_environment
    backup_data
    stop_services
    build_images
    start_services
    health_check
    cleanup
    show_status

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "=================================================="
    log_success "部署完成! 耗时: ${duration}秒"
    log_info "部署日志: $LOG_FILE"

    # 显示后续操作提示
    echo ""
    log_info "后续操作:"
    echo "1. 查看服务状态: docker-compose -f $COMPOSE_FILE ps"
    echo "2. 查看服务日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "3. 停止服务: docker-compose -f $COMPOSE_FILE down"
    echo "4. 重启服务: docker-compose -f $COMPOSE_FILE restart"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志: $LOG_FILE"; exit 1' ERR

# 执行主函数
main "$@"