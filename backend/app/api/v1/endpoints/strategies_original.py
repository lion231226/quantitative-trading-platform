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
async def get_strategy_list() -> Any:
    """获取可用的策略列表"""
    try:
        logger.info("获取策略列表")
        strategies = [
            {
                "id": "single_ma",
                "name": "单均线策略",
                "description": "基于单一移动平均线的交易策略",
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
                        "max": 0.2,
                        "description": "止损比例"
                    }
                }
            }
        ]

        return {
            "strategies": strategies,
            "total": len(strategies)
        }
    except Exception as e:
        logger.error("获取策略列表失败", error=str(e))
        raise APIError(f"获取策略列表失败: {str(e)}")

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

        # 验证请求参数
        if request.strategy_type != "single_ma":
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

        # 提交异步任务
        await task_manager.create_task(run_strategy_task)

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
        if not task_info:
            raise ValidationError(f"任务不存在: {task_id}")

        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": task_info["status"],
                "progress": task_info["progress"],
                "created_at": task_info["created_at"].isoformat(),
                "started_at": task_info["started_at"].isoformat() if task_info["started_at"] else None,
                "completed_at": task_info["completed_at"].isoformat() if task_info["completed_at"] else None,
                "error": task_info["error"]
            }
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取任务状态失败", error=str(e), task_id=task_id)
        raise APIError(f"获取任务状态失败: {str(e)}")

