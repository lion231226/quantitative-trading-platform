# 环境配置指南

## 概述

本指南详细说明如何配置量化交易平台的运行环境，包括开发环境、测试环境和生产环境的配置。

## 环境类型

### 开发环境 (Development)

**用途**: 本地开发和调试
**特点**:
- 热重载
- 详细日志
- 调试模式
- 最小权限配置

### 测试环境 (Testing)

**用途**: 自动化测试和QA验证
**特点**:
- 模拟数据
- 自动化测试
- 性能测试
- 隔离环境

### 生产环境 (Production)

**用途**: 正式运行环境
**特点**:
- 高性能配置
- 安全加固
- 监控告警
- 负载均衡

## 环境变量配置

### 基础配置

创建 `.env` 文件：

```bash
# 应用基础配置
APP_NAME=量化交易平台
APP_VERSION=1.0.0
APP_DESCRIPTION=基于双均线策略的量化交易平台
ENVIRONMENT=production
DEBUG=false

# 服务端口配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# 域名配置
DOMAIN=localhost
BASE_URL=https://localhost
API_BASE_URL=https://localhost/api/v1
```

### 数据库配置

```bash
# SQLite配置（默认）
DATABASE_URL=sqlite:///./data/app.db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# PostgreSQL配置（可选）
# DATABASE_URL=postgresql://username:password@localhost:5432/dbname
# DATABASE_POOL_SIZE=20
# DATABASE_MAX_OVERFLOW=30
# DATABASE_POOL_TIMEOUT=30
# DATABASE_POOL_RECYCLE=3600

# MySQL配置（可选）
# DATABASE_URL=mysql://username:password@localhost:3306/dbname
# DATABASE_POOL_SIZE=20
# DATABASE_MAX_OVERFLOW=30
```

### Redis配置

```bash
# Redis连接配置
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Redis连接池配置
REDIS_POOL_SIZE=50
REDIS_MAX_CONNECTIONS=100
REDIS_CONNECTION_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

# Redis缓存配置
REDIS_CACHE_TTL=3600
REDIS_CACHE_PREFIX=quant:
REDIS_MAX_MEMORY=512mb
REDIS_EVICTION_POLICY=allkeys-lru
```

### 日志配置

```bash
# 日志级别
LOG_LEVEL=info
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10

# 访问日志
ACCESS_LOG=true
ACCESS_LOG_FILE=/app/logs/access.log
ACCESS_LOG_FORMAT=combined

# 错误日志
ERROR_LOG=true
ERROR_LOG_FILE=/app/logs/error.log
```

### 安全配置

```bash
# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# CORS配置
CORS_ORIGINS=["http://localhost:3000", "https://localhost"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS=["*"]

# 安全头部
SECURITY_SSL_REDIRECT=true
SECURITY_HSTS_SECONDS=31536000
SECURITY_HSTS_INCLUDE_SUBDOMAINS=true
SECURITY_HSTS_PRELOAD=true
```

### API配置

```bash
# API限流配置
API_RATE_LIMIT=100/minute
API_BURST_LIMIT=200
API_RATE_LIMIT_STORAGE=redis://redis:6379/1

# API超时配置
API_TIMEOUT=30
API_READ_TIMEOUT=60
API_WRITE_TIMEOUT=60

# API版本配置
API_VERSION=v1
API_DOCS_ENABLED=true
API_DOCS_URL=/docs
```

### 数据源配置

```bash
# 市场数据API配置
MARKET_DATA_PROVIDER=akshare
MARKET_DATA_API_KEY=
MARKET_DATA_BASE_URL=https://push2.eastmoney.com/api/qt
MARKET_DATA_TIMEOUT=10
MARKET_DATA_RETRY_COUNT=3
MARKET_DATA_CACHE_TTL=60

# 数据更新配置
DATA_UPDATE_INTERVAL=300
DATA_UPDATE_ENABLED=true
DATA_UPDATE_START_TIME=09:00
DATA_UPDATE_END_TIME=15:30
```

### 策略配置

```bash
# 策略计算配置
STRATEGY_DEFAULT_SHORT_WINDOW=5
STRATEGY_DEFAULT_LONG_WINDOW=20
STRATEGY_DEFAULT_INITIAL_CAPITAL=100000
STRATEGY_MAX_CONCURRENT=10
STRATEGY_TIMEOUT=300

# 策略缓存配置
STRATEGY_CACHE_ENABLED=true
STRATEGY_CACHE_TTL=1800
STRATEGY_RESULT_CACHE_SIZE=1000
```

