from fastapi import APIRouter, HTTPException, Depends
from typing import List, Any
import structlog
import uuid

from app.schemas.strategy import (
    StrategyRequest,
    StrategyResponse,
    StrategyListResponse,
    StrategyParameters
)
from app.strategy.strategy_engine import StrategyEngine
from app.services.cache_service import CacheService
from app.services.task_manager import task_manager
from app.utils.errors import ValidationError, APIError

logger = structlog.get_logger()
router = APIRouter()

def get_strategy_engine() -> StrategyEngine:
    # 创建默认配置 - 使用简化的字典方式避免复杂的配置依赖
    from app.strategy.config import create_single_ma_config

    # 使用工厂函数创建单均线策略配置
    default_config = create_single_ma_config(
        ma_period=20,
        initial_capital=100000
    )
    return StrategyEngine(default_config)

def get_cache_service() -> CacheService:
    return CacheService()

@router.get("/", response_model=StrategyListResponse)
async def get_strategies():
    """获取可用策略列表"""
    try:
        strategies = [
            {
                "name": "single_ma",
                "display_name": "单均线策略",
                "description": "基于单条移动平均线的简单交易策略",
                "parameters": {
                    "ma_period": {
                        "type": "integer",
                        "default": 20,
                        "min": 5,
                        "max": 200,
                        "description": "移动平均线周期"
                    },
                    "initial_capital": {
                        "type": "number",
                        "default": 100000,
                        "min": 10000,
                        "max": 10000000,
                        "description": "初始资金"
                    },
                    "stop_loss": {
                        "type": "number",
                        "default": 0.05,
                        "min": 0.01,
                        "max": 0.5,
                        "description": "止损比例"
                    }
                }
            }
        ]

        logger.info("获取策略列表", strategies_count=len(strategies))
        return {"strategies": strategies, "total": len(strategies)}

    except Exception as e:
        logger.error("获取策略列表失败", error=str(e))
        raise APIError(f"获取策略列表失败: {str(e)}")

@router.get("/parameters/{strategy_type}")
async def get_strategy_parameters(strategy_type: str):
    """获取策略参数说明"""
    try:
        # 支持多种策略类型命名
        supported_types = ["single_ma", "single_moving_average"]
        if strategy_type not in supported_types:
            raise ValidationError(f"不支持的策略类型: {strategy_type}")

        parameters = {
            "ma_period": {
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 200,
                "description": "移动平均线周期",
                "unit": "天"
            },
            "initial_capital": {
                "type": "number",
                "default": 100000,
                "min": 10000,
                "max": 10000000,
                "description": "初始资金",
                "unit": "元"
            },
            "stop_loss": {
                "type": "number",
                "default": 0.05,
                "min": 0.01,
                "max": 0.5,
                "description": "止损比例",
                "unit": "百分比"
            },
            "take_profit": {
                "type": "number",
                "default": 0.10,
                "min": 0.01,
                "max": 1.0,
                "description": "止盈比例",
                "unit": "百分比"
            }
        }

        logger.info("获取策略参数", strategy_type=strategy_type)
        return {"parameters": parameters}

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取策略参数失败", strategy_type=strategy_type, error=str(e))
        raise APIError(f"获取策略参数失败: {str(e)}")

