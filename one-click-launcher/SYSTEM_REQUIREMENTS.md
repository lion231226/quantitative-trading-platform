# 系统要求与兼容性矩阵

## 📋 系统要求概述

量化交易平台一键启动器支持主流操作系统和硬件配置。为确保最佳性能，建议满足或超过推荐配置。

## 💻 操作系统支持

### Windows 系统

| 版本 | 支持状态 | 最低要求 | 推荐配置 | 备注 |
|------|----------|----------|----------|------|
| Windows 11 | ✅ 完全支持 | 21H2 (22000) | 23H2 (22631) | 推荐，性能最佳 |
| Windows 10 | ✅ 完全支持 | 1909 (18363) | 22H2 (19045) | 需要安装最新的Windows更新 |
| Windows 8.1 | ⚠️ 有限支持 | - | - | 不推荐，缺少某些系统API |
| Windows 7 | ❌ 不支持 | - | - | 已停止支持 |

### macOS 系统

| 版本 | 支持状态 | 最低要求 | 推荐配置 | 备注 |
|------|----------|----------|----------|------|
| macOS Sonoma 14 | ✅ 完全支持 | 14.0+ | 14.2+ | 推荐，性能最佳 |
| macOS Ventura 13 | ✅ 完全支持 | 13.0+ | 13.6+ | 性能良好 |
| macOS Monterey 12 | ✅ 完全支持 | 12.3+ | 12.7+ | 基本功能完整 |
| macOS Big Sur 11 | ⚠️ 有限支持 | 11.6+ | - | 某些功能可能受限 |
| macOS Catalina 10.15 | ❌ 不支持 | - | - | Python 3.11兼容性问题 |

### Linux 发行版

| 发行版 | 版本 | 支持状态 | 最低要求 | 推荐配置 | 备注 |
|--------|------|----------|----------|----------|------|
| Ubuntu | 22.04 LTS | ✅ 完全支持 | 22.04+ | 24.04 LTS | 官方测试环境 |
| Ubuntu | 20.04 LTS | ✅ 完全支持 | 20.04+ | 22.04 LTS | 稳定可靠 |
| Debian | 12 | ✅ 完全支持 | 12+ | 12+ | 与Ubuntu兼容 |
| CentOS | 9 Stream | ✅ 完全支持 | 9+ | 9+ | 企业环境推荐 |
| Fedora | 39+ | ✅ 完全支持 | 39+ | 40+ | 最新技术栈 |
| Arch Linux | 滚动更新 | ✅ 完全支持 | - | - | 技术用户推荐 |

## 🔧 硬件要求

### 处理器 (CPU)

| 类型 | 最低要求 | 推荐配置 | 性能影响 |
|------|----------|----------|----------|
| Intel | Core i3 (双核) | Core i5/i7 (四核+) | 启动速度、数据处理 |
| AMD | Ryzen 3 (双核) | Ryzen 5/7 (四核+) | 同上 |
| Apple Silicon | M1 | M2/M3 | 原生性能优化 |

### 内存 (RAM)

| 使用场景 | 最低要求 | 推荐配置 | 说明 |
|----------|----------|----------|------|
| 基础使用 | 4GB | 8GB | 基本功能正常运行 |
| 数据分析 | 8GB | 16GB | 大量数据处理 |
| 高频交易 | 16GB | 32GB+ | 实时数据处理 |

### 存储空间

| 类型 | 最低要求 | 推荐配置 | 性能建议 |
|------|----------|----------|----------|
| HDD | 2GB | 5GB | 可用，但启动较慢 |
| SSD | 2GB | 5GB | 推荐，启动速度快 |
| NVMe SSD | 2GB | 5GB | 最佳性能选择 |

### 网络连接

| 连接类型 | 最低要求 | 推荐配置 | 说明 |
|----------|----------|----------|------|
| 宽带 | 10 Mbps | 100 Mbps+ | 数据下载和API调用 |
| WiFi | 802.11n | 802.11ac/ax | 稳定性很重要 |
| 有线网络 | 100Mbps | 1Gbps | 最稳定的选择 |

## 📦 软件依赖

### Python 环境

