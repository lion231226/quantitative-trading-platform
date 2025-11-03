"""
策略模块集成测试
测试所有组件协同工作
"""

import pytest
from datetime import datetime, timezone
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.strategy.config import StrategyConfig, StrategyType, MAConfig
from app.strategy.strategy_engine import StrategyEngine, MarketDataUpdate


class TestStrategyIntegration:
    """策略集成测试"""

    def test_complete_strategy_workflow(self):
        """测试完整的策略工作流程"""
        # 创建策略配置
        config = StrategyConfig(
            strategy_name="集成测试策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="用于集成测试的完整策略配置",
            ma_configs=[
                MAConfig(ma_type="SMA", period=5, enabled=True)
            ]
        )

        # 验证配置
        is_valid, errors = config.validate()
        assert is_valid is True, f"配置验证失败: {errors}"

        # 创建策略引擎
        engine = StrategyEngine(config)
        assert engine.config is config
        assert engine.state.value == "STOPPED"

    def test_strategy_with_real_data_simulation(self):
        """测试策略使用模拟真实数据"""
        # 创建保守型策略配置
        config = StrategyConfig(
            strategy_name="保守测试策略",
            strategy_type=StrategyType.SINGLE_MA,
            ma_configs=[
                MAConfig(ma_type="SMA", period=3, enabled=True)  # 使用较短周期便于测试
            ]
        )

        engine = StrategyEngine(config)

        # 模拟市场数据（上升趋势）
        base_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        market_data_updates = []

        # 价格序列：从低于MA到高于MA（金叉）
        prices = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]

        for i, price in enumerate(prices):
            market_data = MarketDataUpdate(
                symbol="TEST",
                price=price,
                timestamp=base_timestamp + i * 60,  # 每分钟一个数据点
                volume=1000.0
            )
            market_data_updates.append(market_data)

        # 设置引擎为运行状态
        engine._running = True
        engine.state = engine.state.RUNNING

        # 处理市场数据
        new_positions = []
        for market_data in market_data_updates:
            positions = engine.process_market_data(market_data)
            new_positions.extend(positions)

        # 验证结果
        assert isinstance(new_positions, list)
        # 由于数据趋势向上且设置了短周期MA，可能会产生买入信号
        print(f"产生了 {len(new_positions)} 个新持仓")

    def test_strategy_configuration_persistence(self):
        """测试策略配置持久化"""
        # 创建复杂策略配置
        config = StrategyConfig(
            strategy_name="持久化测试策略",
            strategy_type=StrategyType.DUAL_MA,
            description="用于测试配置持久化的复杂策略",
            ma_configs=[
                MAConfig(ma_type="EMA", period=10, enabled=True, weight=0.6),
                MAConfig(ma_type="SMA", period=20, enabled=True, weight=0.4)
            ]
        )

        # 转换为字典
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict['strategy_name'] == "持久化测试策略"
        assert len(config_dict['ma_configs']) == 2

        # 从字典重建配置
        rebuilt_config = StrategyConfig.from_dict(config_dict)
        assert rebuilt_config.strategy_name == config.strategy_name
        assert rebuilt_config.strategy_type == config.strategy_type
        assert len(rebuilt_config.ma_configs) == len(config.ma_configs)

        # 验证重建的配置
        is_valid, errors = rebuilt_config.validate()
        assert is_valid is True, f"重建配置验证失败: {errors}"

    def test_strategy_performance_metrics_calculation(self):
        """测试策略性能指标计算"""
        config = StrategyConfig(strategy_name="性能测试策略")
        engine = StrategyEngine(config)

        # 模拟权益曲线数据
        base_equity = 100000.0
        equity_points = []

        # 模拟一个简单的收益曲线
        for i in range(20):
            # 简单的线性增长 + 小幅波动
            equity = base_equity + (i * 1000) + (i % 3) * 500
            timestamp = int(datetime.now(tz=timezone.utc).timestamp()) + i * 3600  # 每小时
            engine.strategy_state.add_equity_point(timestamp, equity)
            equity_points.append((timestamp, equity))

        # 获取性能指标
        metrics = engine.get_performance_metrics()

        assert isinstance(metrics, dict)
        if metrics:  # 如果有足够数据计算指标
            assert "total_return" in metrics
            assert "max_drawdown" in metrics
            assert "sharpe_ratio" in metrics
            assert "total_trades" in metrics
            assert "win_rate" in metrics

            # 验证总收益率为正（因为数据是上升趋势）
            assert metrics["total_return"] >= 0

    def test_strategy_error_handling(self):
        """测试策略错误处理"""
        config = StrategyConfig(strategy_name="错误处理测试策略")
        engine = StrategyEngine(config)

        # 测试无效市场数据处理
        try:
            # 创建一些无效数据
            invalid_market_data = MarketDataUpdate(
                symbol="TEST",
                price=-100.0,  # 负价格（虽然不现实，但测试鲁棒性）
                timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
                volume=-1000.0  # 负成交量
            )

            engine._running = True
            engine.state = engine.state.RUNNING

            # 处理无效数据不应该崩溃
            result = engine.process_market_data(invalid_market_data)
            assert isinstance(result, list)

        except Exception as e:
            # 如果发生异常，应该是被正确处理的业务异常
            pytest.fail(f"处理无效市场数据时发生未预期异常: {e}")

    def test_strategy_reset_functionality(self):
        """测试策略重置功能"""
        config = StrategyConfig(strategy_name="重置测试策略")
        engine = StrategyEngine(config)

        # 添加一些数据
        engine.price_history["TEST"] = [100.0, 101.0, 102.0, 103.0, 104.0]
        engine.strategy_state.add_equity_point(1234567890, 100000.0)
        engine.strategy_state.add_equity_point(1234567891, 101000.0)

        # 验证数据存在
        assert len(engine.price_history["TEST"]) == 5
        assert len(engine.strategy_state.equity_curve) == 2

        # 重置策略
        engine.reset()

        # 验证数据已清理
        assert len(engine.price_history) == 0
        assert len(engine.strategy_state.equity_curve) == 0
        assert engine.strategy_state.total_trades == 0
        assert engine.state.value == "STOPPED"

    def test_strategy_multi_symbol_support(self):
        """测试策略多标的支持"""
        config = StrategyConfig(strategy_name="多标的测试策略")
        engine = StrategyConfig(config)
        engine = StrategyEngine(config)

        # 模拟多个标的数据
        symbols = ["AAPL", "GOOGL", "MSFT"]
        base_timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        # 为每个标的不同价格趋势
        price_trends = {
            "AAPL": list(range(100, 120)),      # 上升趋势
            "GOOGL": list(range(200, 180, -2)), # 下降趋势
            "MSFT": [150] * 20                   # 平稳
        }

        # 添加市场数据
        for symbol in symbols:
            for i, price in enumerate(price_trends[symbol][:10]):  # 取前10个数据点
                market_data = MarketDataUpdate(
                    symbol=symbol,
                    price=float(price),
                    timestamp=base_timestamp + i * 60,
                    volume=1000.0
                )
                engine._update_price_history(market_data)

        # 验证所有标的数据都被保存
        for symbol in symbols:
            assert symbol in engine.price_history
            assert len(engine.price_history[symbol]) == 10

        # 验证价格历史正确
        assert engine.price_history["AAPL"][0] == 100.0
        assert engine.price_history["GOOGL"][0] == 200.0
        assert all(price == 150.0 for price in engine.price_history["MSFT"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])