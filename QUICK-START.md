# 🚀 量化交易平台 - 快速启动指南

## 📋 前置要求

用户需要预先安装以下环境：

### 必需软件
1. **Python 3.11+**
   ```bash
   # 检查版本
   python3 --version

   # 下载地址: https://www.python.org/downloads/
   ```

2. **Node.js 18+**
   ```bash
   # 检查版本
   node --version
   npm --version

   # 下载地址: https://nodejs.org/
   ```

3. **Git**
   ```bash
   # 检查版本
   git --version

   # 下载地址: https://git-scm.com/
   ```

## ⚡ 一键启动流程

### 1. 克隆项目
```bash
git clone https://github.com/lion231226/quantitative-trading-platform.git
cd quantitative-trading-platform
```

### 2. 一键启动
```bash
# Linux/Mac
chmod +x quick-start.sh
./quick-start.sh start

# Windows (Git Bash)
./quick-start.sh start
```

### 3. 访问应用
启动成功后，访问以下地址：

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 🛠️ 管理命令

```bash
# 启动服务
./quick-start.sh start

# 停止服务
./quick-start.sh stop

# 重启服务
./quick-start.sh restart

# 查看服务状态
./quick-start.sh status
```

## 📁 项目结构

```
quantitative-trading-platform/
├── quick-start.sh              # 一键启动脚本 ⭐
├── backend/
│   ├── requirements.txt        # Python依赖
│   ├── main.py                 # FastAPI入口
│   └── app/                    # 后端应用代码
├── frontend/
│   ├── package.json            # Node.js依赖
│   └── src/                    # 前端应用代码
├── data/                       # 数据存储目录
└── logs/                       # 日志文件目录
```

## 🔄 自动化流程

脚本会自动执行以下操作：

### ✅ 环境检查
- 检查 Python 版本
- 检查 Node.js 版本
- 检查项目文件完整性

### ✅ 后端设置
- 创建 Python 虚拟环境
- 安装 Python 依赖 (requirements.txt)
- 启动 FastAPI 服务 (端口 8000)

### ✅ 前端设置
- 安装 Node.js 依赖 (package.json)
- 启动 Next.js 开发服务器 (端口 3000)

### ✅ 服务验证
- 检查服务启动状态
- 提供访问地址和管理命令

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -an | grep :3000
   netstat -an | grep :8000

   # 停止其他服务后重新启动
   ./quick-start.sh restart
   ```

2. **Python 版本过低**
   ```bash
   # 确保使用 Python 3.11+
   python3 --version
   ```

3. **Node.js 版本过低**
   ```bash
   # 确保使用 Node.js 18+
   node --version
   ```

4. **依赖安装失败**
   ```bash
   # 清理缓存后重新安装
   cd backend && rm -rf venv && cd ..
   ./quick-start.sh start
   ```

### 查看日志

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

## 🌟 特色功能

- ✅ **跨平台支持** - Windows、Linux、Mac
- ✅ **自动化环境检查** - 确保运行环境正确
- ✅ **智能进程管理** - 自动启动和停止服务
- ✅ **状态监控** - 实时检查服务状态
- ✅ **日志管理** - 统一的日志文件管理

## 📞 技术支持

如果遇到问题：

1. 检查前置要求是否满足
2. 查看日志文件了解详细错误
3. 确保端口 3000 和 8000 未被占用
4. 尝试停止服务后重新启动

## 🎯 下一步

启动成功后，您可以：

1. 访问前端应用进行策略分析
2. 查看 API 文档了解接口使用
3. 根据需要修改配置文件
4. 参与项目开发和贡献

---

**🎉 享受您的量化交易分析之旅！**