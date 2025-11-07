# Redis多平台安装指南

当自动安装失败时，请参考以下手动安装指南：

## 🪟 Windows 安装指南

### 方法1: 使用Chocolatey（推荐）
```powershell
# 安装Chocolatey（如果尚未安装）
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装Redis
choco install redis-64
```

### 方法2: 使用WSL（Windows Subsystem for Linux）
```powershell
# 启用WSL
wsl --install

# 在WSL中按照Linux指南安装Redis
```

### 方法3: 下载官方Windows版本
1. 访问 [Microsoft Redis GitHub](https://github.com/microsoftarchive/redis/releases)
2. 下载最新的 `.msi` 文件
3. 运行安装程序并按照向导完成安装
4. 配置环境变量（可选）

### 方法4: 使用Docker Desktop
```powershell
# 安装Docker Desktop后运行
docker run -d --name redis -p 6379:6379 redis:latest
```

## 🍎 macOS 安装指南

### 方法1: 使用Homebrew（推荐）
```bash
# 安装Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Redis
brew install redis

# 启动Redis服务
brew services start redis
```

### 方法2: 使用MacPorts
```bash
sudo port install redis
sudo port load redis
```

### 方法3: 使用Docker
```bash
# 安装Docker Desktop后运行
docker run -d --name redis -p 6379:6379 redis:latest
```

## 🐧 Linux 安装指南

### Ubuntu/Debian
```bash
# 更新包列表
sudo apt update

# 安装Redis
sudo apt install redis-server

# 启动并启用Redis服务
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### CentOS/RHEL
```bash
# 安装EPEL仓库
sudo yum install epel-release

# 安装Redis
sudo yum install redis

# 启动并启用Redis服务
sudo systemctl start redis
sudo systemctl enable redis
```

### Fedora
```bash
# 安装Redis
sudo dnf install redis

# 启动并启用Redis服务
sudo systemctl start redis
sudo systemctl enable redis
```

### Arch Linux
```bash
# 安装Redis
sudo pacman -S redis

# 启动并启用Redis服务
sudo systemctl start redis
sudo systemctl enable redis
```

### 使用Docker（通用Linux）
```bash
# 安装Docker后运行
docker run -d --name redis -p 6379:6379 redis:latest
```

## 🔧 验证安装

### 1. 检查Redis服务状态
```bash
# Linux/macOS
sudo systemctl status redis

# Windows (使用Chocolatey)
Get-Service redis64

# Docker
docker ps | grep redis
```

### 2. 测试Redis连接
```bash
# 命令行测试
redis-cli ping

# 应该返回: PONG
```

### 3. 验证端口监听
```bash
# Linux/macOS
netstat -tlnp | grep 6379

# Windows
netstat -ano | findstr 6379
```

## 🛠️ 配置优化

### 基本配置文件位置
- **Linux/macOS**: `/etc/redis/redis.conf`
- **Windows**: `C:\ProgramData\redis\redis.windows.conf`
- **Docker**: 通过环境变量或挂载配置文件

### 推荐配置
```bash
# 设置内存限制
maxmemory 256mb
maxmemory-policy allkeys-lru

# 启用持久化
save 900 1
save 300 10
save 60 10000

# 网络配置
bind 127.0.0.1
port 6379
timeout 300
```

## 🔒 安全配置

### 1. 设置密码
```bash
# 在配置文件中设置
requirepass your_strong_password

# 或运行时设置
redis-cli CONFIG SET requirepass your_strong_password
```

### 2. 禁用危险命令
```bash
# 在配置文件中禁用
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 3. 网络安全
```bash
# 仅绑定本地接口
bind 127.0.0.1

# 如果需要远程访问，使用防火墙限制
sudo ufw allow from 192.168.1.0/24 to any port 6379
```

## 🔍 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查找占用端口的进程
   sudo netstat -tlnp | grep 6379
   sudo lsof -i :6379

   # 杀死进程或更改Redis端口
   ```

2. **权限问题**
   ```bash
   # 确保Redis用户有权限访问数据和日志目录
   sudo chown -R redis:redis /var/lib/redis
   sudo chown -R redis:redis /var/log/redis
   ```

3. **内存不足**
   ```bash
   # 调整系统内存设置
   echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf
   sudo sysctl vm.overcommit_memory=1
   ```

4. **服务启动失败**
   ```bash
   # 检查配置文件语法
   redis-server /path/to/redis.conf --test-memory

   # 查看详细日志
   sudo journalctl -u redis-server -f
   ```

## 📚 官方资源

- [Redis官方文档](https://redis.io/docs/)
- [Redis下载页面](https://redis.io/download)
- [Redis配置参考](https://redis.io/topics/config)
- [Redis安全指南](https://redis.io/topics/security)

## 💡 提示

1. **生产环境建议**:
   - 启用持久化（RDB + AOF）
   - 设置强密码
   - 配置适当的内存限制
   - 定期备份
   - 监控性能指标

2. **开发环境**:
   - 可以使用默认配置
   - Docker是最简单的选择
   - 考虑使用Redis Desktop GUI进行管理

3. **版本选择**:
   - 推荐使用最新的稳定版本
   - 检查与应用程序的兼容性要求

---

**注意**: 本指南会持续更新，如发现错误或有改进建议，请提交反馈。