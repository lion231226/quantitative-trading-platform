"""
配置管理器

This module provides configuration management capabilities
for the one-click launcher including environment-specific settings,
dependency configuration, and user preferences.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LauncherConfig:
    """启动器配置"""
    # 项目配置
    project_name: str = "Demo"
    project_root: str = ""
    environment: str = "development"

    # 依赖配置
    auto_install_dependencies: bool = True
    offline_mode: bool = False
    preferred_package_manager: Dict[str, str] = None

    # 安装配置
    parallel_installation: bool = True
    max_concurrent_installs: int = 4
    installation_timeout: int = 300  # 秒

    # 网络配置
    use_mirror: bool = True
    mirror_sources: Dict[str, str] = None

    def __post_init__(self):
        if self.preferred_package_manager is None:
            self.preferred_package_manager = {
                "python": "pip",
                "nodejs": "npm"
            }
        if self.mirror_sources is None:
            self.mirror_sources = {
                "pypi": "https://pypi.tuna.tsinghua.edu.cn/simple/",
                "npm": "https://registry.npmmirror.com/"
            }


class ConfigManager:
    """
    配置管理器

    功能特性：
    - 环境配置管理
    - 用户偏好设置
    - 动态配置更新
    - 配置验证
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置目录路径
        """
        self.logger = get_logger(self.__class__.__name__)

        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 默认配置目录
            self.config_dir = Path(__file__).parent.parent / "config"

        self.config_dir.mkdir(exist_ok=True)

        # 配置文件路径
        self.main_config_file = self.config_dir / "launcher.yaml"
        self.user_config_file = self.config_dir / "user.yaml"
        self.env_config_file = self.config_dir / f"{os.getenv('ENV', 'development')}.yaml"

        # 加载配置
        self._config = LauncherConfig()
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有配置文件"""
        try:
            # 1. 加载主配置
            self._load_main_config()

            # 2. 加载环境配置
            self._load_env_config()

            # 3. 加载用户配置
            self._load_user_config()

            self.logger.info("配置加载完成")

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            # 使用默认配置
            self._config = LauncherConfig()

    def _load_main_config(self):
        """加载主配置文件"""
        if self.main_config_file.exists():
            try:
                with open(self.main_config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}

                # 更新配置
                for key, value in config_data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)

                self.logger.debug(f"主配置已加载: {self.main_config_file}")

            except Exception as e:
                self.logger.warning(f"加载主配置失败: {e}")

    def _load_env_config(self):
        """加载环境配置文件"""
        if self.env_config_file.exists():
            try:
                with open(self.env_config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}

                # 环境配置覆盖
                for key, value in config_data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)

                self.logger.debug(f"环境配置已加载: {self.env_config_file}")

            except Exception as e:
                self.logger.warning(f"加载环境配置失败: {e}")

    def _load_user_config(self):
        """加载用户配置文件"""
        if self.user_config_file.exists():
            try:
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}

                # 用户配置覆盖
                for key, value in config_data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)

                self.logger.debug(f"用户配置已加载: {self.user_config_file}")

            except Exception as e:
                self.logger.warning(f"加载用户配置失败: {e}")

    def get_config(self) -> LauncherConfig:
        """获取当前配置"""
        return self._config

    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                self.logger.debug(f"配置已更新: {key} = {value}")
            else:
                self.logger.warning(f"未知配置项: {key}")

    def save_user_config(self) -> bool:
        """保存用户配置"""
        try:
            config_data = asdict(self._config)

            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"用户配置已保存: {self.user_config_file}")
            return True

        except Exception as e:
            self.logger.error(f"保存用户配置失败: {e}")
            return False

    def get_project_root(self) -> str:
        """获取项目根目录"""
        if self._config.project_root:
            return self._config.project_root

        # 自动检测项目根目录
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir.resolve())

    def is_offline_mode(self) -> bool:
        """检查是否为离线模式"""
        return self._config.offline_mode

    def get_package_manager(self, ecosystem: str) -> str:
        """获取指定生态系统的包管理器"""
        return self._config.preferred_package_manager.get(ecosystem, "unknown")

    def get_mirror_source(self, ecosystem: str) -> Optional[str]:
        """获取镜像源"""
        if not self._config.use_mirror:
            return None

        return self._config.mirror_sources.get(ecosystem)

    def get_max_concurrent_installs(self) -> int:
        """获取最大并发安装数"""
        return self._config.max_concurrent_installs

    def get_installation_timeout(self) -> int:
        """获取安装超时时间"""
        return self._config.installation_timeout

    def validate_config(self) -> List[str]:
        """验证配置"""
        errors = []

        # 验证项目根目录
        if self._config.project_root and not Path(self._config.project_root).exists():
            errors.append(f"项目根目录不存在: {self._config.project_root}")

        # 验证并发数
        if self._config.max_concurrent_installs < 1:
            errors.append("最大并发安装数必须大于0")

        # 验证超时时间
        if self._config.installation_timeout < 10:
            errors.append("安装超时时间必须大于10秒")

        # 验证包管理器
        valid_managers = {"python": ["pip", "conda"], "nodejs": ["npm", "yarn", "pnpm"]}
        for ecosystem, manager in self._config.preferred_package_manager.items():
            if ecosystem in valid_managers and manager not in valid_managers[ecosystem]:
                errors.append(f"不支持的 {ecosystem} 包管理器: {manager}")

        return errors

    def reset_to_defaults(self):
        """重置为默认配置"""
        self._config = LauncherConfig()
        self.logger.info("配置已重置为默认值")

    def export_config(self, output_path: str) -> bool:
        """导出配置"""
        try:
            config_data = asdict(self._config)

            with open(output_path, 'w', encoding='utf-8') as f:
                if output_path.endswith('.json'):
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"配置已导出到: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            return False

    def import_config(self, config_path: str) -> bool:
        """导入配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)

            # 更新配置
            for key, value in config_data.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)

            self.logger.info(f"配置已从文件导入: {config_path}")
            return True

        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_config() -> LauncherConfig:
    """获取当前配置"""
    return get_config_manager().get_config()