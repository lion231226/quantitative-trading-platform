from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, field_validator, ConfigDict
from pydantic_settings import BaseSettings
import secrets
from pathlib import Path

class Settings(BaseSettings):
    """应用配置设置"""

    # 基础设置
    PROJECT_NAME: str = "量化交易策略分析平台"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ENVIRONMENT: str = "development"

    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    # CORS设置
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8080",
        "https://localhost:3000",
        "https://localhost:3001",
        "https://localhost:3002",
        "https://localhost:8080",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库设置
    DATABASE_URL: Optional[str] = None
    SQLITE_DB_PATH: str = str(Path(__file__).parent.parent.parent / "quant_trading.db")

    # Redis设置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # AKShare API设置
    AKSHARE_CACHE_TTL: int = 86400  # 24小时
    AKSHARE_MAX_RETRY_ATTEMPTS: int = 3
    AKSHARE_RETRY_DELAY: float = 1.0

    # 策略计算设置
    STRATEGY_TIMEOUT: int = 30  # 秒
    MAX_CALCULATION_PERIODS: int = 1000

    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 安全设置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"

    # 文件上传设置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"

    # 缓存设置
    CACHE_TTL: int = 3600  # 1小时
    CACHE_MAX_SIZE: int = 1000

    # API限流设置
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 200

    # 测试设置
    TESTING: bool = False
    TEST_DATABASE_URL: Optional[str] = None

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        elif self.DATABASE_URL:
            return self.DATABASE_URL
        else:
            # 默认使用SQLite
            return f"sqlite:///{self.SQLITE_DB_PATH}"

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        config = {
            "url": self.REDIS_URL,
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
        }

        if self.REDIS_PASSWORD:
            config["password"] = self.REDIS_PASSWORD

        return config

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.ENVIRONMENT.lower() == "production"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        validate_assignment=True,
        extra="ignore"
    )

# 创建全局设置实例
settings = Settings()

# 常用配置常量
API_PREFIX = "/api/v1"
PROJECT_NAME = settings.PROJECT_NAME
VERSION = settings.VERSION
DEBUG = settings.DEBUG

# 安全相关常量
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 数据库相关
DATABASE_URL = settings.get_database_url()

# Redis相关
REDIS_CONFIG = settings.get_redis_config()

# CORS相关
CORS_ORIGINS = settings.get_cors_origins()

# 缓存相关
CACHE_TTL = settings.CACHE_TTL
CACHE_MAX_SIZE = settings.CACHE_MAX_SIZE

# API限流
RATE_LIMIT_PER_MINUTE = settings.RATE_LIMIT_PER_MINUTE
RATE_LIMIT_BURST = settings.RATE_LIMIT_BURST

# 日志相关
LOG_LEVEL = settings.LOG_LEVEL
LOG_FORMAT = settings.LOG_FORMAT

# 文件上传
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE
UPLOAD_DIR = settings.UPLOAD_DIR