from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, date
import structlog

from app.schemas.market_data import MarketDataResponse, SymbolResponse, RefreshDataRequest
from app.services.akshare_client import AKShareClient
from app.services.cache_service import CacheService
from app.utils.errors import ValidationError, APIError, ExternalAPIError, DataError, handle_success_response

logger = structlog.get_logger()
router = APIRouter()

# 依赖注入
def get_akshare_client() -> AKShareClient:
    return AKShareClient()

def get_cache_service() -> CacheService:
    return CacheService()

@router.get("/symbols")
async def get_available_symbols(
    sector: Optional[str] = Query(None, description="版块类型：energy, metal, agriculture, chemical"),
    client: AKShareClient = Depends(get_akshare_client)
):
    """获取可用的期货品种列表"""
    try:
        logger.info("获取期货品种列表", sector=sector)
        symbols = await client.get_available_symbols(sector)
        return handle_success_response(symbols, "获取期货品种列表成功")
    except ValidationError:
        raise
    except ExternalAPIError:
        raise
    except Exception as e:
        logger.error("获取期货品种失败", error=str(e), sector=sector)
        raise APIError(f"获取期货品种失败: {str(e)}")

@router.get("/history")
async def get_market_data_history(
    symbol: str = Query(..., description="期货代码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    cache_service: CacheService = Depends(get_cache_service),
    client: AKShareClient = Depends(get_akshare_client)
):
    """获取期货历史数据"""
    try:
        # 验证日期范围
        if start_date > end_date:
            raise ValidationError("开始日期不能晚于结束日期")

        # 验证日期范围不超过1年
        date_diff = (end_date - start_date).days
        if date_diff > 365:
            raise ValidationError("查询时间范围不能超过1年")

        logger.info("获取历史数据", symbol=symbol, start_date=start_date, end_date=end_date)

        # 尝试从缓存获取数据
        cached_data = await cache_service.get_market_data(symbol, start_date, end_date)
        if cached_data:
            logger.info("从缓存获取数据", symbol=symbol, count=len(cached_data))
            return handle_success_response(cached_data, f"获取{symbol}历史数据成功（缓存）")

        # 从API获取数据
        data = await client.get_market_data(symbol, start_date, end_date)

        # 缓存数据
        await cache_service.set_market_data(symbol, data)

        logger.info("获取数据成功", symbol=symbol, count=len(data))
        return handle_success_response(data, f"获取{symbol}历史数据成功")

    except ValidationError:
        raise
    except ExternalAPIError:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("获取历史数据失败", error=str(e), symbol=symbol)
        raise APIError(f"获取历史数据失败: {str(e)}")

@router.post("/refresh")
async def refresh_market_data(
    request: RefreshDataRequest,
    cache_service: CacheService = Depends(get_cache_service),
    client: AKShareClient = Depends(get_akshare_client)
):
    """刷新指定品种的数据缓存"""
    try:
        logger.info("刷新数据缓存", symbol=request.symbol)

        # 清除缓存
        await cache_service.delete_market_data(request.symbol)

        # 重新获取最新数据
        if request.end_date:
            data = await client.get_market_data(
                request.symbol,
                request.start_date or date(2023, 1, 1),
                request.end_date
            )
        else:
            # 默认获取最近一年的数据
            end_date = date.today()
            start_date = date(end_date.year - 1, end_date.month, end_date.day)
            data = await client.get_market_data(request.symbol, start_date, end_date)

        # 缓存新数据
        await cache_service.set_market_data(request.symbol, data)

        logger.info("数据刷新成功", symbol=request.symbol, count=len(data))
        return handle_success_response(
            {
                "symbol": request.symbol,
                "data_count": len(data),
                "refresh_time": date.today().isoformat()
            },
            f"品种 {request.symbol} 数据刷新成功"
        )

    except ValidationError:
        raise
    except ExternalAPIError:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("刷新数据失败", error=str(e), symbol=request.symbol)
        raise APIError(f"刷新数据失败: {str(e)}")

@router.get("/sectors")
async def get_supported_sectors(
    client: AKShareClient = Depends(get_akshare_client)
):
    """获取支持的版块列表"""
    try:
        logger.info("获取支持版块列表")
        sectors = await client.get_supported_sectors()
        return handle_success_response(sectors, "获取支持版块列表成功")
    except ValidationError:
        raise
    except ExternalAPIError:
        raise
    except Exception as e:
        logger.error("获取版块列表失败", error=str(e))
        raise APIError(f"获取版块列表失败: {str(e)}")