| 组件 | 最低版本 | 推荐版本 | 安装方式 |
|------|----------|----------|----------|
| Python | 3.11.0 | 3.11.5+ | [python.org](https://www.python.org/downloads/) |
| pip | 22.0+ | 24.0+ | 随Python安装 |
| virtualenv | 20.0+ | 20.24+ | `pip install virtualenv` |

### Node.js 环境

| 组件 | 最低版本 | 推荐版本 | 安装方式 |
|------|----------|----------|----------|
| Node.js | 18.0.0 | 20.0.0+ | [nodejs.org](https://nodejs.org/) |
| npm | 8.0.0 | 10.0.0+ | 随Node.js安装 |
| npx | 8.0.0 | 10.0.0+ | 随npm安装 |

### 可选依赖

| 组件 | 用途 | 最低版本 | 推荐版本 | 必需性 |
|------|------|----------|----------|--------|
| Git | 版本控制 | 2.30+ | 2.41+ | 可选 |
| Redis | 缓存服务 | 6.0+ | 7.0+ | 可选 |
| PostgreSQL | 数据库 | 13+ | 15+ | 可选 |
| Docker | 容器化 | 20.10+ | 24.0+ | 可选 |

## 🎯 兼容性矩阵

### 功能兼容性

| 功能 | Windows | macOS | Linux | 说明 |
|------|---------|--------|-------|------|
| 一键启动 | ✅ | ✅ | ✅ | 核心功能 |
| 进度显示 | ✅ | ✅ | ✅ | Rich库支持 |
| 错误恢复 | ✅ | ✅ | ✅ | 智能错误处理 |
| 桌面快捷方式 | ✅ | ✅ | ✅ | 跨平台支持 |
| 浏览器集成 | ✅ | ✅ | ✅ | 自动打开 |
| 服务监控 | ✅ | ✅ | ✅ | 实时状态 |

### 性能对比

| 场景 | Windows 11 | macOS Sonoma | Ubuntu 24.04 | 说明 |
|------|------------|--------------|--------------|------|
| 冷启动时间 | ~90秒 | ~75秒 | ~60秒 | 包含依赖安装 |
| 热启动时间 | ~15秒 | ~12秒 | ~10秒 | 服务已安装 |
| 内存占用 | ~512MB | ~450MB | ~380MB | 运行时内存 |
| CPU使用率 | ~15% | ~12% | ~10% | 启动期间 |

## 🚀 安装验证

### 系统检查脚本

创建 `check_system.py` 脚本验证系统兼容性：

```python
#!/usr/bin/env python3
import sys
import platform
import subprocess
import psutil

def check_system():
    print("🔍 系统兼容性检查")
    print("=" * 40)

    # 操作系统检查
    os_info = platform.uname()
    print(f"操作系统: {os_info.system} {os_info.release}")

    # Python版本检查
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    if python_version < (3, 11):
        print("❌ Python版本过低，需要3.11+")
        return False

    # 内存检查
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    print(f"可用内存: {memory_gb:.1f}GB")

    if memory_gb < 4:
        print("⚠️ 内存不足4GB，可能影响性能")

    # 磁盘空间检查
    disk = psutil.disk_usage('.')
    disk_gb = disk.free / (1024**3)
    print(f"可用磁盘: {disk_gb:.1f}GB")

    if disk_gb < 2:
        print("❌ 磁盘空间不足2GB")
        return False

    print("✅ 系统检查通过！")
    return True

if __name__ == "__main__":
    check_system()
```

### 环境测试命令

```bash
# Python环境测试
python --version
pip --version

# Node.js环境测试
node --version
npm --version

# 系统资源检查
# Windows
wmic computersystem get TotalPhysicalMemory
wmic logicaldisk get size,freespace,caption

# macOS/Linux
free -h
df -h
```

## ⚠️ 已知限制

### Windows限制

1. **长路径名**: Windows默认路径长度限制为260字符
2. **权限要求**: 某些操作需要管理员权限
3. **防火墙**: 首次运行可能需要防火墙例外
4. **杀毒软件**: 可能误报为潜在威胁

### macOS限制

1. **Gatekeeper**: 可能需要允许未签名应用运行
2. **文件权限**: 某些目录需要额外权限
3. **Rosetta**: Intel Mac在Apple Silicon Mac上运行需要转译

### Linux限制

1. **包管理器差异**: 不同发行版包管理器不同
2. **权限管理**: 可能需要sudo权限
3. **桌面环境**: 不同桌面环境快捷方式创建方式不同

## 🔧 性能优化建议

### 硬件优化

1. **使用SSD**: 显著提升启动和数据加载速度
2. **充足内存**: 8GB+内存提升多任务处理能力
3. **多核CPU**: 提升数据处理和并行计算性能

### 软件优化

1. **定期更新**: 保持Python、Node.js等依赖最新版本
2. **清理缓存**: 定期清理npm和pip缓存
3. **关闭不必要服务**: 减少后台资源占用

### 网络优化

1. **使用有线连接**: 比WiFi更稳定
2. **配置镜像源**: 使用国内镜像加速依赖下载
3. **DNS优化**: 使用快速DNS服务器

## 📊 测试覆盖

### 自动化测试

我们的CI/CD系统在以下环境进行测试：

- **Windows**: Windows 11 23H2, Windows 10 22H2
- **macOS**: macOS Sonoma 14, macOS Ventura 13
- **Linux**: Ubuntu 24.04 LTS, Ubuntu 22.04 LTS, CentOS 9

### 测试矩阵

| 测试类型 | Windows | macOS | Linux | 频率 |
|----------|---------|--------|-------|------|
| 单元测试 | ✅ | ✅ | ✅ | 每次提交 |
| 集成测试 | ✅ | ✅ | ✅ | 每日 |
| 性能测试 | ✅ | ✅ | ✅ | 每周 |
| 兼容性测试 | ✅ | ✅ | ✅ | 每次发布 |

## 🆘 获取帮助

如果您在使用过程中遇到兼容性问题：

1. **查看日志**: `logs/launcher.log` 包含详细的错误信息
2. **运行诊断**: `python launcher.py --diagnose` 获取系统诊断报告
3. **查看FAQ**: [常见问题解答](TROUBLESHOOTING.md)
4. **提交问题**: [GitHub Issues](https://github.com/lion231226/quantitative-trading-platform/issues)

---

*最后更新: 2025-11-06 | 版本: 1.0.0*