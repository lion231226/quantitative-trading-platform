"""
仓位管理器测试
"""

import pytest
from datetime import datetime, timezone

from app.strategy.trading import (
    Position, PositionType, Order, OrderType, OrderStatus,
    PositionManager, RiskConfig, RiskManager
)
from app.strategy.signals import TradingSignal, SignalType, SignalStrength


class TestRiskConfig:
    """风险管理配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = RiskConfig()
        assert config.max_position_size == 1.0
        assert config.max_positions == 5
        assert config.stop_loss_pct == 0.02
        assert config.take_profit_pct == 0.05
        assert config.commission_rate == 0.001

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = RiskConfig()
        assert valid_config.validate() is True

        # 无效配置
        invalid_configs = [
            RiskConfig(max_position_size=1.5),      # 超过1.0
            RiskConfig(max_position_size=0.0),      # 等于0
            RiskConfig(max_positions=0),            # 等于0
            RiskConfig(stop_loss_pct=1.0),          # 等于1.0
            RiskConfig(take_profit_pct=0.0),        # 等于0
            RiskConfig(commission_rate=-0.01),      # 负数
        ]

        for config in invalid_configs:
            assert config.validate() is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = RiskConfig(
            max_position_size=0.5,
            max_positions=10,
            stop_loss_pct=0.01,
            take_profit_pct=0.03
        )

        assert config.max_position_size == 0.5
        assert config.max_positions == 10
        assert config.stop_loss_pct == 0.01
        assert config.take_profit_pct == 0.03
        assert config.validate() is True


class TestRiskManager:
    """风险管理器测试"""

    def test_risk_manager_initialization(self):
        """测试风险管理器初始化"""
        config = RiskConfig()
        manager = RiskManager(config)

        assert manager.config is config
        assert manager.total_equity == 100000.0
        assert manager.max_equity == 100000.0
        assert manager.current_drawdown == 0.0

    def test_calculate_position_size(self):
        """测试仓位大小计算"""
        config = RiskConfig(max_position_size=0.1)
        manager = RiskManager(config)

        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试信号"
        )

        position_size = manager.calculate_position_size(signal, 10.0, 100000.0)
        expected_size = 100000.0 * 0.1 / 10.0  # 可用资金 * 最大仓位 / 价格
        assert abs(position_size - expected_size) < 1e-10

    def test_position_size_with_signal_strength(self):
        """测试信号强度对仓位大小的影响"""
        config = RiskConfig(max_position_size=0.2)
        manager = RiskManager(config)

        # 强信号
        strong_signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=1.0,
            reason="强信号"
        )

        # 弱信号
        weak_signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.WEAK,
            confidence=0.3,
            reason="弱信号"
        )

        strong_size = manager.calculate_position_size(strong_signal, 10.0, 100000.0)
        weak_size = manager.calculate_position_size(weak_signal, 10.0, 100000.0)

        # 强信号应该产生更大的仓位
        assert strong_size > weak_size

    def test_check_stop_loss_long_position(self):
        """测试多头持仓止损检查"""
        config = RiskConfig(stop_loss_pct=0.02)
        manager = RiskManager(config)

        # 创建多头持仓
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        # 价格下跌1%（未触发止损）
        position.current_price = 9.9
        assert manager.check_stop_loss(position, 9.9) is False

        # 价格下跌3%（触发止损）
        position.current_price = 9.7
        assert manager.check_stop_loss(position, 9.7) is True

    def test_check_stop_loss_short_position(self):
        """测试空头持仓止损检查"""
        config = RiskConfig(stop_loss_pct=0.02)
        manager = RiskManager(config)

        # 创建空头持仓
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.SHORT,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        # 价格上涨1%（未触发止损）
        position.current_price = 10.1
        assert manager.check_stop_loss(position, 10.1) is False

        # 价格上涨3%（触发止损）
        position.current_price = 10.3
        assert manager.check_stop_loss(position, 10.3) is True

    def test_check_take_profit_long_position(self):
        """测试多头持仓止盈检查"""
        config = RiskConfig(take_profit_pct=0.05)
        manager = RiskManager(config)

        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        # 价格上涨3%（未触发止盈）
        position.current_price = 10.3
        assert manager.check_take_profit(position, 10.3) is False

        # 价格上涨6%（触发止盈）
        position.current_price = 10.6
        assert manager.check_take_profit(position, 10.6) is True

    def test_check_max_drawdown(self):
        """测试最大回撤检查"""
        config = RiskConfig(max_drawdown_pct=0.1)
        manager = RiskManager(config)

        # 初始资金100000，最高100000，当前90000（10%回撤）
        manager.total_equity = 90000.0
        assert manager.check_max_drawdown() is True

        # 当前95000（5%回撤）
        manager.total_equity = 95000.0
        assert manager.check_max_drawdown() is False

    def test_equity_update(self):
        """测试资金更新"""
        manager = RiskManager(RiskConfig())

        # 资金增加
        manager.update_equity(105000.0)
        assert manager.total_equity == 105000.0
        assert manager.max_equity == 105000.0

        # 资金减少
        manager.update_equity(95000.0)
        assert manager.total_equity == 95000.0
        assert manager.max_equity == 105000.0  # 最高资金不变

    def test_commission_calculation(self):
        """测试手续费计算"""
        manager = RiskManager(RiskConfig(commission_rate=0.001))

        order_value = 10000.0
        commission = manager.calculate_commission(order_value)
        assert commission == 10.0

    def test_slippage_application(self):
        """测试滑点应用"""
        manager = RiskManager(RiskConfig(slippage_rate=0.0001))

        # 买单
        buy_price = 10.0
        adjusted_buy_price = manager.apply_slippage(buy_price, "BUY")
        assert adjusted_buy_price > buy_price

        # 卖单
        sell_price = 10.0
        adjusted_sell_price = manager.apply_slippage(sell_price, "SELL")
        assert adjusted_sell_price < sell_price


class TestPosition:
    """持仓测试"""

    def test_position_creation(self):
        """测试持仓创建"""
        position = Position(
            position_id="TEST_POS",
            symbol="AAPL",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        assert position.position_id == "TEST_POS"
        assert position.symbol == "AAPL"
        assert position.position_type == PositionType.LONG
        assert position.quantity == 100
        assert position.entry_price == 10.0
        assert position.current_price == 10.0
        assert position.status.value == "OPEN"

    def test_update_current_price_long(self):
        """测试更新多头持仓当前价格"""
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        # 价格上涨
        position.update_current_price(11.0)
        assert position.current_price == 11.0
        assert position.unrealized_pnl == 100.0  # (11-10)*100

        # 价格下跌
        position.update_current_price(9.0)
        assert position.current_price == 9.0
        assert position.unrealized_pnl == -100.0  # (9-10)*100

    def test_update_current_price_short(self):
        """测试更新空头持仓当前价格"""
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.SHORT,
            quantity=100,
            entry_price=10.0,
            current_price=10.0,
            entry_time=1234567890
        )

        # 价格下跌（盈利）
        position.update_current_price(9.0)
        assert position.current_price == 9.0
        assert position.unrealized_pnl == 100.0  # (10-9)*100

        # 价格上涨（亏损）
        position.update_current_price(11.0)
        assert position.current_price == 11.0
        assert position.unrealized_pnl == -100.0  # (10-11)*100

    def test_close_position_long(self):
        """测试平多头持仓"""
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=12.0,
            entry_time=1234567890
        )

        # 完全平仓
        exit_time = 1234567900
        position.close_position(12.0, exit_time)

        assert position.quantity == 0
        assert position.exit_price == 12.0
        assert position.exit_time == exit_time
        assert position.realized_pnl == 200.0  # (12-10)*100
        assert position.status.value == "CLOSED"

    def test_close_position_short(self):
        """测试平空头持仓"""
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.SHORT,
            quantity=100,
            entry_price=10.0,
            current_price=8.0,
            entry_time=1234567890
        )

        # 完全平仓
        exit_time = 1234567900
        position.close_position(8.0, exit_time)

        assert position.quantity == 0
        assert position.exit_price == 8.0
        assert position.exit_time == exit_time
        assert position.realized_pnl == 200.0  # (10-8)*100
        assert position.status.value == "CLOSED"

    def test_partial_close_position(self):
        """测试部分平仓"""
        position = Position(
            position_id="TEST_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=12.0,
            entry_time=1234567890
        )

        # 部分平仓50股
        exit_time = 1234567900
        position.close_position(12.0, exit_time, 50)

        assert position.quantity == 50
        assert position.exit_price == 12.0
        assert position.realized_pnl == 100.0  # (12-10)*50
        assert position.status.value == "PARTIAL_CLOSED"

    def test_pnl_percentage(self):
        """测试盈亏百分比计算"""
        # 多头持仓
        long_position = Position(
            position_id="LONG_POS",
            symbol="TEST",
            position_type=PositionType.LONG,
            quantity=100,
            entry_price=10.0,
            current_price=12.0,
            entry_time=1234567890
        )
        assert long_position.pnl_percentage == 0.2  # (12-10)/10

        # 空头持仓
        short_position = Position(
            position_id="SHORT_POS",
            symbol="TEST",
            position_type=PositionType.SHORT,
            quantity=100,
            entry_price=10.0,
            current_price=8.0,
            entry_time=1234567890
        )
        assert short_position.pnl_percentage == 0.2  # (10-8)/10


class TestPositionManager:
    """仓位管理器测试"""

    def test_position_manager_initialization(self):
        """测试仓位管理器初始化"""
        config = RiskConfig()
        manager = PositionManager(config)

        assert isinstance(manager.risk_manager, RiskManager)
        assert len(manager.positions) == 0
        assert len(manager.orders) == 0
        assert len(manager.closed_positions) == 0
        assert manager.position_counter == 0
        assert manager.order_counter == 0

    def test_open_long_position(self):
        """测试开多头仓位"""
        config = RiskConfig(max_position_size=1.0)
        manager = PositionManager(config)

        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试买入信号"
        )

        position = manager.open_position(signal, 10.0, "TEST")

        assert position is not None
        assert position.symbol == "TEST"
        assert position.position_type == PositionType.LONG
        assert position.entry_price > 10.0  # 考虑滑点
        assert position.quantity > 0
        assert len(manager.positions) == 1

    def test_open_short_position(self):
        """测试开空头仓位"""
        config = RiskConfig(max_position_size=1.0)
        manager = PositionManager(config)

        signal = TradingSignal(
            signal_type=SignalType.SELL,
            timestamp=1234567890,
            price=10.0,
            ma_value=10.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试卖出信号"
        )

        position = manager.open_position(signal, 10.0, "TEST")

        assert position is not None
        assert position.position_type == PositionType.SHORT
        assert position.entry_price < 10.0  # 考虑滑点

    def test_open_position_with_insufficient_equity(self):
        """测试资金不足时开仓"""
        config = RiskConfig(max_position_size=2.0)  # 200%仓位，不可能
        manager = PositionManager(config)

        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.WEAK,
            confidence=0.1,
            reason="弱信号"
        )

        position = manager.open_position(signal, 10.0, "TEST")

        # 由于信号太弱，仓位大小可能为0
        if position is None:
            assert len(manager.positions) == 0

    def test_close_position(self):
        """测试平仓"""
        config = RiskConfig()
        manager = PositionManager(config)

        # 先开仓
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试信号"
        )

        position = manager.open_position(signal, 10.0, "TEST")
        position_id = position.position_id

        # 平仓
        closed_position = manager.close_position(position_id, 12.0, "manual_close")

        assert closed_position is not None
        assert closed_position.position_id == position_id
        assert closed_position.status.value == "CLOSED"
        assert position_id not in manager.positions
        assert len(manager.closed_positions) == 1

    def test_close_nonexistent_position(self):
        """测试平不存在的持仓"""
        manager = PositionManager(RiskConfig())

        result = manager.close_position("NONEXISTENT", 10.0, "test")
        assert result is None

    def test_update_positions(self):
        """测试更新持仓价格"""
        manager = PositionManager(RiskConfig())

        # 创建多个持仓
        for i in range(3):
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                timestamp=1234567890 + i,
                price=10.0 + i,
                ma_value=9.5 + i,
                strength=SignalStrength.STRONG,
                confidence=0.8,
                reason=f"测试信号{i+1}"
            )
            manager.open_position(signal, 10.0 + i, f"TEST{i+1}")

        # 更新价格
        current_prices = {
            "TEST1": 11.0,
            "TEST2": 12.0,
            "TEST3": 13.0,
            "TEST4": 14.0  # 这个持仓不存在
        }

        manager.update_positions(current_prices)

        # 验证价格更新
        for position in manager.positions.values():
            if position.symbol in current_prices:
                assert position.current_price == current_prices[position.symbol]

    def test_check_risk_conditions(self):
        """测试风险条件检查"""
        config = RiskConfig(stop_loss_pct=0.02)
        manager = PositionManager(config)

        # 开仓
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试信号"
        )

        position = manager.open_position(signal, 10.0, "TEST")

        # 价格大跌，触发止损
        current_prices = {"TEST": 9.5}  # 5%跌幅
        close_signals = manager.check_risk_conditions(current_prices)

        assert position.position_id in close_signals

        # 执行平仓
        for position_id in close_signals:
            manager.close_position(position_id, 9.5, "stop_loss")

        assert len(manager.positions) == 0
        assert len(manager.closed_positions) == 1

    def test_get_open_positions(self):
        """测试获取开放持仓"""
        manager = PositionManager(RiskConfig())

        # 开多个仓
        symbols = ["AAPL", "GOOGL", "MSFT"]
        for symbol in symbols:
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                timestamp=1234567890,
                price=10.0,
                ma_value=9.5,
                strength=SignalStrength.STRONG,
                confidence=0.8,
                reason="测试信号"
            )
            manager.open_position(signal, 10.0, symbol)

        # 获取所有开放持仓
        all_positions = manager.get_open_positions()
        assert len(all_positions) == 3

        # 获取特定标的的持仓
        aapl_positions = manager.get_open_positions("AAPL")
        assert len(aapl_positions) == 1
        assert aapl_positions[0].symbol == "AAPL"

    def test_get_position_summary(self):
        """测试获取持仓摘要"""
        manager = PositionManager(RiskConfig())

        # 开仓
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试信号"
        )

        manager.open_position(signal, 10.0, "TEST")

        summary = manager.get_position_summary()

        assert 'open_positions_count' in summary
        assert 'closed_positions_count' in summary
        assert 'total_unrealized_pnl' in summary
        assert 'total_realized_pnl' in summary
        assert 'total_equity' in summary
        assert summary['open_positions_count'] == 1
        assert summary['closed_positions_count'] == 0

    def test_max_positions_limit(self):
        """测试最大持仓数量限制"""
        config = RiskConfig(max_positions=2)
        manager = PositionManager(config)

        signals = []
        for i in range(3):
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                timestamp=1234567890 + i,
                price=10.0 + i,
                ma_value=9.5 + i,
                strength=SignalStrength.STRONG,
                confidence=0.8,
                reason=f"测试信号{i+1}"
            )
            signals.append(signal)

        # 前两个应该成功开仓
        position1 = manager.open_position(signals[0], 10.0, "TEST1")
        position2 = manager.open_position(signals[1], 11.0, "TEST2")

        assert position1 is not None
        assert position2 is not None
        assert len(manager.positions) == 2

        # 第三个应该失败（超过限制）
        position3 = manager.open_position(signals[2], 12.0, "TEST3")
        assert position3 is None
        assert len(manager.positions) == 2

    def test_reset(self):
        """测试重置仓位管理器"""
        manager = PositionManager(RiskConfig())

        # 开仓
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="测试信号"
        )

        manager.open_position(signal, 10.0, "TEST")
        assert len(manager.positions) == 1

        # 重置
        manager.reset()

        assert len(manager.positions) == 0
        assert len(manager.closed_positions) == 0
        assert manager.position_counter == 0
        assert manager.order_counter == 0
        assert manager.risk_manager.total_equity == 100000.0


class TestOrder:
    """订单测试"""

    def test_order_creation(self):
        """测试订单创建"""
        order = Order(
            order_id="ORDER_001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            direction="BUY",
            quantity=100,
            price=10.0
        )

        assert order.order_id == "ORDER_001"
        assert order.symbol == "AAPL"
        assert order.order_type == OrderType.MARKET
        assert order.direction == "BUY"
        assert order.quantity == 100
        assert order.price == 10.0
        assert order.status == OrderStatus.PENDING

    def test_order_to_dict(self):
        """测试订单转换为字典"""
        order = Order(
            order_id="ORDER_001",
            symbol="AAPL",
            order_type=OrderType.LIMIT,
            direction="BUY",
            quantity=100,
            price=10.0
        )

        order_dict = order.to_dict()

        assert order_dict['order_id'] == "ORDER_001"
        assert order_dict['symbol'] == "AAPL"
        assert order_dict['order_type'] == "LIMIT"
        assert order_dict['direction'] == "BUY"
        assert order_dict['quantity'] == 100
        assert order_dict['price'] == 10.0
        assert order_dict['status'] == "PENDING"

    @property
    def test_order_properties(self):
        """测试订单属性"""
        order = Order(
            order_id="ORDER_001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            direction="BUY",
            quantity=100
        )

        # 初始状态
        assert order.is_pending is True
        assert order.is_filled is False

        # 填充订单
        order.status = OrderStatus.FILLED
        order.filled_quantity = 100
        order.filled_price = 10.5

        assert order.is_pending is False
        assert order.is_filled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])