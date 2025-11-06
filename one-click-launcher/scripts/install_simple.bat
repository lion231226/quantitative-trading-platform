@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 量化交易平台一键启动器 - Windows 安装脚本
echo.
echo ========================================================
echo    量化交易平台一键启动器 - Windows 版本
echo ========================================================
echo.

REM 设置脚本目录
set SCRIPT_DIR=%~dp0
set LAUNCHER_DIR=%SCRIPT_DIR%..

REM 切换到启动器目录
cd /d "%LAUNCHER_DIR%"

REM 检查 Python 是否已安装
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo 错误: Python 未安装或未添加到 PATH
    echo 请先安装 Python 3.8 或更高版本: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 显示 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python 版本: !PYTHON_VERSION!

REM 检查 launcher.py 是否存在
if not exist "%LAUNCHER_DIR%\launcher.py" (
    echo 错误: 找不到 launcher.py 文件
    echo 请确保在正确的目录中运行此脚本
    pause
    exit /b 1
)

REM 安装 Python 依赖
echo.
echo 正在检查和安装 Python 依赖...
python -m pip install --upgrade pip
python -m pip install psutil rich requests

REM 启动主启动器
echo.
echo 正在启动量化交易平台...
echo.

REM 传递所有参数给 Python 脚本
python launcher.py %*

REM 如果发生错误，暂停以便查看错误信息
if %errorLevel% neq 0 (
    echo.
    echo 启动过程中发生错误，错误代码: %errorLevel%
    pause
    exit /b %errorLevel%
)

endlocal