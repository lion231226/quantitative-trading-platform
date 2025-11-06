# 配置指南

## 📋 目录

- [配置文件结构](#配置文件结构)
- [服务配置](#服务配置)
- [数据库配置](#数据库配置)
- [缓存配置](#缓存配置)
- [日志配置](#日志配置)
- [环境变量](#环境变量)
- [高级配置](#高级配置)
- [自定义示例](#自定义示例)

---

## 📁 配置文件结构

启动器使用分层配置系统，配置文件按优先级加载：

```
config/
├── config.yaml           # 默认配置
├── custom.yaml          # 用户自定义配置
├── development.yaml     # 开发环境配置
├── production.yaml      # 生产环境配置
└── local.yaml          # 本地覆盖配置（不提交到版本控制）
```

### 配置加载优先级

1. 命令行参数（最高优先级）
2. 环境变量
3. `local.yaml`
4. `custom.yaml`
5. 环境特定配置（development.yaml/production.yaml）
6. `config.yaml`（最低优先级）

---

## 🚀 服务配置

### 后端服务配置

```yaml
services:
  backend:
    # 基本配置
    host: "localhost"
    port: 8000
    auto_restart: true

    # 启动命令
    command: "uvicorn app.main:app --host {host} --port {port}"

    # 环境变量
    env_vars:
      DATABASE_URL: "sqlite:///data/trading_platform.db"
      REDIS_URL: "redis://localhost:6379"
      LOG_LEVEL: "INFO"

    # 健康检查
    health_check:
      endpoint: "/health"
      timeout: 30
      retries: 3

    # 资源限制
    resources:
      max_memory: "1GB"
      max_cpu: "80%"
```

### 前端服务配置

```yaml
services:
  frontend:
    # 基本配置
    host: "localhost"
    port: 3000
    auto_open_browser: true

    # 启动命令
    command: "npm run dev"

    # 环境变量
    env_vars:
      NEXT_PUBLIC_API_URL: "http://localhost:8000"
      NEXT_PUBLIC_WS_URL: "ws://localhost:8000/ws"
      NODE_ENV: "development"

    # 构建配置
    build:
      output_dir: "dist"
      minify: true
      source_map: false

    # 开发配置
    dev_server:
      hot_reload: true
      port: 3001
      proxy_api: true
```

### 服务依赖配置

```yaml
services:
  # 服务启动顺序
  startup_order:
    - database
    - cache
    - backend
    - frontend

  # 服务依赖关系
  dependencies:
    backend:
      - database
      - cache
    frontend:
      - backend

  # 并行启动配置
  parallel_groups:
    data_services: [database, cache]
    app_services: [backend, frontend]
```

---

## 🗄️ 数据库配置

### SQLite 配置（默认）

```yaml
database:
  type: "sqlite"
  path: "data/trading_platform.db"

  # 连接池配置
  pool:
    max_connections: 10
    timeout: 30

  # SQLite特定配置
  sqlite:
    journal_mode: "WAL"
    synchronous: "NORMAL"
    cache_size: 2000

  # 备份配置
  backup:
    enabled: true
    interval: "daily"
    retention: 7  # 保留7天
    path: "data/backups/"
```

### PostgreSQL 配置

```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "trading_db"
  username: "postgres"
  password: "${POSTGRES_PASSWORD}"

  # 连接池配置
  pool:
    max_connections: 20
    min_connections: 5
    timeout: 60

  # SSL配置
  ssl:
    enabled: false
    cert_file: ""
    key_file: ""
    ca_file: ""

  # 高可用配置
  replication:
    enabled: false
    master_host: ""
    slave_hosts: []
```

### MySQL 配置

```yaml
database:
  type: "mysql"
  host: "localhost"
  port: 3306
  database: "trading_db"
  username: "root"
  password: "${MYSQL_PASSWORD}"

  # 字符集配置
  charset: "utf8mb4"
  collation: "utf8mb4_unicode_ci"

  # 连接池配置
  pool:
    max_connections: 15
    timeout: 45

  # MySQL特定配置
  mysql:
    strict_mode: true
    engine: "InnoDB"
```

---

## 💾 缓存配置

### Redis 配置

```yaml
cache:
  type: "redis"
  url: "redis://localhost:6379"

  # 连接配置
  connection:
    max_connections: 10
    timeout: 5
    retry_on_timeout: true

  # 缓存策略
  default_ttl: 3600  # 1小时
  max_ttl: 86400     # 24小时

  # 键命名空间
  namespace: "trading_platform:"

  # 缓存分类配置
  categories:
    market_data:
      ttl: 60      # 1分钟
      max_size: 1000

    user_sessions:
      ttl: 1800    # 30分钟
      max_size: 500

    api_responses:
      ttl: 300     # 5分钟
      max_size: 200
```

### 内存缓存配置

```yaml
cache:
  type: "memory"

  # 内存限制
  max_memory: "512MB"
  max_items: 10000

  # 缓存策略
  eviction_policy: "lru"  # lru, lfu, fifo

  # 序列化配置
  serialization:
    method: "pickle"  # pickle, json, msgpack
    compression: true
```

---

## 📝 日志配置

### 日志系统配置

```yaml
logging:
  # 日志级别
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

  # 日志格式
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"

  # 文件配置
  file:
    enabled: true
    path: "logs/launcher.log"
    max_size: "10MB"
    backup_count: 5
    rotation: "daily"

  # 控制台配置
  console:
    enabled: true
    level: "INFO"
    colored: true

  # 结构化日志
  structured:
    enabled: true
    format: "json"
    include_metadata: true
```

### 日志分类配置

```yaml
logging:
  # 不同组件的日志级别
  components:
    launcher: "INFO"
    backend: "DEBUG"
    frontend: "WARNING"
    database: "INFO"

  # 特定功能的日志配置
  features:
    api_calls:
      enabled: true
      include_request_body: false
      include_response_body: false

    performance:
      enabled: true
      include_execution_time: true
      include_memory_usage: true

    security:
      enabled: true
      include_ip_address: true
      include_user_agent: true
```

---

## 🔧 环境变量

### 系统环境变量

```bash
# 基本配置
LAUNCHER_ENV=development          # 环境: development, production, testing
LAUNCHER_CONFIG=config/custom.yaml # 配置文件路径
LAUNCHER_LOG_LEVEL=INFO           # 日志级别
LAUNCHER_DEBUG=false              # 调试模式

# 服务配置
BACKEND_HOST=localhost
BACKEND_PORT=8000
FRONTEND_HOST=localhost
FRONTEND_PORT=3000

# 数据库配置
DATABASE_URL=sqlite:///data/trading_platform.db
POSTGRES_PASSWORD=your_password
MYSQL_PASSWORD=your_password

# 缓存配置
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# 安全配置
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# 外部服务
API_KEY=your-api-key
WEBHOOK_URL=your-webhook-url
```

### .env 文件示例

```env
# .env 文件示例（不要提交到版本控制）
LAUNCHER_ENV=development
LAUNCHER_DEBUG=true

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/trading_db
POSTGRES_PASSWORD=postgres123

# Redis配置
REDIS_URL=redis://localhost:6379/0

# API配置
NEXT_PUBLIC_API_URL=http://localhost:8000
API_SECRET_KEY=your-super-secret-key

# 第三方服务
ALPHAVANTAGE_API_KEY=your-key
BINANCE_API_KEY=your-key
```

---

## 🎛️ 高级配置

### 性能调优配置

```yaml
performance:
  # 启动器性能
  startup:
    parallel_download: true
    max_concurrent_operations: 4
    cache_dependencies: true

  # 内存优化
  memory:
    optimization_enabled: true
    gc_threshold: 0.8
    max_memory_usage: "2GB"

  # CPU优化
  cpu:
    max_workers: 4
    worker_timeout: 300
    worker_restarts: 3

  # 网络优化
  network:
    connection_pool_size: 10
    timeout: 30
    retry_attempts: 3
    backoff_factor: 2
```

### 安全配置

```yaml
security:
  # 认证配置
  authentication:
    enabled: true
    method: "jwt"  # jwt, oauth, basic
    token_expiry: 3600
    refresh_token_expiry: 86400

  # CORS配置
  cors:
    enabled: true
    origins: ["http://localhost:3000", "https://yourdomain.com"]
    methods: ["GET", "POST", "PUT", "DELETE"]
    headers: ["*"]
    credentials: true

  # HTTPS配置
  https:
    enabled: false
    cert_file: "certs/server.crt"
    key_file: "certs/server.key"

  # 速率限制
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_size: 20
```

### 监控配置

```yaml
monitoring:
  # 健康检查
  health_check:
    enabled: true
    interval: 30
    endpoint: "/health"
    detailed_info: true

  # 指标收集
  metrics:
    enabled: true
    endpoint: "/metrics"
    include_system_metrics: true
    include_application_metrics: true

  # 性能监控
  performance:
    enabled: true
    track_response_times: true
    track_memory_usage: true
    track_cpu_usage: true
    alert_thresholds:
      memory_usage: 0.8
      cpu_usage: 0.9
      response_time: 5.0
```

---

## 🔧 命令行配置

### 启动器命令行选项

```bash
# 基本启动
python launcher.py

# 指定配置文件
python launcher.py --config config/custom.yaml

# 调试模式
python launcher.py --debug --verbose

# 端口配置
python launcher.py --backend-port 8001 --frontend-port 3001

# 环境配置
python launcher.py --env production

# 数据库配置
python launcher.py --database-url postgresql://user:pass@localhost/db

# 缓存配置
python launcher.py --cache-url redis://localhost:6379

# 启用/禁用功能
python launcher.py --no-browser --no-auto-restart

# 日志配置
python launcher.py --log-level DEBUG --log-file custom.log

# 性能配置
python launcher.py --max-workers 8 --memory-limit 4GB
```

### 配置验证

```bash
# 验证配置文件
python launcher.py --validate-config

# 检查配置兼容性
python launcher.py --check-compatibility

# 生成配置模板
python launcher.py --generate-config-template
```

---

## 🎨 自定义配置示例

### 开发环境配置

```yaml
# config/development.yaml
services:
  backend:
    host: "localhost"
    port: 8000
    debug: true
    reload: true

  frontend:
    host: "localhost"
    port: 3000
    hot_reload: true
    source_maps: true

database:
  type: "sqlite"
  path: "data/dev_trading_platform.db"

logging:
  level: "DEBUG"
  console:
    enabled: true
    colored: true

performance:
  startup:
    cache_dependencies: false
```

### 生产环境配置

```yaml
# config/production.yaml
services:
  backend:
    host: "0.0.0.0"
    port: 8000
    workers: 4

  frontend:
    host: "0.0.0.0"
    port: 3000
    build:
      minify: true
      source_map: false

database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "trading_db"
  username: "app_user"
  password: "${POSTGRES_PASSWORD}"

cache:
  type: "redis"
  url: "redis://localhost:6379"

logging:
  level: "INFO"
  file:
    enabled: true
    path: "/var/log/trading_platform/launcher.log"
    max_size: "100MB"
    backup_count: 10

security:
  cors:
    origins: ["https://yourdomain.com"]
  https:
    enabled: true
```

### 高性能配置

```yaml
# config/high_performance.yaml
performance:
  startup:
    parallel_download: true
    max_concurrent_operations: 8

  memory:
    optimization_enabled: true
    max_memory_usage: "4GB"

  cpu:
    max_workers: 8
    worker_timeout: 600

cache:
  type: "redis"
  default_ttl: 7200  # 2小时
  categories:
    market_data:
      ttl: 30       # 30秒
    calculations:
      ttl: 3600     # 1小时

database:
  pool:
    max_connections: 50
    min_connections: 10
```

### 最小资源配置

```yaml
# config/minimal.yaml
services:
  backend:
    workers: 1
    resources:
      max_memory: "512MB"
      max_cpu: "50%"

  frontend:
    dev_server:
      hot_reload: false

cache:
  type: "memory"
  max_memory: "128MB"
  max_items: 1000

logging:
  level: "WARNING"
  console:
    enabled: false
  file:
    max_size: "5MB"
    backup_count: 2
```

---

## 🔄 动态配置更新

### 运行时配置更新

```bash
# 重新加载配置
python launcher.py --reload-config

# 热更新特定配置
python launcher.py --update-config services.backend.port=8001

# 临时配置覆盖
python launcher.py --env=production --log-level=ERROR
```

### 配置监听

```yaml
# config.yaml
config_watcher:
  enabled: true
  watch_files: ["config/*.yaml"]
  auto_reload: true
  debounce_seconds: 5
```

---

## 📊 配置最佳实践

### 1. 环境分离
- 为不同环境创建独立的配置文件
- 使用环境变量管理敏感信息
- 不要将生产环境配置提交到版本控制

### 2. 安全考虑
- 使用环境变量存储密码和密钥
- 启用配置文件权限控制
- 定期轮换敏感配置

### 3. 性能优化
- 根据硬件资源调整并发配置
- 合理设置缓存TTL值
- 监控配置变更对性能的影响

### 4. 维护管理
- 保持配置文件结构清晰
- 添加配置说明和示例
- 定期审查和清理无用配置

---

*最后更新: 2025-11-06 | 版本: 1.0.0*