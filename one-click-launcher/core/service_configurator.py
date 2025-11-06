"""
服务配置器

提供服务启动配置文件的解析、验证、参数注入和环境特定配置支持。
支持YAML和JSON格式，包含完整的配置验证和错误报告功能。
"""

import os
import yaml
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from datetime import datetime

from .service_dependency_analyzer import ServiceInfo, ServiceType
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigFormat(Enum):
    """配置文件格式"""
    YAML = "yaml"
    JSON = "json"
    AUTO = "auto"  # 自动检测


class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    service_type: ServiceType
    host: str = "localhost"
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    startup_timeout: int = 60
    dependencies: List[str] = field(default_factory=list)
    startup_command: Optional[str] = None
    startup_args: Dict[str, Any] = field(default_factory=dict)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    auto_restart: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'service_type': self.service_type.value,
            'host': self.host,
            'port': self.port,
            'health_endpoint': self.health_endpoint,
            'startup_timeout': self.startup_timeout,
            'dependencies': self.dependencies,
            'startup_command': self.startup_command,
            'startup_args': self.startup_args,
            'environment_variables': self.environment_variables,
            'working_directory': self.working_directory,
            'auto_restart': self.auto_restart,
            'enabled': self.enabled,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        """从字典创建服务配置"""
        # 确保service_type是枚举类型
        if isinstance(data.get('service_type'), str):
            data['service_type'] = ServiceType(data['service_type'])

        return cls(**data)

    def to_service_info(self) -> ServiceInfo:
        """转换为ServiceInfo对象"""
        return ServiceInfo(
            name=self.name,
            service_type=self.service_type,
            host=self.host,
            port=self.port,
            health_endpoint=self.health_endpoint,
            startup_timeout=self.startup_timeout,
            dependencies=self.dependencies,
            metadata=self.metadata
        )


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)

    def add_info(self, info: str) -> None:
        """添加信息"""
        self.info.append(info)

    def merge(self, other: 'ValidationResult') -> None:
        """合并另一个验证结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
        if not other.is_valid:
            self.is_valid = False


@dataclass
class StartupParameters:
    """启动参数"""
    command: str
    args: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'command': self.command,
            'args': self.args,
            'env_vars': self.env_vars,
            'working_dir': self.working_dir
        }


class ServiceConfigurator:
    """
    服务配置器

    功能特性：
    - 配置文件解析（YAML/JSON）
    - 配置验证和错误报告
    - 参数注入和替换
    - 环境特定配置支持
    - 配置模板和继承
    """

    def __init__(self, config_path: str,
                 config_format: ConfigFormat = ConfigFormat.AUTO,
                 environment: Environment = Environment.DEVELOPMENT):
        """
        初始化服务配置器

        Args:
            config_path: 配置文件路径
            config_format: 配置文件格式
            environment: 环境类型
        """
        self.config_path = Path(config_path)
        self.config_format = config_format
        self.environment = environment
        self.logger = get_logger(self.__class__.__name__)

        # 配置数据
        self.raw_config: Dict[str, Any] = {}
        self.processed_config: Dict[str, Any] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}

        # 配置验证规则
        self.validation_rules = {
            'required_fields': ['name', 'service_type'],
            'port_ranges': {
                'user': (1024, 65535),
                'system': (1, 1023)
            },
            'timeout_limits': {
                'min': 5,
                'max': 600
            },
            'name_pattern': re.compile(r'^[a-zA-Z0-9_-]+$'),
            'host_pattern': re.compile(r'^[a-zA-Z0-9.-]+$')
        }

        # 环境变量替换模式
        self.env_var_pattern = re.compile(r'\$\{([^}]+)\}')

        self.logger.info(f"服务配置器初始化完成，配置文件: {config_path}, 环境: {environment.value}")

    def load_configuration(self) -> ServiceConfig:
        """
        加载配置文件

        Returns:
            服务配置对象

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        try:
            # 读取配置文件内容
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检测文件格式
            if self.config_format == ConfigFormat.AUTO:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    self.config_format = ConfigFormat.YAML
                elif self.config_path.suffix.lower() == '.json':
                    self.config_format = ConfigFormat.JSON
                else:
                    # 根据内容判断
                    content_stripped = content.strip()
                    if content_stripped.startswith('{') and content_stripped.endswith('}'):
                        self.config_format = ConfigFormat.JSON
                    else:
                        self.config_format = ConfigFormat.YAML

            # 解析配置内容
            if self.config_format == ConfigFormat.YAML:
                self.raw_config = yaml.safe_load(content)
            else:
                self.raw_config = json.loads(content)

            self.logger.info(f"成功加载配置文件: {self.config_path} (格式: {self.config_format.value})")

            # 处理环境特定配置
            self._process_environment_config()

            # 验证配置
            validation_result = self.validate_configuration()
            if not validation_result.is_valid:
                raise ValueError(f"配置验证失败: {'; '.join(validation_result.errors)}")

            # 构建服务配置对象
            self._build_service_configs()

            return self.get_default_service_config()

        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析错误: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析错误: {e}")
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")

    def validate_configuration(self) -> ValidationResult:
        """
        验证配置

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)

        if not self.raw_config:
            result.add_error("配置文件为空")
            return result

        # 验证全局配置
        self._validate_global_config(self.raw_config, result)

        # 验证服务配置
        services = self.raw_config.get('services', {})
        if not services:
            result.add_error("未找到服务配置")
        else:
            for service_name, service_config in services.items():
                self._validate_service_config(service_name, service_config, result)

        # 输出验证信息
        if result.errors:
            self.logger.error(f"配置验证失败，发现 {len(result.errors)} 个错误")
            for error in result.errors:
                self.logger.error(f"  错误: {error}")

        if result.warnings:
            self.logger.warning(f"配置验证发现 {len(result.warnings)} 个警告")
            for warning in result.warnings:
                self.logger.warning(f"  警告: {warning}")

        if result.info:
            self.logger.info(f"配置验证信息: {len(result.info)} 条")
            for info in result.info:
                self.logger.info(f"  信息: {info}")

        return result

    def inject_parameters(self, service_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入自定义启动参数

        Args:
            service_name: 服务名称
            params: 参数字典

        Returns:
            注入后的配置
        """
        if service_name not in self.service_configs:
            raise ValueError(f"未找到服务配置: {service_name}")

        service_config = self.service_configs[service_name]
        injected_config = service_config.to_dict()

        # 注入启动参数
        if 'startup_args' in params:
            injected_config['startup_args'].update(params['startup_args'])

        # 注入环境变量
        if 'env_vars' in params:
            injected_config['environment_variables'].update(params['env_vars'])

        # 注入其他配置
        for key, value in params.items():
            if key not in ['startup_args', 'env_vars']:
                injected_config[key] = value

        # 处理环境变量替换
        injected_config = self._substitute_environment_variables(injected_config)

        self.logger.debug(f"为服务 {service_name} 注入参数: {list(params.keys())}")
        return injected_config

    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """
        获取指定服务的配置

        Args:
            service_name: 服务名称

        Returns:
            服务配置对象
        """
        return self.service_configs.get(service_name)

    def get_all_service_configs(self) -> Dict[str, ServiceConfig]:
        """获取所有服务配置"""
        return self.service_configs.copy()

    def get_default_service_config(self) -> ServiceConfig:
        """
        获取默认服务配置

        Returns:
            默认服务配置对象
        """
        if not self.service_configs:
            raise ValueError("没有可用的服务配置")

        # 返回第一个启用的服务配置
        for service_config in self.service_configs.values():
            if service_config.enabled:
                return service_config

        # 如果没有启用的服务，返回第一个配置
        return next(iter(self.service_configs.values()))

    def get_startup_parameters(self, service_name: str) -> StartupParameters:
        """
        获取服务启动参数

        Args:
            service_name: 服务名称

        Returns:
            启动参数对象

        Raises:
            ValueError: 服务配置不存在
        """
        service_config = self.get_service_config(service_name)
        if not service_config:
            raise ValueError(f"未找到服务配置: {service_name}")

        if not service_config.startup_command:
            raise ValueError(f"服务 {service_name} 未配置启动命令")

        # 构建启动参数
        args = []
        if service_config.startup_args:
            for key, value in service_config.startup_args.items():
                if isinstance(value, bool):
                    if value:
                        args.append(f"--{key}")
                elif value is not None:
                    args.append(f"--{key}={value}")

        # 处理环境变量替换
        env_vars = self._substitute_environment_variables(service_config.environment_variables)

        return StartupParameters(
            command=service_config.startup_command,
            args=args,
            env_vars=env_vars,
            working_dir=service_config.working_directory
        )

    def save_configuration(self, output_path: Optional[str] = None,
                          format: Optional[ConfigFormat] = None) -> bool:
        """
        保存配置到文件

        Args:
            output_path: 输出文件路径
            format: 输出格式

        Returns:
            是否成功保存
        """
        if not output_path:
            output_path = self.config_path

        if not format:
            format = self.config_format

        try:
            # 构建输出数据
            output_data = {
                'version': '1.0',
                'environment': self.environment.value,
                'generated_at': datetime.now().isoformat(),
                'services': {
                    name: config.to_dict()
                    for name, config in self.service_configs.items()
                }
            }

            # 添加原始配置中的元数据
            if 'metadata' in self.raw_config:
                output_data['metadata'] = self.raw_config['metadata']

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"配置已保存到: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False

    def _process_environment_config(self) -> None:
        """处理环境特定配置"""
        # 查找环境特定配置
        env_config_key = f"{self.environment.value}_config"
        env_config = self.raw_config.get(env_config_key, {})

        # 合并全局配置
        global_config = self.raw_config.get('global', {})
        merged_global = {**global_config, **env_config.get('global', {})}

        # 合并服务配置
        services_config = self.raw_config.get('services', {})
        env_services_config = env_config.get('services', {})

        merged_services = {}
        for service_name, service_config in services_config.items():
            merged_config = service_config.copy()
            if service_name in env_services_config:
                merged_config.update(env_services_config[service_name])
            merged_services[service_name] = merged_config

        # 添加环境特定的服务配置
        for service_name, service_config in env_services_config.items():
            if service_name not in merged_services:
                merged_services[service_name] = service_config

        # 构建处理后的配置
        self.processed_config = {
            'global': merged_global,
            'services': merged_services,
            'environment': self.environment.value
        }

    def _validate_global_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """验证全局配置"""
        global_config = config.get('global', {})

        # 验证默认超时设置
        default_timeout = global_config.get('default_timeout', 60)
        if not (self.validation_rules['timeout_limits']['min'] <= default_timeout <=
                self.validation_rules['timeout_limits']['max']):
            result.add_warning(f"默认超时时间 {default_timeout} 超出建议范围")

        # 验证默认主机设置
        default_host = global_config.get('default_host', 'localhost')
        if not self.validation_rules['host_pattern'].match(default_host):
            result.add_error(f"无效的默认主机地址: {default_host}")

    def _validate_service_config(self, service_name: str, config: Dict[str, Any],
                                result: ValidationResult) -> None:
        """验证单个服务配置"""
        # 检查必需字段
        for field in self.validation_rules['required_fields']:
            if field not in config:
                result.add_error(f"服务 {service_name} 缺少必需字段: {field}")

        # 验证服务名称
        if 'name' in config and not self.validation_rules['name_pattern'].match(config['name']):
            result.add_error(f"服务 {service_name} 的名称格式无效: {config['name']}")

        # 验证服务类型
        if 'service_type' in config:
            try:
                ServiceType(config['service_type'])
            except ValueError:
                result.add_error(f"服务 {service_name} 的服务类型无效: {config['service_type']}")

        # 验证端口配置
        if 'port' in config and config['port'] is not None:
            port = config['port']
            if not (1 <= port <= 65535):
                result.add_error(f"服务 {service_name} 的端口号无效: {port}")
            elif port < 1024:
                result.add_warning(f"服务 {service_name} 使用系统端口: {port}")

        # 验证超时配置
        if 'startup_timeout' in config:
            timeout = config['startup_timeout']
            if not (self.validation_rules['timeout_limits']['min'] <= timeout <=
                    self.validation_rules['timeout_limits']['max']):
                result.add_warning(f"服务 {service_name} 的超时时间超出建议范围: {timeout}")

        # 验证主机地址
        if 'host' in config and not self.validation_rules['host_pattern'].match(config['host']):
            result.add_error(f"服务 {service_name} 的主机地址格式无效: {config['host']}")

        # 验证依赖关系
        if 'dependencies' in config:
            dependencies = config['dependencies']
            if not isinstance(dependencies, list):
                result.add_error(f"服务 {service_name} 的依赖关系必须是列表格式")
            elif service_name in dependencies:
                result.add_error(f"服务 {service_name} 不能依赖自己")

    def _build_service_configs(self) -> None:
        """构建服务配置对象"""
        services_config = self.processed_config.get('services', {})
        global_config = self.processed_config.get('global', {})

        for service_name, service_data in services_config.items():
            # 合并全局配置
            merged_data = {
                'host': global_config.get('default_host', 'localhost'),
                'startup_timeout': global_config.get('default_timeout', 60),
                'auto_restart': global_config.get('auto_restart', False),
                **service_data
            }

            # 处理环境变量替换
            merged_data = self._substitute_environment_variables(merged_data)

            # 创建服务配置对象
            try:
                service_config = ServiceConfig.from_dict(merged_data)
                self.service_configs[service_name] = service_config
            except Exception as e:
                self.logger.error(f"构建服务配置失败 {service_name}: {e}")

    async def load_env_file(self, env_file: str) -> None:
        """
        加载环境变量文件

        Args:
            env_file: 环境变量文件路径
        """
        from dotenv import load_dotenv

        try:
            load_dotenv(env_file)
            self.logger.info(f"Environment file loaded: {env_file}")
        except Exception as e:
            self.logger.error(f"Failed to load environment file {env_file}: {e}")
            raise

    def _substitute_environment_variables(self, data: Any) -> Any:
        """替换环境变量"""
        if isinstance(data, str):
            # 替换字符串中的环境变量
            def replace_env_var(match):
                var_name = match.group(1)
                # 首先检查系统环境变量
                value = os.getenv(var_name)
                if value is None:
                    # 检查配置中的默认值
                    default_value = os.getenv(f"{var_name}_DEFAULT", "")
                    if default_value:
                        return default_value
                    # 如果都没有，保持原样
                    return match.group(0)
                return value

            return self.env_var_pattern.sub(replace_env_var, data)

        elif isinstance(data, dict):
            return {key: self._substitute_environment_variables(value) for key, value in data.items()}

        elif isinstance(data, list):
            return [self._substitute_environment_variables(item) for item in data]

        else:
            return data

    def export_config_schema(self) -> Dict[str, Any]:
        """
        导出配置模式

        Returns:
            配置模式字典
        """
        return {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            'title': 'Service Configuration Schema',
            'description': '服务启动配置文件模式',
            'type': 'object',
            'properties': {
                'version': {
                    'type': 'string',
                    'description': '配置文件版本'
                },
                'environment': {
                    'type': 'string',
                    'enum': ['development', 'testing', 'staging', 'production'],
                    'description': '目标环境'
                },
                'global': {
                    'type': 'object',
                    'properties': {
                        'default_host': {
                            'type': 'string',
                            'default': 'localhost',
                            'description': '默认主机地址'
                        },
                        'default_timeout': {
                            'type': 'integer',
                            'minimum': 5,
                            'maximum': 600,
                            'default': 60,
                            'description': '默认启动超时时间（秒）'
                        },
                        'auto_restart': {
                            'type': 'boolean',
                            'default': False,
                            'description': '是否自动重启失败的服务'
                        }
                    }
                },
                'services': {
                    'type': 'object',
                    'patternProperties': {
                        '^[a-zA-Z0-9_-]+$': {
                            'type': 'object',
                            'required': ['name', 'service_type'],
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'pattern': '^[a-zA-Z0-9_-]+$',
                                    'description': '服务名称'
                                },
                                'service_type': {
                                    'type': 'string',
                                    'enum': ['database', 'backend_api', 'frontend', 'cache',
                                            'message_queue', 'external_api', 'utility'],
                                    'description': '服务类型'
                                },
                                'host': {
                                    'type': 'string',
                                    'default': 'localhost',
                                    'description': '服务主机地址'
                                },
                                'port': {
                                    'type': 'integer',
                                    'minimum': 1,
                                    'maximum': 65535,
                                    'description': '服务端口号'
                                },
                                'health_endpoint': {
                                    'type': 'string',
                                    'description': '健康检查端点'
                                },
                                'startup_timeout': {
                                    'type': 'integer',
                                    'minimum': 5,
                                    'maximum': 600,
                                    'default': 60,
                                    'description': '启动超时时间（秒）'
                                },
                                'dependencies': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string'
                                    },
                                    'description': '依赖的服务列表'
                                },
                                'startup_command': {
                                    'type': 'string',
                                    'description': '启动命令'
                                },
                                'startup_args': {
                                    'type': 'object',
                                    'description': '启动参数'
                                },
                                'environment_variables': {
                                    'type': 'object',
                                    'description': '环境变量'
                                },
                                'working_directory': {
                                    'type': 'string',
                                    'description': '工作目录'
                                },
                                'auto_restart': {
                                    'type': 'boolean',
                                    'default': False,
                                    'description': '是否自动重启'
                                },
                                'enabled': {
                                    'type': 'boolean',
                                    'default': True,
                                    'description': '是否启用服务'
                                },
                                'metadata': {
                                    'type': 'object',
                                    'description': '元数据'
                                }
                            }
                        }
                    }
                }
            }
        }