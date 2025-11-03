"""
真实场景的绩效分析集成测试
模拟实际交易环境中的复杂情况
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.performance.analytics_engine import PerformanceAnalyticsEngine, PerformanceAnalysisConfig, ReturnType
from app.services.performance.return_calculator import ReturnCalculator, ReturnCalculationConfig
from app.models.market_data import MarketData


class TestRealisticScenarios:
    """真实场景测试类"""

    def setup_method(self):
        """设置测试数据"""
        self.config = PerformanceAnalysisConfig(
            return_type=ReturnType.SIMPLE,
            initial_capital=100000,
            position_size=0.6,
            risk_free_rate=0.025
        )
        self.engine = PerformanceAnalyticsEngine(self.config)

    def create_realistic_market_data(self, days: int = 252, base_price: float = 100.0) -> List[MarketData]:
        """
        创建模拟真实市场数据
        包含趋势、波动、噪声等特征
        """
        np.random.seed(42)  # 确保可重复性

        market_data = []
        current_price = base_price

        for i in range(days):
            date = datetime(2024, 1, 1) + timedelta(days=i)

            # 模拟价格走势：趋势 + 随机波动
            trend = 0.0002 * i  # 轻微上涨趋势
            volatility = 0.015  # 日波动率
            noise = np.random.normal(0, volatility)

            price_change = trend + noise
            current_price *= (1 + price_change)

            # 确保价格为正
            current_price = max(current_price, 10.0)

            # 生成OHLC数据
            high_price = current_price * (1 + abs(np.random.normal(0, 0.005)))
            low_price = current_price * (1 - abs(np.random.normal(0, 0.005)))
            open_price = low_price + (high_price - low_price) * np.random.random()
            close_price = current_price

            # 确保价格关系正确
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            market_data.append(MarketData(
                symbol="TEST001",
                date=date,
                open_price=round(open_price, 2),
                high_price=round(high_price, 2),
                low_price=round(low_price, 2),
                close_price=round(close_price, 2),
                volume=int(np.random.normal(10000, 2000))
            ))

        return market_data

    def create_momentum_signals(self, prices: np.ndarray, short_window: int = 5, long_window: int = 20) -> np.ndarray:
        """
        创建基于动量的交易信号
        短期均线上穿长期均线时买入，下穿时卖出
        """
        signals = np.zeros(len(prices))

        if len(prices) < long_window:
            return signals

        # 计算移动平均线
        short_ma = np.convolve(prices, np.ones(short_window)/short_window, mode='valid')
        long_ma = np.convolve(prices, np.ones(long_window)/long_window, mode='valid')

        # 对齐长度
        padding = long_window - 1
        short_ma = np.pad(short_ma, (padding, 0), 'constant')
        long_ma = np.pad(long_ma, (0, 0), 'constant')

        # 生成信号
        for i in range(long_window-1, len(prices)):
            if i > 0:
                if short_ma[i] > long_ma[i] and short_ma[i-1] <= long_ma[i-1]:
                    signals[i] = 1  # 金叉买入
                elif short_ma[i] < long_ma[i] and short_ma[i-1] >= long_ma[i-1]:
                    signals[i] = -1  # 死叉卖出
                else:
                    signals[i] = signals[i-1]  # 保持原有仓位

        return signals

    def test_bull_market_scenario(self):
        """测试牛市场景下的策略表现"""
        # 创建上涨趋势的市场数据
        market_data = self.create_realistic_market_data(days=126, base_price=100.0)
        prices = np.array([data.close_price for data in market_data])

        # 在牛市中，买入持有策略应该表现良好
        signals = np.zeros(len(market_data))
        signals[10:60] = 1  # 前50天持有
        signals[80:120] = 1  # 中间40天持有

        metrics = self.engine.calculate_strategy_performance(
            strategy_id="bull_market_test",
            signals=signals,
            market_data=market_data
        )

        # 验证结果合理性
        assert metrics.total_return > 0  # 牛市中应该有正收益
        assert metrics.max_drawdown <= 0
        assert 0 <= metrics.win_rate <= 1
        assert metrics.data_points == len(market_data)

    def test_bear_market_scenario(self):
        """测试熊市场景下的策略表现"""
        # 创建下跌趋势的市场数据
        market_data = self.create_realistic_market_data(days=126, base_price=100.0)

        # 修改为下跌趋势
        for i, data in enumerate(market_data):
            data.close_price *= (1 - 0.001 * i)  # 逐渐下跌
            data.high_price *= (1 - 0.001 * i)
            data.low_price *= (1 - 0.001 * i)
            data.open_price *= (1 - 0.001 * i)

        prices = np.array([data.close_price for data in market_data])
        signals = np.zeros(len(market_data))

        # 在熊市中，空仓或做空策略应该表现更好
        signals[10:60] = 0  # 空仓规避下跌

        metrics = self.engine.calculate_strategy_performance(
            strategy_id="bear_market_test",
            signals=signals,
            market_data=market_data
        )

        # 空仓策略应该损失最小
        assert metrics.max_drawdown <= 0
        assert metrics.total_trades == 0  # 空仓没有交易

    def test_sideways_market_scenario(self):
        """测试横盘市场场景下的策略表现"""
        market_data = self.create_realistic_market_data(days=63, base_price=100.0)

        # 创建震荡信号（网格交易）
        prices = np.array([data.close_price for data in market_data])
        signals = np.zeros(len(market_data))

        mean_price = np.mean(prices)
        std_price = np.std(prices)

        for i, price in enumerate(prices):
            if price < mean_price - 0.5 * std_price:
                signals[i] = 1  # 价格低于均值时买入
            elif price > mean_price + 0.5 * std_price:
                signals[i] = 0  # 价格高于均值时卖出
            else:
                signals[i] = signals[i-1] if i > 0 else 0

        metrics = self.engine.calculate_strategy_performance(
            strategy_id="sideways_market_test",
            signals=signals,
            market_data=market_data
        )

        # 验证横盘市场中的表现
        assert metrics.total_trades > 0  # 应该有交易
        assert 0 <= metrics.win_rate <= 1

    def test_momentum_strategy_integration(self):
        """测试动量策略的完整集成"""
        market_data = self.create_realistic_market_data(days=252)
        prices = np.array([data.close_price for data in market_data])
        signals = self.create_momentum_signals(prices)

        # 计算策略绩效
        metrics = self.engine.calculate_strategy_performance(
            strategy_id="momentum_strategy",
            signals=signals,
            market_data=market_data
        )

        # 验证动量策略的特性
        assert metrics.total_trades > 0  # 动量策略应该有交易
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown <= 0

        # 动量策略通常有较高的交易频率
        assert metrics.total_trades >= 2

    def test_risk_metrics_calculation(self):
        """测试风险指标计算的准确性"""
        market_data = self.create_realistic_market_data(days=100)
        prices = np.array([data.close_price for data in market_data])

        # 创建有明显回撤的信号
        signals = np.zeros(len(market_data))
        signals[10:30] = 1  # 持仓20天
        signals[50:70] = 1  # 再持仓20天

        metrics = self.engine.calculate_strategy_performance(
            strategy_id="risk_metrics_test",
            signals=signals,
            market_data=market_data
        )

        # 验证风险指标的合理性
        assert -1 <= metrics.max_drawdown <= 0
        assert metrics.volatility >= 0

        if metrics.sharpe_ratio is not None:
            assert isinstance(metrics.sharpe_ratio, (int, float))

        if metrics.sortino_ratio is not None:
            assert isinstance(metrics.sortino_ratio, (int, float))

    def test_large_dataset_performance(self):
        """测试大数据集的性能表现"""
        # 创建5年的数据
        market_data = self.create_realistic_market_data(days=1260)
        prices = np.array([data.close_price for data in market_data])
        signals = self.create_momentum_signals(prices)

        import time
        start_time = time.time()

        metrics = self.engine.calculate_strategy_performance(
            strategy_id="large_dataset_test",
            signals=signals,
            market_data=market_data
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证性能要求
        assert execution_time < 2.0  # 应该在2秒内完成
        assert metrics.data_points == 1260
        assert metrics.total_return is not None

    def test_edge_cases_handling(self):
        """测试边界情况的处理"""
        # 极短数据集
        short_data = self.create_realistic_market_data(days=2)
        signals = np.array([0, 1])

        # 应该能够处理极短数据
        try:
            metrics = self.engine.calculate_strategy_performance(
                strategy_id="short_data_test",
                signals=signals,
                market_data=short_data
            )
            assert metrics.data_points == 2
        except ValueError:
            # 如果数据太少无法计算，也是合理的
            pass

        # 单一数据点
        single_data = short_data[:1]
        single_signals = np.array([0])

        # 单一数据点通常无法计算有效指标
        try:
            metrics = self.engine.calculate_strategy_performance(
                strategy_id="single_data_test",
                signals=single_signals,
                market_data=single_data
            )
        except (ValueError, IndexError):
            # 预期会失败
            pass

    def test_different_return_types(self):
        """测试不同收益率计算类型"""
        market_data = self.create_realistic_market_data(days=50)
        prices = np.array([data.close_price for data in market_data])
        signals = np.ones(len(market_data))  # 持续持有

        # 测试简单收益率
        simple_config = PerformanceAnalysisConfig(return_type=ReturnType.SIMPLE)
        simple_engine = PerformanceAnalyticsEngine(simple_config)
        simple_metrics = simple_engine.calculate_strategy_performance(
            strategy_id="simple_return_test",
            signals=signals,
            market_data=market_data
        )

        # 测试对数收益率
        log_config = PerformanceAnalysisConfig(return_type=ReturnType.LOG)
        log_engine = PerformanceAnalyticsEngine(log_config)
        log_metrics = log_engine.calculate_strategy_performance(
            strategy_id="log_return_test",
            signals=signals,
            market_data=market_data
        )

        # 两种方法应该给出相似但不完全相同的结果
        assert simple_metrics.total_return is not None
        assert log_metrics.total_return is not None
        # 对数收益率通常略低于简单收益率（当收益率较小时）
        assert abs(simple_metrics.total_return - log_metrics.total_return) < 0.1