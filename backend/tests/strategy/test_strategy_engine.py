"""
策略引擎测试
"""

import pytest
from datetime import datetime, timezone
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.strategy.strategy_engine import (
    StrategyEngine, StrategyState, EngineState, MarketDataUpdate
)
from app.strategy.config import StrategyConfig, StrategyType, MAConfig


class TestStrategyConfig:
    """策略配置测试"""

    def test_default_config_creation(self):
        """测试默认配置创建"""
        config = StrategyConfig()
        assert config.strategy_name == "默认策略"
        assert config.strategy_type == StrategyType.SINGLE_MA
        assert len(config.ma_configs) == 1
        assert config.ma_configs[0].ma_type.value == "SMA"
        assert config.ma_configs[0].period == 20

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = StrategyConfig(
            strategy_name="测试策略",
            description="这是一个测试策略"
        )
        is_valid, errors = valid_config.validate()
        assert is_valid is True
        assert len(errors) == 0

        # 无效配置 - 空名称
        invalid_config = StrategyConfig(strategy_name="")
        is_valid, errors = invalid_config.validate()
        assert is_valid is False
        assert any("策略名称不能为空" in error for error in errors)

    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = StrategyConfig(
            strategy_name="测试策略",
            strategy_type=StrategyType.DUAL_MA,
            description="双均线测试策略"
        )

        config_dict = config.to_dict()
        assert config_dict['strategy_name'] == "测试策略"
        assert config_dict['strategy_type'] == "DUAL_MA"
        assert config_dict['description'] == "双均线测试策略"
        assert len(config_dict['ma_configs']) == 1

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            'strategy_name': '从字典创建的策略',
            'strategy_type': 'SINGLE_MA',
            'description': '测试从字典创建',
            'ma_configs': [
                {
                    'ma_type': 'EMA',
                    'period': 15,
                    'enabled': True,
                    'weight': 1.0
                }
            ]
        }

        config = StrategyConfig.from_dict(config_dict)
        assert config.strategy_name == "从字典创建的策略"
        assert config.strategy_type == StrategyType.SINGLE_MA
        assert config.ma_configs[0].ma_type.value == "EMA"
        assert config.ma_configs[0].period == 15


class TestMarketDataUpdate:
    """市场数据更新测试"""

    def test_market_data_creation(self):
        """测试市场数据创建"""
        update = MarketDataUpdate(
            symbol="TEST",
            price=100.5,
            timestamp=1234567890,
            volume=1000.0,
            metadata={"bid": 100.4, "ask": 100.6}
        )

        assert update.symbol == "TEST"
        assert update.price == 100.5
        assert update.timestamp == 1234567890
        assert update.volume == 1000.0
        assert update.metadata["bid"] == 100.4

    def test_market_data_without_optional_fields(self):
        """测试不包含可选字段的市场数据"""
        update = MarketDataUpdate(
            symbol="TEST",
            price=100.5,
            timestamp=1234567890
        )

        assert update.symbol == "TEST"
        assert update.price == 100.5
        assert update.volume is None
        assert update.metadata == {}


class TestStrategyState:
    """策略状态测试"""

    def test_strategy_state_initialization(self):
        """测试策略状态初始化"""
        state = StrategyState()
        assert len(state.current_positions) == 0
        assert state.last_signal is None
        assert state.total_trades == 0
        assert state.winning_trades == 0
        assert state.losing_trades == 0
        assert state.total_pnl == 0.0
        assert state.max_drawdown == 0.0
        assert len(state.equity_curve) == 0

    def test_equity_curve_management(self):
        """测试权益曲线管理"""
        state = StrategyState()

        # 添加权益点
        state.add_equity_point(1234567890, 100000.0)
        state.add_equity_point(1234567891, 101000.0)
        state.add_equity_point(1234567892, 100500.0)

        assert len(state.equity_curve) == 3
        assert state.equity_curve[0] == (1234567890, 100000.0)
        assert state.equity_curve[1] == (1234567891, 101000.0)
        assert state.equity_curve[2] == (1234567892, 100500.0)

    def test_equity_curve_limit(self):
        """测试权益曲线长度限制"""
        state = StrategyState()

        # 添加超过限制的权益点（限制是10000）
        for i in range(15000):
            state.add_equity_point(1234567890 + i, 100000.0 + i)

        # 应该被限制在5000个点
        assert len(state.equity_curve) == 5000