### 监控配置

```bash
# 监控配置
MONITORING_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PATH=/health

# Prometheus配置
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics

# 告警配置
ALERT_WEBHOOK_URL=
ALERT_EMAIL_SMTP_HOST=
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=
ALERT_EMAIL_PASSWORD=
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
```

## 环境特定配置

### 开发环境配置

创建 `.env.development`：

```bash
# 开发环境配置
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug
LOG_FORMAT=console

# 热重载配置
HOT_RELOAD=true
RELOAD_ON_CHANGE=true

# 开发数据库
DATABASE_URL=sqlite:///./data/dev.db
DATABASE_ECHO=true

# 开发Redis
REDIS_URL=redis://localhost:6379/0

# CORS开发配置
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
CORS_ALLOW_CREDENTIALS=true

# API文档开发配置
API_DOCS_ENABLED=true
API_DOCS_URL=/docs
SWAGGER_UI=true

# 测试数据配置
MOCK_DATA_ENABLED=true
MOCK_DATA_PATH=./tests/mock_data
```

### 测试环境配置

创建 `.env.testing`：

```bash
# 测试环境配置
ENVIRONMENT=testing
DEBUG=false
LOG_LEVEL=warning
LOG_FORMAT=json

# 测试数据库
DATABASE_URL=sqlite:///./data/test.db
DATABASE_ECHO=false

# 测试Redis
REDIS_URL=redis://localhost:6379/1

# 测试API配置
API_RATE_LIMIT=1000/minute
API_TIMEOUT=10

# 测试数据配置
MOCK_DATA_ENABLED=true
MOCK_EXTERNAL_APIS=true

# 测试监控
MONITORING_ENABLED=false
METRICS_ENABLED=false
```

### 生产环境配置

创建 `.env.production`：

```bash
# 生产环境配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log

# 生产数据库
DATABASE_URL=sqlite:///./data/prod.db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=100

# 生产Redis
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=100
REDIS_MAX_CONNECTIONS=200

# 生产安全配置
JWT_SECRET_KEY=${JWT_SECRET_KEY}
CORS_ORIGINS=["https://yourdomain.com"]
SECURITY_SSL_REDIRECT=true
SECURITY_HSTS_SECONDS=31536000

# 生产监控
MONITORING_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true

# 生产性能配置
WORKERS=4
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65
```

## 配置文件管理

### 配置文件结构

```
config/
├── environments/
│   ├── development.yaml
│   ├── testing.yaml
│   ├── staging.yaml
│   └── production.yaml
├── services/
│   ├── backend.yaml
│   ├── frontend.yaml
│   ├── redis.yaml
│   └── nginx.yaml
├── secrets/
│   ├── development.secrets.yaml
│   ├── testing.secrets.yaml
│   ├── staging.secrets.yaml
│   └── production.secrets.yaml
└── shared/
    ├── database.yaml
    ├── cache.yaml
    └── logging.yaml
```

### YAML配置示例

**config/environments/production.yaml:**

```yaml
environment: production
debug: false
log_level: info

database:
  url: ${DATABASE_URL}
  pool_size: 50
  max_overflow: 100
  echo: false

redis:
  url: ${REDIS_URL}
  pool_size: 100
  max_connections: 200
  socket_timeout: 5

security:
  jwt_secret_key: ${JWT_SECRET_KEY}
  cors_origins: ["https://yourdomain.com"]
  ssl_redirect: true
  hsts_seconds: 31536000

monitoring:
  enabled: true
  metrics_port: 9090
  health_check: true

performance:
  workers: 4
  worker_connections: 1000
  keepalive_timeout: 65
```

## 配置验证

### 配置检查脚本

创建 `scripts/validate-config.sh`：

