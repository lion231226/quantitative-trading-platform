@echo off
REM 量化交易前端部署脚本
REM 使用说明：deploy.bat [环境] [方法]

setlocal enabledelayedexpansion

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=production

set METHOD=%2
if "%METHOD%"=="" set METHOD=static

echo 🚀 开始部署量化交易前端应用...
echo 环境: %ENVIRONMENT%
echo 方法: %METHOD%

REM 进入前端目录
cd frontend

REM 检查环境变量文件
if not exist ".env.local" (
    echo ⚠️  未找到 .env.local 文件，使用 .env.example 创建...
    copy .env.example .env.local
    echo 📝 请编辑 frontend\.env.local 文件设置正确的环境变量
    echo    特别是 NEXT_PUBLIC_API_URL
    pause
)

REM 根据方法选择部署方式
if "%METHOD%"=="static" (
    echo 📦 构建静态文件...
    call npm run deploy:static
    echo ✅ 静态文件已生成在 frontend\out\ 目录
    echo 💡 你可以使用这些文件部署到静态托管服务
    echo    访问 https://app.netlify.com/drop 拖拽 out 文件夹
) else if "%METHOD%"=="build-only" (
    echo 📦 仅构建项目...
    call npm run build
    echo ✅ 构建完成，文件在 frontend\.next 目录
) else if "%METHOD%"=="vercel" (
    echo 📦 使用 Vercel 部署...
    echo ⚠️  如果 Vercel CLI 有问题，请使用 Vercel Dashboard 方法
    echo    访问 https://vercel.com/new
    echo    导入你的 Git 仓库并设置：
    echo    - Root Directory: frontend
    echo    - Build Command: npm run build
    echo    - Output Directory: .next
) else (
    echo ❌ 未知的部署方法: %METHOD%
    echo 可用的方法: static, build-only, vercel
    goto :end
)

echo.
echo 🎉 部署脚本执行完成！
echo.
echo 📚 更多部署选项请查看: frontend\DEPLOYMENT.md

:end
pause