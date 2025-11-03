from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union, Dict, Any
import structlog
import traceback

logger = structlog.get_logger()

class BaseError(Exception):
    """基础异常类"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BaseError):
    """验证错误"""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field

class APIError(BaseError):
    """API业务逻辑错误"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "API_ERROR", details)

class DatabaseError(BaseError):
    """数据库错误"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "DATABASE_ERROR", details)

class CacheError(BaseError):
    """缓存错误"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "CACHE_ERROR", details)

class ExternalAPIError(BaseError):
    """外部API错误"""
    def __init__(self, message: str, service: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "EXTERNAL_API_ERROR", details)
        self.service = service

class StrategyError(BaseError):
    """策略计算错误"""
    def __init__(self, message: str, strategy_id: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "STRATEGY_ERROR", details)
        self.strategy_id = strategy_id

class DataError(BaseError):
    """数据处理错误"""
    def __init__(self, message: str, symbol: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "DATA_ERROR", details)
        self.symbol = symbol

class ProcessingError(BaseError):
    """数据处理错误"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "PROCESSING_ERROR", details)

class AuthenticationError(BaseError):
    """认证错误"""
    def __init__(self, message: str = "认证失败", details: Dict[str, Any] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details)

class AuthorizationError(BaseError):
    """授权错误"""
    def __init__(self, message: str = "权限不足", details: Dict[str, Any] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)

class RateLimitError(BaseError):
    """频率限制错误"""
    def __init__(self, message: str = "请求过于频繁", retry_after: int = None, details: Dict[str, Any] = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.retry_after = retry_after

def create_error_response(
    success: bool = False,
    error_type: str = "UNKNOWN_ERROR",
    message: str = "未知错误",
    details: Dict[str, Any] = None,
    status_code: int = 500
) -> JSONResponse:
    """创建统一的错误响应格式"""

    error_response = {
        "success": success,
        "error": {
            "type": error_type,
            "message": message
        }
    }

    if details:
        error_response["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

def setup_exception_handlers(app):
    """设置全局异常处理器"""

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """处理验证错误"""
        logger.warning(
            "验证错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            field=exc.field,
            details=exc.details
        )

        return create_error_response(
            error_type="VALIDATION_ERROR",
            message=exc.message,
            details={
                "field": exc.field,
                **exc.details
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @app.exception_handler(APIError)
    async def api_exception_handler(request: Request, exc: APIError):
        """处理API业务逻辑错误"""
        logger.warning(
            "API业务错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            details=exc.details
        )

        return create_error_response(
            error_type="API_ERROR",
            message=exc.message,
            details=exc.details,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @app.exception_handler(DatabaseError)
    async def database_exception_handler(request: Request, exc: DatabaseError):
        """处理数据库错误"""
        logger.error(
            "数据库错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            details=exc.details
        )

        return create_error_response(
            error_type="DATABASE_ERROR",
            message="数据库操作失败",
            details=exc.details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @app.exception_handler(ExternalAPIError)
    async def external_api_exception_handler(request: Request, exc: ExternalAPIError):
        """处理外部API错误"""
        logger.error(
            "外部API错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            service=exc.service,
            details=exc.details
        )

        return create_error_response(
            error_type="EXTERNAL_API_ERROR",
            message="外部服务暂时不可用",
            details={
                "service": exc.service,
                **exc.details
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    @app.exception_handler(StrategyError)
    async def strategy_exception_handler(request: Request, exc: StrategyError):
        """处理策略计算错误"""
        logger.error(
            "策略计算错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            strategy_id=exc.strategy_id,
            details=exc.details
        )

        return create_error_response(
            error_type="STRATEGY_ERROR",
            message=exc.message,
            details={
                "strategy_id": exc.strategy_id,
                **exc.details
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @app.exception_handler(DataError)
    async def data_exception_handler(request: Request, exc: DataError):
        """处理数据错误"""
        logger.error(
            "数据错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            symbol=exc.symbol,
            details=exc.details
        )

        return create_error_response(
            error_type="DATA_ERROR",
            message=exc.message,
            details={
                "symbol": exc.symbol,
                **exc.details
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
        """处理频率限制错误"""
        logger.warning(
            "频率限制错误",
            path=request.url.path,
            method=request.method,
            message=exc.message,
            retry_after=exc.retry_after
        )

        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "type": "RATE_LIMIT_ERROR",
                    "message": exc.message,
                    "retry_after": exc.retry_after
                }
            },
            headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        logger.warning(
            "请求验证错误",
            path=request.url.path,
            method=request.method,
            errors=exc.errors()
        )

        # 格式化验证错误信息
        formatted_errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            formatted_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        return create_error_response(
            error_type="VALIDATION_ERROR",
            message="请求参数验证失败",
            details={"validation_errors": formatted_errors},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理HTTP异常"""
        logger.warning(
            "HTTP异常",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            detail=exc.detail
        )

        return create_error_response(
            error_type="HTTP_ERROR",
            message=exc.detail or "HTTP错误",
            details={"status_code": exc.status_code},
            status_code=exc.status_code
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.error(
            "未处理异常",
            path=request.url.path,
            method=request.method,
            exception_type=type(exc).__name__,
            message=str(exc),
            traceback=traceback.format_exc()
        )

        # 开发环境返回详细错误信息
        from app.core.config import settings
        if settings.is_development:
            return create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message=f"内部服务器错误: {str(exc)}",
                details={
                    "exception_type": type(exc).__name__,
                    "traceback": traceback.format_exc()
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            # 生产环境返回通用错误信息
            return create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message="内部服务器错误，请稍后重试",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def handle_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应格式"""
    response = {
        "success": True,
        "message": message
    }

    if data is not None:
        response["data"] = data

    return response