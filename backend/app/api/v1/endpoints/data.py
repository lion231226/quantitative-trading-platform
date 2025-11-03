from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Any
from datetime import date, datetime
from io import BytesIO
import structlog

from app.schemas.market_data import MarketDataResponse, DataQueryResponse, DataExportRequest, DataSyncResponse
from app.services.data_storage import DataStorageService
from app.services.data_processor import DataProcessor
from app.utils.errors import APIError, ValidationError, DataError, handle_success_response

logger = structlog.get_logger()
router = APIRouter(prefix="/data", tags=["data"])

# 依赖注入
data_storage_service = DataStorageService()
data_processor = DataProcessor()

@router.get("/query", response_model=DataQueryResponse)
async def query_market_data(
    symbol: str = Query(..., description="期货代码"),
    start_date: Optional[date] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="返回记录数限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(100, ge=1, le=1000, description="每页大小")
):
    """查询市场数据"""
    try:
        logger.info(
            "查询市场数据请求",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size
        )

        # 计算偏移量
        if page > 1:
            offset = (page - 1) * size
        if limit is None:
            limit = size

        # 查询数据
        data = await data_storage_service.query_market_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        # 转换为响应格式
        market_data_responses = [
            MarketDataResponse(
                symbol=item.symbol,
                date=item.date,
                open_price=item.open_price,
                high_price=item.high_price,
                low_price=item.low_price,
                close_price=item.close_price,
                volume=item.volume,
                turnover=item.turnover,
                settlement_price=item.settlement_price,
                open_interest=item.open_interest
            )
            for item in data
        ]

        # 构建响应
        response_data = DataQueryResponse(
            symbol=symbol,
            data=market_data_responses,
            total_count=len(market_data_responses),
            page=page,
            size=size,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(
            "查询完成",
            symbol=symbol,
            count=len(market_data_responses),
            page=page
        )

        return handle_success_response(response_data, f"查询{symbol}市场数据成功")

    except ValidationError:
        raise
    except APIError:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("查询市场数据失败", error=str(e), symbol=symbol)
        raise APIError(f"查询市场数据失败: {str(e)}")

@router.get("/latest/{symbol}", response_model=List[MarketDataResponse])
async def get_latest_data(
    symbol: str,
    days: int = Query(1, ge=1, le=365, description="查询天数")
):
    """获取最新市场数据"""
    try:
        logger.info("获取最新数据", symbol=symbol, days=days)

        data = await data_storage_service.query_latest_data(symbol=symbol, days=days)

        market_data_responses = [
            MarketDataResponse(
                symbol=item.symbol,
                date=item.date,
                open_price=item.open_price,
                high_price=item.high_price,
                low_price=item.low_price,
                close_price=item.close_price,
                volume=item.volume,
                turnover=item.turnover,
                settlement_price=item.settlement_price,
                open_interest=item.open_interest
            )
            for item in data
        ]

        logger.info("最新数据查询完成", symbol=symbol, count=len(market_data_responses))
        return handle_success_response(market_data_responses, f"获取{symbol}最新数据成功")

    except ValidationError:
        raise
    except APIError:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("获取最新数据失败", error=str(e), symbol=symbol)
        raise APIError(f"获取最新数据失败: {str(e)}")

@router.get("/statistics")
async def get_data_statistics(
    symbol: Optional[str] = Query(None, description="期货代码，为空则统计所有品种")
):
    """获取数据统计信息"""
    try:
        logger.info("获取数据统计", symbol=symbol)

        stats = await data_storage_service.get_data_statistics(symbol=symbol)
        return handle_success_response(stats, f"获取数据统计成功")

    except ValidationError:
        raise
    except APIError:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("获取数据统计失败", error=str(e), symbol=symbol)
        raise APIError(f"获取数据统计失败: {str(e)}")

@router.get("/health")
async def get_storage_health() -> Any:
    """存储系统健康检查"""
    try:
        health_info = await data_storage_service.get_storage_health_check()
        return handle_success_response(health_info, "存储健康检查成功")

    except Exception as e:
        logger.error("存储健康检查失败", error=str(e))
        return handle_success_response({
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'healthy': False
        }, "存储健康检查发现问题")

@router.post("/export/{symbol}")
async def export_data(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    format: str = Query("csv", regex="^(csv|json|excel)$", description="导出格式")
):
    """导出市场数据"""
    try:
        logger.info(
            "导出数据请求",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            format=format
        )

        # 导出数据
        data_bytes = await data_storage_service.export_market_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            format=format
        )

        if not data_bytes:
            raise HTTPException(status_code=404, detail="没有找到要导出的数据")

        # 设置响应头
        filename = f"{symbol}_data_{start_date or 'start'}_to_{end_date or 'end'}.{format}"

        if format == "csv":
            media_type = "text/csv"
        elif format == "json":
            media_type = "application/json"
        elif format == "excel":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            media_type = "application/octet-stream"

        # 创建流式响应
        response = StreamingResponse(
            BytesIO(data_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

        logger.info(
            "数据导出完成",
            symbol=symbol,
            format=format,
            size_bytes=len(data_bytes)
        )

        return response

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("导出数据失败", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/sync/{symbol}", response_model=DataSyncResponse)
async def sync_incremental_data(
    symbol: str,
    raw_data: List[Dict[str, Any]]
) -> Any:
    """增量同步数据"""
    try:
        logger.info("增量同步请求", symbol=symbol, data_count=len(raw_data))

        if not raw_data:
            raise ValidationError("同步数据不能为空")

        # 执行增量同步
        sync_result = await data_storage_service.sync_incremental_data(symbol, raw_data)

        # 构建响应
        response = DataSyncResponse(
            symbol=sync_result['symbol'],
            new_records=sync_result['new_records'],
            updated_records=sync_result['updated_records'],
            quality_score=sync_result['quality_score'],
            sync_time=sync_result['sync_time']
        )

        logger.info(
            "增量同步完成",
            symbol=symbol,
            new_records=response.new_records,
            quality_score=response.quality_score
        )

        return response

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("增量同步失败", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.delete("/{symbol}")
async def delete_market_data(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """删除市场数据"""
    try:
        logger.info(
            "删除数据请求",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        # 执行删除
        deleted_count = await data_storage_service.delete_market_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(
            "数据删除完成",
            symbol=symbol,
            deleted_count=deleted_count
        )

        return {
            "symbol": symbol,
            "deleted_count": deleted_count,
            "start_date": start_date,
            "end_date": end_date
        }

    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("删除数据失败", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/vacuum")
async def vacuum_database() -> Any:
    """优化数据库"""
    try:
        logger.info("数据库优化请求")

        success = await data_storage_service.vacuum_database()

        if success:
            logger.info("数据库优化完成")
            return {"message": "数据库优化完成", "success": True}
        else:
            logger.error("数据库优化失败")
            raise HTTPException(status_code=500, detail="数据库优化失败")

    except Exception as e:
        logger.error("数据库优化异常", error=str(e))
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/quality/{symbol}")
async def get_data_quality_report(symbol: str) -> Any:
    """获取数据质量报告"""
    try:
        logger.info("获取数据质量报告", symbol=symbol)

        # 查询最近30天的数据
        data = await data_storage_service.query_latest_data(symbol, days=30)

        if not data:
            return {
                "symbol": symbol,
                "message": "没有找到数据",
                "quality_score": 0.0
            }

        # 生成质量报告
        quality_report = await data_processor.get_data_quality_report(symbol, data)

        logger.info(
            "数据质量报告生成完成",
            symbol=symbol,
            quality_score=quality_report.get('quality_score', 0)
        )

        return quality_report

    except Exception as e:
        logger.error("获取数据质量报告失败", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/symbols/latest")
async def get_symbols_latest_dates(
    symbols: str = Query(..., description="期货代码列表，逗号分隔")
):
    """获取多个品种的最新数据日期"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

        if not symbol_list:
            raise ValidationError("品种列表不能为空")

        logger.info("查询最新日期", symbols=symbol_list)

        latest_dates = await data_storage_service.query_symbols_latest_date(symbol_list)

        return {
            "symbols": symbol_list,
            "latest_dates": {
                symbol: latest_dates.get(symbol).isoformat() if latest_dates.get(symbol) else None
                for symbol in symbol_list
            }
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("查询最新日期失败", error=str(e), symbols=symbols)
        raise HTTPException(status_code=500, detail="内部服务器错误")