from fastapi import APIRouter, HTTPException, Depends
from typing import List
import structlog
import uuid

from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestReport,
    PerformanceMetrics
)
from app.services.backtest_engine import BacktestEngine
from app.services.cache_service import CacheService
from app.utils.errors import ValidationError, APIError

logger = structlog.get_logger()
router = APIRouter()

def get_backtest_engine() -> BacktestEngine:
    return BacktestEngine()

def get_cache_service() -> CacheService:
    return CacheService()

@router.post("/", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    backtest_engine: BacktestEngine = Depends(get_backtest_engine),
    cache_service: CacheService = Depends(get_cache_service)
):
    """执行策略回测"""
    try:
        # 生成回测ID
        backtest_id = str(uuid.uuid4())

        logger.info(
            "开始执行回测",
            backtest_id=backtest_id,
            symbol=request.symbol,
            strategy_type=request.strategy_type
        )

        # 验证回测参数
        if request.start_date >= request.end_date:
            raise ValidationError("开始日期必须早于结束日期")

        # 执行回测
        result = await backtest_engine.run_backtest(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_type=request.strategy_type,
            parameters=request.parameters
        )

        # 缓存回测结果
        await cache_service.set_backtest_result(backtest_id, result)

        logger.info(
            "回测执行完成",
            backtest_id=backtest_id,
            total_return=result.performance_metrics.total_return,
            max_drawdown=result.performance_metrics.max_drawdown,
            sharpe_ratio=result.performance_metrics.sharpe_ratio
        )

        return {
            "backtest_id": backtest_id,
            "symbol": request.symbol,
            "strategy_type": request.strategy_type,
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date
            },
            "parameters": request.parameters,
            "performance_metrics": result.performance_metrics,
            "trades": result.trades,
            "equity_curve": result.equity_curve,
            "execution_time": result.execution_time
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("回测执行失败", error=str(e), request=request.dict())
        raise APIError(f"回测执行失败: {str(e)}")

