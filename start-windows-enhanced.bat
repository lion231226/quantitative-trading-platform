@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ========================================
:: 🚀 量化交易平台增强版启动脚本 (Windows)
:: ========================================

:: 颜色定义
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "MAGENTA=[95m"
set "CYAN=[96m"
set "WHITE=[97m"
set "NC=[0m"

:: 标题显示
echo %CYAN%======================================%NC%
echo %CYAN%  量化交易平台增强版启动脚本        %NC%
echo %CYAN%  Enhanced Windows Launcher          %NC%
echo %CYAN%======================================%NC%
echo.

:: 环境检查函数
:check_environment
echo %GREEN%[INFO]%NC% 检查运行环境...

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Python 未安装或未添加到 PATH
    echo %YELLOW%[HELP]%NC% 请从 https://www.python.org/downloads/ 下载安装 Python 3.11+
    echo %YELLOW%[HELP]%NC% 安装时请勾选 "Add Python to PATH" 选项
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✓%NC% Python 版本: %PYTHON_VERSION%

:: 检查Python版本是否满足要求 (3.11+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if %MAJOR% lss 3 (
    echo %RED%[ERROR]%NC% Python 版本过低，需要 3.11+，当前版本: %PYTHON_VERSION%
    pause
    exit /b 1
)
if %MAJOR% equ 3 if %MINOR% lss 11 (
    echo %RED%[ERROR]%NC% Python 版本过低，需要 3.11+，当前版本: %PYTHON_VERSION%
    pause
    exit /b 1
)

:: 检查Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Node.js 未安装或未添加到 PATH
    echo %YELLOW%[HELP]%NC% 请从 https://nodejs.org/ 下载安装 Node.js 18+
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo %GREEN%✓%NC% Node.js 版本: %NODE_VERSION%

:: 检查npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% npm 未安装
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo %GREEN%✓%NC% npm 版本: %NPM_VERSION%

:: 检查Git (可选)
git --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
    echo %GREEN%✓%NC% Git 版本: !GIT_VERSION!
) else (
    echo %YELLOW%[WARNING]%NC% Git 未安装 (可选，不影响运行)
)

:: 检查端口占用
echo %GREEN%[INFO]%NC% 检查端口占用情况...

netstat -an | findstr ":3000" >nul 2>&1
if %errorlevel% equ 0 (
    echo %YELLOW%[WARNING]%NC% 端口 3000 已被占用
    choice /M "是否要停止占用端口3000的进程"
    if !errorlevel! equ 1 (
        for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":3000"') do (
            taskkill /F /PID %%i >nul 2>&1
        )
        echo %GREEN%[INFO]%NC% 已停止占用端口3000的进程
    )
)

netstat -an | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo %YELLOW%[WARNING]%NC% 端口 8000 已被占用
    choice /M "是否要停止占用端口8000的进程"
    if !errorlevel! equ 1 (
        for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":8000"') do (
            taskkill /F /PID %%i >nul 2>&1
        )
        echo %GREEN%[INFO]%NC% 已停止占用端口8000的进程
    )
)

echo %GREEN%✅%NC% 环境检查通过
echo.

:: 启动后端服务
:start_backend
echo %GREEN%[INFO]%NC% 启动后端服务...
cd backend

:: 创建必要目录
if not exist "..\data" mkdir "..\data"
if not exist "..\logs" mkdir "..\logs"
if not exist "..\temp" mkdir "..\temp"

:: 检查虚拟环境
if not exist "venv" (
    echo %GREEN%[INFO]%NC% 创建Python虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo %GREEN%✓%NC% 虚拟环境创建成功
)

:: 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo %GREEN%✓%NC% 虚拟环境激活成功
) else (
    echo %RED%[ERROR]%NC% 无法激活虚拟环境
    pause
    exit /b 1
)

:: 升级pip
echo %GREEN%[INFO]%NC% 升级pip...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% pip升级失败，继续使用现有版本
)

:: 检查requirements文件
if not exist "requirements.txt" (
    echo %RED%[ERROR]%NC% requirements.txt 文件不存在
    pause
    exit /b 1
)

:: 安装依赖
echo %GREEN%[INFO]%NC% 安装Python依赖...
echo %YELLOW%[INFO]%NC% 首次安装可能需要几分钟，请耐心等待...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Python依赖安装失败
    echo %YELLOW%[HELP]%NC% 尝试手动运行: pip install -r requirements.txt
    pause
    exit /b 1
)
echo %GREEN%✓%NC% Python依赖安装完成

:: 创建环境变量文件
if not exist ".env" (
    echo %GREEN%[INFO]%NC% 创建后端环境配置...
    (
        echo # 后端配置
        echo DATABASE_URL=sqlite:///./../data/quant_trading.db
        echo REDIS_URL=redis://localhost:6379
        echo PYTHONPATH=%CD%
        echo LOG_LEVEL=INFO
        echo.
        echo # API配置
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo API_RELOAD=true
        echo.
        echo # AKShare配置
        echo AKSHARE_TIMEOUT=30
        echo AKSHARE_RETRY=3
    ) > .env
    echo %GREEN%✓%NC% 环境配置创建完成
)

