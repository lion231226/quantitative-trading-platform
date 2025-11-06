# 故障排除指南

## 🔍 目录

- [环境问题](#环境问题)
- [服务问题](#服务问题)
- [性能问题](#性能问题)
- [网络问题](#网络问题)
- [权限问题](#权限问题)
- [数据问题](#数据问题)
- [浏览器问题](#浏览器问题)
- [高级诊断](#高级诊断)

---

## 🌡️ 环境问题

### Python 相关问题

#### 问题：Python版本不兼容
**错误信息**: `Python版本过低，需要3.11+`

**症状**:
- 启动器提示Python版本不支持
- 某些Python包安装失败
- 运行时出现语法错误

**解决方案**:

**Windows**:
1. 下载Python 3.11+：https://www.python.org/downloads/
2. 安装时勾选"Add Python to PATH"
3. 验证安装：
```cmd
python --version
pip --version
```

**macOS**:
```bash
# 使用Homebrew安装
brew install python@3.11

# 或从官网下载安装包
# https://www.python.org/downloads/macos/

# 验证安装
python3 --version
pip3 --version
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-pip python3.11-venv

# CentOS/RHEL
sudo yum install python311 python311-pip

# 验证安装
python3.11 --version
pip3.11 --version
```

#### 问题：pip版本过低或损坏
**错误信息**: `pip版本过低` 或 `pip损坏`

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装pip
python -m ensurepip --upgrade

# 如果仍有问题，重装pip
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

### Node.js 相关问题

#### 问题：Node.js未安装或版本过低
**错误信息**: `Node.js未安装或版本低于18.0`

**解决方案**:

**Windows**:
1. 下载Node.js LTS：https://nodejs.org/
2. 运行安装程序，默认设置即可
3. 验证安装：
```cmd
node --version
npm --version
```

**macOS**:
```bash
# 使用Homebrew
brew install node

# 使用nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
nvm use --lts
```

**Linux**:
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# 使用nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
```

#### 问题：npm安装速度慢或失败
**错误信息**: `npm install超时` 或 `网络错误`

**解决方案**:
```bash
# 清理npm缓存
npm cache clean --force

# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 或临时使用镜像
npm install --registry https://registry.npmmirror.com

# 使用yarn替代
npm install -g yarn
yarn install
```

### Git相关问题

#### 问题：Git未安装
**错误信息**: `git: command not found`

**解决方案**:

**Windows**:
1. 下载Git：https://git-scm.com/download/win
2. 安装时选择默认配置
3. 验证安装：`git --version`

**macOS**:
```bash
# 安装Xcode Command Line Tools
xcode-select --install

# 或使用Homebrew
brew install git
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install git

# CentOS/RHEL
sudo yum install git
```

---

## 🔄 服务问题

### 端口占用问题

#### 问题：端口8000或3000被占用
**错误信息**: `端口被占用` 或 `Address already in use`

**诊断方法**:
```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# macOS/Linux
lsof -i :8000
lsof -i :3000
```

**解决方案**:

**方法1：终止占用进程**
```bash
# Windows
taskkill /PID <进程ID> /F

# macOS/Linux
kill -9 <进程ID>
```

**方法2：使用自定义端口**
```bash
python launcher.py --backend-port 8001 --frontend-port 3001
```

**方法3：配置文件修改**
```yaml
# config/config.yaml
services:
  backend:
    port: 8001
  frontend:
    port: 3001
```

### 数据库连接问题

#### 问题：无法连接到数据库
**错误信息**: `数据库连接失败`

**诊断步骤**:
```bash
# 检查数据库文件是否存在
ls -la data/

# 检查数据库权限
ls -la data/*.db

# 测试数据库连接
python launcher.py --test-database
```

**解决方案**:

**SQLite问题**:
```bash
# 重新初始化数据库
python launcher.py --init-database

# 修复数据库权限
chmod 666 data/*.db
chown $USER:$USER data/
```

**PostgreSQL问题**:
```bash
# 检查PostgreSQL服务状态
sudo systemctl status postgresql

# 启动PostgreSQL服务
sudo systemctl start postgresql

# 检查连接配置
psql -h localhost -U postgres -d trading_db
```

### 服务启动失败

#### 问题：后端服务启动失败
**错误信息**: `后端服务启动失败`

**诊断方法**:
```bash
# 查看详细错误日志
tail -f logs/backend.log

# 手动启动后端服务
cd ../backend
python main.py

# 检查依赖是否完整
pip list | grep fastapi
pip list | grep sqlalchemy
```

**解决方案**:
```bash
# 重新安装后端依赖
cd ../backend
pip install -r requirements.txt

# 检查环境变量
echo $DATABASE_URL
echo $REDIS_URL

# 验证配置文件
cat ../backend/config.py
```

#### 问题：前端服务启动失败
**错误信息**: `前端服务启动失败`

**诊断方法**:
```bash
# 查看前端错误日志
cd ../frontend
npm run dev 2>&1 | tee frontend.log

# 检查Node.js版本
node --version
npm --version
```

**解决方案**:
```bash
# 重新安装前端依赖
cd ../frontend
rm -rf node_modules package-lock.json
npm install

# 清理npm缓存
npm cache clean --force

# 检查配置文件
cat next.config.js
cat package.json
```

---

## ⚡ 性能问题

### 启动速度慢

#### 问题：启动过程缓慢
**症状**: 启动时间超过5分钟

**诊断方法**:
```bash
# 启用调试模式查看详细进度
python launcher.py --debug --verbose

# 监控系统资源
python launcher.py --monitor-resources

# 检查磁盘IO
iostat -x 1  # Linux
# 或使用任务管理器查看（Windows）
```

**优化方案**:

**硬件优化**:
- 使用SSD硬盘
- 增加内存到8GB+
- 使用多核CPU

**软件优化**:
```bash
# 启用缓存模式
python launcher.py --enable-cache

# 跳过可选检查
python launcher.py --skip-optional-checks

# 并行下载
python launcher.py --parallel-download
```

**网络优化**:
```bash
# 使用国内镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
npm config set registry https://registry.npmmirror.com
```

### 内存占用过高

#### 问题：内存使用过高
**症状**: 系统变慢，内存占用超过1GB

**诊断方法**:
```bash
# 监控内存使用
python launcher.py --monitor-memory

# 检查进程内存占用
ps aux | grep launcher  # Linux/macOS
tasklist | findstr launcher  # Windows
```

**解决方案**:
```bash
# 启用内存优化模式
python launcher.py --memory-efficient

# 清理临时文件
python launcher.py --clean-temp

# 调整配置限制
# 编辑 config/config.yaml
performance:
  memory:
    max_usage: "512MB"
```

### CPU使用率过高

#### 问题：CPU占用率持续很高
**症状**: CPU使用率超过50%，系统响应慢

**诊断方法**:
```bash
# 检查CPU使用情况
top -p $(pgrep launcher)  # Linux/macOS
# 或使用任务管理器（Windows）

# 查看进程详情
ps -p $(pgrep launcher) -o pid,ppid,cmd,%cpu,%mem
```

**解决方案**:
```bash
# 降低并发数
python launcher.py --max-workers 2

# 启用性能模式
python launcher.py --performance-mode

# 调整配置
performance:
  cpu:
    max_workers: 2
    worker_timeout: 300
```

---

## 🌐 网络问题

### 连接超时

#### 问题：网络连接超时
**错误信息**: `连接超时` 或 `网络不可达`

**诊断方法**:
```bash
# 测试网络连接
ping google.com
python launcher.py --test-network

# 检查DNS解析
nslookup google.com
dig google.com  # Linux/macOS
```

**解决方案**:
```bash
# 使用代理
export HTTP_PROXY=http://proxy-server:port
export HTTPS_PROXY=http://proxy-server:port

# 或配置启动器使用代理
python launcher.py --proxy http://proxy-server:port

# 修改DNS服务器
# Windows：网络适配器设置
# macOS：系统偏好设置 → 网络 → 高级 → DNS
# Linux：编辑 /etc/resolv.conf
```

### 依赖下载失败

#### 问题：Python包下载失败
**错误信息**: `下载失败` 或 `网络错误`

**解决方案**:
```bash
# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ package-name

# 配置永久镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# 增加超时时间
pip install --timeout 300 package-name

# 离线安装（如果已有包）
pip install package-name --no-index --find-links file:///path/to/packages
```

#### 问题：npm包下载失败
**解决方案**:
```bash
# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 清理缓存重试
npm cache clean --force
npm install

# 使用yarn替代
npm install -g yarn
yarn install

# 增加超时时间
npm install --timeout 300000
```

### API调用失败

#### 问题：API服务无法访问
**症状**: 前端页面显示"网络错误"或"API不可用"

**诊断方法**:
```bash
# 测试API端点
curl http://localhost:8000/health
curl http://localhost:8000/docs

# 检查后端服务状态
python launcher.py --status

# 查看API日志
tail -f logs/api.log
```

**解决方案**:
```bash
# 重启后端服务
python launcher.py --restart-backend

# 检查防火墙设置
# Windows：防火墙设置 → 允许应用通过防火墙
# macOS：系统偏好设置 → 安全性与隐私 → 防火墙
# Linux：sudo ufw status

# 检查代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

---

## 🔐 权限问题

### 文件权限不足

#### 问题：无法创建或修改文件
**错误信息**: `权限被拒绝` 或 `Permission denied`

**Windows解决方案**:
```cmd
# 以管理员身份运行
# 右键 → 以管理员身份运行

# 或修改文件夹权限
# 右键文件夹 → 属性 → 安全 → 编辑权限
```

**macOS/Linux解决方案**:
```bash
# 修改文件权限
chmod +x launcher.py
chmod 755 data/
chmod 644 config/*.yaml

# 修改文件所有者
sudo chown -R $USER:$USER .

# 使用sudo运行
sudo python3 launcher.py
```

### 端口权限问题

#### 问题：无法绑定特权端口（<1024）
**错误信息**: `Permission denied: bind to port 80`

**解决方案**:
```bash
# 使用非特权端口（推荐）
python launcher.py --backend-port 8000 --frontend-port 3000

# 或使用sudo运行（不推荐）
sudo python launcher.py --backend-port 80
```

### 数据库权限问题

#### 问题：无法访问数据库文件
**错误信息**: `数据库访问被拒绝`

**解决方案**:
```bash
# 检查文件权限
ls -la data/*.db

# 修改数据库文件权限
chmod 666 data/*.db
chown $USER:$USER data/

# 重新初始化数据库
python launcher.py --init-database
```

---

## 💾 数据问题

### 数据库损坏

#### 问题：数据库文件损坏
**错误信息**: `数据库文件损坏` 或 `sqlite database disk image is malformed`

**解决方案**:
```bash
# 备份现有数据库
cp data/trading_platform.db data/trading_platform_backup.db

# 重新初始化数据库
python launcher.py --init-database

# 如果需要恢复数据
python launcher.py --restore-from-backup
```

### 数据丢失

#### 问题：数据文件丢失
**症状**: 平台显示没有数据或配置丢失

**解决方案**:
```bash
# 检查数据目录
ls -la data/

# 从备份恢复
python launcher.py --restore-data

# 重新初始化所有数据
python launcher.py --factory-reset
```

### 磁盘空间不足

#### 问题：磁盘空间不足
**错误信息**: `磁盘空间不足` 或 `No space left on device`

**诊断方法**:
```bash
# 检查磁盘使用情况
df -h  # Linux/macOS
# 或查看磁盘属性（Windows）

# 检查日志文件大小
du -sh logs/
ls -lh logs/*.log
```

**解决方案**:
```bash
# 清理日志文件
python launcher.py --clean-logs

# 清理缓存
python launcher.py --clean-cache

# 压缩旧数据
python launcher.py --compress-old-data

# 手动清理
rm -rf logs/*.log.old
rm -rf data/cache/*
```

---

## 🌍 浏览器问题

### 页面无法加载

#### 问题：浏览器无法访问平台
**症状**: 访问 http://localhost:3000 失败

**诊断方法**:
```bash
# 检查服务状态
python launcher.py --status

# 测试本地连接
curl http://localhost:3000

# 检查端口监听
netstat -an | grep 3000  # Linux/macOS
netstat -an | findstr 3000  # Windows
```

**解决方案**:
```bash
# 重启所有服务
python launcher.py --restart

# 只重启前端服务
python launcher.py --restart-frontend

# 手动访问其他浏览器
# 尝试Chrome、Firefox、Edge等不同浏览器
```

### 页面显示异常

#### 问题：页面布局错乱或功能异常
**症状**: 按钮点击无效、图表不显示、样式错误

**解决方案**:

**浏览器修复**:
1. 清除浏览器缓存和Cookie
2. 禁用浏览器扩展
3. 尝试无痕模式
4. 更新浏览器到最新版本

**前端修复**:
```bash
# 清理前端缓存
cd ../frontend
rm -rf .next/
npm run build

# 重新启动前端服务
python launcher.py --restart-frontend
```

### HTTPS/SSL问题

#### 问题：HTTPS证书错误
**错误信息**: `SSL证书错误` 或 `连接不安全`

**解决方案**:
```bash
# 如果启用了HTTPS，检查证书配置
ls -la certs/

# 或切换到HTTP模式
python launcher.py --no-https

# 重新生成证书
python launcher.py --generate-cert
```

---

## 🔧 高级诊断

### 系统诊断工具

#### 运行完整诊断
```bash
# 完整系统诊断
python launcher.py --diagnose

# 生成诊断报告
python launcher.py --generate-report

# 保存报告到文件
python launcher.py --generate-report --output diagnosis.json
```

#### 网络诊断
```bash
# 测试网络连接
python launcher.py --test-network

# 检查端口可用性
python launcher.py --check-ports

# DNS诊断
python launcher.py --test-dns
```

#### 性能诊断
```bash
# 系统性能测试
python launcher.py --benchmark

# 内存使用分析
python launcher.py --memory-profile

# 启动时间分析
python launcher.py --startup-profile
```

### 日志分析

#### 查看实时日志
```bash
# 查看所有日志
python launcher.py --follow-logs

# 查看特定服务日志
python launcher.py --follow-logs --service backend
python launcher.py --follow-logs --service frontend

# 查看错误日志
python launcher.py --follow-logs --level ERROR
```

#### 日志搜索和分析
```bash
# 搜索错误信息
grep "ERROR" logs/*.log

# 搜索特定时间段的日志
grep "2025-11-06 10:" logs/*.log

# 分析日志模式
python launcher.py --analyze-logs
```

### 配置验证

#### 验证配置文件
```bash
# 检查配置文件语法
python launcher.py --validate-config

# 检查配置兼容性
python launcher.py --check-compatibility

# 显示当前配置
python launcher.py --show-config
```

#### 测试服务连接
```bash
# 测试数据库连接
python launcher.py --test-database

# 测试缓存连接
python launcher.py --test-cache

# 测试API连接
python launcher.py --test-api
```

---

## 🆘 获取帮助

### 自动修复功能

启动器提供自动修复功能：
```bash
# 自动修复常见问题
python launcher.py --auto-fix

# 安全模式启动（最小配置）
python launcher.py --safe-mode

# 恢复出厂设置
python launcher.py --factory-reset
```

### 联系技术支持

如果问题仍未解决，请收集以下信息后联系技术支持：

1. **系统信息**：
```bash
python launcher.py --system-info > system-info.txt
```

2. **诊断报告**：
```bash
python launcher.py --generate-report > diagnosis.json
```

3. **错误日志**：
```bash
tar -czf logs.tar.gz logs/
```

4. **配置文件**：
```bash
cp config/config.yaml config-backup.yaml
```

**联系方式**：
- 📧 **邮箱**: support@example.com
- 💬 **在线客服**: 工作日 9:00-18:00
- 🐛 **GitHub Issues**: https://github.com/your-repo/issues
- 📱 **微信群**: 扫描二维码加入

### 社区支持

- **用户论坛**: https://forum.example.com
- **QQ群**: 123456789
- **Telegram群**: @trading-platform-support

---

## 📋 预防措施

### 定期维护

**每日**：
- 检查系统状态
- 查看错误日志
- 清理临时文件

**每周**：
- 备份重要数据
- 更新依赖包
- 清理日志文件

**每月**：
- 全面系统检查
- 性能优化
- 安全更新

### 监控设置

```bash
# 启用自动监控
python launcher.py --enable-monitoring

# 设置警报阈值
python launcher.py --set-alert-thresholds

# 配置监控报告
python launcher.py --configure-monitoring
```

---

*最后更新: 2025-11-06 | 版本: 1.0.0*

**💡 提示**: 大多数问题都可以通过重启解决。如果遇到问题，首先尝试 `python launcher.py --restart`。