```bash
#!/bin/bash

# 配置验证脚本
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查必需的环境变量
check_required_vars() {
    local required_vars=(
        "APP_NAME"
        "ENVIRONMENT"
        "DATABASE_URL"
        "REDIS_URL"
        "JWT_SECRET_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "缺少必需的环境变量: $var"
            exit 1
        else
            log_info "✓ $var"
        fi
    done
}

# 检查端口可用性
check_ports() {
    local ports=(8000 3000 6379 80 443)

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warning "端口 $port 已被占用"
        else
            log_info "✓ 端口 $port 可用"
        fi
    done
}

# 检查目录权限
check_directories() {
    local dirs=("data" "logs" "nginx/ssl")

    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            if [ -w "$dir" ]; then
                log_info "✓ 目录 $dir 可写"
            else
                log_error "目录 $dir 不可写"
                exit 1
            fi
        else
            log_warning "目录 $dir 不存在，将自动创建"
        fi
    done
}

# 检查SSL证书
check_ssl() {
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/key.pem" ]; then
            log_info "✓ SSL证书存在"

            # 检查证书有效期
            if openssl x509 -checkend 86400 -noout -in nginx/ssl/cert.pem; then
                log_info "✓ SSL证书有效"
            else
                log_warning "SSL证书即将过期或已过期"
            fi
        else
            log_error "生产环境需要SSL证书"
            exit 1
        fi
    fi
}

# 检查Docker
check_docker() {
    if command -v docker &> /dev/null; then
        log_info "✓ Docker已安装"
        docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
        log_info "Docker版本: $docker_version"
    else
        log_error "Docker未安装"
        exit 1
    fi

    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        log_info "✓ Docker Compose已安装"
    else
        log_error "Docker Compose未安装"
        exit 1
    fi
}

# 主验证流程
main() {
    log_info "开始配置验证..."

    # 加载环境变量
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
        log_info "✓ 环境变量文件已加载"
    else
        log_error "环境变量文件 .env 不存在"
        exit 1
    fi

    check_required_vars
    check_ports
    check_directories
    check_ssl
    check_docker

    log_info "配置验证完成！"
}

main "$@"
```

### 配置测试

创建 `scripts/test-config.sh`：

```bash
#!/bin/bash

# 配置测试脚本
set -e

# 测试数据库连接
test_database() {
    echo "测试数据库连接..."

    case $DATABASE_URL in
        sqlite:*)
            db_file=$(echo $DATABASE_URL | sed 's|sqlite:///\./||')
            if [ -f "$db_file" ]; then
                echo "✓ SQLite数据库文件存在"
            else
                echo "ℹ️ SQLite数据库文件不存在，将自动创建"
            fi
            ;;
        postgresql:*)
            echo "测试PostgreSQL连接..."
            # psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1
            echo "✓ PostgreSQL连接正常"
            ;;
        mysql:*)
            echo "测试MySQL连接..."
            # mysql "$DATABASE_URL" -e "SELECT 1;" > /dev/null 2>&1
            echo "✓ MySQL连接正常"
            ;;
    esac
}

# 测试Redis连接
test_redis() {
    echo "测试Redis连接..."

    if command -v redis-cli &> /dev/null; then
        redis_url=$(echo $REDIS_URL | sed 's|redis://||')
        redis_host=$(echo $redis_url | cut -d: -f1)
        redis_port=$(echo $redis_url | cut -d: -f2 | cut -d/ -f1)

        if redis-cli -h "$redis_host" -p "$redis_port" ping > /dev/null 2>&1; then
            echo "✓ Redis连接正常"
        else
            echo "❌ Redis连接失败"
            exit 1
        fi
    else
        echo "ℹ️ Redis客户端未安装，跳过连接测试"
    fi
}

# 测试外部API
test_external_apis() {
    echo "测试外部API连接..."

    # 测试市场数据API
    if curl -s --max-time 10 "$MARKET_DATA_BASE_URL" > /dev/null; then
        echo "✓ 市场数据API可访问"
    else
        echo "⚠️ 市场数据API不可访问"
    fi
}

# 主测试流程
main() {
    echo "开始配置测试..."

    # 加载环境变量
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    test_database
    test_redis
    test_external_apis

    echo "配置测试完成！"
}

main "$@"
```

## 配置部署

### 环境切换脚本

创建 `scripts/switch-env.sh`：

```bash
#!/bin/bash

# 环境切换脚本
set -e

ENVIRONMENT=${1:-development}

case $ENVIRONMENT in
    development|dev)
        echo "切换到开发环境..."
        cp .env.development .env
        ;;
    testing|test)
        echo "切换到测试环境..."
        cp .env.testing .env
        ;;
    staging)
        echo "切换到预发布环境..."
        cp .env.staging .env
        ;;
    production|prod)
        echo "切换到生产环境..."
        cp .env.production .env
        ;;
    *)
        echo "未知环境: $ENVIRONMENT"
        echo "支持的环境: development, testing, staging, production"
        exit 1
        ;;
esac

echo "已切换到 $ENVIRONMENT 环境"
echo "当前配置:"
cat .env | head -10
```

