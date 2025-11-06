# 常见问题解答 (FAQ)

## 📖 目录

- [安装相关](#安装相关)
- [启动问题](#启动问题)
- [依赖和环境](#依赖和环境)
- [网络连接](#网络连接)
- [性能和优化](#性能和优化)
- [功能使用](#功能使用)
- [错误排查](#错误排查)
- [高级配置](#高级配置)
- [跨平台问题](#跨平台问题)

---

## 🚀 安装相关

### Q: 如何确认我的系统是否满足要求？

**A:** 运行系统检查命令：
```bash
# 使用启动器内置检查
python launcher.py --check-only

# 或手动检查
python --version  # 需要3.11+
node --version    # 需要18.0+
```

详细要求请参考 [系统要求文档](SYSTEM_REQUIREMENTS.md)。

### Q: 我应该选择哪个Python版本？

**A:** 推荐使用Python 3.11.5或更高版本：
- Python 3.11.0+：基本支持
- Python 3.11.5+：推荐版本，性能更佳
- Python 3.12+：也可以使用，但未经充分测试

### Q: 可以同时安装多个Python版本吗？

**A:** 可以，但需要确保启动器使用正确的版本：
```bash
# Windows
py -3.11 launcher.py

# macOS/Linux (使用pyenv)
pyenv global 3.11.5
python launcher.py
```

### Q: 安装过程中提示权限不足怎么办？

**A:** 根据操作系统选择解决方案：

**Windows:**
- 以管理员身份运行PowerShell或命令提示符
- 或右键点击启动器选择"以管理员身份运行"

**macOS/Linux:**
```bash
sudo python3 launcher.py
```

### Q: 安装失败后如何重新开始？

**A:** 清理并重新安装：
```bash
# 清理缓存
python launcher.py --clean-cache

# 强制重新安装依赖
python launcher.py --force-reinstall
```

---

## 🔄 启动问题

### Q: 启动器卡在"正在检查环境"步骤

**A:** 可能的原因和解决方案：

1. **网络连接问题**：检查网络连接
2. **防火墙阻拦**：临时关闭防火墙或添加例外
3. **杀毒软件干扰**：将启动器目录添加到白名单

```bash
# 测试网络连接
python launcher.py --test-network
```

### Q: 启动时显示"端口被占用"错误

**A:** 端口冲突解决方案：

**方法1：使用自定义端口**
```bash
python launcher.py --backend-port 8001 --frontend-port 3001
```

**方法2：停止占用端口的进程**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# macOS/Linux
lsof -i :8000
kill -9 <进程ID>
```

### Q: 启动器无法自动打开浏览器

**A:** 手动访问应用：
- 前端应用：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### Q: 服务启动失败，提示数据库连接错误

**A:** 数据库问题排查：

```bash
# 检查数据库文件权限
ls -la data/

# 重新初始化数据库
python launcher.py --init-database

# 检查数据库配置
cat config/config.yaml
```

---

## 📦 依赖和环境

### Q: pip install 安装速度很慢怎么办？

**A:** 使用国内镜像源：

```bash
# 临时使用
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

### Q: npm install 失败或超时

**A:** npm安装问题解决方案：

```bash
# 清理npm缓存
npm cache clean --force

# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 或使用yarn替代
npm install -g yarn
yarn install
```

### Q: 某些Python包安装失败

**A:** 常见问题和解决方案：

**1. 编译错误（Windows）**
```bash
# 安装Microsoft C++ Build Tools
# 或使用预编译包
pip install package-name --only-binary=all
```

**2. 权限错误（macOS/Linux）**
```bash
# 使用用户安装
pip install --user package-name

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### Q: 如何查看已安装的依赖版本？

**A:** 检查依赖版本：

```bash
# Python依赖
pip list
pip freeze

# Node.js依赖
npm list
npm list --depth=0  # 只显示直接依赖
```

---

## 🌐 网络连接

### Q: 无法下载GitHub上的代码

**A:** GitHub访问问题解决方案：

**国内用户：**
```bash
# 使用Gitee镜像
git clone https://gitee.com/lion20231226/quantitative-trading-platform.git

# 或配置GitHub代理
git config --global http.proxy http://proxy-server:port
```

### Q: API调用失败，提示网络错误

**A:** API连接问题排查：

1. **检查网络连接**：
```bash
ping google.com
```

2. **检查防火墙设置**：确保端口8000和3000未被阻拦

3. **使用代理**：
```bash
# 设置环境变量
export HTTP_PROXY=http://proxy-server:port
export HTTPS_PROXY=http://proxy-server:port
```

### Q: 数据下载速度很慢

**A:** 数据下载优化：

1. **使用CDN加速**：配置文件中启用CDN选项
2. **调整并发数**：降低同时下载的文件数量
3. **分批下载**：大数据集分批次下载

---

## ⚡ 性能和优化

### Q: 启动速度很慢，如何优化？

**A:** 启动速度优化方案：

**1. 硬件优化**
- 使用SSD硬盘
- 增加内存到8GB+
- 使用多核CPU

**2. 软件优化**
```bash
# 启用缓存模式
python launcher.py --enable-cache

# 跳过不必要的检查
python launcher.py --skip-optional-checks
```

**3. 网络优化**
- 使用有线网络连接
- 配置国内镜像源

### Q: 内存占用过高怎么办？

**A:** 内存使用优化：

```bash
# 监控内存使用
python launcher.py --monitor-memory

# 启用内存优化模式
python launcher.py --memory-efficient

# 清理临时文件
python launcher.py --clean-temp
```

### Q: CPU使用率很高，系统变慢

**A:** CPU优化建议：

1. **关闭不必要的后台程序**
2. **调整启动器并发设置**
3. **使用性能模式**：
```bash
python launcher.py --performance-mode
```

---

## 🎯 功能使用

### Q: 如何修改默认端口配置？

**A:** 端口配置方法：

**1. 命令行参数**
```bash
python launcher.py --backend-port 8001 --frontend-port 3001
```

**2. 配置文件**
编辑 `config/config.yaml`：
```yaml
services:
  backend:
    port: 8001
  frontend:
    port: 3001
```

### Q: 如何启用调试模式？

**A:** 调试模式启用：

```bash
# 基本调试模式
python launcher.py --debug

# 详细调试日志
python launcher.py --debug --verbose

# 保存调试日志到文件
python launcher.py --debug --log-file debug.log
```

### Q: 如何备份数据？

**A:** 数据备份方法：

```bash
# 完整备份
python launcher.py --backup-data

# 增量备份
python launcher.py --backup-incremental

# 指定备份路径
python launcher.py --backup-to /path/to/backup
```

### Q: 如何恢复数据？

**A:** 数据恢复方法：

```bash
# 从备份恢复
python launcher.py --restore-from /path/to/backup

# 恢复到指定时间点
python launcher.py --restore-to "2025-11-01 10:00:00"
```

---

## ❌ 错误排查

### Q: 启动时显示"未知错误"

**A:** 通用错误排查步骤：

1. **查看详细日志**：
```bash
tail -f logs/launcher.log
```

2. **运行诊断工具**：
```bash
python launcher.py --diagnose
python launcher.py --generate-report
```

3. **检查系统状态**：
```bash
python launcher.py --system-info
```

### Q: "ModuleNotFoundError" 错误

**A:** 模块缺失解决方案：

```bash
# 重新安装所有依赖
pip install -r requirements.txt

# 安装特定缺失模块
pip install missing-module-name

# 检查Python路径
python -c "import sys; print(sys.path)"
```

### Q: "Permission denied" 错误

**A:** 权限问题解决：

**Windows:**
```powershell
# 以管理员身份运行
Start-Process powershell -Verb RunAs
```

**macOS/Linux:**
```bash
# 修改文件权限
chmod +x launcher.py
sudo chown $USER:$USER data/
```

### Q: 服务启动后无法访问

**A:** 服务访问问题排查：

1. **检查服务状态**：
```bash
python launcher.py --status
```

2. **检查端口监听**：
```bash
netstat -an | grep 8000  # Linux/macOS
netstat -an | findstr 8000  # Windows
```

3. **测试本地连接**：
```bash
curl http://localhost:8000/health
```

---

## 🔧 高级配置

### Q: 如何自定义配置文件？

**A:** 配置文件自定义：

1. **创建自定义配置**：
```bash
cp config/config.yaml config/custom.yaml
```

2. **编辑配置文件**：
```yaml
# 自定义服务配置
services:
  backend:
    command: "uvicorn app.main:app --host 0.0.0.0 --port 8000"
    env_vars:
      DATABASE_URL: "postgresql://user:pass@localhost/db"
```

3. **使用自定义配置**：
```bash
python launcher.py --config config/custom.yaml
```

### Q: 如何配置数据库？

**A:** 数据库配置选项：

**SQLite（默认）**：
```yaml
database:
  type: "sqlite"
  path: "data/trading_platform.db"
```

**PostgreSQL**：
```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "trading_db"
  username: "postgres"
  password: "your_password"
```

### Q: 如何启用Redis缓存？

**A:** Redis配置方法：

1. **安装Redis**：
```bash
# Ubuntu
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# 下载Redis for Windows或使用WSL
```

2. **配置Redis**：
```yaml
cache:
  type: "redis"
  url: "redis://localhost:6379"
  ttl: 3600
```

---

## 🌍 跨平台问题

### Q: Windows中文显示乱码怎么办？

**A:** 中文显示问题解决：

1. **设置控制台编码**：
```batch
chcp 65001
```

2. **设置环境变量**：
```cmd
set PYTHONIOENCODING=utf-8
```

3. **使用PowerShell**：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### Q: macOS安全限制无法运行

**A:** macOS安全限制绕过：

1. **允许任何来源的应用**：
```bash
sudo spctl --master-disable
```

2. **移除隔离属性**：
```bash
xattr -d com.apple.quarantine launcher.py
```

3. **手动允许运行**：
   - 右键点击应用 → "打开" → "打开"

### Q: Linux权限问题

**A:** Linux权限解决方案：

```bash
# 修改文件权限
chmod +x launcher.py
chmod -R 755 data/

# 修改文件所有者
sudo chown -R $USER:$USER ./

# 添加用户到必要的组
sudo usermod -a -G docker $USER  # 如果使用Docker
```

---

## 📞 获取更多帮助

### 在线资源

1. **文档中心**: [完整文档](https://docs.example.com)
2. **视频教程**: [YouTube频道](https://youtube.com/example)
3. **社区论坛**: [讨论区](https://forum.example.com)

### 联系支持

- **邮箱支持**: support@example.com
- **GitHub Issues**: [提交问题](https://github.com/lion231226/quantitative-trading-platform/issues)
- **即时聊天**: [在线客服](https://chat.example.com)

### 贡献FAQ

如果您遇到的问题不在此列表中，欢迎：
1. 提交Issue帮助其他用户
2. 改进现有答案
3. 翻译成其他语言

---

*最后更新: 2025-11-06 | 版本: 1.0.0*

**💡 提示**: 使用搜索功能（Ctrl+F）快速找到您的问题！