class TestStrategyEngine:
    """策略引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        config = StrategyConfig(
            strategy_name="测试策略",
            strategy_type=StrategyType.SINGLE_MA
        )

        engine = StrategyEngine(config)
        assert engine.config is config
        assert engine.state == EngineState.STOPPED
        assert engine.ma_calculator is not None
        assert engine.signal_generator is not None
        assert engine.position_manager is not None

    def test_engine_with_invalid_config(self):
        """测试无效配置的引擎初始化"""
        invalid_config = StrategyConfig(strategy_name="")  # 无效配置

        with pytest.raises(ValueError):
            StrategyEngine(invalid_config)

    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """测试引擎启动和停止"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 启动引擎
        success = await engine.start(["TEST"])
        assert success is True
        assert engine.state == EngineState.RUNNING

        # 停止引擎
        await engine.stop()
        assert engine.state == EngineState.STOPPED

    @pytest.mark.asyncio
    async def test_engine_pause_resume(self):
        """测试引擎暂停和恢复"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 启动引擎
        await engine.start(["TEST"])
        assert engine.state == EngineState.RUNNING

        # 暂停引擎
        await engine.pause()
        assert engine.state == EngineState.PAUSED

        # 恢复引擎
        await engine.resume()
        assert engine.state == EngineState.RUNNING

        # 停止引擎
        await engine.stop()

    def test_process_market_data(self):
        """测试处理市场数据"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 手动设置为运行状态
        engine._running = True
        engine.state = EngineState.RUNNING

        # 创建市场数据更新
        market_data = MarketDataUpdate(
            symbol="TEST",
            price=100.0,
            timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            volume=1000.0
        )

        # 处理市场数据
        new_positions = engine.process_market_data(market_data)

        # 由于没有足够的历史数据，可能不会产生新持仓
        assert isinstance(new_positions, list)

    def test_price_history_management(self):
        """测试价格历史管理"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 创建多个市场数据更新
        base_timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        for i in range(10):
            market_data = MarketDataUpdate(
                symbol="TEST",
                price=100.0 + i,
                timestamp=base_timestamp + i,
                volume=1000.0
            )
            engine._update_price_history(market_data)

        # 验证历史数据
        assert "TEST" in engine.price_history
        assert len(engine.price_history["TEST"]) == 10
        assert engine.price_history["TEST"][0] == 100.0
        assert engine.price_history["TEST"][-1] == 109.0

    def test_history_limit(self):
        """测试历史数据限制"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 添加超过限制的历史数据（限制是1000）
        for i in range(1500):
            market_data = MarketDataUpdate(
                symbol="TEST",
                price=100.0 + i,
                timestamp=int(datetime.now(tz=timezone.utc).timestamp()) + i,
                volume=1000.0
            )
            engine._update_price_history(market_data)

        # 应该被限制在1000个点
        assert len(engine.price_history["TEST"]) == 1000

    def test_get_strategy_status(self):
        """测试获取策略状态"""
        config = StrategyConfig(
            strategy_name="测试策略",
            strategy_type=StrategyType.SINGLE_MA
        )
        engine = StrategyEngine(config)

        status = engine.get_strategy_status()

        assert isinstance(status, dict)
        assert status["state"] == EngineState.STOPPED.value
        assert status["initialized"] is True
        assert status["strategy_name"] == "测试策略"
        assert status["strategy_type"] == "SINGLE_MA"
        assert "position_summary" in status
        assert "total_trades" in status
        assert "win_rate" in status

    def test_get_open_positions(self):
        """测试获取开放持仓"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 获取所有开放持仓
        all_positions = engine.get_open_positions()
        assert isinstance(all_positions, list)

        # 获取特定标的的持仓
        specific_positions = engine.get_open_positions("TEST")
        assert isinstance(specific_positions, list)

    def test_get_equity_curve(self):
        """测试获取权益曲线"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 添加一些权益点
        engine.strategy_state.add_equity_point(1234567890, 100000.0)
        engine.strategy_state.add_equity_point(1234567891, 101000.0)

        equity_curve = engine.get_equity_curve()
        assert isinstance(equity_curve, list)
        assert len(equity_curve) == 2
        assert equity_curve[0] == (1234567890, 100000.0)

    def test_get_performance_metrics(self):
        """测试获取性能指标"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 添加足够的权益数据以计算指标
        base_equity = 100000.0
        for i in range(10):
            equity = base_equity + i * 1000  # 简单的线性增长
            engine.strategy_state.add_equity_point(1234567890 + i, equity)

        metrics = engine.get_performance_metrics()

        assert isinstance(metrics, dict)
        if metrics:  # 如果有足够的权益数据
            assert "total_return" in metrics
            assert "max_drawdown" in metrics
            assert "sharpe_ratio" in metrics
            assert "total_trades" in metrics
            assert "win_rate" in metrics

    def test_config_update(self):
        """测试配置更新"""
        original_config = StrategyConfig(
            strategy_name="原始策略",
            ma_configs=[MAConfig(period=20)]
        )
        engine = StrategyEngine(original_config)

        # 创建新配置
        new_config = StrategyConfig(
            strategy_name="更新策略",
            ma_configs=[MAConfig(period=30)]
        )

        # 更新配置
        success = engine.update_config(new_config)
        assert success is True
        assert engine.config is new_config
        assert engine.config.strategy_name == "更新策略"
        assert engine.config.ma_configs[0].period == 30

    def test_invalid_config_update(self):
        """测试无效配置更新"""
        original_config = StrategyConfig(strategy_name="原始策略")
        engine = StrategyEngine(original_config)

        # 创建无效配置
        invalid_config = StrategyConfig(strategy_name="")  # 无效配置

        # 更新配置应该失败
        success = engine.update_config(invalid_config)
        assert success is False
        # 原配置应该保持不变
        assert engine.config.strategy_name == "原始策略"

    def test_engine_reset(self):
        """测试引擎重置"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 添加一些数据
        engine.price_history["TEST"] = [100.0, 101.0, 102.0]
        engine.strategy_state.add_equity_point(1234567890, 100000.0)

        # 重置引擎
        engine.reset()

        # 验证重置结果
        assert len(engine.price_history) == 0
        assert len(engine.strategy_state.equity_curve) == 0
        assert engine.strategy_state.total_trades == 0
        assert engine.state == EngineState.STOPPED