:: 启动后端服务
echo %GREEN%[INFO]%NC% 启动FastAPI服务...
echo %CYAN%[INFO]%NC% 后端服务地址: http://localhost:8000
echo %CYAN%[INFO]%NC% API文档地址: http://localhost:8000/docs
echo.

:: 在新窗口中启动后端
start "量化交易-后端服务" cmd /k "title 量化交易-后端服务 && cd /d %CD% && call venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
echo %GREEN%[INFO]%NC% 等待后端服务启动...
timeout /t 15 /nobreak >nul

cd ..

:: 启动前端服务
:start_frontend
echo.
echo %GREEN%[INFO]%NC% 启动前端服务...
cd frontend

:: 检查package.json
if not exist "package.json" (
    echo %RED%[ERROR]%NC% package.json 文件不存在
    pause
    exit /b 1
)

:: 创建环境变量文件
if not exist ".env.local" (
    echo %GREEN%[INFO]%NC% 创建前端环境配置...
    (
        echo # 前端配置
        echo NEXT_PUBLIC_API_URL=http://localhost:8000
        echo NEXT_PUBLIC_NODE_ENV=development
        echo NEXT_PUBLIC_APP_NAME=量化交易平台
        echo NEXT_PUBLIC_APP_VERSION=1.0.0
        echo.
        echo # API配置
        echo NEXT_PUBLIC_API_TIMEOUT=30000
        echo NEXT_PUBLIC_API_RETRY=3
    ) > .env.local
    echo %GREEN%✓%NC% 前端环境配置创建完成
)

:: 安装前端依赖
if not exist "node_modules" (
    echo %GREEN%[INFO]%NC% 安装Node.js依赖...
    echo %YELLOW%[INFO]%NC% 首次安装可能需要几分钟，请耐心等待...
    npm install --silent
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Node.js依赖安装失败
        echo %YELLOW%[HELP]%NC% 尝试手动运行: npm install
        pause
        exit /b 1
    )
    echo %GREEN%✓%NC% Node.js依赖安装完成
)

:: 启动前端服务
echo %GREEN%[INFO]%NC% 启动Next.js服务...
echo %CYAN%[INFO]%NC% 前端服务地址: http://localhost:3000
echo.

:: 在新窗口中启动前端
start "量化交易-前端服务" cmd /k "title 量化交易-前端服务 && cd /d %CD% && npm run dev"

:: 等待前端启动
echo %GREEN%[INFO]%NC% 等待前端服务启动...
timeout /t 20 /nobreak >nul

cd ..

:: 服务验证
:verify_services
echo.
echo %GREEN%[INFO]%NC% 验证服务状态...

:: 检查后端服务
timeout /t 5 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓%NC% 后端服务运行正常
) else (
    echo %YELLOW%⚠%NC% 后端服务启动中，请稍等...
)

:: 检查前端服务
timeout /t 5 /nobreak >nul
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓%NC% 前端服务运行正常
) else (
    echo %YELLOW%⚠%NC% 前端服务启动中，请稍等...
)

:: 显示成功信息
:show_success
echo.
echo %CYAN%======================================%NC%
echo %GREEN%🎉 量化交易平台启动成功！%NC%
echo %CYAN%======================================%NC%
echo.
echo %BLUE%服务访问地址：%NC%
echo   %WHITE%•%NC% 前端应用: %YELLOW%http://localhost:3000%NC%
echo   %WHITE%•%NC% 后端API:  %YELLOW%http://localhost:8000%NC%
echo   %WHITE%•%NC% API文档:  %YELLOW%http://localhost:8000/docs%NC%
echo.
echo %BLUE%管理说明：%NC%
echo   %WHITE%•%NC% 两个服务已在独立的命令行窗口中启动
echo   %WHITE%•%NC% 关闭对应的窗口即可停止服务
echo   %WHITE%•%NC% 按 Ctrl+C 也可停止当前窗口的服务
echo   %WHITE%•%NC% 首次启动可能需要等待依赖下载
echo.
echo %BLUE%故障排除：%NC%
echo   %WHITE%•%NC% 如果页面无法访问，请等待1-2分钟后刷新
echo   %WHITE%•%NC% 如果遇到端口占用，请关闭其他相关程序
echo   %WHITE%•%NC% 详细日志请查看对应的命令行窗口
echo.
echo %MAGENTA%💡 提示：%NC% 现在可以打开浏览器访问 http://localhost:3000 开始使用
echo.

choice /M "是否立即打开浏览器访问应用"
if %errorlevel% equ 1 (
    start http://localhost:3000
)

echo %GREEN%✅%NC% 启动脚本执行完成！
echo %YELLOW%[INFO]%NC% 按任意键关闭此窗口...
pause >nul

endlocal