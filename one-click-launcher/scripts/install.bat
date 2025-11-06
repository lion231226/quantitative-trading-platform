@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ===================================================================
:: 量化交易平台一键安装脚本 (Windows增强版)
:: 版本: 1.0.0
:: 更新: 2025-11-06
:: ===================================================================

title 量化交易平台 - 一键安装

:: 设置变量
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER_DIR=%SCRIPT_DIR%.."
set "PYTHON_MIN_VERSION=3.11"
set "NODE_MIN_VERSION=18"
set "LOG_FILE=%TEMP%\trading_platform_install.log"

:: 创建日志文件
echo [%date% %time%] 开始安装量化交易平台 > "%LOG_FILE%"

:: 显示欢迎信息
cls
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              量化交易平台一键安装器 v1.0.0                ║
echo ║                                                              ║
echo ║  此安装器将自动检查环境并安装所有必需的依赖包             ║
echo ║  支持自动环境检测、依赖安装和错误恢复                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 安装目录: %LAUNCHER_DIR%
echo 安装日志: %LOG_FILE%
echo.

:: 检查管理员权限（可选）
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 检测到管理员权限，可以进行完整安装
    set "HAS_ADMIN=1"
) else (
    echo ⚠️  未检测到管理员权限，某些功能可能受限
    set "HAS_ADMIN=0"
)

:: 环境检测阶段
echo [1/5] 环境检测...
echo.

:: 检查操作系统
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%version%" == "10.0" (
    echo ✅ Windows 10/11 检测通过
) else (
    echo ⚠️  Windows版本: %VERSION% (推荐Windows 10+)
)

:: 检查网络连接
ping -n 1 pypi.org >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  网络连接检查失败，可能影响依赖安装
    set "NETWORK_AVAILABLE=0"
) else (
    echo ✅ 网络连接正常
    set "NETWORK_AVAILABLE=1"
)

:: 检查磁盘空间
for /f "tokens=2" %%a in ('wmic logicaldisk get size^,freespace /value ^| find "=" ^| findstr /C:"FreeSpace"') do set "free_space=%%a"
if defined free_space (
    set /a free_gb=!free_space:~0,-9!
    if !free_gb! lss 2 (
        echo ❌ 磁盘空间不足，至少需要2GB可用空间
        goto :error_exit
    ) else (
        echo ✅ 磁盘空间充足 (!free_gb!GB可用)
    )
)

:: Python环境检查
echo.
echo [2/5] Python环境检查...
echo.

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python未安装或未添加到PATH
    echo.
    echo 请从以下链接下载Python %PYTHON_MIN_VERSION%+:
    echo https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH" 选项
    echo.
    pause
    goto :error_exit
)

:: 显示Python版本
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_CURRENT=%%a
echo ✅ Python版本: %PYTHON_CURRENT%

:: 检查Python版本兼容性
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_CURRENT%") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

if %PYTHON_MAJOR% geq 3 (
    if %PYTHON_MINOR% geq 11 (
        echo ✅ Python版本满足要求 (≥%PYTHON_MIN_VERSION%)
    ) else (
        echo ⚠️  Python版本较低，建议升级到%PYTHON_MIN_VERSION%+
        echo    当前版本: %PYTHON_CURRENT%
        set "PYTHON_VERSION_OK=0"
    )
) else (
    echo ❌ Python版本过低，需要%PYTHON_MIN_VERSION%+
    set "PYTHON_VERSION_OK=0"
)

if not defined PYTHON_VERSION_OK set "PYTHON_VERSION_OK=1"

:: Node.js环境检查
echo.
echo [3/5] Node.js环境检查...
echo.

node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Node.js未安装，前端功能可能受限
    echo.
    echo 可选安装Node.js %NODE_MIN_VERSION%+:
    echo https://nodejs.org/
    echo.
    set "NODE_AVAILABLE=0"
) else (
    for /f "tokens=1" %%a in ('node --version') do set NODE_CURRENT=%%a
    echo ✅ Node.js版本: !NODE_CURRENT!

    :: 检查Node.js版本兼容性
    set "NODE_VERSION_NUMBER=!NODE_CURRENT:~1!"
    if !NODE_VERSION_NUMBER! geq %NODE_MIN_VERSION% (
        echo ✅ Node.js版本满足要求
        set "NODE_AVAILABLE=1"
    ) else (
        echo ⚠️  Node.js版本较低，建议升级到%NODE_MIN_VERSION%+
        set "NODE_AVAILABLE=0"
    )
)

:: 检查 launcher.py 是否存在
if not exist "%LAUNCHER_DIR%\launcher.py" (
    echo ❌ 找不到 launcher.py 文件
    echo 请确保在正确的目录中运行此脚本
    echo 当前目录: %LAUNCHER_DIR%
    pause
    goto :error_exit
) else (
    echo ✅ 启动器文件存在
)

:: Python依赖安装
echo.
echo [4/5] Python依赖安装...
echo.

cd /d "%LAUNCHER_DIR%"

:: 升级pip
echo 正在升级pip...
python -m pip install --upgrade pip --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
if %errorLevel% neq 0 (
    echo ⚠️  pip升级失败，使用默认源
    python -m pip install --upgrade pip
)

