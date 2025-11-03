@echo off
echo 🚀 量化交易策略分析平台 - 云端部署开始
echo ==========================================

:: 检查 Node.js
echo 📋 检查部署要求...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js 未安装，请先安装 Node.js
    pause
    exit /b 1
)

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 未安装，请先安装 Python
    pause
    exit /b 1
)

:: 检查 Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git 未安装，请先安装 Git
    pause
    exit /b 1
)

echo ✅ 所有检查通过

:: 前端部署
echo 🌐 部署前端到 Vercel...
cd frontend

:: 安装依赖
echo 📦 安装前端依赖...
npm install

:: 构建项目
echo 🔨 构建前端项目...
npm run build

:: 检查 Vercel CLI
vercel --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 安装 Vercel CLI...
    npm i -g vercel
)

:: 部署前端
echo 🚀 部署前端到 Vercel...
vercel --prod

cd ..

:: 后端部署
echo ⚙️ 部署后端到 Railway...
cd backend

:: 检查 Railway CLI
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 安装 Railway CLI...
    npm i -g @railway/cli
)

:: 登录 Railway
echo 🔐 登录 Railway...
railway login

:: 部署后端
echo 🚀 部署后端到 Railway...
railway up

cd ..

:: 生成部署报告
echo 📊 生成部署报告...
echo # 量化交易策略分析平台 - 部署报告 > deployment-report.md
echo. >> deployment-report.md
echo ## 部署信息 >> deployment-report.md
echo - **部署时间**: %date% %time% >> deployment-report.md
echo - **前端URL**: https://your-app.vercel.app >> deployment-report.md
echo - **后端URL**: https://your-backend.up.railway.app >> deployment-report.md
echo - **版本**: v1.0.0 >> deployment-report.md
echo. >> deployment-report.md
echo ## 技术栈 >> deployment-report.md
echo - **前端**: Next.js 14 + TypeScript + Tailwind CSS >> deployment-report.md
echo - **后端**: FastAPI + Python 3.11 >> deployment-report.md
echo - **部署**: Vercel (前端) + Railway (后端) >> deployment-report.md

echo ✅ 部署完成！
echo 🌐 请查看 Vercel 控制台获取前端 URL
echo ⚙️ 请查看 Railway 控制台获取后端 URL
echo 📊 部署报告已生成: deployment-report.md
echo.
echo 💡 下一步操作:
echo 1. 在 Vercel 中配置环境变量 NEXT_PUBLIC_API_URL
echo 2. 在 Railway 中配置必要的环境变量
echo 3. 测试应用功能是否正常
echo.
pause