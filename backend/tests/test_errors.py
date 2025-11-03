import pytest
from fastapi import HTTPException, status
from app.utils.errors import (
    ValidationError,
    APIError,
    DatabaseError,
    ExternalAPIError,
    StrategyError,
    DataError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    create_error_response,
    handle_success_response
)

class TestCustomExceptions:
    """自定义异常测试"""

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError("Invalid input", field="email")
        assert str(error) == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field == "email"

    def test_api_error(self):
        """测试API错误"""
        error = APIError("API call failed", details={"code": 500})
        assert str(error) == "API call failed"
        assert error.error_code == "API_ERROR"
        assert error.details["code"] == 500

    def test_database_error(self):
        """测试数据库错误"""
        error = DatabaseError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.error_code == "DATABASE_ERROR"

    def test_external_api_error(self):
        """测试外部API错误"""
        error = ExternalAPIError("Service unavailable", service="akshare")
        assert str(error) == "Service unavailable"
        assert error.error_code == "EXTERNAL_API_ERROR"
        assert error.service == "akshare"

    def test_strategy_error(self):
        """测试策略错误"""
        error = StrategyError("Calculation failed", strategy_id="123")
        assert str(error) == "Calculation failed"
        assert error.error_code == "STRATEGY_ERROR"
        assert error.strategy_id == "123"

    def test_data_error(self):
        """测试数据错误"""
        error = DataError("Invalid data", symbol="CU2401")
        assert str(error) == "Invalid data"
        assert error.error_code == "DATA_ERROR"
        assert error.symbol == "CU2401"

    def test_authentication_error(self):
        """测试认证错误"""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert error.error_code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self):
        """测试授权错误"""
        error = AuthorizationError("Access denied")
        assert str(error) == "Access denied"
        assert error.error_code == "AUTHORIZATION_ERROR"

    def test_rate_limit_error(self):
        """测试频率限制错误"""
        error = RateLimitError("Too many requests", retry_after=60)
        assert str(error) == "Too many requests"
        assert error.error_code == "RATE_LIMIT_ERROR"
        assert error.retry_after == 60

class TestErrorResponse:
    """错误响应测试"""

    def test_create_error_response_basic(self):
        """测试基础错误响应"""
        response = create_error_response(
            error_type="TEST_ERROR",
            message="Test message"
        )

        assert response.status_code == 500
        content = response.body.decode()
        import json
        data = json.loads(content)

        assert data["success"] is False
        assert data["error"]["type"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test message"
        assert "details" not in data["error"]

    def test_create_error_response_with_details(self):
        """测试带详情的错误响应"""
        response = create_error_response(
            error_type="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "email", "value": "invalid"},
            status_code=400
        )

        assert response.status_code == 400
        content = response.body.decode()
        import json
        data = json.loads(content)

        assert data["success"] is False
        assert data["error"]["type"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Validation failed"
        assert data["error"]["details"]["field"] == "email"
        assert data["error"]["details"]["value"] == "invalid"

    def test_handle_success_response(self):
        """测试成功响应"""
        response = handle_success_response(
            data={"id": 123},
            message="Operation completed"
        )

        assert response["success"] is True
        assert response["message"] == "Operation completed"
        assert response["data"]["id"] == 123

    def test_handle_success_response_no_data(self):
        """测试无数据的成功响应"""
        response = handle_success_response(message="Operation completed")

        assert response["success"] is True
        assert response["message"] == "Operation completed"
        assert "data" not in response

class TestErrorHierarchy:
    """错误层次结构测试"""

    def test_base_error_inheritance(self):
        """测试基础错误继承"""
        error = ValidationError("Test error")
        assert isinstance(error, Exception)
        assert hasattr(error, 'message')
        assert hasattr(error, 'error_code')
        assert hasattr(error, 'details')

    def test_all_errors_inherit_from_base(self):
        """测试所有错误都继承自基础错误"""
        errors = [
            ValidationError("test"),
            APIError("test"),
            DatabaseError("test"),
            ExternalAPIError("test"),
            StrategyError("test"),
            DataError("test"),
            AuthenticationError("test"),
            AuthorizationError("test"),
            RateLimitError("test"),
        ]

        for error in errors:
            assert isinstance(error, Exception)
            assert hasattr(error, 'message')
            assert hasattr(error, 'error_code')

class TestErrorContext:
    """错误上下文测试"""

    def test_error_with_context(self):
        """测试带上下文的错误"""
        details = {
            "user_id": 123,
            "request_id": "abc-123",
            "timestamp": "2023-01-01T00:00:00Z"
        }

        error = APIError("Context error", details=details)
        assert error.details == details

    def test_error_serialization(self):
        """测试错误序列化"""
        error = ValidationError("Serialization test", field="test_field")

        error_dict = {
            "message": error.message,
            "error_code": error.error_code,
            "details": error.details,
            "field": error.field
        }

        assert "message" in error_dict
        assert "error_code" in error_dict
        assert "details" in error_dict
        assert "field" in error_dict