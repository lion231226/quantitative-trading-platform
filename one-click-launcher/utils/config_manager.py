"""
配置管理模块

提供配置文件的读取、写入和管理功能。
"""

import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional
import configparser

from utils.logger import get_logger
from utils.file_utils import ensure_dir, read_file_text, write_file_text

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config/config.ini"):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                self.config.read(self.config_file, encoding='utf-8')
                logger.info(f"加载配置文件: {self.config_file}")
            else:
                logger.warning(f"配置文件不存在: {self.config_file}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")

    def get(self, section: str, key: str, fallback: Any = None) -> Optional[str]:
        """
        获取配置值

        Args:
            section: 配置节
            key: 配置键
            fallback: 默认值

        Returns:
            str: 配置值
        """
        try:
            return self.config.get(section, key, fallback=fallback)
        except Exception as e:
            logger.error(f"获取配置失败 [{section}]{key}: {e}")
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置值"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except Exception:
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置值"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except Exception:
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置值"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except Exception:
            return fallback

    def set(self, section: str, key: str, value: Any) -> bool:
        """
        设置配置值

        Args:
            section: 配置节
            key: 配置键
            value: 配置值

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)

            self.config.set(section, key, str(value))
            return True
        except Exception as e:
            logger.error(f"设置配置失败 [{section}]{key}={value}: {e}")
            return False

    def save(self) -> bool:
        """保存配置到文件"""
        try:
            ensure_dir(str(self.config_file.parent))
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info(f"保存配置文件: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def get_platform_config(self) -> str:
        """获取平台特定配置文件路径"""
        current_platform = platform.system().lower()
        if current_platform == 'windows':
            return 'config/platform-configs/windows.ini'
        elif current_platform == 'darwin':
            return 'config/platform-configs/macos.ini'
        elif current_platform == 'linux':
            return 'config/platform-configs/linux.ini'
        else:
            return 'config/platform-configs/default.ini'

    def load_platform_overrides(self) -> None:
        """加载平台特定配置覆盖"""
        platform_config_file = self.get_platform_config()
        platform_config = Path(platform_config_file)

        if platform_config.exists():
            try:
                platform_parser = configparser.ConfigParser()
                platform_parser.read(platform_config_file, encoding='utf-8')

                # 合并平台配置
                for section_name in platform_parser.sections():
                    if not self.config.has_section(section_name):
                        self.config.add_section(section_name)

                    for key, value in platform_parser.items(section_name):
                        self.config.set(section_name, key, value)

                logger.info(f"加载平台配置覆盖: {platform_config_file}")
            except Exception as e:
                logger.error(f"加载平台配置失败: {e}")

    def get_service_ports(self) -> Dict[str, int]:
        """获取服务端口配置"""
        return {
            'redis': self.get_int('default', 'redis_port', 6379),
            'backend': self.get_int('default', 'backend_port', 8000),
            'frontend': self.get_int('default', 'frontend_port', 3000)
        }

    def get_paths(self) -> Dict[str, str]:
        """获取路径配置"""
        return {
            'project_root': self.get('paths', 'project_root', '..'),
            'frontend_path': self.get('paths', 'frontend_path', '../frontend'),
            'backend_path': self.get('paths', 'backend_path', '../backend'),
            'logs_path': self.get('paths', 'logs_path', './logs'),
            'temp_path': self.get('paths', 'temp_path', './temp')
        }

    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        return self.get_bool('features', feature, False)

    def get_timeout_config(self) -> Dict[str, int]:
        """获取超时配置"""
        return {
            'service_start': self.get_int('default', 'service_start_timeout', 120),
            'health_check': self.get_int('default', 'health_check_timeout', 30),
            'network_check': self.get_int('default', 'network_check_timeout', 10),
            'npm_install': self.get_int('dependencies', 'npm_install_timeout', 300)
        }

    def get_dependency_config(self) -> Dict[str, Any]:
        """获取依赖配置"""
        return {
            'min_python_version': self.get('dependencies', 'min_python_version', '3.8'),
            'min_node_version': self.get('dependencies', 'min_node_version', '18.0.0'),
            'required_python_packages': self.get('dependencies', 'required_python_packages', 'psutil,rich,requests').split(','),
            'redis_required': self.get_bool('dependencies', 'redis_required', True),
            'git_required': self.get_bool('dependencies', 'git_required', True)
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load_platform_overrides()
    return _config_manager


def get_config(section: str, key: str, fallback: Any = None) -> Optional[str]:
    """便捷函数：获取配置值"""
    return get_config_manager().get(section, key, fallback)


def get_config_int(section: str, key: str, fallback: int = 0) -> int:
    """便捷函数：获取整数配置值"""
    return get_config_manager().get_int(section, key, fallback)


def get_config_bool(section: str, key: str, fallback: bool = False) -> bool:
    """便捷函数：获取布尔配置值"""
    return get_config_manager().get_bool(section, key, fallback)


def get_service_ports() -> Dict[str, int]:
    """便捷函数：获取服务端口配置"""
    return get_config_manager().get_service_ports()


def get_project_paths() -> Dict[str, str]:
    """便捷函数：获取项目路径配置"""
    return get_config_manager().get_paths()


if __name__ == "__main__":
    # 测试配置管理器
    config = ConfigManager()

    print("配置测试:")
    print(f"应用名称: {config.get('default', 'app_name')}")
    print(f"Redis端口: {config.get_int('default', 'redis_port')}")
    print(f"调试模式: {config.get_bool('default', 'debug')}")
    print(f"服务端口: {config.get_service_ports()}")
    print(f"项目路径: {config.get_paths()}")