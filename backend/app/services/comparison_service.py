"""
多品种对比分析服务
"""
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime

class ComparisonService:
    """对比分析服务类"""

    def __init__(self):
        """初始化对比分析服务"""
        pass

    async def calculate_metrics(self, strategy_result: Dict[str, Any]) -> Dict[str, float]:
        """
        计算策略绩效指标

        Args:
            strategy_result: 策略运行结果

        Returns:
            绩效指标字典
        """
        try:
            trades = strategy_result.get("trades", [])
            equity = strategy_result.get("equity", [])

            if not trades or not equity:
                return {}

            # 转换为DataFrame便于计算
            equity_df = pd.DataFrame(equity)
            trades_df = pd.DataFrame(trades)

            # 基础指标计算
            initial_equity = equity_df.iloc[0]["equity"]
            final_equity = equity_df.iloc[-1]["equity"]
            total_return = (final_equity - initial_equity) / initial_equity

            # 年化收益率
            start_date = pd.to_datetime(equity_df.iloc[0]["date"])
            end_date = pd.to_datetime(equity_df.iloc[-1]["date"])
            days = (end_date - start_date).days
            annualized_return = (final_equity / initial_equity) ** (365 / days) - 1 if days > 0 else 0

            # CAGR（复合年增长率）
            cagr = (final_equity / initial_equity) ** (1 / (days / 365)) - 1 if days > 0 else 0

            # 计算每日收益率
            equity_df["daily_return"] = equity_df["equity"].pct_change()
            daily_returns = equity_df["daily_return"].dropna()

            # 波动率
            volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0

            # 下行标准差
            negative_returns = daily_returns[daily_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 1 else 0

            # 最大回撤
            equity_df["cummax"] = equity_df["equity"].cummax()
            equity_df["drawdown"] = (equity_df["equity"] - equity_df["cummax"]) / equity_df["cummax"]
            max_drawdown = equity_df["drawdown"].min()

            # 夏普比率（假设无风险利率为3%）
            risk_free_rate = 0.03
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0

            # 索提诺比率
            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0

            # 卡玛比率
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

            # 交易统计
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df["pnl"] > 0])
            losing_trades = len(trades_df[trades_df["pnl"] <= 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            # 盈亏统计
            winning_pnl = trades_df[trades_df["pnl"] > 0]["pnl"].sum() if winning_trades > 0 else 0
            losing_pnl = abs(trades_df[trades_df["pnl"] <= 0]["pnl"].sum()) if losing_trades > 0 else 0
            profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')

            average_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
            average_loss = trades_df[trades_df["pnl"] <= 0]["pnl"].mean() if losing_trades > 0 else 0
            average_trade = trades_df["pnl"].mean() if total_trades > 0 else 0

            # VaR计算（95%）
            var95 = np.percentile(daily_returns, 5) if len(daily_returns) > 0 else 0

            # 偏度和峰度
            skewness = daily_returns.skew() if len(daily_returns) > 2 else 0
            kurtosis = daily_returns.kurtosis() if len(daily_returns) > 3 else 0

            # Alpha和Beta（这里简化处理，实际需要基准数据）
            alpha = 0.0  # 需要基准数据计算
            beta = 1.0   # 需要基准数据计算

            return {
                "totalReturn": total_return,
                "annualizedReturn": annualized_return,
                "cagr": cagr,
                "maxDrawdown": abs(max_drawdown),
                "volatility": volatility,
                "downsideDeviation": downside_deviation,
                "sharpeRatio": sharpe_ratio,
                "sortinoRatio": sortino_ratio,
                "calmarRatio": calmar_ratio,
                "totalTrades": total_trades,
                "winningTrades": winning_trades,
                "losingTrades": losing_trades,
                "winRate": win_rate,
                "averageWin": average_win,
                "averageLoss": average_loss,
                "profitFactor": profit_factor,
                "averageTrade": average_trade,
                "var95": var95,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "beta": beta,
                "alpha": alpha
            }

        except Exception as e:
            print(f"计算绩效指标失败: {str(e)}")
            return {}

    async def generate_summary(self, results: List[Dict[str, Any]], request: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成对比分析总结

        Args:
            results: 各品种分析结果
            request: 请求参数

        Returns:
            总结信息
        """
        try:
            successful_results = [r for r in results if not r.get("error")]
            failed_results = [r for r in results if r.get("error")]

            if not successful_results:
                return {
                    "totalVarieties": len(results),
                    "successfulVarieties": 0,
                    "failedVarieties": len(results),
                    "bestPerformer": "",
                    "worstPerformer": "",
                    "averageReturn": 0,
                    "averageSharpeRatio": 0,
                    "totalTrades": 0,
                    "dateRange": {
                        "start": request.get("start_date"),
                        "end": request.get("end_date"),
                        "tradingDays": 0
                    }
                }

            # 找出最佳和最差表现品种
            returns = [(r["symbol"], r["metrics"].get("totalReturn", 0)) for r in successful_results]
            best_performer = max(returns, key=lambda x: x[1])[0]
            worst_performer = min(returns, key=lambda x: x[1])[0]

            # 计算平均值
            avg_return = np.mean([r["metrics"].get("totalReturn", 0) for r in successful_results])
            avg_sharpe = np.mean([r["metrics"].get("sharpeRatio", 0) for r in successful_results])
            total_trades = sum([r["metrics"].get("totalTrades", 0) for r in successful_results])

            # 计算交易天数
            if successful_results and successful_results[0].get("equity"):
                equity_data = successful_results[0]["equity"]
                trading_days = len(equity_data)
            else:
                trading_days = 0

            return {
                "totalVarieties": len(results),
                "successfulVarieties": len(successful_results),
                "failedVarieties": len(failed_results),
                "bestPerformer": best_performer,
                "worstPerformer": worst_performer,
                "averageReturn": avg_return,
                "averageSharpeRatio": avg_sharpe,
                "totalTrades": total_trades,
                "dateRange": {
                    "start": request.get("start_date"),
                    "end": request.get("end_date"),
                    "tradingDays": trading_days
                }
            }

        except Exception as e:
            print(f"生成总结失败: {str(e)}")
            return {}

    async def generate_rankings(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成品种排名

        Args:
            results: 各品种分析结果

        Returns:
            排名列表
        """
        try:
            successful_results = [r for r in results if not r.get("error") and r.get("metrics")]

            if not successful_results:
                return []

            # 准备排名数据
            ranking_data = []
            for result in successful_results:
                metrics = result["metrics"]

                # 计算各维度排名分数
                return_score = self._normalize_score(metrics.get("totalReturn", 0), higher_better=True)
                sharpe_score = self._normalize_score(metrics.get("sharpeRatio", 0), higher_better=True)
                risk_score = self._normalize_score(abs(metrics.get("maxDrawdown", 0)), higher_better=False)
                consistency_score = self._normalize_score(1 / (1 + metrics.get("volatility", 1)), higher_better=True)

                # 综合评分（加权平均）
                overall_score = (
                    return_score * 0.3 +
                    sharpe_score * 0.3 +
                    risk_score * 0.2 +
                    consistency_score * 0.2
                )

                # 生成高亮信息
                highlights = []
                if metrics.get("totalReturn", 0) > 0.2:
                    highlights.append("高收益率")
                if metrics.get("sharpeRatio", 0) > 1.5:
                    highlights.append("优秀风险调整收益")
                if abs(metrics.get("maxDrawdown", 0)) < 0.1:
                    highlights.append("低回撤")
                if metrics.get("winRate", 0) > 0.6:
                    highlights.append("高胜率")

                ranking_data.append({
                    "symbol": result["symbol"],
                    "name": result["name"],
                    "sector": result["sector"],
                    "score": overall_score,
                    "metrics": {
                        "returnRank": 0,  # 稍后计算
                        "riskRank": 0,
                        "riskAdjustedReturnRank": 0,
                        "consistencyRank": 0
                    },
                    "highlights": highlights,
                    "raw_metrics": metrics
                })

            # 计算各维度排名
            # 收益排名
            ranking_data.sort(key=lambda x: x["raw_metrics"].get("totalReturn", 0), reverse=True)
            for i, item in enumerate(ranking_data):
                item["metrics"]["returnRank"] = i + 1

            # 风险排名（回撤越小越好）
            ranking_data.sort(key=lambda x: abs(x["raw_metrics"].get("maxDrawdown", 1)))
            for i, item in enumerate(ranking_data):
                item["metrics"]["riskRank"] = i + 1

            # 风险调整收益排名（夏普比率）
            ranking_data.sort(key=lambda x: x["raw_metrics"].get("sharpeRatio", 0), reverse=True)
            for i, item in enumerate(ranking_data):
                item["metrics"]["riskAdjustedReturnRank"] = i + 1

            # 稳定性排名（波动率越小越好）
            ranking_data.sort(key=lambda x: x["raw_metrics"].get("volatility", 1))
            for i, item in enumerate(ranking_data):
                item["metrics"]["consistencyRank"] = i + 1

            # 最终综合排名
            ranking_data.sort(key=lambda x: x["score"], reverse=True)
            for i, item in enumerate(ranking_data):
                item["rank"] = i + 1

            return ranking_data

        except Exception as e:
            print(f"生成排名失败: {str(e)}")
            return []

    def _normalize_score(self, value: float, higher_better: bool = True) -> float:
        """
        标准化分数到0-1范围

        Args:
            value: 原始值
            higher_better: 是否越高越好

        Returns:
            标准化后的分数
        """
        if value <= 0:
            return 0 if higher_better else 1

        # 使用sigmoid函数进行标准化
        if higher_better:
            return 1 / (1 + np.exp(-value * 10))
        else:
            return 1 / (1 + np.exp(value * 10))

    async def calculate_correlation_matrix(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算品种间相关性矩阵

        Args:
            results: 各品种分析结果

        Returns:
            相关性矩阵
        """
        try:
            successful_results = [r for r in results if not r.get("error") and r.get("equity")]

            if len(successful_results) < 2:
                return {}

            # 提取权益曲线数据
            equity_curves = {}
            for result in successful_results:
                equity_data = result["equity"]
                if equity_data:
                    df = pd.DataFrame(equity_data)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date")
                    # 计算日收益率
                    df["daily_return"] = df["equity"].pct_change()
                    equity_curves[result["symbol"]] = df.set_index("date")["daily_return"]

            # 构建相关性矩阵
            if len(equity_curves) >= 2:
                combined_df = pd.DataFrame(equity_curves)
                correlation_matrix = combined_df.corr()

                symbols = correlation_matrix.columns.tolist()
                matrix_values = correlation_matrix.values.tolist()

                # 计算统计信息
                upper_triangle = []
                for i in range(len(symbols)):
                    for j in range(i + 1, len(symbols)):
                        upper_triangle.append(matrix_values[i][j])

                avg_correlation = np.mean(upper_triangle) if upper_triangle else 0
                min_correlation = np.min(upper_triangle) if upper_triangle else 0
                max_correlation = np.max(upper_triangle) if upper_triangle else 0

                return {
                    "symbols": symbols,
                    "matrix": matrix_values,
                    "averageCorrelation": avg_correlation,
                    "minCorrelation": min_correlation,
                    "maxCorrelation": max_correlation
                }

        except Exception as e:
            print(f"计算相关性矩阵失败: {str(e)}")
            return {}

    async def statistical_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        进行统计显著性检验

        Args:
            results: 各品种分析结果

        Returns:
            统计分析结果
        """
        try:
            successful_results = [r for r in results if not r.get("error") and r.get("metrics")]

            if len(successful_results) < 2:
                return {}

            # 提取收益率数据
            returns = [r["metrics"].get("totalReturn", 0) for r in successful_results]

            # 正态性检验（Shapiro-Wilk）
            from scipy import stats
            shapiro_stat, shapiro_p = stats.shapiro(returns)

            # 配对t检验
            pairwise_tests = {}
            for i, result1 in enumerate(successful_results):
                for j, result2 in enumerate(successful_results[i+1:], i+1):
                    returns1 = [result1["metrics"].get("totalReturn", 0)]
                    returns2 = [result2["metrics"].get("totalReturn", 0)]

                    # 这里简化处理，实际应该使用时间序列数据
                    t_stat, p_value = stats.ttest_ind(returns1, returns2)

                    pair_key = f"{result1['symbol']}_vs_{result2['symbol']}"
                    pairwise_tests[pair_key] = {
                        "statistic": t_stat,
                        "pValue": p_value,
                        "significant": p_value < 0.05
                    }

            return {
                "normalityTest": {
                    "statistic": shapiro_stat,
                    "pValue": shapiro_p,
                    "isNormal": shapiro_p > 0.05
                },
                "pairwiseTests": pairwise_tests
            }

        except Exception as e:
            print(f"统计分析失败: {str(e)}")
            return {}