from fastapi import APIRouter

from app.api.v1.endpoints import market_data, strategies, comparison
# 暂时注释掉有问题的端点
# from app.api.v1.endpoints import backtest, data, performance

api_router = APIRouter()

# 包含各个模块的API路由
api_router.include_router(
    market_data.router,
    prefix="/market-data",
    tags=["market-data"]
)
api_router.include_router(
    strategies.router,
    prefix="/strategies",
    tags=["strategies"]
)
# api_router.include_router(
#     performance.router,
#     prefix="/performance",
#     tags=["performance"]
# )
api_router.include_router(
    comparison.router,
    prefix="/comparison",
    tags=["comparison"]
)
# 暂时注释掉有问题的路由
# api_router.include_router(data.router, prefix="/data-storage", tags=["data-storage"])
# api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])