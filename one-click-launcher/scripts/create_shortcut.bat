@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 创建桌面快捷方式脚本
REM 用于在 Windows 桌面创建量化交易平台快捷方式

echo.
echo 正在创建桌面快捷方式...

REM 获取脚本目录
set SCRIPT_DIR=%~dp0
set LAUNCHER_DIR=%SCRIPT_DIR%..

REM 获取桌面路径
for /f "tokens=2,*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v "Desktop"') do set DESKTOP_PATH=%%b

if not defined DESKTOP_PATH (
    echo ✗ 无法获取桌面路径
    pause
    exit /b 1
)

REM 设置快捷方式路径
set SHORTCUT_PATH=%DESKTOP_PATH%\量化交易平台.lnk

REM 使用 PowerShell 创建快捷方式
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%LAUNCHER_DIR%\scripts\install.bat'; $Shortcut.WorkingDirectory = '%LAUNCHER_DIR%'; $Shortcut.Description = '量化交易平台一键启动器'; $Shortcut.Save()"

if exist "%SHORTCUT_PATH%" (
    echo ✓ 桌面快捷方式创建成功
    echo   路径: %SHORTCUT_PATH%
    echo.
    echo 现在可以直接从桌面双击快捷方式启动平台
) else (
    echo ✗ 桌面快捷方式创建失败
    echo   请手动创建快捷方式指向:
    echo   %LAUNCHER_DIR%\scripts\install.bat
)

echo.
pause