@router.post("/configure")
async def configure_strategy(
    request: StrategyRequest,
    strategy_engine: StrategyEngine = Depends(get_strategy_engine)
):
    """配置策略参数"""
    try:
        # 验证请求参数 - 支持多种策略类型命名
        supported_types = ["single_ma", "single_moving_average"]
        if request.strategy_type not in supported_types:
            raise ValidationError(f"不支持的策略类型: {request.strategy_type}")

        # 验证参数
        params = request.parameters
        if not (5 <= params.get("ma_period", 20) <= 200):
            raise ValidationError("移动平均线周期必须在5-200之间")

        if not (10000 <= params.get("initial_capital", 100000) <= 10000000):
            raise ValidationError("初始资金必须在10000-10000000之间")

        config_id = str(uuid.uuid4())

        logger.info("策略配置完成",
                   config_id=config_id,
                   strategy_type=request.strategy_type,
                   parameters=params)

        return {
            "success": True,
            "config_id": config_id,
            "strategy_type": request.strategy_type,
            "parameters": params,
            "message": "策略配置成功"
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("配置策略失败", error=str(e), request=request.dict())
        raise APIError(f"配置策略失败: {str(e)}")

@router.post("/run", response_model=StrategyResponse)
async def run_strategy(
    request: StrategyRequest,
    strategy_engine: StrategyEngine = Depends(get_strategy_engine),
    cache_service: CacheService = Depends(get_cache_service)
):
    """运行策略分析（异步）"""
    try:
        # 生成策略执行ID
        strategy_id = str(uuid.uuid4())

        logger.info(
            "创建异步策略任务",
            strategy_id=strategy_id,
            symbol=request.symbol,
            strategy_type=request.strategy_type
        )

        # 验证请求参数 - 支持多种策略类型命名
        supported_types = ["single_ma", "single_moving_average"]
        if request.strategy_type not in supported_types:
            raise ValidationError(f"不支持的策略类型: {request.strategy_type}")

        # 创建异步任务
        async def run_strategy_task() -> Any:
            """策略执行任务"""
            # 更新进度 - 开始
            task_manager.update_progress(strategy_id, 0.1)

            # 执行策略
            result = await strategy_engine.run_single_ma_strategy(
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                parameters=request.parameters
            )

            # 更新进度 - 完成
            task_manager.update_progress(strategy_id, 0.9)

            # 缓存结果
            await cache_service.set_strategy_result(strategy_id, result)

            # 更新进度 - 完成
            task_manager.update_progress(strategy_id, 1.0)

            return result

        # 提交异步任务，使用自定义任务ID
        await task_manager.create_task(run_strategy_task, strategy_id)

        logger.info(
            "异步策略任务已创建",
            strategy_id=strategy_id,
            symbol=request.symbol,
            strategy_type=request.strategy_type
        )

        return {
            "strategy_id": strategy_id,
            "strategy_type": request.strategy_type,
            "symbol": request.symbol,
            "parameters": request.parameters,
            "status": "running",
            "message": "策略正在后台执行，请使用task_id查询结果"
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("创建策略任务失败", error=str(e), request=request.dict())
        raise APIError(f"创建策略任务失败: {str(e)}")

@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str) -> Any:
    """获取异步任务状态"""
    try:
        task_info = task_manager.get_task_status(task_id)

        logger.info("查询任务状态", task_id=task_id, status=task_info["status"])
        return task_info

    except ValueError as e:
        logger.warning("任务不存在", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("查询任务状态失败", task_id=task_id, error=str(e))
        raise APIError(f"查询任务状态失败: {str(e)}")

@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str) -> Any:
    """取消异步任务"""
    try:
        success = await task_manager.cancel_task(task_id)

        if success:
            logger.info("任务取消成功", task_id=task_id)
            return {"success": True, "message": "任务已取消"}
        else:
            logger.warning("任务取消失败", task_id=task_id)
            return {"success": False, "message": "任务无法取消或已完成"}

    except Exception as e:
        logger.error("取消任务失败", task_id=task_id, error=str(e))
        raise APIError(f"取消任务失败: {str(e)}")

@router.get("/results/{strategy_id}")
async def get_strategy_results(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略执行结果"""
    try:
        # 先从缓存获取结果
        result = await cache_service.get_strategy_result(strategy_id)

        if result is None:
            # 如果缓存中没有，检查任务状态
            try:
                task_info = task_manager.get_task_status(strategy_id)
                if task_info["status"] == "running":
                    return {
                        "strategy_id": strategy_id,
                        "status": "running",
                        "progress": task_info.get("progress", 0.0),
                        "message": "策略正在执行中"
                    }
                elif task_info["status"] == "failed":
                    return {
                        "strategy_id": strategy_id,
                        "status": "failed",
                        "error": task_info.get("error", "未知错误"),
                        "message": "策略执行失败"
                    }
            except ValueError:
                pass

            raise HTTPException(
                status_code=404,
                detail=f"策略结果不存在: {strategy_id}"
            )

        logger.info("获取策略结果", strategy_id=strategy_id)
        return {
            "strategy_id": strategy_id,
            "status": "completed",
            "result": result,
            "message": "策略执行完成"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取策略结果失败", strategy_id=strategy_id, error=str(e))
        raise APIError(f"获取策略结果失败: {str(e)}")

@router.get("/results/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略执行结果（性能指标）"""
    try:
        result = await cache_service.get_strategy_result(strategy_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"策略结果不存在: {strategy_id}"
            )

        # 提取性能指标
        performance = {
            "strategy_id": strategy_id,
            "total_return": result.get("total_return", 0),
            "annualized_return": result.get("annualized_return", 0),
            "max_drawdown": result.get("max_drawdown", 0),
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "win_rate": result.get("win_rate", 0),
            "total_trades": result.get("total_trades", 0),
            "profitable_trades": result.get("profitable_trades", 0),
            "losing_trades": result.get("losing_trades", 0),
        }

        logger.info("获取策略性能指标", strategy_id=strategy_id)
        return performance

    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取策略性能失败", strategy_id=strategy_id, error=str(e))
        raise APIError(f"获取策略性能失败: {str(e)}")

@router.get("/results/{strategy_id}/trades")
async def get_strategy_trades(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service),
    page: int = 1,
    limit: int = 50
):
    """获取策略交易记录"""
    try:
        result = await cache_service.get_strategy_result(strategy_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"策略结果不存在: {strategy_id}"
            )

        trades = result.get("trades", [])

        # 分页处理
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_trades = trades[start_idx:end_idx]

        response = {
            "strategy_id": strategy_id,
            "trades": paginated_trades,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(trades),
                "pages": (len(trades) + limit - 1) // limit
            }
        }

        logger.info("获取策略交易记录",
                   strategy_id=strategy_id,
                   trades_count=len(paginated_trades))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取策略交易记录失败", strategy_id=strategy_id, error=str(e))
        raise APIError(f"获取策略交易记录失败: {str(e)}")

@router.get("/results/{strategy_id}/summary")
async def get_strategy_summary(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略执行摘要"""
    try:
        result = await cache_service.get_strategy_result(strategy_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"策略结果不存在: {strategy_id}"
            )

        summary = {
            "strategy_id": strategy_id,
            "symbol": result.get("symbol"),
            "start_date": result.get("start_date"),
            "end_date": result.get("end_date"),
            "initial_capital": result.get("initial_capital"),
            "final_capital": result.get("final_capital"),
            "total_return": result.get("total_return"),
            "max_drawdown": result.get("max_drawdown"),
            "sharpe_ratio": result.get("sharpe_ratio"),
            "total_trades": result.get("total_trades"),
            "win_rate": result.get("win_rate"),
        }

        logger.info("获取策略摘要", strategy_id=strategy_id)
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取策略摘要失败", strategy_id=strategy_id, error=str(e))
        raise APIError(f"获取策略摘要失败: {str(e)}")