"""
多品种对比分析API端点
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import asyncio
import uuid

from app.core.database import get_db
from app.services.comparison_service import ComparisonService
from app.services.market_data_service import MarketDataService
from app.services.strategy_service import StrategyService

router = APIRouter()

# 请求模型
class VarietyComparisonRequest(BaseModel):
    symbols: List[str] = Field(..., description="要对比的期货品种列表")
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    strategy: Dict[str, Any] = Field(..., description="策略配置")

class ComparisonTaskRequest(BaseModel):
    request: VarietyComparisonRequest
    task_id: Optional[str] = None

# 响应模型
class VarietyResult(BaseModel):
    symbol: str
    name: str
    sector: str
    exchange: str
    metrics: Dict[str, float]
    trades: List[Dict[str, Any]]
    equity: List[Dict[str, Any]]
    signals: List[Dict[str, Any]]
    error: Optional[str] = None

class ComparisonSummary(BaseModel):
    totalVarieties: int
    successfulVarieties: int
    failedVarieties: int
    bestPerformer: str
    worstPerformer: str
    averageReturn: float
    averageSharpeRatio: float
    totalTrades: int
    dateRange: Dict[str, Any]

class VarietyRanking(BaseModel):
    rank: int
    symbol: str
    name: str
    sector: str
    score: float
    metrics: Dict[str, int]
    highlights: List[str]

class VarietyComparisonResult(BaseModel):
    requestId: str
    timestamp: str
    request: VarietyComparisonRequest
    results: List[VarietyResult]
    summary: ComparisonSummary
    rankings: List[VarietyRanking]

# 全局任务存储（生产环境应使用Redis等）
comparison_tasks: Dict[str, Dict[str, Any]] = {}

# 服务实例
comparison_service = ComparisonService()
market_data_service = MarketDataService()
strategy_service = StrategyService()

@router.post("/run", response_model=Dict[str, str])
async def run_comparison(
    request: VarietyComparisonRequest,
    background_tasks: BackgroundTasks
):
    """
    启动多品种对比分析任务
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 验证请求
    if len(request.symbols) < 2:
        raise HTTPException(status_code=400, detail="至少需要选择2个品种进行对比")

    if len(request.symbols) > 10:
        raise HTTPException(status_code=400, detail="最多支持10个品种同时对比")

    # 验证日期格式
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")
        if end_date > datetime.now():
            raise HTTPException(status_code=400, detail="结束日期不能超过当前日期")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，请使用YYYY-MM-DD格式")

    # 初始化任务状态
    comparison_tasks[task_id] = {
        "status": "pending",
        "request": request.dict(),
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }

    # 启动后台任务
    background_tasks.add_task(
        process_comparison_task,
        task_id,
        request
    )

    return {
        "task_id": task_id,
        "status": "started",
        "message": "对比分析任务已启动"
    }

@router.get("/results/{task_id}", response_model=Dict[str, Any])
async def get_comparison_results(task_id: str):
    """
    获取对比分析结果
    """
    if task_id not in comparison_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = comparison_tasks[task_id]

    response = {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "created_at": task["created_at"]
    }

    if task["status"] == "completed":
        response["result"] = task["result"]
    elif task["status"] == "failed":
        response["error"] = task["error"]

    return response

@router.delete("/cancel/{task_id}")
async def cancel_comparison(task_id: str):
    """
    取消对比分析任务
    """
    if task_id not in comparison_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = comparison_tasks[task_id]

    if task["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="任务已完成，无法取消")

    # 更新任务状态
    task["status"] = "cancelled"

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "任务已取消"
    }

@router.get("/metrics")
async def get_available_metrics():
    """
    获取可用的对比指标列表
    """
    return {
        "metrics": [
            {
                "name": "total_return",
                "label": "总收益率",
                "description": "策略的总收益率",
                "unit": "%",
                "higher_is_better": True
            },
            {
                "name": "sharpe_ratio",
                "label": "夏普比率",
                "description": "风险调整后的收益指标",
                "unit": "",
                "higher_is_better": True
            },
            {
                "name": "max_drawdown",
                "label": "最大回撤",
                "description": "策略历史最大回撤",
                "unit": "%",
                "higher_is_better": False
            },
            {
                "name": "volatility",
                "label": "波动率",
                "description": "收益波动率",
                "unit": "%",
                "higher_is_better": False
            },
            {
                "name": "win_rate",
                "label": "胜率",
                "description": "盈利交易占比",
                "unit": "%",
                "higher_is_better": True
            },
            {
                "name": "profit_factor",
                "label": "盈亏比",
                "description": "总盈利/总亏损",
                "unit": "",
                "higher_is_better": True
            },
            {
                "name": "total_trades",
                "label": "交易次数",
                "description": "总交易次数",
                "unit": "次",
                "higher_is_better": False
            }
        ]
    }

