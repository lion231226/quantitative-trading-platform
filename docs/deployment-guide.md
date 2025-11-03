# 量化交易单均线策略分析平台 - 部署指南

**版本:** 1.0.0
**日期:** 2025-11-03
**适用环境:** Vercel、本地开发、Docker

---

## 📋 **目录**

1. [部署概览](#部署概览)
2. [Vercel部署（推荐）](#vercel部署推荐)
3. [本地部署](#本地部署)
4. [环境配置](#环境配置)
5. [故障排除](#故障排除)

---

## 🎯 **部署概览**

### **技术架构**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (Next.js) │────│  后端 (FastAPI) │────│  数据 (SQLite)  │
│   Port: 3000    │    │   Port: 8000    │    │   本地文件      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│  缓存 (Redis)   │──────────────┘
                        │   Port: 6379    │
                        └─────────────────┘
```

### **部署要求**

**最低要求:**
- Node.js 18+
- Python 3.12+
- Redis 7.2+
- 2GB RAM
- 10GB 存储空间

**推荐配置:**
- Node.js 20+
- Python 3.12+
- Redis 7.2+
- 4GB RAM
- 20GB 存储空间

---

## 🚀 **Vercel部署（推荐）**

### **第一步：准备代码仓库**

```bash
# 1. 确保代码在GitHub仓库
git remote -v
# 应该显示origin指向你的GitHub仓库

# 2. 检查分支结构
git branch -a
# 确保main分支包含最新代码

# 3. 推送最新代码
git push origin main
```

### **第二步：Vercel项目设置**

#### **A. 连接GitHub仓库**

1. 访问 [vercel.com](https://vercel.com)
2. 点击 "New Project"
3. 导入GitHub仓库
4. 选择项目目录

#### **B. 环境变量配置**

在Vercel控制台设置以下环境变量：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./quant_trading.db
REDIS_URL=redis://localhost:6379

# API配置
AKSHARE_CACHE_TTL=86400
MAX_RETRY_ATTEMPTS=3
API_TIMEOUT=10

# 安全配置
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://your-domain.vercel.app

# 功能开关
ENABLE_CACHE=true
ENABLE_LOGGING=true
LOG_LEVEL=INFO
```

### **第三步：部署执行**

```bash
# 1. 触发部署
git push origin main

# 2. 监控部署日志
# 在Vercel控制台查看部署进度

# 3. 验证部署
curl https://your-domain.vercel.app/api/health
```

---

## 💻 **本地部署**

### **第一步：环境准备**

```bash
# 1. 安装Python 3.12+
python --version  # 应该显示3.12.x

# 2. 安装Node.js 18+
node --version    # 应该显示18.x.x

# 3. 安装pnpm
npm install -g pnpm

# 4. 安装Redis
# Windows: 使用WSL或Docker
# macOS: brew install redis
# Linux: sudo apt-get install redis-server
```

### **第二步：项目设置**

```bash
# 1. 克隆项目
git clone https://github.com/your-username/quant-trading-platform.git
cd quant-trading-platform

# 2. 设置后端环境
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 3. 设置前端环境
cd ../frontend
pnpm install
```

### **第三步：启动服务**

```bash
# 1. 启动Redis（新终端）
redis-server

# 2. 启动后端（新终端）
cd backend
uvicorn main:app --reload --port 8000

# 3. 启动前端（新终端）
cd frontend
pnpm dev

# 4. 访问应用
# 前端: http://localhost:3000
# 后端API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

---

## ⚙️ **环境配置**

### **生产环境变量**

```bash
# 必需变量
DATABASE_URL=sqlite:///./quant_trading.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-super-secret-key

# API配置
AKSHARE_CACHE_TTL=86400
MAX_RETRY_ATTEMPTS=3
API_TIMEOUT=10

# 前端配置
NEXT_PUBLIC_API_URL=https://your-domain.vercel.app
```

### **开发环境变量**

```bash
# 开发配置
NODE_ENV=development
PYTHON_ENV=development
LOG_LEVEL=DEBUG

# 本地服务
NEXT_PUBLIC_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
```

---

## 🔧 **故障排除**

### **常见问题及解决方案**

#### **1. 前端无法连接后端**

**症状**: 前端显示网络错误，API调用失败

**解决方案**:
```bash
# 1. 确保后端服务正在运行
cd backend && uvicorn main:app --reload --port 8000

# 2. 检查环境变量
echo $NEXT_PUBLIC_API_URL

# 3. 检查CORS配置
# 在backend/main.py中添加:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### **2. Redis连接失败**

**症状**: 应用启动时显示Redis连接错误

**解决方案**:
```bash
# 1. 启动Redis服务
redis-server

# 2. 或使用Docker启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 3. 检查环境变量
echo $REDIS_URL
```

#### **3. 数据库文件权限问题**

**症状**: SQLite数据库无法创建或访问

**解决方案**:
```bash
# 1. 修改文件权限
chmod 664 backend/quant_trading.db

# 2. 修改目录权限
chmod 755 backend/

# 3. 创建数据库目录
mkdir -p backend/data
chmod 755 backend/data
```

#### **4. AKShare API调用失败**

**症状**: 数据获取失败，显示API错误

**解决方案**:
```bash
# 1. 升级AKShare
pip install --upgrade akshare

# 2. 清除缓存
pip cache purge

# 3. 检查网络连接
ping api.akshare.xyz
```

---

## 📋 **部署检查清单**

### **部署前检查**

- [ ] 代码已推送到GitHub仓库
- [ ] 环境变量已配置
- [ ] 依赖版本已锁定
- [ ] 健康检查端点已实现
- [ ] 日志配置已完成
- [ ] 错误处理已测试

### **部署后验证**

- [ ] 主页可以正常访问
- [ ] API健康检查通过
- [ ] 数据库连接正常
- [ ] Redis缓存工作正常
- [ ] 核心功能测试通过
- [ ] 性能指标正常
- [ ] 错误监控已启用

---

## 📊 **性能监控**

### **健康检查端点**

```python
# backend/api/health.py
from fastapi import APIRouter
import redis
import sqlite3
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """系统健康检查"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # 检查数据库
    try:
        conn = sqlite3.connect("quant_trading.db")
        status["services"]["database"] = "healthy"
        conn.close()
    except Exception as e:
        status["services"]["database"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    # 检查Redis
    try:
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        status["services"]["redis"] = "healthy"
    except Exception as e:
        status["services"]["redis"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    return status
```

---

**🎉 部署成功！**

如有问题，请参考故障排除部分或联系技术支持。

*最后更新: 2025-11-03*