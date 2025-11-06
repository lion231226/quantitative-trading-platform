# 诊断工具指南

## 🔍 目录

- [系统诊断](#系统诊断)
- [服务诊断](#服务诊断)
- [网络诊断](#网络诊断)
- [性能诊断](#性能诊断)
- [日志分析](#日志分析)
- [自动修复](#自动修复)
- [报告生成](#报告生成)

---

## 🖥️ 系统诊断

### 完整系统检查

```bash
# 运行完整系统诊断
python launcher.py --diagnose

# 输出示例：
"""
🔍 系统诊断报告
==================
操作系统: Windows 11 (Build 22631)
架构: x64
Python版本: 3.11.5 (64-bit)
Node.js版本: 20.9.0
内存总量: 16.0 GB (可用: 12.3 GB)
磁盘空间: C: 50GB可用 / D: 100GB可用
网络状态: 正常
✅ 系统环境检查通过
"""
```

### 环境兼容性检查

```bash
# 检查环境兼容性
python launcher.py --check-compatibility

# 检查特定组件
python launcher.py --check-python
python launcher.py --check-nodejs
python launcher.py --check-git
python launcher.py --check-docker  # 如果使用Docker
```

### 依赖完整性检查

```bash
# 检查所有依赖
python launcher.py --check-dependencies

# 检查Python依赖
python launcher.py --check-python-deps

# 检查Node.js依赖
python launcher.py --check-nodejs-deps

# 输出示例：
"""
📦 依赖检查结果
==================
Python依赖:
✅ fastapi==0.111.0
✅ uvicorn==0.29.0
✅ sqlalchemy==2.0.30
❌ pandas==2.2.1 (需要: 2.2.2)

Node.js依赖:
✅ next@14.2.33
✅ react@18.2.0
✅ chart.js@4.4.2
"""
```

---

## 🔄 服务诊断

### 服务状态检查

```bash
# 检查所有服务状态
python launcher.py --status

# 检查特定服务
python launcher.py --status --service backend
python launcher.py --status --service frontend

# 输出示例：
"""
🚀 服务状态报告
==================
启动器: ✅ 运行中 (PID: 12345, 启动时间: 10:23:45)
后端服务: ✅ 运行中 (端口: 8000, 响应时间: 45ms)
前端服务: ✅ 运行中 (端口: 3000, 构建状态: 最新)
数据库: ✅ 连接正常 (SQLite, 大小: 125MB)
缓存服务: ✅ 运行中 (Redis, 内存使用: 256MB)
"""
```

### 服务健康检查

```bash
# 详细健康检查
python launcher.py --health-check

# 端口可用性检查
python launcher.py --check-ports

# 服务响应时间测试
python launcher.py --response-time

# 输出示例：
"""
🏥 健康检查结果
==================
后端API (/health): ✅ 200 OK (45ms)
前端页面 (/): ✅ 200 OK (120ms)
数据库连接: ✅ 正常 (查询时间: 5ms)
缓存连接: ✅ 正常 (ping时间: 2ms)
WebSocket连接: ✅ 正常
"""
```

### 进程监控

```bash
# 监控所有相关进程
python launcher.py --monitor-processes

# 实时监控
python launcher.py --monitor-processes --real-time

# 输出示例：
"""
📊 进程监控
==================
PID    名称           CPU%  内存(MB)  启动时间
12345  launcher.py    2.1   156      10:23:45
12346  python(main)   5.2   512      10:23:50
12347  node(dev)      8.3   384      10:24:00
"""
```

---

## 🌐 网络诊断

### 网络连接测试

```bash
# 基本网络测试
python launcher.py --test-network

# 详细网络诊断
python launcher.py --network-diagnosis

# 连接速度测试
python launcher.py --speed-test

# 输出示例：
"""
🌐 网络诊断结果
==================
网络连接: ✅ 正常
DNS解析: ✅ 正常 (8.8.8.8: 5ms)
下载速度: 85.2 Mbps
上传速度: 42.1 Mbps
延迟: 12ms
GitHub连接: ✅ 正常
包管理器连接: ✅ 正常
"""
```

### 端口诊断

```bash
# 检查所有相关端口
python launcher.py --check-ports

# 扫描端口范围
python launcher.py --scan-ports --range 8000-8010

# 端口冲突检测
python launcher.py --detect-port-conflicts

# 输出示例：
"""
🔌 端口检查结果
==================
8000 (后端): ✅ 可用 - 正在监听
3000 (前端): ✅ 可用 - 正在监听
6379 (Redis): ✅ 可用 - 正在监听
5432 (PostgreSQL): ⚠️  未使用
80 (HTTP): ❌ 被占用 (PID: 4)
"""
```

### DNS诊断

```bash
# DNS解析测试
python launcher.py --test-dns

# 测试特定域名
python launcher.py --test-dns --domain google.com
python launcher.py --test-dns --domain pypi.org
python launcher.py --test-dns --domain registry.npmjs.org

# 输出示例：
"""
🔍 DNS解析结果
==================
google.com: ✅ 142.250.191.78 (5ms)
pypi.org: ✅ 151.101.1.69 (15ms)
registry.npmjs.org: ✅ 104.16.27.35 (12ms)
"""
```

---

## ⚡ 性能诊断

### 系统性能测试

```bash
# 性能基准测试
python launcher.py --benchmark

# 启动时间分析
python launcher.py --startup-profile

# 资源使用分析
python launcher.py --resource-analysis

# 输出示例：
"""
📈 性能基准测试
==================
启动时间: 95.2秒 (目标: <120秒) ✅
内存使用: 512MB (峰值: 756MB)
CPU使用: 平均15% (峰值: 45%)
磁盘IO: 读取45MB/s, 写入12MB/s
网络吞吐: 下载5.2MB/s, 上传1.1MB/s
"""
```

### 内存分析

```bash
# 内存使用分析
python launcher.py --memory-analysis

# 内存泄漏检测
python launcher.py --memory-leak-detection

# 内存优化建议
python launcher.py --memory-optimization

# 输出示例：
"""
💾 内存分析报告
==================
总内存: 16.0GB
已使用: 4.2GB (26%)
可用: 11.8GB

进程内存使用:
- launcher.py: 156MB
- python(main): 512MB
- node(dev): 384MB
- chrome: 1.2GB

内存优化建议:
✅ 当前内存使用正常
⚠️ 建议关闭不必要的浏览器标签
"""
```

### CPU分析

```bash
# CPU使用分析
python launcher.py --cpu-analysis

# CPU瓶颈检测
python launcher.py --cpu-bottleneck-detection

# CPU优化建议
python launcher.py --cpu-optimization

# 输出示例：
"""
🖥️ CPU分析报告
==================
CPU型号: Intel Core i7-12700K
核心数: 12 (8性能核 + 4效率核)
当前使用率: 15% (平均: 12%)

进程CPU使用:
- launcher.py: 2.1%
- python(main): 5.2%
- node(dev): 8.3%

CPU状态: ✅ 正常，无瓶颈
"""
```

---

## 📝 日志分析

### 日志检查

```bash
# 检查所有日志
python launcher.py --check-logs

# 检查特定类型日志
python launcher.py --check-logs --type error
python launcher.py --check-logs --type warning
python launcher.py --check-logs --type performance

# 最近日志分析
python launcher.py --recent-logs --lines 50

# 输出示例：
"""
📋 日志分析结果
==================
日志文件大小: 125MB (最近7天)
错误日志: 2条
警告日志: 15条
信息日志: 1,234条

最近错误:
- 2025-11-06 10:23:45 ERROR: 数据库连接超时
- 2025-11-06 09:15:22 ERROR: 内存不足

日志健康状态: ⚠️ 发现2个错误，建议处理
"""
```

### 日志模式分析

```bash
# 分析日志模式
python launcher.py --analyze-log-patterns

# 错误频率分析
python launcher.py --error-frequency

# 性能日志分析
python launcher.py --performance-logs

# 输出示例：
"""
🔍 日志模式分析
==================
常见错误模式:
1. 数据库连接超时 (5次) - 主要在10:00-11:00
2. 内存不足警告 (12次) - 通常在高负载时出现
3. 网络连接失败 (3次) - 与外部API相关

性能趋势:
- API响应时间: 平均125ms (趋势: 稳定)
- 内存使用: 平均512MB (趋势: 上升)
- 错误率: 0.5% (趋势: 下降)
"""
```

### 实时日志监控

```bash
# 实时日志监控
python launcher.py --monitor-logs

# 过滤特定日志
python launcher.py --monitor-logs --filter error
python launcher.py --monitor-logs --filter backend

# 日志告警
python launcher.py --log-alerts

# 输出示例（实时）：
"""
📡 实时日志监控 (Ctrl+C退出)
================================
2025-11-06 14:23:45 INFO: 用户登录成功
2025-11-06 14:23:47 DEBUG: API调用 /api/v1/data
2025-11-06 14:23:50 WARNING: 内存使用达到85%
2025-11-06 14:23:52 ERROR: 数据库查询超时
"""
```

---

## 🔧 自动修复

### 自动修复功能

```bash
# 自动修复常见问题
python launcher.py --auto-fix

# 安全模式修复
python launcher.py --auto-fix --safe-mode

# 强制修复
python launcher.py --auto-fix --force

# 输出示例：
"""
🔧 自动修复过程
==================
检查系统环境... ✅
检查依赖完整性... ✅
检查服务状态... ✅
发现问题:
- 端口3000被占用
- 缺少pandas包

正在修复...
1. 终止占用端口的进程... ✅
2. 安装缺失的依赖... ✅
3. 重启相关服务... ✅

修复完成！建议重启系统。
"""
```

### 一键恢复

```bash
# 恢复出厂设置
python launcher.py --factory-reset

# 恢复到备份点
python launcher.py --restore-to-backup --backup-name "2025-11-01-backup"

# 数据库恢复
python launcher.py --restore-database --from-backup

# 配置恢复
python launcher.py --restore-config --from-backup
```

### 问题检测和修复

```bash
# 检测和修复权限问题
python launcher.py --fix-permissions

# 检测和修复磁盘空间问题
python launcher.py --fix-disk-space

# 检测和修复网络问题
python launcher.py --fix-network

# 检测和修复依赖问题
python launcher.py --fix-dependencies
```

---

## 📊 报告生成

### 生成诊断报告

```bash
# 生成完整诊断报告
python launcher.py --generate-report

# 生成简化报告
python launcher.py --generate-report --summary

# 生成JSON格式报告
python launcher.py --generate-report --format json

# 指定报告输出路径
python launcher.py --generate-report --output /path/to/report.txt

# 输出示例：
"""
📋 系统诊断报告
生成时间: 2025-11-06 14:30:00

1. 系统信息
   - 操作系统: Windows 11 (Build 22631)
   - CPU: Intel Core i7-12700K (12核)
   - 内存: 16.0GB (使用: 4.2GB)
   - 磁盘: C: 50GB可用, D: 100GB可用

2. 服务状态
   - 启动器: ✅ 运行中
   - 后端: ✅ 运行中 (8000端口)
   - 前端: ✅ 运行中 (3000端口)
   - 数据库: ✅ 正常

3. 网络状态
   - 连接状态: ✅ 正常
   - 下载速度: 85.2 Mbps
   - DNS解析: ✅ 正常

4. 性能指标
   - 启动时间: 95.2秒
   - 内存使用: 512MB
   - CPU使用: 15%

5. 发现的问题
   - 无严重问题
   - 建议: 定期清理日志文件

6. 修复建议
   - 系统运行良好，无需特殊修复
   - 建议保持当前配置
"""
```

### 性能报告

```bash
# 生成性能报告
python launcher.py --performance-report

# 历史性能对比
python launcher.py --performance-comparison --days 7

# 性能趋势分析
python launcher.py --performance-trend
```

### 健康报告

```bash
# 生成健康报告
python launcher.py --health-report

# 服务健康评分
python launcher.py --health-score

# 系统健康指数
python launcher.py --health-index
```

---

## 🛠️ 高级诊断工具

### 深度系统分析

```bash
# 深度系统分析
python launcher.py --deep-scan

# 安全扫描
python launcher.py --security-scan

# 配置验证
python launcher.py --validate-config

# 依赖冲突检测
python launcher.py --dependency-conflict-check
```

### 专家模式诊断

```bash
# 专家模式
python launcher.py --expert-mode

# 调试模式
python launcher.py --debug-mode

# 详细跟踪
python launcher.py --trace
```

---

## 📞 获取帮助

### 诊断工具帮助

```bash
# 查看诊断工具帮助
python launcher.py --help-diagnostics

# 查看所有可用选项
python launcher.py --help-all

# 示例命令
python launcher.py --examples-diagnostics
```

### 联系支持

如果诊断工具无法解决问题，请收集以下信息：

```bash
# 生成支持包
python launcher.py --generate-support-package

# 上传到技术支持
# - 系统信息报告
# - 错误日志
# - 诊断报告
# - 配置文件
```

---

## 📅 定期维护建议

### 日常维护（每天）

```bash
# 快速健康检查
python launcher.py --quick-health

# 清理临时文件
python launcher.py --clean-temp

# 检查错误日志
python launcher.py --check-errors
```

### 周期性维护（每周）

```bash
# 完整系统诊断
python launcher.py --diagnose

# 清理日志文件
python launcher.py --clean-logs

# 性能分析
python launcher.py --performance-report

# 备份重要数据
python launcher.py --backup-data
```

### 深度维护（每月）

```bash
# 深度系统扫描
python launcher.py --deep-scan

# 依赖更新检查
python launcher.py --check-updates

# 系统优化
python launcher.py --optimize-system

# 生成月度报告
python launcher.py --monthly-report
```

---

## 🔮 预测性分析

### 故障预测

```bash
# 故障预测分析
python launcher.py --predict-failures

# 性能趋势预测
python launcher.py --predict-performance

# 资源使用预测
python launcher.py --predict-resource-usage
```

### 维护建议

```bash
# 智能维护建议
python launcher.py --maintenance-suggestions

# 优化建议
python launcher.py --optimization-suggestions

# 升级建议
python launcher.py --upgrade-suggestions
```

---

*最后更新: 2025-11-06 | 版本: 1.0.0*