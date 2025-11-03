"""
Production environment configuration
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class ProductionSettings(BaseSettings):
    """Production settings"""

    # App settings
    app_name: str = "量化交易策略分析平台"
    debug: bool = False
    environment: str = "production"

    # Server settings
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))

    # Database
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Redis
    redis_url: Optional[str] = os.getenv("REDIS_URL")

    # CORS
    allowed_origins: list = [
        "https://your-frontend-domain.vercel.app",
        "https://your-custom-domain.com"
    ]

    # API Keys (set in environment variables)
    akshare_timeout: int = 30

    # Cache settings
    cache_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    access_token_expire_minutes: int = 1440  # 24 hours

    class Config:
        env_file = ".env.production"
        case_sensitive = False


@lru_cache()
def get_production_settings() -> ProductionSettings:
    """Get production settings (cached)"""
    return ProductionSettings()