@router.delete("/task/{task_id}")
async def cancel_task(task_id: str) -> Any:
    """取消异步任务"""
    try:
        success = await task_manager.cancel_task(task_id)
        if not success:
            raise ValidationError(f"无法取消任务: {task_id}")

        return {
            "success": True,
            "message": f"任务 {task_id} 已取消"
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("取消任务失败", error=str(e), task_id=task_id)
        raise APIError(f"取消任务失败: {str(e)}")

@router.get("/{strategy_id}/results", response_model=dict)
async def get_strategy_results(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略执行结果"""
    try:
        logger.info("获取策略结果", strategy_id=strategy_id)

        # 首先检查任务状态
        task_info = task_manager.get_task_status(strategy_id)
        if task_info:
            if task_info["status"] == "running":
                return {
                    "success": False,
                    "message": "策略正在执行中",
                    "status": "running",
                    "progress": task_info["progress"]
                }
            elif task_info["status"] == "failed":
                return {
                    "success": False,
                    "message": "策略执行失败",
                    "status": "failed",
                    "error": task_info["error"]
                }

        # 从缓存获取结果
        result = await cache_service.get_strategy_result(strategy_id)
        if not result:
            raise ValidationError(f"策略结果不存在或已过期: {strategy_id}")

        return {
            "success": True,
            "data": result,
            "status": "completed"
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取策略结果失败", error=str(e), strategy_id=strategy_id)
        raise APIError(f"获取策略结果失败: {str(e)}")

@router.get("/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略绩效指标"""
    try:
        logger.info("获取策略绩效指标", strategy_id=strategy_id)

        # 从缓存获取结果
        result = await cache_service.get_strategy_result(strategy_id)
        if not result:
            raise ValidationError(f"策略结果不存在或已过期: {strategy_id}")

        # 提取绩效指标
        performance_metrics = result.get("performance_metrics", {})

        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "total_return": performance_metrics.get("total_return", 0),
                "annualized_return": performance_metrics.get("annualized_return", 0),
                "max_drawdown": performance_metrics.get("max_drawdown", 0),
                "sharpe_ratio": performance_metrics.get("sharpe_ratio", 0),
                "sortino_ratio": performance_metrics.get("sortino_ratio", 0),
                "win_rate": performance_metrics.get("win_rate", 0),
                "profit_loss_ratio": performance_metrics.get("profit_loss_ratio", 0),
                "total_trades": performance_metrics.get("total_trades", 0),
                "profitable_trades": performance_metrics.get("profitable_trades", 0),
                "execution_time": result.get("execution_time", 0)
            }
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取策略绩效指标失败", error=str(e), strategy_id=strategy_id)
        raise APIError(f"获取策略绩效指标失败: {str(e)}")

@router.get("/{strategy_id}/trades")
async def get_strategy_trades(
    strategy_id: str,
    page: int = 1,
    size: int = 20,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略交易记录（分页）"""
    try:
        logger.info("获取策略交易记录", strategy_id=strategy_id, page=page, size=size)

        # 验证分页参数
        if page < 1:
            raise ValidationError("页码必须大于0")
        if size < 1 or size > 100:
            raise ValidationError("每页大小必须在1-100之间")

        # 从缓存获取结果
        result = await cache_service.get_strategy_result(strategy_id)
        if not result:
            raise ValidationError(f"策略结果不存在或已过期: {strategy_id}")

        # 获取交易记录
        trades = result.get("trades", [])
        total_count = len(trades)

        # 分页处理
        start_index = (page - 1) * size
        end_index = start_index + size
        paginated_trades = trades[start_index:end_index]

        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "trades": paginated_trades,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_count": total_count,
                    "total_pages": (total_count + size - 1) // size,
                    "has_next": end_index < total_count,
                    "has_prev": page > 1
                }
            }
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取策略交易记录失败", error=str(e), strategy_id=strategy_id)
        raise APIError(f"获取策略交易记录失败: {str(e)}")

@router.get("/{strategy_id}/summary")
async def get_strategy_summary(
    strategy_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取策略执行摘要"""
    try:
        logger.info("获取策略执行摘要", strategy_id=strategy_id)

        # 从缓存获取结果
        result = await cache_service.get_strategy_result(strategy_id)
        if not result:
            raise ValidationError(f"策略结果不存在或已过期: {strategy_id}")

        # 构建摘要信息
        performance_metrics = result.get("performance_metrics", {})
        trades = result.get("trades", [])

        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "basic_info": {
                    "symbol": result.get("symbol"),
                    "strategy_type": result.get("strategy_type"),
                    "start_date": result.get("start_date"),
                    "end_date": result.get("end_date"),
                    "execution_time": result.get("execution_time")
                },
                "performance_summary": {
                    "total_return": performance_metrics.get("total_return", 0),
                    "max_drawdown": performance_metrics.get("max_drawdown", 0),
                    "sharpe_ratio": performance_metrics.get("sharpe_ratio", 0),
                    "win_rate": performance_metrics.get("win_rate", 0)
                },
                "trading_summary": {
                    "total_trades": len(trades),
                    "profitable_trades": len([t for t in trades if t.get("pnl", 0) > 0]),
                    "average_trade": sum(t.get("pnl", 0) for t in trades) / len(trades) if trades else 0
                }
            }
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取策略执行摘要失败", error=str(e), strategy_id=strategy_id)
        raise APIError(f"获取策略执行摘要失败: {str(e)}")

@router.post("/configure", response_model=dict)
async def configure_strategy_parameters(
    request: dict,
    cache_service: CacheService = Depends(get_cache_service)
):
    """配置策略参数"""
    try:
        logger.info("配置策略参数", request=request)

        # 验证请求包含必要字段
        required_fields = ["strategy_type", "parameters"]
        for field in required_fields:
            if field not in request:
                raise ValidationError(f"缺少必需字段: {field}")

        strategy_type = request["strategy_type"]
        parameters = request["parameters"]

        # 验证策略类型
        if strategy_type != "single_ma":
            raise ValidationError(f"不支持的策略类型: {strategy_type}")

        # 验证参数
        if "ma_period" not in parameters:
            raise ValidationError("缺少移动平均线周期参数")
        if "initial_capital" not in parameters:
            raise ValidationError("缺少初始资金参数")
        if "stop_loss" not in parameters:
            raise ValidationError("缺少止损比例参数")

        # 参数范围验证
        ma_period = parameters["ma_period"]
        if not isinstance(ma_period, int) or ma_period < 5 or ma_period > 200:
            raise ValidationError("移动平均线周期必须是5-200之间的整数")

        initial_capital = parameters["initial_capital"]
        if not isinstance(initial_capital, (int, float)) or initial_capital < 10000 or initial_capital > 10000000:
            raise ValidationError("初始资金必须是10000-10000000之间的数字")

        stop_loss = parameters["stop_loss"]
        if not isinstance(stop_loss, (int, float)) or stop_loss < 0.01 or stop_loss > 0.2:
            raise ValidationError("止损比例必须是0.01-0.2之间的数字")

        # 生成配置ID
        config_id = str(uuid.uuid4())

        # 缓存配置
        config_data = {
            "config_id": config_id,
            "strategy_type": strategy_type,
            "parameters": parameters,
            "created_at": str(uuid.uuid4())[:8],  # 简单的时间戳
            "is_valid": True
        }

        await cache_service.set_strategy_config(config_id, config_data)

        logger.info(
            "策略参数配置成功",
            config_id=config_id,
            strategy_type=strategy_type,
            parameters=parameters
        )

        return {
            "success": True,
            "message": "策略参数配置成功",
            "config_id": config_id,
            "strategy_type": strategy_type,
            "parameters": parameters
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("配置策略参数失败", error=str(e), request=request)
        raise APIError(f"配置策略参数失败: {str(e)}")

@router.get("/parameters/single-ma", response_model=dict)
async def get_single_ma_parameters() -> Any:
    """获取单均线策略参数说明"""
    try:
        parameters = {
            "ma_period": {
                "name": "移动平均线周期",
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 200,
                "description": "计算移动平均线的天数",
                "examples": [5, 10, 20, 50, 120]
            },
            "initial_capital": {
                "name": "初始资金",
                "type": "number",
                "default": 100000,
                "min": 10000,
                "max": 10000000,
                "description": "策略开始时的资金数量",
                "examples": [50000, 100000, 500000]
            },
            "stop_loss": {
                "name": "止损比例",
                "type": "number",
                "default": 0.05,
                "min": 0.01,
                "max": 0.2,
                "description": "止损的比例，例如0.05表示5%",
                "examples": [0.03, 0.05, 0.1]
            }
        }

        return {
            "strategy_name": "单均线策略",
            "description": "基于单一移动平均线的趋势跟踪策略",
            "parameters": parameters,
            "usage": {
                "entry_signal": "价格上穿均线时买入",
                "exit_signal": "价格下穿均线时卖出",
                "risk_control": "固定百分比止损"
            }
        }

    except Exception as e:
        logger.error("获取策略参数失败", error=str(e))
        raise APIError(f"获取策略参数失败: {str(e)}")