@router.post("/historical")
async def get_historical_comparison(
    symbols: List[str],
    days: int = 30
):
    """
    获取历史对比数据
    """
    if len(symbols) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个品种")

    if days < 7 or days > 365:
        raise HTTPException(status_code=400, detail="天数范围应在7-365天之间")

    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 获取历史数据
        results = []
        for symbol in symbols:
            try:
                # 获取历史价格数据
                price_data = await market_data_service.get_historical_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )

                # 计算简单的收益指标
                if price_data and len(price_data) > 1:
                    first_price = price_data[0]["close"]
                    last_price = price_data[-1]["close"]
                    total_return = (last_price - first_price) / first_price

                    # 简单的波动率计算
                    daily_returns = []
                    for i in range(1, len(price_data)):
                        daily_return = (price_data[i]["close"] - price_data[i-1]["close"]) / price_data[i-1]["close"]
                        daily_returns.append(daily_return)

                    volatility = (sum([r**2 for r in daily_returns]) / len(daily_returns)) ** 0.5 if daily_returns else 0

                    results.append({
                        "symbol": symbol,
                        "total_return": total_return,
                        "volatility": volatility,
                        "data_points": len(price_data)
                    })

            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })

        return {
            "symbols": symbols,
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": days
            },
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")

# 后台任务处理函数
async def process_comparison_task(task_id: str, request: VarietyComparisonRequest):
    """
    处理对比分析任务
    """
    try:
        # 更新任务状态
        comparison_tasks[task_id]["status"] = "running"

        # 获取品种信息
        symbols_info = {}
        for symbol in request.symbols:
            try:
                symbol_info = await market_data_service.get_symbol_info(symbol)
                symbols_info[symbol] = symbol_info
            except Exception as e:
                symbols_info[symbol] = {
                    "symbol": symbol,
                    "name": symbol,
                    "sector": "未知",
                    "exchange": "未知",
                    "error": str(e)
                }

        # 处理每个品种
        results = []
        total_symbols = len(request.symbols)

        for i, symbol in enumerate(request.symbols):
            try:
                # 更新进度
                comparison_tasks[task_id]["progress"] = int((i / total_symbols) * 100)

                # 获取历史数据
                price_data = await market_data_service.get_historical_data(
                    symbol,
                    request.start_date,
                    request.end_date
                )

                if not price_data:
                    results.append({
                        "symbol": symbol,
                        "name": symbols_info[symbol].get("name", symbol),
                        "sector": symbols_info[symbol].get("sector", "未知"),
                        "exchange": symbols_info[symbol].get("exchange", "未知"),
                        "metrics": {},
                        "trades": [],
                        "equity": [],
                        "signals": [],
                        "error": "无法获取历史数据"
                    })
                    continue

                # 运行策略
                strategy_result = await strategy_service.run_strategy(
                    symbol,
                    price_data,
                    request.strategy
                )

                # 计算绩效指标
                metrics = await comparison_service.calculate_metrics(strategy_result)

                results.append({
                    "symbol": symbol,
                    "name": symbols_info[symbol].get("name", symbol),
                    "sector": symbols_info[symbol].get("sector", "未知"),
                    "exchange": symbols_info[symbol].get("exchange", "未知"),
                    "metrics": metrics,
                    "trades": strategy_result.get("trades", []),
                    "equity": strategy_result.get("equity", []),
                    "signals": strategy_result.get("signals", [])
                })

            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "name": symbols_info[symbol].get("name", symbol),
                    "sector": symbols_info[symbol].get("sector", "未知"),
                    "exchange": symbols_info[symbol].get("exchange", "未知"),
                    "metrics": {},
                    "trades": [],
                    "equity": [],
                    "signals": [],
                    "error": str(e)
                })

        # 生成总结和排名
        summary = await comparison_service.generate_summary(results, request)
        rankings = await comparison_service.generate_rankings(results)

        # 构建最终结果
        final_result = {
            "requestId": task_id,
            "timestamp": datetime.now().isoformat(),
            "request": request.dict(),
            "results": results,
            "summary": summary,
            "rankings": rankings
        }

        # 更新任务状态
        comparison_tasks[task_id]["status"] = "completed"
        comparison_tasks[task_id]["progress"] = 100
        comparison_tasks[task_id]["result"] = final_result

    except Exception as e:
        # 更新任务状态为失败
        comparison_tasks[task_id]["status"] = "failed"
        comparison_tasks[task_id]["error"] = str(e)

# 清理过期任务
async def cleanup_expired_tasks():
    """
    清理过期任务（24小时前）
    """
    cutoff_time = datetime.now() - timedelta(hours=24)
    expired_tasks = [
        task_id for task_id, task in comparison_tasks.items()
        if datetime.fromisoformat(task["created_at"]) < cutoff_time
    ]

    for task_id in expired_tasks:
        del comparison_tasks[task_id]