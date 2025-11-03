"""
绩效报告生成器
提供综合绩效报告生成功能
"""

from typing import Dict, Any, List, Optional, Union, Any
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

from ..data_storage import DataStorageService
from ...models.performance import PerformanceMetrics, TradingStatistics
from ...models.market_data import MarketData

logger = structlog.get_logger()


@dataclass
class ReportConfig:
    """报告配置"""
    include_charts: bool = True
    include_detailed_trades: bool = True
    include_risk_analysis: bool = True
    language: str = "zh"  # 报告语言
    format: str = "json"  # 输出格式


class PerformanceReportGenerator:
    """绩效报告生成器"""

    def __init__(self, config: ReportConfig = None) -> Any:
        """
        初始化报告生成器

        Args:
            config: 报告配置
        """
        self.config = config or ReportConfig()
        self.data_service = DataStorageService()
        logger.info("绩效报告生成器初始化", config=self.config)

    def generate_comprehensive_report(
        self,
        strategy_id: str,
        metrics: PerformanceMetrics,
        trading_stats: Optional[TradingStatistics] = None,
        benchmark_id: Optional[str] = None,
        time_period: str = "1y"
    ) -> Dict[str, Any]:
        """
        生成综合绩效报告

        Args:
            strategy_id: 策略ID
            metrics: 绩效指标
            trading_stats: 交易统计
            benchmark_id: 基准ID
            time_period: 时间期间

        Returns:
            综合报告数据
        """
        logger.info("生成绩效报告", strategy_id=strategy_id, time_period=time_period)

        # 报告基本信息
        report_info = {
            "strategy_id": strategy_id,
            "report_type": "comprehensive",
            "time_period": time_period,
            "generation_date": datetime.now().isoformat(),
            "period_start": metrics.period_start.isoformat() if metrics.period_start else None,
            "period_end": metrics.period_end.isoformat() if metrics.period_end else None
        }

        # 执行摘要
        executive_summary = self._generate_executive_summary(metrics, trading_stats)

        # 绩效指标分析
        performance_analysis = self._analyze_performance_metrics(metrics)

        # 风险分析
        risk_analysis = self._analyze_risk_metrics(metrics)

        # 交易分析
        trading_analysis = self._analyze_trading_performance(trading_stats)

        # 基准比较
        benchmark_comparison = self._generate_benchmark_comparison(metrics, benchmark_id)

        # 图表数据
        charts_data = {}
        if self.config.include_charts:
            charts_data = self._generate_charts_data(strategy_id, time_period)

        # 改进建议
        recommendations = self._generate_recommendations(metrics, trading_stats)

        # 组装完整报告
        report = {
            "info": report_info,
            "executive_summary": executive_summary,
            "performance_analysis": performance_analysis,
            "risk_analysis": risk_analysis,
            "trading_analysis": trading_analysis,
            "benchmark_comparison": benchmark_comparison,
            "charts": charts_data,
            "recommendations": recommendations,
            "raw_metrics": self._serialize_metrics(metrics)
        }

        logger.info("绩效报告生成完成", strategy_id=strategy_id)

        return report

    def _generate_executive_summary(
        self,
        metrics: PerformanceMetrics,
        trading_stats: Optional[TradingStatistics]
    ) -> Dict[str, Any]:
        """生成执行摘要"""
        summary = {
            "overall_performance": self._assess_overall_performance(metrics),
            "key_metrics": {
                "total_return": f"{metrics.total_return:.2%}",
                "annualized_return": f"{metrics.annualized_return:.2%}" if metrics.annualized_return else "N/A",
                "max_drawdown": f"{metrics.max_drawdown:.2%}",
                "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio else "N/A",
                "win_rate": f"{metrics.win_rate:.2%}" if metrics.win_rate else "N/A"
            },
            "highlights": self._extract_key_highlights(metrics, trading_stats),
            "concerns": self._identify_concerns(metrics, trading_stats)
        }

        return summary

    def _analyze_performance_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """分析绩效指标"""
        analysis = {
            "return_analysis": {
                "total_return": {
                    "value": metrics.total_return,
                    "assessment": self._assess_return_performance(metrics.total_return),
                    "benchmark_comparison": "优于市场平均水平" if metrics.total_return > 0.1 else "需要改进"
                },
                "annualized_return": {
                    "value": metrics.annualized_return,
                    "assessment": self._assess_return_performance(metrics.annualized_return) if metrics.annualized_return else None
                }
            },
            "risk_adjusted_performance": {
                "sharpe_ratio": {
                    "value": metrics.sharpe_ratio,
                    "assessment": self._assess_sharpe_ratio(metrics.sharpe_ratio) if metrics.sharpe_ratio else None
                },
                "sortino_ratio": {
                    "value": metrics.sortino_ratio,
                    "assessment": self._assess_sortino_ratio(metrics.sortino_ratio) if metrics.sortino_ratio else None
                }
            },
            "volatility_analysis": {
                "volatility": metrics.volatility,
                "risk_level": self._assess_volatility(metrics.volatility) if metrics.volatility else None
            }
        }

        return analysis

    def _analyze_risk_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """分析风险指标"""
        risk_analysis = {
            "drawdown_analysis": {
                "max_drawdown": metrics.max_drawdown,
                "max_drawdown_period": metrics.max_drawdown_period,
                "risk_assessment": self._assess_drawdown_risk(metrics.max_drawdown),
                "recovery_analysis": "需要关注回撤恢复时间" if metrics.max_drawdown_period and metrics.max_drawdown_period > 50 else "回撤恢复及时"
            },
            "risk_adjusted_metrics": {
                "sharpe_ratio_interpretation": self._interpret_sharpe_ratio(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
                "sortino_ratio_interpretation": self._interpret_sortino_ratio(metrics.sortino_ratio) if metrics.sortino_ratio else None
            }
        }

        return risk_analysis

    def _analyze_trading_performance(
        self,
        trading_stats: Optional[TradingStatistics]
    ) -> Dict[str, Any]:
        """分析交易绩效"""
        if not trading_stats:
            return {"message": "交易统计数据不可用"}

        analysis = {
            "trading_frequency": {
                "total_trades": trading_stats.trade_count,
                "trading_frequency_monthly": trading_stats.trade_frequency,
                "assessment": self._assess_trading_frequency(trading_stats.trade_frequency)
            },
            "profitability_analysis": {
                "win_rate": trading_stats.win_rate,
                "profit_loss_ratio": trading_stats.profit_loss_ratio,
                "profitability_assessment": self._assess_profitability(trading_stats.win_rate, trading_stats.profit_loss_ratio)
            },
            "trade_size_analysis": {
                "average_win": trading_stats.average_win,
                "average_loss": trading_stats.average_loss,
                "largest_win": trading_stats.largest_win,
                "largest_loss": trading_stats.largest_loss,
                "consistency_assessment": self._assess_trade_consistency(trading_stats)
            }
        }

        return analysis

    def _generate_benchmark_comparison(
        self,
        metrics: PerformanceMetrics,
        benchmark_id: Optional[str]
    ) -> Dict[str, Any]:
        """生成基准比较"""
        if not benchmark_id:
            return {"message": "未提供基准进行比较"}

        # 这里可以添加实际的基准数据获取逻辑
        # 目前返回模拟的比较数据
        comparison = {
            "benchmark_id": benchmark_id,
            "relative_performance": {
                "excess_return": f"{metrics.total_return:.2%}" if metrics.total_return > 0 else "需要改进",
                "alpha": "策略表现优于基准" if metrics.total_return > 0 else "策略表现不如基准",
                "beta": "风险特征相似"  # 需要实际计算
            },
            "comparison_summary": "策略在该期间表现良好，建议继续监控和优化"
        }

        return comparison

    def _generate_charts_data(self, strategy_id: str, time_period: str) -> Dict[str, Any]:
        """生成图表数据"""
        # 这里可以添加实际的图表数据生成逻辑
        # 目前返回模拟数据
        charts_data = {
            "cumulative_returns": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [
                    {
                        "label": "策略累计收益",
                        "data": [0.05, 0.08, 0.06, 0.12, 0.15, 0.18]
                    }
                ]
            },
            "drawdown_chart": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [
                    {
                        "label": "回撤",
                        "data": [-0.02, -0.05, -0.03, -0.08, -0.04, -0.02]
                    }
                ]
            }
        }

        return charts_data

    def _generate_recommendations(
        self,
        metrics: PerformanceMetrics,
        trading_stats: Optional[TradingStatistics]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于收益率的建议
        if metrics.total_return < 0:
            recommendations.append("策略收益为负，建议重新评估策略参数和入场时机")
        elif metrics.total_return < 0.05:
            recommendations.append("策略收益偏低，建议优化风险管理并提高仓位管理效率")

        # 基于回撤的建议
        if metrics.max_drawdown < -0.2:
            recommendations.append("最大回撤较大，建议加强止损策略和风险控制")
        elif metrics.max_drawdown < -0.15:
            recommendations.append("回撤控制有待改进，建议优化仓位管理和止损设置")

        # 基于夏普比率的建议
        if metrics.sharpe_ratio and metrics.sharpe_ratio < 1:
            recommendations.append("夏普比率较低，建议优化风险调整收益，考虑降低波动率或提高收益率")

        # 基于胜率的建议
        if trading_stats and trading_stats.win_rate and trading_stats.win_rate < 0.4:
            recommendations.append("胜率偏低，建议改进入场信号质量和趋势识别能力")

        # 基于交易频率的建议
        if trading_stats and trading_stats.trade_frequency and trading_stats.trade_frequency > 10:
            recommendations.append("交易频率过高，可能导致过度交易和成本增加，建议优化交易信号")

        # 通用建议
        recommendations.append("建议定期回顾和优化策略参数，适应市场环境变化")
        recommendations.append("建议结合多个指标综合评估策略表现，避免单一指标依赖")

        return recommendations

    def _assess_overall_performance(self, metrics: PerformanceMetrics) -> str:
        """评估整体绩效"""
        if not metrics.sharpe_ratio:
            return "数据不足，无法评估"

        if metrics.total_return > 0.15 and metrics.sharpe_ratio > 1.5:
            return "优秀"
        elif metrics.total_return > 0.05 and metrics.sharpe_ratio > 1.0:
            return "良好"
        elif metrics.total_return > 0 and metrics.sharpe_ratio > 0.5:
            return "一般"
        else:
            return "需要改进"

    def _assess_return_performance(self, return_value: float) -> str:
        """评估收益表现"""
        if return_value > 0.20:
            return "优秀"
        elif return_value > 0.10:
            return "良好"
        elif return_value > 0:
            return "一般"
        else:
            return "亏损"

    def _assess_sharpe_ratio(self, sharpe_ratio: float) -> str:
        """评估夏普比率"""
        if sharpe_ratio > 2.0:
            return "优秀"
        elif sharpe_ratio > 1.0:
            return "良好"
        elif sharpe_ratio > 0.5:
            return "一般"
        else:
            return "需要改进"

    def _assess_sortino_ratio(self, sortino_ratio: float) -> str:
        """评估Sortino比率"""
        if sortino_ratio > 2.5:
            return "优秀"
        elif sortino_ratio > 1.5:
            return "良好"
        elif sortino_ratio > 1.0:
            return "一般"
        else:
            return "需要改进"

    def _assess_volatility(self, volatility: float) -> str:
        """评估波动率"""
        if volatility > 0.25:
            return "高风险"
        elif volatility > 0.15:
            return "中等风险"
        elif volatility > 0.10:
            return "低风险"
        else:
            return "极低风险"

    def _assess_drawdown_risk(self, max_drawdown: float) -> str:
        """评估回撤风险"""
        if max_drawdown < -0.25:
            return "高风险"
        elif max_drawdown < -0.15:
            return "中等风险"
        elif max_drawdown < -0.10:
            return "低风险"
        else:
            return "风险可控"

    def _interpret_sharpe_ratio(self, sharpe_ratio: float) -> str:
        """解释夏普比率"""
        if sharpe_ratio > 2:
            return "每单位风险获得超额收益，风险调整收益优秀"
        elif sharpe_ratio > 1:
            return "风险调整收益良好，表现优于无风险投资"
        elif sharpe_ratio > 0:
            return "风险调整收益一般，建议优化"
        else:
            return "风险调整收益为负，建议重新评估策略"

    def _interpret_sortino_ratio(self, sortino_ratio: float) -> str:
        """解释Sortino比率"""
        if sortino_ratio > 2:
            return "下行风险控制优秀，风险调整收益突出"
        elif sortino_ratio > 1:
            return "下行风险控制良好，收益质量较高"
        elif sortino_ratio > 0:
            return "下行风险控制一般，有改进空间"
        else:
            return "下行风险控制不足，需要加强"

    def _assess_trading_frequency(self, frequency: float) -> str:
        """评估交易频率"""
        if frequency > 20:
            return "过度交易"
        elif frequency > 10:
            return "交易频繁"
        elif frequency > 2:
            return "交易频率适中"
        elif frequency > 0:
            return "交易较少"
        else:
            return "无交易"

    def _assess_profitability(self, win_rate: float, profit_loss_ratio: float) -> str:
        """评估盈利能力"""
        if win_rate > 0.6 and profit_loss_ratio > 2:
            return "优秀"
        elif win_rate > 0.5 and profit_loss_ratio > 1.5:
            return "良好"
        elif win_rate > 0.4 and profit_loss_ratio > 1:
            return "一般"
        else:
            return "需要改进"

    def _assess_trade_consistency(self, trading_stats: TradingStatistics) -> str:
        """评估交易一致性"""
        if not trading_stats.average_win or not trading_stats.average_loss:
            return "数据不足"

        consistency_factor = abs(trading_stats.average_win / abs(trading_stats.average_loss))
        if consistency_factor < 3:
            return "盈亏比较均衡"
        elif consistency_factor < 5:
            return "盈亏比较合理"
        else:
            return "盈亏比较失衡"

    def _extract_key_highlights(
        self,
        metrics: PerformanceMetrics,
        trading_stats: Optional[TradingStatistics]
    ) -> List[str]:
        """提取关键亮点"""
        highlights = []

        if metrics.total_return > 0.15:
            highlights.append(f"总收益率达到{metrics.total_return:.2%}，表现优异")

        if metrics.sharpe_ratio and metrics.sharpe_ratio > 1.5:
            highlights.append(f"夏普比率为{metrics.sharpe_ratio:.2f}，风险调整收益良好")

        if trading_stats and trading_stats.win_rate and trading_stats.win_rate > 0.6:
            highlights.append(f"胜率达到{trading_stats.win_rate:.2%}，交易质量较高")

        if metrics.max_drawdown > -0.05:
            highlights.append("最大回撤控制在5%以内，风险管理良好")

        return highlights

    def _identify_concerns(
        self,
        metrics: PerformanceMetrics,
        trading_stats: Optional[TradingStatistics]
    ) -> List[str]:
        """识别关注点"""
        concerns = []

        if metrics.total_return < 0:
            concerns.append("策略整体亏损，需要重新评估")

        if metrics.max_drawdown < -0.2:
            concerns.append(f"最大回撤达到{abs(metrics.max_drawdown):.2%}，风险控制有待加强")

        if metrics.sharpe_ratio and metrics.sharpe_ratio < 0.5:
            concerns.append("风险调整收益偏低，需要优化")

        if trading_stats and trading_stats.win_rate and trading_stats.win_rate < 0.4:
            concerns.append("胜率偏低，需要改进交易信号质量")

        return concerns

    def _serialize_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """序列化指标数据"""
        return {
            "strategy_id": metrics.strategy_id,
            "total_return": metrics.total_return,
            "annualized_return": metrics.annualized_return,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_period": metrics.max_drawdown_period,
            "volatility": metrics.volatility,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "win_rate": metrics.win_rate,
            "profit_loss_ratio": metrics.profit_loss_ratio,
            "total_trades": metrics.total_trades,
            "profitable_trades": metrics.profitable_trades,
            "calculation_date": metrics.calculation_date.isoformat()
        }


def create_report_generator(config: ReportConfig = None) -> PerformanceReportGenerator:
    """
    创建报告生成器的工厂函数

    Args:
        config: 报告配置

    Returns:
        报告生成器实例
    """
    return PerformanceReportGenerator(config)