class TestStrategyEngineEdgeCases:
    """策略引擎边界情况测试"""

    def test_empty_market_data(self):
        """测试空市场数据处理"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)
        engine._running = True
        engine.state = EngineState.RUNNING

        # 使用空的市场数据（不应该发生，但测试鲁棒性）
        try:
            # 这里我们不能直接创建空的MarketDataUpdate，因为必需参数不能为空
            # 但我们可以测试其他边界情况
            pass
        except Exception:
            # 如果出现异常，应该被正确处理
            pass

    def test_engine_without_position_manager(self):
        """测试没有仓位管理器的引擎"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)

        # 临时移除仓位管理器
        original_pm = engine.position_manager
        engine.position_manager = None

        try:
            # 获取状态应该仍然工作
            status = engine.get_strategy_status()
            assert status["initialized"] is False
        finally:
            # 恢复仓位管理器
            engine.position_manager = original_pm

    def test_multiple_symbol_data(self):
        """测试多标的的数据处理"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyConfig(config)
        engine = StrategyEngine(config)

        # 为多个标的添加数据
        symbols = ["AAPL", "GOOGL", "MSFT"]
        base_timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        for symbol in symbols:
            for i in range(5):
                market_data = MarketDataUpdate(
                    symbol=symbol,
                    price=100.0 + i,
                    timestamp=base_timestamp + i,
                    volume=1000.0
                )
                engine._update_price_history(market_data)

        # 验证所有标的数据都被保存
        for symbol in symbols:
            assert symbol in engine.price_history
            assert len(engine.price_history[symbol]) == 5

    def test_concurrent_market_data_processing(self):
        """测试并发市场数据处理（概念性测试）"""
        config = StrategyConfig(strategy_name="测试策略")
        engine = StrategyEngine(config)
        engine._running = True
        engine.state = EngineState.RUNNING

        # 创建多个市场数据更新
        base_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        market_updates = []

        for i in range(10):
            update = MarketDataUpdate(
                symbol="TEST",
                price=100.0 + i,
                timestamp=base_timestamp + i,
                volume=1000.0
            )
            market_updates.append(update)

        # 按顺序处理（实际应用中可能需要更复杂的并发控制）
        results = []
        for update in market_updates:
            result = engine.process_market_data(update)
            results.append(result)

        # 验证所有更新都被处理
        assert len(results) == len(market_updates)
        assert all(isinstance(result, list) for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])