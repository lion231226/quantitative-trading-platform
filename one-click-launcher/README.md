# 量化交易平台一键启动器

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/lion231226/quantitative-trading-platform)

## 🚀 **智能化一键启动：您的量化交易环境即刻就绪**

---

## 📖 系统概述

- 🎯 **零配置启动**: 无需配置开发环境，自动检测并安装依赖
- 🌍 **跨平台支持**: 完美支持 Windows 10/11、macOS、Linux
- ⚡ **智能诊断**: 自动解决90%以上的环境配置问题
- 🔧 **专业级服务**: 完整的数据库、后端API、前端界面
- 📊 **开箱即用**: 预置回测引擎、数据管理、策略展示
- 🛡️ **安全可靠**: 内置安全检查和错误恢复机制

---

## ✨ 核心特性

### 🎯 用户体验
- **5分钟快速启动**: 从下载到运行，非技术用户也能轻松完成
- **图形化进度条**: 实时显示安装和启动进度
- **智能错误诊断**: 自动检测并提供解决方案
- **一键修复**: 常见问题自动修复功能

### 🔧 技术架构
- **现代技术栈**: Python 3.11+ + FastAPI + Next.js 14 + React 18
- **微服务架构**: 前后端分离，服务独立管理
- **数据库支持**: PostgreSQL + Redis 双数据库
- **跨平台兼容**: Windows PowerShell + Unix Shell 适配

### 📊 交易功能
- **回测引擎**: 支持多种量化策略回测
- **实时数据**: 股票、期货、加密货币数据支持
- **策略展示**: 交互式图表和性能分析
- **风险管理**: 专业的风险评估和控制工具

---

## 🚀 快速开始

### 方法一：一键安装（推荐）

**Windows 用户:**
```batch
# 下载并运行安装脚本
curl -o install.bat https://raw.githubusercontent.com/lion231226/quantitative-trading-platform/main/one-click-launcher/scripts/install.bat
install.bat
```

**macOS/Linux 用户:**
```bash
# 下载并运行安装脚本
curl -o install.sh https://raw.githubusercontent.com/lion231226/quantitative-trading-platform/main/one-click-launcher/scripts/install.sh
chmod +x install.sh
./install.sh
```

### 方法二：手动启动

1. **克隆项目**
   ```bash
   git clone https://github.com/lion231226/quantitative-trading-platform.git
   cd quantitative-trading-platform/one-click-launcher
   ```

2. **运行启动器**
   ```bash
   # Windows
   python launcher.py

   # macOS/Linux
   python3 launcher.py
   ```

---

## 📋 系统要求

### 最低要求
- **操作系统**: Windows 10 / macOS 10.15 / Ubuntu 18.04
- **内存**: 4GB RAM
- **存储**: 2GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Windows 11 / macOS 12 / Ubuntu 20.04+
- **内存**: 8GB+ RAM
- **存储**: 5GB+ 可用空间
- **处理器**: 多核 CPU

### 自动安装的依赖
- Python 3.11+ (如果未安装)
- Node.js 18+ (如果未安装)
- Git (如果未安装)
- Redis (数据库服务)
- PostgreSQL (数据库服务，可选)

---

## 🎮 使用指南

### 首次启动
1. 双击桌面快捷方式 **量化交易平台**
2. 等待自动检测系统环境
3. 选择安装选项（推荐：自动安装）
4. 等待所有服务启动完成
5. 浏览器自动打开 http://localhost:3000

### 日常使用
```bash
# 启动系统
python launcher.py

# 调试模式启动
python launcher.py --debug

# 查看帮助
python launcher.py --help
```

### 服务管理
- **启动所有服务**: `python launcher.py start`
- **停止所有服务**: `python launcher.py stop`
- **重启服务**: `python launcher.py restart`
- **查看状态**: `python launcher.py status`

---

## 🔧 高级配置

### 自定义端口
```bash
# 设置自定义端口
python launcher.py --frontend-port 8080 --backend-port 8000
```

### 开发模式
```bash
# 启用开发模式（热重载）
python launcher.py --dev
```

### 数据库配置
编辑 `config/database.yaml`:
```yaml
database:
  host: localhost
  port: 5432
  name: quantitative_trading
  user: postgres
  password: your_password
```