:: 检查requirements.txt
if exist requirements.txt (
    echo 正在安装Python依赖包...
    echo 使用国内镜像源加速下载...

    :: 尝试使用清华镜像源
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --progress-bar off
    if %errorLevel% neq 0 (
        echo ⚠️  国内镜像源安装失败，尝试默认源...
        python -m pip install -r requirements.txt --progress-bar off
        if %errorLevel% neq 0 (
            echo ❌ Python依赖包安装失败
            echo 请检查网络连接或手动安装
        ) else (
            echo ✅ Python依赖包安装完成 (默认源)
        )
    ) else (
        echo ✅ Python依赖包安装完成 (国内镜像源)
    )
) else (
    echo ⚠️  未找到requirements.txt文件
    echo 正在安装基础依赖...
    python -m pip install psutil rich requests fastapi uvicorn sqlalchemy pandas pydantic
)

:: Node.js依赖安装（如果可用）
if %NODE_AVAILABLE%==1 (
    echo.
    echo [5/5] Node.js依赖安装...
    echo.

    if exist "frontend\package.json" (
        echo 正在安装Node.js依赖包...
        cd frontend

        :: 配置npm镜像源
        npm config set registry https://registry.npmmirror.com

        npm install
        if %errorLevel% equ 0 (
            echo ✅ Node.js依赖包安装完成
            set "NODE_DEPS_OK=1"
        ) else (
            echo ⚠️  Node.js依赖包安装失败，尝试默认源...
            npm config set registry https://registry.npmjs.org/
            npm install
            if %errorLevel% equ 0 (
                echo ✅ Node.js依赖包安装完成 (默认源)
                set "NODE_DEPS_OK=1"
            ) else (
                echo ❌ Node.js依赖包安装失败
                set "NODE_DEPS_OK=0"
            )
        )

        cd ..
    ) else (
        echo ⚠️  未找到frontend/package.json文件
        set "NODE_DEPS_OK=0"
    )
) else (
    set "NODE_DEPS_OK=0"
)

:: 创建桌面快捷方式（可选）
echo.
echo 正在创建桌面快捷方式...
call :create_desktop_shortcut

:: 安装完成总结
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        安装完成！                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 安装结果总结:
echo ✅ Python环境: %PYTHON_CURRENT%
if %NODE_AVAILABLE%==1 (
    echo ✅ Node.js环境: %NODE_CURRENT%
    if %NODE_DEPS_OK%==1 (
        echo ✅ 前端依赖: 安装完成
    ) else (
        echo ⚠️  前端依赖: 安装失败
    )
) else (
    echo ⚠️  Node.js环境: 未安装
    echo ⚠️  前端功能: 不可用
)
echo.
echo 启动方式:
echo   1. 双击桌面快捷方式 "量化交易平台"
echo   2. 或运行: python launcher.py
echo.
echo 访问地址:
if %NODE_DEPS_OK%==1 (
    echo   🌐 前端应用: http://localhost:3000
) else (
    echo   🌐 前端应用: 不可用 (Node.js依赖安装失败)
)
echo   🔧 后端API:  http://localhost:8000
echo   📚 API文档:  http://localhost:8000/docs
echo.
echo 技术支持:
echo   📧 邮箱: support@quant-trading.example.com
echo   📞 电话: 400-123-4567
echo   📖 文档: https://docs.quant-trading.example.com
echo.

:: 询问是否立即启动
set /p choice=是否现在启动平台？ (Y/N):
if /i "%choice%"=="Y" (
    echo.
    echo 正在启动量化交易平台...
    cd /d "%LAUNCHER_DIR%"
    python launcher.py
    if %errorLevel% neq 0 (
        echo.
        echo 启动失败，错误代码: %errorLevel%
        pause
    )
)

echo.
echo [%date% %time%] 安装完成 >> "%LOG_FILE%"
echo 安装日志已保存到: %LOG_FILE%
echo.
pause
exit /b 0

:: ===================================================================
:: 函数定义
:: ===================================================================

:create_desktop_shortcut
:: 创建VBS脚本来创建桌面快捷方式
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"

(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = oWS.SpecialFolders^("Desktop"^) ^& "\量化交易平台.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%LAUNCHER_DIR%\launcher.py"
echo oLink.WorkingDirectory = "%LAUNCHER_DIR%"
echo oLink.Description = "量化交易平台一键启动器"
echo oLink.Arguments = ""
echo oLink.Save
) > "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ 桌面快捷方式创建完成
) else (
    echo ⚠️  桌面快捷方式创建失败
)

del "%VBS_SCRIPT%" >nul 2>&1
goto :eof

:error_exit
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        安装失败！                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 错误信息已保存到: %LOG_FILE%
echo.
echo 常见解决方案:
echo 1. 确保Python %PYTHON_MIN_VERSION%+已正确安装并添加到PATH
echo 2. 检查网络连接是否正常
echo 3. 以管理员身份运行此脚本
echo 4. 检查磁盘空间是否充足 (至少2GB)
echo 5. 临时关闭杀毒软件和防火墙
echo.
echo 如需帮助，请联系技术支持:
echo   📧 邮箱: support@quant-trading.example.com
echo   📞 电话: 400-123-4567
echo   📖 在线文档: https://docs.quant-trading.example.com
echo.
pause
exit /b 1