@router.get("/{backtest_id}/report", response_model=BacktestReport)
async def get_backtest_report(
    backtest_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """获取回测报告"""
    try:
        logger.info("获取回测报告", backtest_id=backtest_id)

        result = await cache_service.get_backtest_result(backtest_id)
        if not result:
            raise ValidationError(f"回测结果不存在或已过期: {backtest_id}")

        # 生成详细报告
        report = await generate_backtest_report(result)

        return report

    except ValidationError:
        raise
    except Exception as e:
        logger.error("获取回测报告失败", error=str(e), backtest_id=backtest_id)
        raise APIError(f"获取回测报告失败: {str(e)}")

@router.get("/comparison", response_model=List[dict])
async def compare_backtests(
    backtest_ids: List[str] = None,
    cache_service: CacheService = Depends(get_cache_service)
):
    """比较多个回测结果"""
    try:
        if not backtest_ids or len(backtest_ids) < 2:
            raise ValidationError("至少需要两个回测ID进行比较")

        logger.info("比较回测结果", backtest_ids=backtest_ids)

        results = []
        for backtest_id in backtest_ids:
            result = await cache_service.get_backtest_result(backtest_id)
            if result:
                results.append(result)
            else:
                logger.warning("回测结果不存在", backtest_id=backtest_id)

        if len(results) < 2:
            raise ValidationError("有效的回测结果不足，无法进行比较")

        # 生成比较报告
        comparison = await generate_comparison_report(results)

        return comparison

    except ValidationError:
        raise
    except Exception as e:
        logger.error("回测比较失败", error=str(e), backtest_ids=backtest_ids)
        raise APIError(f"回测比较失败: {str(e)}")

async def generate_backtest_report(result) -> BacktestReport:
    """生成详细回测报告"""
    try:
        metrics = result.performance_metrics

        # 计算收益等级
        if metrics.total_return > 0.2:
            return_grade = "优秀"
        elif metrics.total_return > 0.1:
            return_grade = "良好"
        elif metrics.total_return > 0:
            return_grade = "一般"
        else:
            return_grade = "较差"

        # 计算风险等级
        if metrics.max_drawdown < 0.05:
            risk_grade = "低风险"
        elif metrics.max_drawdown < 0.1:
            risk_grade = "中等风险"
        else:
            risk_grade = "高风险"

        # 夏普比率评级
        if metrics.sharpe_ratio > 2:
            sharpe_grade = "优秀"
        elif metrics.sharpe_ratio > 1:
            sharpe_grade = "良好"
        elif metrics.sharpe_ratio > 0.5:
            sharpe_grade = "一般"
        else:
            sharpe_grade = "较差"

        return BacktestReport(
            backtest_id=result.backtest_id,
            summary={
                "总收益率": metrics.total_return,
                "收益率评级": return_grade,
                "最大回撤": metrics.max_drawdown,
                "风险等级": risk_grade,
                "夏普比率": metrics.sharpe_ratio,
                "夏普比率评级": sharpe_grade,
                "胜率": metrics.win_rate,
                "总交易次数": metrics.total_trades,
                "盈亏比": metrics.profit_loss_ratio
            },
            performance_metrics=metrics,
            risk_analysis={
                "value_at_risk_95": metrics.value_at_risk_95,
                "conditional_var_95": metrics.conditional_var_95,
                "volatility": metrics.volatility,
                "beta": metrics.beta,
                "alpha": metrics.alpha
            },
            trade_analysis={
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "average_trade_return": metrics.average_trade_return,
                "best_trade": metrics.best_trade,
                "worst_trade": metrics.worst_trade,
                "average_holding_period": metrics.average_holding_period
            },
            recommendations=generate_recommendations(metrics)
        )

    except Exception as e:
        logger.error("生成回测报告失败", error=str(e))
        raise APIError(f"生成回测报告失败: {str(e)}")

async def generate_comparison_report(results: List[dict]) -> List[dict]:
    """生成比较报告"""
    try:
        comparison = []

        for result in results:
            metrics = result.performance_metrics
            comparison.append({
                "backtest_id": result.backtest_id,
                "symbol": result.symbol,
                "strategy_type": result.strategy_type,
                "总收益率": metrics.total_return,
                "最大回撤": metrics.max_drawdown,
                "夏普比率": metrics.sharpe_ratio,
                "胜率": metrics.win_rate,
                "总交易次数": metrics.total_trades,
                "盈亏比": metrics.profit_loss_ratio,
                "综合评分": calculate_overall_score(metrics)
            })

        # 按综合评分排序
        comparison.sort(key=lambda x: x["综合评分"], reverse=True)

        return comparison

    except Exception as e:
        logger.error("生成比较报告失败", error=str(e))
        raise APIError(f"生成比较报告失败: {str(e)}")

def calculate_overall_score(metrics: PerformanceMetrics) -> float:
    """计算综合评分"""
    try:
        # 收益率评分 (40%)
        return_score = min(metrics.total_return * 100, 40)

        # 夏普比率评分 (30%)
        sharpe_score = min(metrics.sharpe_ratio * 10, 30)

        # 胜率评分 (20%)
        win_rate_score = metrics.win_rate * 20

        # 回撤控制评分 (10%)
        drawdown_score = max(10 - metrics.max_drawdown * 100, 0)

        total_score = return_score + sharpe_score + win_rate_score + drawdown_score
        return round(total_score, 2)

    except Exception:
        return 0.0

def generate_recommendations(metrics: PerformanceMetrics) -> List[str]:
    """生成策略优化建议"""
    recommendations = []

    try:
        if metrics.total_return < 0:
            recommendations.append("策略整体亏损，建议优化入场和出场条件")

        if metrics.max_drawdown > 0.15:
            recommendations.append("最大回撤较大，建议加强风险控制")

        if metrics.sharpe_ratio < 1:
            recommendations.append("夏普比率偏低，建议提高风险调整后收益")

        if metrics.win_rate < 0.4:
            recommendations.append("胜率较低，建议优化信号生成逻辑")

        if metrics.profit_loss_ratio < 1:
            recommendations.append("盈亏比不平衡，建议优化止损止盈策略")

        if not recommendations:
            recommendations.append("策略表现良好，建议保持当前参数设置")

        return recommendations

    except Exception:
        return ["无法生成策略建议"]