---

## 🆘 故障排除

### 常见问题

**Q: 启动时提示"Python未安装"**
```bash
# Windows: 自动下载安装 Python
# 或手动访问 https://www.python.org/downloads/

# macOS:
brew install python3

# Linux:
sudo apt-get install python3 python3-pip
```

**Q: 端口被占用**
```bash
# 查看端口占用
netstat -ano | findstr :3000  # Windows
lsof -i :3000                 # macOS/Linux

# 使用自定义端口
python launcher.py --frontend-port 3001
```

**Q: 服务启动失败**
```bash
# 查看详细日志
python launcher.py --debug

# 重置所有服务
python launcher.py --reset
```

**Q: 前端构建失败**
```bash
# 清理并重新安装依赖
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 获取帮助

1. **查看详细故障排除**: [故障排除指南](TROUBLESHOOTING.md)
2. **常见错误解答**: [错误消息手册](ERROR_MESSAGES.md)
3. **系统诊断工具**: [诊断指南](DIAGNOSTICS.md)
4. **联系技术支持**: [支持页面](SUPPORT.md)

---

## 📚 文档导航

### 用户文档
- [快速入门指南](QUICKSTART.md) - 5分钟快速上手
- [系统要求详情](SYSTEM_REQUIREMENTS.md) - 详细的兼容性信息
- [常见问题](FAQ.md) - 常见问题解答
- [配置指南](CONFIGURATION.md) - 高级配置选项

### 技术文档
- [故障排除指南](TROUBLESHOOTING.md) - 详细的问题诊断
- [错误消息手册](ERROR_MESSAGES.md) - 错误代码说明
- [诊断工具](DIAGNOSTICS.md) - 系统诊断工具
- [开发者指南](../README.md) - 主项目文档

---

## 🌍 多语言支持

### 界面语言
- **简体中文**: 默认界面语言
- **English**: 自动检测系统语言切换

### 切换语言
```bash
# 设置语言为中文
python launcher.py --language zh

# 设置语言为英文
python launcher.py --language en
```

---

## 🛡️ 安全说明

### 数据安全
- 所有数据本地存储，不上传到云端
- 数据库连接使用 SSL 加密
- 支持数据备份和恢复

### 系统安全
- 最小权限原则，仅请求必要的系统权限
- 自动安全更新检查
- 恶意软件扫描集成

---

## 🔄 更新与维护

### 自动更新
```bash
# 检查更新
python launcher.py --check-updates

# 应用更新
python launcher.py --update
```

### 备份与恢复
```bash
# 备份配置和数据
python launcher.py --backup

# 恢复备份
python launcher.py --restore backup_file.zip
```

---

## 📊 性能监控

### 系统监控
- CPU 和内存使用率
- 服务响应时间
- 数据库性能指标
- 网络连接状态

### 优化建议
- 自动性能优化建议
- 资源使用优化配置
- 缓存策略优化

---

## 🤝 贡献与支持

### 贡献代码
欢迎提交 Issue 和 Pull Request！请查看 [贡献指南](../CONTRIBUTING.md)。

### 技术支持
- **GitHub Issues**: [提交问题](https://github.com/lion231226/quantitative-trading-platform/issues)
- **文档反馈**: [文档改进建议](https://github.com/lion231226/quantitative-trading-platform/discussions)
- **社区讨论**: [技术交流](https://github.com/lion231226/quantitative-trading-platform/discussions)

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 允许商业和非商业使用。

---

## 🎉 致谢

感谢所有为这个项目做出贡献的开发者和用户！

### 核心依赖
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Next.js](https://nextjs.org/) - React 全栈框架
- [Chart.js](https://www.chartjs.org/) - 数据可视化库
- [Redis](https://redis.io/) - 内存数据库
- [PostgreSQL](https://www.postgresql.org/) - 关系型数据库

---

**🚀 [立即开始使用](QUICKSTART.md) | [遇到问题？](TROUBLESHOOTING.md) | [查看演示](https://demo.quantitative-trading.com)**

---

*最后更新: 2025-11-06 | 版本: 1.0.0*