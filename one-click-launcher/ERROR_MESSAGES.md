# 常见错误消息和解决方案

## 🔍 快速索引

| 错误类型 | 错误消息 | 解决方案 |
|---------|----------|----------|
| [环境错误](#环境错误) | Python版本过低 | [升级Python](#python版本过低) |
| [依赖错误](#依赖错误) | pip安装失败 | [配置镜像源](#pip安装失败) |
| [服务错误](#服务错误) | 端口被占用 | [修改端口或终止进程](#端口被占用) |
| [权限错误](#权限错误) | Permission denied | [修改权限](#权限不足) |
| [网络错误](#网络错误) | 连接超时 | [检查网络配置](#网络连接超时) |

---

## 🚨 环境错误

### Python版本过低

**错误消息**:
```
错误: Python版本过低，需要3.11+
当前版本: Python 3.9.7
```

**快速解决**:
```bash
# Windows: 从 https://www.python.org/downloads/ 下载Python 3.11+

# macOS: 使用Homebrew
brew install python@3.11

# Linux: Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-pip
```

### Python未找到

**错误消息**:
```
错误: 未找到Python
请确保已安装Python 3.11+并添加到PATH环境变量
```

**解决方案**:

**Windows**:
1. 重新安装Python，确保勾选"Add Python to PATH"
2. 或手动添加到PATH：
   - 系统属性 → 高级 → 环境变量
   - 添加Python安装路径（如 `C:\Python311\`）

**macOS/Linux**:
```bash
# 添加到shell配置文件
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 或创建符号链接
sudo ln -s /usr/bin/python3.11 /usr/bin/python
```

### Node.js未安装

**错误消息**:
```
错误: 未找到Node.js
需要Node.js 18.0.0+版本
```

**解决方案**:

**Windows**:
1. 访问 https://nodejs.org/ 下载LTS版本
2. 运行安装程序

**macOS**:
```bash
# 使用Homebrew
brew install node

# 使用nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
```

**Linux**:
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Git未安装

**错误消息**:
```
错误: 未找到Git
请先安装Git工具
```

**解决方案**:

**Windows**: 从 https://git-scm.com/download/win 下载安装

**macOS**:
```bash
# 安装Xcode Command Line Tools
xcode-select --install
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install git

# CentOS/RHEL
sudo yum install git
```

---

## 📦 依赖错误

### pip安装失败

**错误消息**:
```
错误: pip安装失败
超时或网络错误
```

**解决方案**:

**方法1: 使用国内镜像**
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ package-name

# 配置永久镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

**方法2: 增加超时时间**
```bash
pip install --timeout 300 package-name
```

**方法3: 离线安装**
```bash
pip install --no-index --find-links file:///path/to/packages package-name
```

### npm install失败

**错误消息**:
```
错误: npm install失败
网络错误或权限不足
```

**解决方案**:

**方法1: 清理缓存**
```bash
npm cache clean --force
npm install
```

**方法2: 使用国内镜像**
```bash
npm config set registry https://registry.npmmirror.com
npm install
```

**方法3: 使用yarn替代**
```bash
npm install -g yarn
yarn install
```

### 模块导入错误

**错误消息**:
```
ModuleNotFoundError: No module named 'package_name'
```

**解决方案**:
```bash
# 安装缺失的模块
pip install package-name

# 检查Python路径
python -c "import sys; print(sys.path)"

# 重新安装所有依赖
pip install -r requirements.txt
```

### 包版本冲突

**错误消息**:
```
错误: 包版本冲突
package-a requires package-b==1.0.0, but package-b==2.0.0 is installed
```

**解决方案**:
```bash
# 查看冲突详情
pip check

# 降级包版本
pip install package-b==1.0.0

# 或升级冲突包
pip install --upgrade package-a

# 使用虚拟环境避免冲突
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

---

## 🔄 服务错误

### 端口被占用

**错误消息**:
```
错误: 端口8000被占用
请停止占用该端口的程序或使用其他端口
```

**解决方案**:

**方法1: 查找并终止进程**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# macOS/Linux
lsof -i :8000
kill -9 <进程ID>
```

**方法2: 使用自定义端口**
```bash
python launcher.py --backend-port 8001 --frontend-port 3001
```

### 服务启动失败

**错误消息**:
```
错误: 后端服务启动失败
启动超时或配置错误
```

**解决方案**:

**检查日志**:
```bash
tail -f logs/backend.log
```

**手动启动测试**:
```bash
cd ../backend
python main.py
```

**检查依赖**:
```bash
pip list | grep fastapi
pip install fastapi uvicorn
```

### 数据库连接失败

**错误消息**:
```
错误: 数据库连接失败
无法连接到数据库服务器
```

**解决方案**:

**SQLite问题**:
```bash
# 检查数据库文件
ls -la data/*.db

# 重新初始化数据库
python launcher.py --init-database

# 修复权限
chmod 666 data/*.db
```

**PostgreSQL问题**:
```bash
# 检查服务状态
sudo systemctl status postgresql

# 启动服务
sudo systemctl start postgresql

# 测试连接
psql -h localhost -U postgres
```

### 前端构建失败

**错误消息**:
```
错误: 前端构建失败
TypeScript错误或依赖缺失
```

**解决方案**:
```bash
# 清理缓存
cd ../frontend
rm -rf .next node_modules package-lock.json

# 重新安装依赖
npm install

# 检查TypeScript配置
npx tsc --noEmit

# 重新构建
npm run build
```

---

## 🔐 权限错误

### Permission denied

**错误消息**:
```
PermissionError: [Errno 13] Permission denied: 'filename'
```

**解决方案**:

**Windows**:
```cmd
# 以管理员身份运行
# 或修改文件权限：右键文件 → 属性 → 安全
```

**macOS/Linux**:
```bash
# 修改文件权限
chmod +x launcher.py
chmod 755 data/

# 修改所有者
sudo chown -R $USER:$USER .
```

### 无法创建文件

**错误消息**:
```
错误: 无法创建配置文件
权限不足或磁盘空间不足
```

**解决方案**:
```bash
# 检查磁盘空间
df -h

# 检查目录权限
ls -la config/

# 创建必要的目录
mkdir -p data logs

# 修改权限
chmod 755 data logs
```

### 管理员权限不足

**错误消息**:
```
错误: 需要管理员权限
请以管理员身份运行
```

**解决方案**:

**Windows**:
- 右键点击程序 → "以管理员身份运行"
- 或使用管理员权限的命令提示符

**macOS/Linux**:
```bash
sudo python3 launcher.py
# 输入用户密码
```

---

## 🌐 网络错误

### 网络连接超时

**错误消息**:
```
错误: 网络连接超时
无法下载依赖或访问API
```

**解决方案**:

**检查网络连接**:
```bash
ping google.com
curl -I https://www.python.org
```

**配置代理**:
```bash
export HTTP_PROXY=http://proxy-server:port
export HTTPS_PROXY=http://proxy-server:port

# 或使用启动器参数
python launcher.py --proxy http://proxy-server:port
```

**使用镜像源**:
```bash
# Python包
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# Node.js包
npm config set registry https://registry.npmmirror.com
```

### DNS解析失败

**错误消息**:
```
错误: DNS解析失败
无法解析域名
```

**解决方案**:

**检查DNS设置**:
```bash
nslookup google.com
dig google.com
```

**更换DNS服务器**:
- Windows: 网络适配器 → DNS设置 → 使用 `8.8.8.8` 和 `8.8.4.4`
- macOS: 系统偏好设置 → 网络 → 高级 → DNS
- Linux: 编辑 `/etc/resolv.conf`

### API调用失败

**错误消息**:
```
错误: API调用失败
HTTP 500 Internal Server Error
```

**解决方案**:

**检查后端服务**:
```bash
# 测试API端点
curl http://localhost:8000/health

# 查看API日志
tail -f logs/api.log

# 重启后端服务
python launcher.py --restart-backend
```

**检查防火墙**:
```bash
# Windows: 防火墙设置
# macOS: 系统偏好设置 → 安全性与隐私 → 防火墙
# Linux: sudo ufw status
```

---

## 💾 数据错误

### 数据库文件损坏

**错误消息**:
```
错误: 数据库文件损坏
sqlite database disk image is malformed
```

**解决方案**:
```bash
# 备份现有数据库
cp data/trading_platform.db data/trading_platform_backup.db

# 重新初始化数据库
python launcher.py --init-database

# 尝试修复（SQLite）
sqlite3 data/trading_platform.db ".recover" | sqlite3 data/recovered.db
```

### 数据丢失

**错误消息**:
```
警告: 数据文件丢失或损坏
正在尝试恢复...
```

**解决方案**:
```bash
# 从备份恢复
python launcher.py --restore-from-backup

# 重新初始化所有数据
python launcher.py --factory-reset

# 检查数据目录
ls -la data/
```

### 磁盘空间不足

**错误消息**:
```
错误: 磁盘空间不足
No space left on device
```

**解决方案**:
```bash
# 检查磁盘使用情况
df -h

# 清理日志文件
python launcher.py --clean-logs

# 清理缓存
python launcher.py --clean-cache

# 手动清理
rm -rf logs/*.log.old
rm -rf data/cache/*
```

---

## 🔧 系统错误

### 内存不足

**错误消息**:
```
错误: 内存不足
MemoryError 或 系统响应缓慢
```

**解决方案**:
```bash
# 检查内存使用
free -h  # Linux/macOS
# 或使用任务管理器（Windows）

# 启用内存优化模式
python launcher.py --memory-efficient

# 清理临时文件
python launcher.py --clean-temp

# 重启系统释放内存
```

### CPU使用率过高

**错误消息**:
```
警告: CPU使用率过高
系统可能过载
```

**解决方案**:
```bash
# 降低并发数
python launcher.py --max-workers 2

# 启用性能模式
python launcher.py --performance-mode

# 检查进程状态
top -p $(pgrep launcher)
```

### 文件锁定

**错误消息**:
```
错误: 文件被锁定
无法访问或修改文件
```

**解决方案**:
```bash
# 查找锁定文件的进程
lsof +D /path/to/directory

# 终止锁定进程
kill -9 <PID>

# 重启系统
reboot
```

---

## 🔍 调试技巧

### 启用调试模式

```bash
# 基本调试
python launcher.py --debug

# 详细调试
python launcher.py --debug --verbose

# 保存调试日志
python launcher.py --debug --log-file debug.log
```

### 查看详细错误

```bash
# 查看实时日志
tail -f logs/launcher.log

# 搜索错误信息
grep "ERROR" logs/*.log

# 查看堆栈跟踪
python launcher.py --show-traceback
```

### 系统诊断

```bash
# 完整诊断
python launcher.py --diagnose

# 生成诊断报告
python launcher.py --generate-report

# 测试系统环境
python launcher.py --check-system
```

---

## 📞 错误报告模板

如果需要联系技术支持，请使用以下模板：

```
错误报告
========

1. 系统信息：
   - 操作系统: [Windows 11/macOS 13/Ubuntu 22.04]
   - Python版本: [3.11.5]
   - Node.js版本: [18.17.0]
   - 内存: [8GB]
   - 磁盘空间: [50GB可用]

2. 错误描述：
   [详细描述遇到的问题]

3. 错误消息：
   [粘贴完整的错误消息]

4. 复现步骤：
   1. [步骤1]
   2. [步骤2]
   3. [步骤3]

5. 已尝试的解决方案：
   - [解决方案1]
   - [解决方案2]

6. 附加信息：
   [任何其他相关信息]

7. 系统诊断输出：
   [运行 python launcher.py --diagnose 的输出]
```

---

## 🔧 快速修复命令

```bash
# 常用修复命令
python launcher.py --restart              # 重启所有服务
python launcher.py --clean-cache          # 清理缓存
python launcher.py --clean-logs           # 清理日志
python launcher.py --auto-fix             # 自动修复
python launcher.py --safe-mode            # 安全模式启动
python launcher.py --factory-reset        # 恢复出厂设置
```

---

*最后更新: 2025-11-06 | 版本: 1.0.0*