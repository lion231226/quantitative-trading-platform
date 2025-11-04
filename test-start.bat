@echo off
echo =====================================
echo   量化交易平台 Windows 测试脚本
echo =====================================

echo.
echo [INFO] 检查运行环境...

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装或未添加到 PATH
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [INFO] ✓ Python 版本: %PYTHON_VERSION%

:: 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js 未安装或未添加到 PATH
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [INFO] ✓ Node.js 版本: %NODE_VERSION%

:: 检查 npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm 未安装
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [INFO] ✓ npm 版本: %NPM_VERSION%

echo.
echo [INFO] ✅ 环境检查通过

:: 进入后端目录
echo.
echo [INFO] 启动后端服务...
cd backend

:: 检查虚拟环境
if not exist "venv" (
    echo [INFO] 创建Python虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] 无法激活虚拟环境
    pause
    exit /b 1
)

:: 升级pip
echo [INFO] 升级pip...
python -m pip install --upgrade pip

:: 安装依赖
echo [INFO] 安装Python依赖...
pip install -r requirements.txt

:: 创建必要目录
if not exist "..\data" mkdir ..\data
if not exist "..\logs" mkdir ..\logs

:: 启动后端服务
echo.
echo [INFO] 启动FastAPI服务...
echo [INFO] 后端服务: http://localhost:8000
echo [INFO] 按 Ctrl+C 停止服务
echo.

:: 启动后端（在新窗口中）
start "量化交易后端" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
timeout /t 10 /nobreak >nul

:: 进入前端目录
echo.
echo [INFO] 启动前端服务...
cd ..\frontend

:: 安装前端依赖
if not exist "node_modules" (
    echo [INFO] 安装Node.js依赖...
    npm install
)

:: 启动前端服务
echo [INFO] 启动Next.js服务...
echo [INFO] 前端服务: http://localhost:3000

:: 启动前端（在新窗口中）
start "量化交易前端" cmd /k "npm run dev"

:: 等待前端启动
timeout /t 15 /nobreak >nul

:: 显示访问信息
echo.
echo =====================================
echo 🎉 量化交易平台启动成功！
echo =====================================
echo.
echo 服务访问地址：
echo   • 前端应用: http://localhost:3000
echo   • 后端API:  http://localhost:8000
echo   • API文档:  http://localhost:8000/docs
echo.
echo 两个服务已在独立的命令行窗口中启动
echo 关闭对应的窗口即可停止服务
echo.
pause