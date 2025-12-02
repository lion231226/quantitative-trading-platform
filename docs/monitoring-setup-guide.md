# 监控和可观测性配置指南
# Monitoring and Observability Setup Guide

## 概述 (Overview)

本指南详细说明如何配置量化交易平台的Sentry监控和可观测性系统，包括错误追踪、性能监控和日志聚合。

## 快速开始 (Quick Start)

### 1. 创建Sentry项目

1. 访问 [Sentry.io](https://sentry.io) 并注册/登录
2. 创建两个新项目：
   - **前端项目**: 选择 `Next.js` 平台
   - **后端项目**: 选择 `Python` 平台
3. 记录两个项目的DSN (Data Source Name)

### 2. 配置环境变量

#### 后端配置

在项目根目录的 `.env` 文件中添加：

```bash
# Sentry APM配置
SENTRY_DSN=https://your-public-key@o123456.ingest.sentry.io/1234567
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_DEBUG=false

# 日志配置
LOG_FORMAT=json
STRUCTURED_LOGGING=true
```

#### 前端配置

在 `frontend/.env.local` 文件中添加：

```bash
# Sentry配置
NEXT_PUBLIC_SENTRY_DSN=https://your-public-key@o123456.ingest.sentry.io/1234568
NEXT_PUBLIC_SENTRY_ENVIRONMENT=development
NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.1

# 启用错误报告
NEXT_PUBLIC_ENABLE_ERROR_REPORTING=true
```

## 详细配置 (Detailed Configuration)

### 环境变量说明

| 变量名 | 描述 | 开发环境建议值 | 生产环境建议值 |
|--------|------|---------------|---------------|
| `SENTRY_DSN` | 后端Sentry数据源链接 | 开发环境DSN | 生产环境DSN |
| `NEXT_PUBLIC_SENTRY_DSN` | 前端Sentry数据源链接 | 开发环境DSN | 生产环境DSN |
| `SENTRY_TRACES_SAMPLE_RATE` | 后端性能追踪采样率 | 0.1 (10%) | 0.05 (5%) |
| `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE` | 前端性能追踪采样率 | 0.1 (10%) | 0.05 (5%) |
| `SENTRY_PROFILES_SAMPLE_RATE` | 性能分析采样率 | 0.1 (10%) | 0.05 (5%) |
| `SENTRY_ENVIRONMENT` | 环境标识 | development | production |
| `SENTRY_DEBUG` | Sentry调试模式 | true | false |

### 生产环境配置

1. **创建生产环境配置文件**：
   ```bash
   cp .env.example .env.production
   cp frontend/.env.example frontend/.env.production
   ```

2. **更新生产环境DSN**：
   - 使用生产项目的DSN
   - 设置较低的采样率（5%）以减少成本
   - 启用安全功能

### Vercel部署配置

在Vercel中设置环境变量：

1. 进入项目设置页面
2. 添加以下环境变量：
   ```
   NEXT_PUBLIC_SENTRY_DSN=your-production-dsn
   NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
   NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.05
   NEXT_PUBLIC_ENABLE_ERROR_REPORTING=true
   ```

## 验证配置 (Verification)

### 1. 后端验证

启动后端服务并检查Sentry集成：

```bash
cd backend
python -m pytest tests/monitoring/ -v
```

### 2. 前端验证

启动前端服务并验证Sentry集成：

```bash
cd frontend
npm run dev
```

在浏览器中访问应用，检查控制台是否有Sentry初始化成功的消息。

### 3. 健康检查端点验证

验证监控端点是否正常工作：

```bash
# 健康检查
curl http://localhost:8000/health

# 就绪状态检查
curl http://localhost:8000/ready

# 系统状态
curl http://localhost:8000/status

# 指标暴露
curl http://localhost:8000/metrics
```

## 监控功能特性 (Monitoring Features)

### 1. 错误追踪
- 自动捕获前端JavaScript错误
- 后端Python异常监控
- 错误上下文和堆栈跟踪
- 用户会话记录

### 2. 性能监控
- Core Web Vitals监控
- API响应时间追踪
- 数据库查询性能
- 分布式追踪

### 3. 健康检查
- 应用状态监控
- 依赖服务检查
- 系统资源监控
- 业务指标追踪

### 4. 告警通知
- 实时错误告警
- 性能阈值告警
- 多渠道通知（邮件、Slack）
- 告警升级机制

## 故障排除 (Troubleshooting)

### 常见问题

1. **DSN未配置错误**
   - 确保环境变量正确设置
   - 检查DSN格式是否正确

2. **数据未出现在Sentry中**
   - 检查网络连接
   - 验证Sentry项目配置
   - 确认采样率设置

3. **性能数据缺失**
   - 检查traces_sample_rate设置
   - 验证性能监控集成

### 调试命令

```bash
# 检查环境变量
echo $SENTRY_DSN
echo $NEXT_PUBLIC_SENTRY_DSN

# 测试Sentry连接
curl -I https://o123456.ingest.sentry.io/api/1234567/store/

# 检查日志配置
python -c "import structlog; print(structlog.get_logger())"
```

## 最佳实践 (Best Practices)

1. **环境分离**：开发和生产环境使用不同的Sentry项目
2. **采样率管理**：生产环境使用较低的采样率以控制成本
3. **敏感信息过滤**：确保不记录敏感的用户数据
4. **告警配置**：设置合理的告警阈值和通知规则
5. **定期审查**：定期检查监控配置和告警规则

## 相关文档 (Related Documentation)

- [Sentry官方文档](https://docs.sentry.io/)
- [Next.js Sentry集成指南](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [Python Sentry集成指南](https://docs.sentry.io/platforms/python/)
- [Prometheus指标格式](https://prometheus.io/docs/practices/instrumentation/)

---

**配置完成后，您的量化交易平台将具备完整的监控和可观测性能力！**