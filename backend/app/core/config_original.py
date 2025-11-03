from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings
import secrets
from pathlib import Path

class Settings(BaseSettings):
    """应用配置设置"""

    # 基础设置
    PROJECT_NAME: str = "量化交易单均线策略分析平台"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # 环境设置
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0", "testserver", "testclient"]

    # 数据库设置
    DATABASE_URL: str = "sqlite:///./quant_trading.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis设置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 86400  # 24小时

    # CORS设置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # AKShare API设置
    AKSHARE_CACHE_TTL: int = 86400  # 24小时
    AKSHARE_MAX_RETRY_ATTEMPTS: int = 3
    AKSHARE_RETRY_DELAY: float = 1.0

    # 策略计算设置
    STRATEGY_TIMEOUT: int = 30  # 秒
    MAX_CALCULATION_PERIODS: int = 1000

    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # JWT设置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30天

    # 文件上传设置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: Path = Path("uploads")

    # 性能设置
    API_REQUEST_TIMEOUT: int = 30
    MAX_REQUESTS_PER_MINUTE: int = 100

    # 测试设置
    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite:///./test_quant_trading.db"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.TESTING or self.ENVIRONMENT.lower() == "testing"

    def get_database_url(self) -> str:
        """获取数据库URL"""
        if self.is_testing:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL

# 创建全局设置实例
settings = Settings()