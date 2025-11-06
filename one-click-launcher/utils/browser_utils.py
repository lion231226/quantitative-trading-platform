"""
浏览器自动化工具

提供自动打开浏览器、生成访问链接和管理浏览器窗口的功能。
"""

import webbrowser
import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import platform
import subprocess
import os

from utils.frontend_logger import get_frontend_logger

logger = get_frontend_logger()


class BrowserType(Enum):
    """支持的浏览器类型"""
    DEFAULT = "default"
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: BrowserType = BrowserType.DEFAULT
    auto_open: bool = True
    delay_seconds: float = 2.0
    try_alternatives: bool = True
    new_window: bool = True
    private_mode: bool = False


class BrowserManager:
    """浏览器管理器"""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self.system = platform.system().lower()
        self.logger = logger

        # 浏览器命令映射
        self.browser_commands = {
            BrowserType.CHROME: self._get_chrome_command(),
            BrowserType.FIREFOX: self._get_firefox_command(),
            BrowserType.SAFARI: self._get_safari_command(),
            BrowserType.EDGE: self._get_edge_command(),
        }

    def _get_chrome_command(self) -> List[str]:
        """获取Chrome浏览器命令"""
        if self.system == "windows":
            return ["chrome", "--new-window"]
        elif self.system == "darwin":  # macOS
            return ["open", "-a", "Google Chrome"]
        else:  # Linux
            return ["google-chrome", "--new-window"]

    def _get_firefox_command(self) -> List[str]:
        """获取Firefox浏览器命令"""
        if self.system == "windows":
            return ["firefox", "-new-window"]
        elif self.system == "darwin":  # macOS
            return ["open", "-a", "Firefox"]
        else:  # Linux
            return ["firefox", "-new-window"]

    def _get_safari_command(self) -> List[str]:
        """获取Safari浏览器命令（仅macOS）"""
        if self.system == "darwin":
            return ["open", "-a", "Safari"]
        return []

    def _get_edge_command(self) -> List[str]:
        """获取Edge浏览器命令"""
        if self.system == "windows":
            return ["msedge", "-new-window"]
        elif self.system == "darwin":  # macOS
            return ["open", "-a", "Microsoft Edge"]
        else:  # Linux
            return ["microsoft-edge", "-new-window"]

    def generate_access_url(self, host: str = "localhost", port: int = 3000,
                           path: str = "", query_params: Optional[Dict[str, str]] = None) -> str:
        """生成访问URL"""
        url = f"http://{host}:{port}"

        if path:
            url = f"{url.rstrip('/')}/{path.lstrip('/')}"

        if query_params:
            query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
            url = f"{url}?{query_string}"

        return url

    def open_browser_sync(self, url: str, browser_type: Optional[BrowserType] = None) -> bool:
        """同步打开浏览器"""
        browser = browser_type or self.config.browser_type

        try:
            if browser == BrowserType.DEFAULT:
                success = webbrowser.open(url, new=self.config.new_window)
            else:
                success = self._open_specific_browser(url, browser)

            if success:
                self.logger.log_browser_opened(url, success=True)
                return True
            else:
                self.logger.log_browser_opened(url, success=False, error="Failed to open browser")
                return False

        except Exception as e:
            self.logger.log_browser_opened(url, success=False, error=str(e))
            return False

    async def open_browser_async(self, url: str, browser_type: Optional[BrowserType] = None) -> bool:
        """异步打开浏览器"""
        # 等待指定的延迟时间
        if self.config.delay_seconds > 0:
            await asyncio.sleep(self.config.delay_seconds)

        # 在事件循环中运行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.open_browser_sync, url, browser_type)

    def _open_specific_browser(self, url: str, browser_type: BrowserType) -> bool:
        """打开指定的浏览器"""
        if browser_type not in self.browser_commands:
            return False

        command = self.browser_commands[browser_type]
        if not command:
            return False

        try:
            # 添加隐私模式参数（如果启用）
            if self.config.private_mode:
                command = self._add_private_mode_param(command, browser_type)

            # 执行浏览器命令
            subprocess.run(command + [url], check=True, capture_output=True)
            return True

        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _add_private_mode_param(self, command: List[str], browser_type: BrowserType) -> List[str]:
        """添加隐私模式参数"""
        privacy_params = {
            BrowserType.CHROME: ["--incognito"],
            BrowserType.FIREFOX: ["--private-window"],
            BrowserType.SAFARI: ["--private"],
            BrowserType.EDGE: ["--inprivate"],
        }

        if browser_type in privacy_params:
            return command + privacy_params[browser_type]

        return command

    async def try_multiple_browsers(self, url: str) -> bool:
        """尝试使用多个浏览器打开URL"""
        if not self.config.try_alternatives:
            return await self.open_browser_async(url)

        # 尝试顺序：指定浏览器 -> 默认浏览器 -> Chrome -> Firefox -> Edge -> Safari
        browsers_to_try = [
            self.config.browser_type,
            BrowserType.DEFAULT,
            BrowserType.CHROME,
            BrowserType.FIREFOX,
            BrowserType.EDGE,
        ]

        # 在macOS上添加Safari
        if self.system == "darwin":
            browsers_to_try.append(BrowserType.SAFARI)

        for browser in browsers_to_try:
            try:
                self.logger.info(f"Trying to open URL with {browser.value} browser")
                success = await self.open_browser_async(url, browser)
                if success:
                    return True

                # 短暂延迟后尝试下一个浏览器
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.warning(f"Failed to open with {browser.value}: {e}")
                continue

        self.logger.error("Failed to open URL with any available browser")
        return False

    def is_browser_available(self, browser_type: BrowserType) -> bool:
        """检查浏览器是否可用"""
        if browser_type not in self.browser_commands:
            return False

        command = self.browser_commands[browser_type]
        if not command:
            return False

        try:
            # 尝试查找浏览器可执行文件
            subprocess.run([command[0], "--version"],
                         check=True, capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_available_browsers(self) -> List[BrowserType]:
        """获取所有可用的浏览器"""
        available = []

        for browser_type in BrowserType:
            if browser_type == BrowserType.DEFAULT:
                continue

            if self.is_browser_available(browser_type):
                available.append(browser_type)

        return available

    def close_browser_windows(self, url_pattern: Optional[str] = None) -> bool:
        """关闭浏览器窗口（高级功能，依赖系统特定实现）"""
        # 这里可以实现特定系统的浏览器窗口关闭逻辑
        # 由于复杂性，这里只是记录日志
        self.logger.info("Browser window closing not implemented yet")
        return True

    def create_desktop_shortcut(self, url: str, name: str = "Frontend App",
                              desktop_path: Optional[str] = None) -> bool:
        """创建桌面快捷方式"""
        try:
            if desktop_path is None:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

            if self.system == "windows":
                return self._create_windows_shortcut(url, name, desktop_path)
            elif self.system == "darwin":
                return self._create_macos_shortcut(url, name, desktop_path)
            else:  # Linux
                return self._create_linux_shortcut(url, name, desktop_path)

        except Exception as e:
            self.logger.error(f"Failed to create desktop shortcut: {e}")
            return False

    def _create_windows_shortcut(self, url: str, name: str, desktop_path: str) -> bool:
        """创建Windows桌面快捷方式"""
        try:
            import winshell
            from win32com.client import Dispatch

            shortcut_path = os.path.join(desktop_path, f"{name}.url")
            shortcut = Dispatch("WScript.Shell").CreateShortCut(shortcut_path)
            shortcut.Targetpath = url
            shortcut.save()
            return True
        except ImportError:
            # 如果没有winshell，创建简单的.url文件
            shortcut_path = os.path.join(desktop_path, f"{name}.url")
            with open(shortcut_path, 'w') as f:
                f.write(f"[InternetShortcut]\nURL={url}\n")
            return True

    def _create_macos_shortcut(self, url: str, name: str, desktop_path: str) -> bool:
        """创建macOS桌面快捷方式"""
        try:
            # 创建.webloc文件
            shortcut_path = os.path.join(desktop_path, f"{name}.webloc")
            with open(shortcut_path, 'w') as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n'
                       f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                       f'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                       f'<plist version="1.0">\n'
                       f'<dict>\n'
                       f'<key>URL</key>\n<string>{url}</string>\n'
                       f'</dict>\n'
                       f'</plist>')
            return True
        except Exception:
            return False

    def _create_linux_shortcut(self, url: str, name: str, desktop_path: str) -> bool:
        """创建Linux桌面快捷方式"""
        try:
            shortcut_path = os.path.join(desktop_path, f"{name}.desktop")
            with open(shortcut_path, 'w') as f:
                f.write(f'[Desktop Entry]\n'
                       f'Version=1.0\n'
                       f'Type=Application\n'
                       f'Name={name}\n'
                       f'Exec=xdg-open {url}\n'
                       f'Icon=web-browser\n'
                       f'Terminal=false\n')
            os.chmod(shortcut_path, 0o755)
            return True
        except Exception:
            return False

    def get_browser_info(self) -> Dict[str, Any]:
        """获取浏览器信息"""
        available_browsers = self.get_available_browsers()

        return {
            "system": self.system,
            "default_browser": self.config.browser_type.value,
            "available_browsers": [b.value for b in available_browsers],
            "auto_open": self.config.auto_open,
            "delay_seconds": self.config.delay_seconds,
            "try_alternatives": self.config.try_alternatives,
        }


# 全局浏览器管理器实例
_browser_manager = None


def get_browser_manager(config: Optional[BrowserConfig] = None) -> BrowserManager:
    """获取浏览器管理器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(config)
    return _browser_manager


async def open_frontend_app(host: str = "localhost", port: int = 3000,
                          browser_type: Optional[BrowserType] = None) -> bool:
    """便捷函数：打开前端应用"""
    manager = get_browser_manager()
    url = manager.generate_access_url(host, port)

    if browser_type:
        return await manager.open_browser_async(url, browser_type)
    else:
        return await manager.try_multiple_browsers(url)