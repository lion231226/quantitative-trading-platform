#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面集成工具
支持Windows、macOS、Linux的桌面快捷方式创建和系统集成
"""

import os
import sys
import platform
import subprocess
import shlex
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def validate_path_input(path_input: str) -> str:
    """验证和清理路径输入，防止路径遍历攻击"""
    if not isinstance(path_input, str):
        raise ValueError("路径必须是字符串")

    # 移除潜在的路径遍历字符
    cleaned = re.sub(r'[<>:"|?*]', '', path_input)
    cleaned = re.sub(r'\.\.[\\/]', '', cleaned)
    cleaned = re.sub(r'^[\\/]', '', cleaned)

    # 限制路径长度
    if len(cleaned) > 260:
        raise ValueError("路径长度超过限制")

    # 确保路径不包含危险字符
    if re.search(r'[\x00-\x1f\x7f-\x9f]', cleaned):
        raise ValueError("路径包含无效字符")

    return cleaned.strip()


def validate_name_input(name_input: str) -> str:
    """验证和清理名称输入，防止注入攻击"""
    if not isinstance(name_input, str):
        raise ValueError("名称必须是字符串")

    # 移除潜在的命令注入字符
    cleaned = re.sub(r'[<>"\'`;&|$()]', '', name_input)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)

    # 限制长度
    if len(cleaned) > 100:
        raise ValueError("名称长度超过限制")

    return cleaned.strip()


def safe_subprocess_run(command: List[str], timeout: int = 30, **kwargs) -> subprocess.CompletedProcess:
    """安全的subprocess调用，防止命令注入"""
    # 确保命令是列表，且所有元素都是字符串
    if not isinstance(command, list):
        raise ValueError("命令必须是列表格式")

    for arg in command:
        if not isinstance(arg, str):
            raise ValueError("命令参数必须是字符串")

        # 检查危险的shell元字符
        if re.search(r'[<>"\'`;&|$()\\]', arg):
            raise ValueError(f"命令参数包含危险字符: {arg}")

    # 设置默认安全参数
    default_kwargs = {
        'capture_output': True,
        'text': True,
        'timeout': timeout,
        'shell': False  # 强制禁用shell，防止命令注入
    }
    default_kwargs.update(kwargs)

    return subprocess.run(command, **default_kwargs)


class DesktopIntegration:
    """桌面集成工具类"""

    def __init__(self, launcher_path: str):
        # 验证启动器路径
        validated_path = validate_path_input(launcher_path)
        self.launcher_path = Path(validated_path).resolve()

        # 确保文件存在
        if not self.launcher_path.exists():
            raise FileNotFoundError(f"启动器文件不存在: {self.launcher_path}")

        self.system = platform.system()
        self.home = Path.home()

    def create_shortcut(self, name: str = "量化交易平台",
                       description: str = "量化交易平台一键启动器") -> bool:
        """创建桌面快捷方式"""
        try:
            # 验证输入参数
            validated_name = validate_name_input(name)
            validated_description = validate_name_input(description)

            if self.system == "Windows":
                return self._create_windows_shortcut(validated_name, validated_description)
            elif self.system == "Darwin":
                return self._create_macos_shortcut(validated_name, validated_description)
            elif self.system == "Linux":
                return self._create_linux_shortcut(validated_name, validated_description)
            else:
                print(f"不支持的系统: {self.system}")
                return False
        except Exception as e:
            print(f"创建快捷方式失败: {e}")
            return False

    def _create_windows_shortcut(self, name: str, description: str) -> bool:
        """创建Windows快捷方式"""
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            path = os.path.join(desktop, f"{name}.lnk")
            target = str(self.launcher_path)
            wDir = str(self.launcher_path.parent)
            icon = target

            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = wDir
            shortcut.Description = description
            shortcut.IconLocation = icon
            shortcut.save()

            return True
        except ImportError:
            # 如果winshell不可用，使用VBS脚本
            return self._create_windows_vbs_shortcut(name, description)

    def _create_windows_vbs_shortcut(self, name: str, description: str) -> bool:
        """使用VBS创建Windows快捷方式"""
        try:
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\\{name}.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{self.launcher_path}"
oLink.WorkingDirectory = "{self.launcher_path.parent}"
oLink.Description = "{description}"
oLink.Save
'''

            vbs_path = Path.home() / "temp_shortcut.vbs"
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_script)

            result = safe_subprocess_run(['cscript', '//nologo', str(vbs_path)])

            vbs_path.unlink()  # 删除临时文件

            return result.returncode == 0
        except Exception as e:
            print(f"VBS创建快捷方式失败: {e}")
            return False

    def _create_macos_shortcut(self, name: str, description: str) -> bool:
        """创建macOS快捷方式"""
        desktop = self.home / "Desktop"
        if not desktop.exists():
            desktop.mkdir(parents=True)

        command_script = f'''#!/bin/bash
cd "{self.launcher_path.parent}"
python "{self.launcher_path}" "$@"
'''

        shortcut_path = desktop / f"{name}.command"

        try:
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(command_script)

            # 设置执行权限
            os.chmod(shortcut_path, 0o755)

            return True
        except Exception as e:
            print(f"macOS快捷方式创建失败: {e}")
            return False

    def _create_linux_shortcut(self, name: str, description: str) -> bool:
        """创建Linux快捷方式"""
        # 创建.desktop文件
        desktop_file = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Name[en]=Quantitative Trading Platform
Comment={description}
Comment[en]=Quantitative Trading Platform Launcher
Exec=python {self.launcher_path}
Icon={self.launcher_path.parent}/assets/icon.png
Terminal=true
Categories=Office;Finance;Development;
'''

        # 应用程序菜单目录
        apps_dir = self.home / ".local/share/applications"
        apps_dir.mkdir(parents=True, exist_ok=True)

        desktop_app_file = apps_dir / "quant-trading-platform.desktop"

        try:
            with open(desktop_app_file, 'w', encoding='utf-8') as f:
                f.write(desktop_file)

            # 如果桌面目录存在，也创建一个副本
            desktop_dir = self.home / "Desktop"
            if desktop_dir.exists():
                desktop_shortcut = desktop_dir / "quant-trading-platform.desktop"
                with open(desktop_shortcut, 'w', encoding='utf-8') as f:
                    f.write(desktop_file)
                os.chmod(desktop_shortcut, 0o755)

            return True
        except Exception as e:
            print(f"Linux快捷方式创建失败: {e}")
            return False

    def create_start_menu_entry(self, name: str = "量化交易平台") -> bool:
        """创建开始菜单项"""
        if self.system == "Windows":
            return self._create_windows_start_menu(name)
        elif self.system == "Linux":
            return self._create_linux_start_menu(name)
        else:
            print(f"{self.system} 系统不支持开始菜单集成")
            return False

    def _create_windows_start_menu(self, name: str) -> bool:
        """创建Windows开始菜单项"""
        try:
            import winshell

            start_menu = winshell.start_menu()
            path = os.path.join(start_menu, "Programs", f"{name}.lnk")

            return self._create_windows_shortcut_at_path(path, name)
        except Exception as e:
            print(f"Windows开始菜单创建失败: {e}")
            return False

    def _create_linux_start_menu(self, name: str) -> bool:
        """创建Linux开始菜单项"""
        # Linux的.desktop文件已经提供了开始菜单集成
        return self._create_linux_shortcut(name, "量化交易平台")

    def setup_autostart(self, enabled: bool = True) -> bool:
        """设置开机自启动"""
        try:
            if self.system == "Windows":
                return self._setup_windows_autostart(enabled)
            elif self.system == "Darwin":
                return self._setup_macos_autostart(enabled)
            elif self.system == "Linux":
                return self._setup_linux_autostart(enabled)
            else:
                return False
        except Exception as e:
            print(f"设置自启动失败: {e}")
            return False

    def _setup_windows_autostart(self, enabled: bool) -> bool:
        """设置Windows自启动"""
        try:
            import winreg

            if enabled:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "QuantitativeTradingPlatform", 0,
                                 winreg.REG_SZ, f'"{self.launcher_path}"')
                winreg.CloseKey(key)
            else:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, "QuantitativeTradingPlatform")
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)

            return True
        except Exception as e:
            print(f"Windows自启动设置失败: {e}")
            return False

    def _setup_macos_autostart(self, enabled: bool) -> bool:
        """设置macOS自启动"""
        launch_agents_dir = self.home / "Library/LaunchAgents"
        launch_agents_dir.mkdir(parents=True, exist_ok=True)

        plist_file = launch_agents_dir / "com.quanttrading.launcher.plist"

        if enabled:
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quanttrading.launcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{self.launcher_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>'''

            try:
                with open(plist_file, 'w', encoding='utf-8') as f:
                    f.write(plist_content)

                # 加载到launchd
                safe_subprocess_run(['launchctl', 'load', str(plist_file)])
                return True
            except Exception as e:
                print(f"macOS自启动设置失败: {e}")
                return False
        else:
            try:
                if plist_file.exists():
                    safe_subprocess_run(['launchctl', 'unload', str(plist_file)])
                    plist_file.unlink()
                return True
            except Exception as e:
                print(f"macOS自启动禁用失败: {e}")
                return False

    def _setup_linux_autostart(self, enabled: bool) -> bool:
        """设置Linux自启动"""
        autostart_dir = self.home / ".config/autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = autostart_dir / "quant-trading-platform.desktop"

        if enabled:
            desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=量化交易平台
Comment=量化交易平台自动启动
Exec=python {self.launcher_path}
Terminal=false
Categories=Office;Finance;
'''

            try:
                with open(desktop_file, 'w', encoding='utf-8') as f:
                    f.write(desktop_content)
                return True
            except Exception as e:
                print(f"Linux自启动设置失败: {e}")
                return False
        else:
            try:
                if desktop_file.exists():
                    desktop_file.unlink()
                return True
            except Exception as e:
                print(f"Linux自启动禁用失败: {e}")
                return False

    def check_integration_status(self) -> Dict[str, bool]:
        """检查集成状态"""
        status = {
            "desktop_shortcut": False,
            "start_menu": False,
            "autostart": False
        }

        try:
            if self.system == "Windows":
                # 检查桌面快捷方式
                import winshell
                desktop = winshell.desktop()
                shortcut_path = os.path.join(desktop, "量化交易平台.lnk")
                status["desktop_shortcut"] = os.path.exists(shortcut_path)

                # 检查开始菜单
                start_menu = winshell.start_menu()
                start_menu_path = os.path.join(start_menu, "Programs", "量化交易平台.lnk")
                status["start_menu"] = os.path.exists(start_menu_path)

                # 检查自启动
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                       r"Software\Microsoft\Windows\CurrentVersion\Run")
                    winreg.QueryValueEx(key, "QuantitativeTradingPlatform")
                    winreg.CloseKey(key)
                    status["autostart"] = True
                except:
                    status["autostart"] = False

            elif self.system == "Darwin":
                # macOS检查
                desktop_shortcut = self.home / "Desktop/量化交易平台.command"
                status["desktop_shortcut"] = desktop_shortcut.exists()

                # 检查自启动
                launch_agents = self.home / "Library/LaunchAgents/com.quanttrading.launcher.plist"
                status["autostart"] = launch_agents.exists()

            elif self.system == "Linux":
                # Linux检查
                desktop_shortcut = self.home / "Desktop/quant-trading-platform.desktop"
                apps_shortcut = self.home / ".local/share/applications/quant-trading-platform.desktop"
                status["desktop_shortcut"] = desktop_shortcut.exists() or apps_shortcut.exists()
                status["start_menu"] = apps_shortcut.exists()

                # 检查自启动
                autostart_file = self.home / ".config/autostart/quant-trading-platform.desktop"
                status["autostart"] = autostart_file.exists()

        except Exception as e:
            print(f"检查集成状态失败: {e}")

        return status

    def remove_integration(self) -> bool:
        """移除所有桌面集成"""
        success = True

        try:
            # 移除自启动
            if not self.setup_autostart(False):
                success = False

            # 移除桌面快捷方式
            if self.system == "Windows":
                import winshell
                desktop = winshell.desktop()
                shortcut_path = os.path.join(desktop, "量化交易平台.lnk")
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)

            elif self.system == "Darwin":
                desktop_shortcut = self.home / "Desktop/量化交易平台.command"
                if desktop_shortcut.exists():
                    desktop_shortcut.unlink()

            elif self.system == "Linux":
                desktop_shortcut = self.home / "Desktop/quant-trading-platform.desktop"
                apps_shortcut = self.home / ".local/share/applications/quant-trading-platform.desktop"

                if desktop_shortcut.exists():
                    desktop_shortcut.unlink()
                if apps_shortcut.exists():
                    apps_shortcut.unlink()

            return success

        except Exception as e:
            print(f"移除集成失败: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="桌面集成工具")
    parser.add_argument("--create-shortcut", action="store_true",
                       help="创建桌面快捷方式")
    parser.add_argument("--remove-shortcut", action="store_true",
                       help="移除桌面快捷方式")
    parser.add_argument("--create-start-menu", action="store_true",
                       help="创建开始菜单项")
    parser.add_argument("--enable-autostart", action="store_true",
                       help="启用开机自启动")
    parser.add_argument("--disable-autostart", action="store_true",
                       help="禁用开机自启动")
    parser.add_argument("--check-status", action="store_true",
                       help="检查集成状态")
    parser.add_argument("--remove-all", action="store_true",
                       help="移除所有集成")
    parser.add_argument("--launcher-path", default="launcher.py",
                       help="启动器路径")

    args = parser.parse_args()

    # 获取启动器路径
    launcher_path = Path(args.launcher_path).resolve()
    if not launcher_path.exists():
        print(f"错误: 启动器文件不存在: {launcher_path}")
        sys.exit(1)

    # 创建桌面集成对象
    desktop = DesktopIntegration(str(launcher_path))

    if args.check_status:
        status = desktop.check_integration_status()
        print("桌面集成状态:")
        print(f"  桌面快捷方式: {'✅' if status['desktop_shortcut'] else '❌'}")
        print(f"  开始菜单项: {'✅' if status['start_menu'] else '❌'}")
        print(f"  开机自启动: {'✅' if status['autostart'] else '❌'}")

    elif args.create_shortcut:
        if desktop.create_shortcut():
            print("✅ 桌面快捷方式创建成功")
        else:
            print("❌ 桌面快捷方式创建失败")

    elif args.remove_shortcut:
        if desktop.remove_integration():
            print("✅ 桌面快捷方式移除成功")
        else:
            print("❌ 桌面快捷方式移除失败")

    elif args.create_start_menu:
        if desktop.create_start_menu_entry():
            print("✅ 开始菜单项创建成功")
        else:
            print("❌ 开始菜单项创建失败")

    elif args.enable_autostart:
        if desktop.setup_autostart(True):
            print("✅ 开机自启动启用成功")
        else:
            print("❌ 开机自启动启用失败")

    elif args.disable_autostart:
        if desktop.setup_autostart(False):
            print("✅ 开机自启动禁用成功")
        else:
            print("❌ 开机自启动禁用失败")

    elif args.remove_all:
        if desktop.remove_integration():
            print("✅ 所有桌面集成移除成功")
        else:
            print("❌ 桌面集成移除失败")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()