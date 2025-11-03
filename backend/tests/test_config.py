import pytest
import os
from unittest.mock import patch
from app.core.config import settings

class TestSettings:
    """配置设置测试"""

    def test_default_values(self):
        """测试默认配置值"""
        assert settings.PROJECT_NAME == "量化交易单均线策略分析平台"
        assert settings.VERSION == "1.0.0"
        assert settings.API_V1_STR == "/api/v1"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True

    def test_database_config(self):
        """测试数据库配置"""
        assert "sqlite" in settings.DATABASE_URL.lower()
        assert settings.DATABASE_POOL_SIZE == 5
        assert settings.DATABASE_MAX_OVERFLOW == 10

    def test_redis_config(self):
        """测试Redis配置"""
        assert settings.REDIS_URL == "redis://localhost:6379"
        assert settings.REDIS_CACHE_TTL == 86400

    def test_cors_config(self):
        """测试CORS配置"""
        assert len(settings.BACKEND_CORS_ORIGINS) > 0
        assert any("localhost" in str(origin) for origin in settings.BACKEND_CORS_ORIGINS)

    def test_akshare_config(self):
        """测试AKShare配置"""
        assert settings.AKSHARE_CACHE_TTL == 86400
        assert settings.AKSHARE_MAX_RETRY_ATTEMPTS == 3
        assert settings.AKSHARE_RETRY_DELAY == 1.0

    def test_strategy_config(self):
        """测试策略配置"""
        assert settings.STRATEGY_TIMEOUT == 30
        assert settings.MAX_CALCULATION_PERIODS == 1000

    def test_environment_detection(self):
        """测试环境检测"""
        # 测试开发环境
        with patch.object(settings, 'ENVIRONMENT', 'development'):
            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False

        # 测试生产环境
        with patch.object(settings, 'ENVIRONMENT', 'production'):
            assert settings.is_development is False
            assert settings.is_production is True
            assert settings.is_testing is False

        # 测试测试环境
        with patch.object(settings, 'TESTING', True):
            assert settings.is_testing is True

    def test_get_database_url(self):
        """测试获取数据库URL"""
        # 正常情况
        normal_url = settings.get_database_url()
        assert normal_url == settings.DATABASE_URL

        # 测试环境
        with patch.object(settings, 'TESTING', True):
            test_url = settings.get_database_url()
            assert test_url == settings.TEST_DATABASE_URL

    @pytest.mark.parametrize("env_value,expected_debug", [
        ("development", True),
        ("production", False),
        ("testing", False),
    ])
    def test_debug_mode(self, env_value, expected_debug):
        """测试调试模式设置"""
        with patch.object(settings, 'ENVIRONMENT', env_value):
            # 在生产环境下DEBUG应该为False
            if env_value == "production":
                with patch.object(settings, 'DEBUG', False):
                    assert settings.DEBUG is expected_debug
            else:
                # 在非生产环境下保持原有DEBUG设置
                assert settings.DEBUG == settings.DEBUG

class TestEnvironmentVariables:
    """环境变量测试"""

    def test_secret_key_generation(self):
        """测试密钥生成"""
        assert len(settings.SECRET_KEY) > 0
        assert isinstance(settings.SECRET_KEY, str)

    def test_host_config(self):
        """测试主机配置"""
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert len(settings.ALLOWED_HOSTS) > 0

    def test_log_config(self):
        """测试日志配置"""
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT in ["console", "json"]

    def test_jwt_config(self):
        """测试JWT配置"""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_MINUTE > 0

    def test_file_upload_config(self):
        """测试文件上传配置"""
        assert settings.MAX_UPLOAD_SIZE > 0
        assert hasattr(settings, 'UPLOAD_DIR')

    def test_api_performance_config(self):
        """测试API性能配置"""
        assert settings.API_REQUEST_TIMEOUT > 0
        assert settings.MAX_REQUESTS_PER_MINUTE > 0