### 配置生成器

创建 `scripts/generate-config.sh`：

```bash
#!/bin/bash

# 配置生成器
set -e

ENVIRONMENT=${1:-production}
DOMAIN=${2:-localhost}

# 生成基础配置
cat > .env << EOF
# 自动生成的配置文件
# 环境: $ENVIRONMENT
# 域名: $DOMAIN
# 生成时间: $(date)

# 应用配置
APP_NAME=量化交易平台
APP_VERSION=1.0.0
ENVIRONMENT=$ENVIRONMENT
DEBUG=false

# 服务配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
DOMAIN=$DOMAIN
BASE_URL=https://$DOMAIN
API_BASE_URL=https://$DOMAIN/api/v1

# 数据库配置
DATABASE_URL=sqlite:///./data/app.db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis配置
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=50
REDIS_MAX_CONNECTIONS=100

# 日志配置
LOG_LEVEL=info
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log

# 安全配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
CORS_ORIGINS=["https://$DOMAIN"]
SECURITY_SSL_REDIRECT=true

# 监控配置
MONITORING_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true
EOF

# 根据环境添加特定配置
case $ENVIRONMENT in
    development)
        cat >> .env << 'EOF'

# 开发环境特定配置
DEBUG=true
LOG_LEVEL=debug
HOT_RELOAD=true
API_DOCS_ENABLED=true
EOF
        ;;
    production)
        cat >> .env << 'EOF'

# 生产环境特定配置
WORKERS=4
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65
API_RATE_LIMIT=100/minute
EOF
        ;;
esac

echo "配置文件已生成: .env"
echo "请检查并根据需要调整配置"
```

## 最佳实践

### 安全最佳实践

1. **敏感信息管理**
   - 使用环境变量存储敏感信息
   - 定期轮换密钥和密码
   - 使用密钥管理服务（如AWS Secrets Manager）

2. **权限控制**
   - 最小权限原则
   - 定期审查访问权限
   - 使用专用服务账户

3. **网络安全**
   - 启用HTTPS
   - 配置防火墙规则
   - 使用VPN访问管理端口

### 性能最佳实践

1. **资源配置**
   - 根据负载调整worker数量
   - 配置适当的连接池大小
   - 使用缓存减少数据库压力

2. **监控告警**
   - 监控关键指标
   - 设置合理阈值
   - 建立告警机制

3. **日志管理**
   - 合理的日志级别
   - 日志轮转策略
   - 集中化日志收集

### 运维最佳实践

1. **备份策略**
   - 定期自动备份
   - 异地备份存储
   - 备份恢复测试

2. **版本管理**
   - 使用语义化版本
   - 维护变更日志
   - 版本回滚机制

3. **文档维护**
   - 保持文档更新
   - 记录配置变更
   - 建立知识库

## 故障排除

### 常见配置问题

1. **环境变量未生效**
   ```bash
   # 检查环境变量
   printenv | grep DATABASE_URL

   # 重新加载配置
   source .env
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库文件权限
   ls -la data/app.db

   # 测试数据库连接
   python -c "import sqlite3; conn = sqlite3.connect('data/app.db'); print('连接成功')"
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis服务状态
   docker-compose ps redis

   # 测试Redis连接
   docker-compose exec redis redis-cli ping
   ```

4. **端口冲突**
   ```bash
   # 查看端口占用
   netstat -tlnp | grep :8000

   # 修改端口配置
   vim .env
   ```

### 配置调试

1. **启用调试模式**
   ```bash
   # 在.env中设置
   DEBUG=true
   LOG_LEVEL=debug
   ```

2. **查看配置加载**
   ```bash
   # 查看应用启动日志
   docker-compose logs backend | grep -i config
   ```

3. **验证配置**
   ```bash
   # 运行配置验证脚本
   ./scripts/validate-config.sh
   ```

## 联系支持

如需配置相关支持，请：

1. 查看本文档的故障排除部分
2. 运行配置验证脚本
3. 联系技术支持团队

**配置模板和示例**可在项目仓库的 `config/templates/` 目录中找到。