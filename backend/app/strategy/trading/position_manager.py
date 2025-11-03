"""
仓位管理器
实现开仓、平仓和风险管理功能
"""

from typing import List, Dict, Any, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import uuid
import structlog

from ..signals import TradingSignal, SignalType

logger = structlog.get_logger()


class PositionType(Enum):
    """持仓类型"""
    LONG = "LONG"      # 多头持仓
    SHORT = "SHORT"    # 空头持仓
    FLAT = "FLAT"      # 空仓


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"        # 市价单
    LIMIT = "LIMIT"          # 限价单
    STOP = "STOP"            # 止损单
    STOP_LIMIT = "STOP_LIMIT" # 止损限价单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待执行
    FILLED = "FILLED"        # 已成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"    # 已拒绝


class PositionStatus(Enum):
    """持仓状态"""
    OPEN = "OPEN"            # 开仓
    CLOSED = "CLOSED"        # 已平仓
    PARTIAL_CLOSED = "PARTIAL_CLOSED"  # 部分平仓


@dataclass
class Order:
    """订单数据结构"""
    order_id: str
    symbol: str
    order_type: OrderType
    direction: str  # "BUY" 或 "SELL"
    quantity: float
    price: Optional[float] = None  # 限价单价格
    stop_price: Optional[float] = None  # 止损价格
    status: OrderStatus = OrderStatus.PENDING
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    filled_at: Optional[int] = None
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'direction': self.direction,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'created_at': self.created_at,
            'filled_at': self.filled_at,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'commission': self.commission,
            'metadata': self.metadata
        }

    @property
    def is_filled(self) -> bool:
        """是否已成交"""
        return self.status == OrderStatus.FILLED

    @property
    def is_pending(self) -> bool:
        """是否待执行"""
        return self.status == OrderStatus.PENDING


@dataclass
class Position:
    """持仓数据结构"""
    position_id: str
    symbol: str
    position_type: PositionType
    quantity: float
    entry_price: float
    current_price: float
    entry_time: int
    status: PositionStatus = PositionStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[int] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'position_type': self.position_type.value,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'entry_time': self.entry_time,
            'status': self.status.value,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'commission': self.commission,
            'metadata': self.metadata
        }

    def update_current_price(self, new_price: float) -> Any:
        """更新当前价格并计算未实现盈亏"""
        self.current_price = new_price
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - new_price) * self.quantity

    def close_position(self, exit_price: float, exit_time: int, quantity: Optional[float] = None) -> Any:
        """平仓"""
        close_quantity = quantity or self.quantity
        if self.position_type == PositionType.LONG:
            realized_pnl = (exit_price - self.entry_price) * close_quantity
        else:  # SHORT
            realized_pnl = (self.entry_price - exit_price) * close_quantity

        self.realized_pnl += realized_pnl
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.quantity -= close_quantity

        if self.quantity <= 0:
            self.quantity = 0
            self.status = PositionStatus.CLOSED
        else:
            self.status = PositionStatus.PARTIAL_CLOSED

    @property
    def is_open(self) -> bool:
        """持仓是否开放"""
        return self.status == PositionStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """持仓是否已关闭"""
        return self.status == PositionStatus.CLOSED

    @property
    def pnl_percentage(self) -> float:
        """盈亏百分比"""
        if self.entry_price == 0:
            return 0.0
        if self.position_type == PositionType.LONG:
            return (self.current_price - self.entry_price) / self.entry_price
        else:  # SHORT
            return (self.entry_price - self.current_price) / self.entry_price


@dataclass
class RiskConfig:
    """风险管理配置"""
    max_position_size: float = 1.0          # 最大仓位（占总资金比例）
    max_positions: int = 5                  # 最大持仓数量
    stop_loss_pct: float = 0.02             # 止损百分比
    take_profit_pct: float = 0.05           # 止盈百分比
    max_drawdown_pct: float = 0.10          # 最大回撤百分比
    max_loss_per_trade: float = 0.02        # 单笔最大亏损比例
    commission_rate: float = 0.001          # 手续费率
    slippage_rate: float = 0.0001           # 滑点率

    def validate(self) -> bool:
        """验证配置参数"""
        if not 0 < self.max_position_size <= 1:
            return False
        if self.max_positions <= 0:
            return False
        if not 0 < self.stop_loss_pct < 1:
            return False
        if not 0 < self.take_profit_pct < 1:
            return False
        if not 0 < self.max_drawdown_pct < 1:
            return False
        if not 0 < self.max_loss_per_trade < 1:
            return False
        if not 0 <= self.commission_rate < 1:
            return False
        if not 0 <= self.slippage_rate < 1:
            return False
        return True


class RiskManager:
    """风险管理器"""

    def __init__(self, config: RiskConfig) -> Any:
        if not config.validate():
            raise ValueError("风险管理配置参数无效")
        self.config = config
        self.total_equity = 100000.0  # 初始资金
        self.max_equity = self.total_equity
        self.current_drawdown = 0.0

    def calculate_position_size(self,
                               signal: TradingSignal,
                               current_price: float,
                               available_equity: float) -> float:
        """
        计算建议仓位大小

        Args:
            signal: 交易信号
            current_price: 当前价格
            available_equity: 可用资金

        Returns:
            建议仓位大小（数量）
        """
        # 基于信号强度调整仓位大小
        strength_multiplier = signal.strength.value / 3.0  # 归一化到0-1
        confidence_multiplier = signal.confidence

        # 基础仓位大小
        base_position_value = available_equity * self.config.max_position_size
        adjusted_position_value = base_position_value * strength_multiplier * confidence_multiplier

        # 转换为数量
        position_quantity = adjusted_position_value / current_price

        return position_quantity

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """检查是否触发止损"""
        if position.position_type == PositionType.LONG:
            loss_pct = (position.entry_price - current_price) / position.entry_price
        else:  # SHORT
            loss_pct = (current_price - position.entry_price) / position.entry_price

        return loss_pct >= self.config.stop_loss_pct

    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """检查是否触发止盈"""
        if position.position_type == PositionType.LONG:
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:  # SHORT
            profit_pct = (position.entry_price - current_price) / position.entry_price

        return profit_pct >= self.config.take_profit_pct

    def check_max_drawdown(self) -> bool:
        """检查是否超过最大回撤限制"""
        self.current_drawdown = (self.max_equity - self.total_equity) / self.max_equity
        return self.current_drawdown >= self.config.max_drawdown_pct

    def check_position_limit(self, positions: List[Position], symbol: str) -> bool:
        """检查是否超过持仓限制"""
        open_positions = [p for p in positions if p.is_open and p.symbol == symbol]
        return len(open_positions) < self.config.max_positions

    def update_equity(self, new_equity: float) -> Any:
        """更新总资金"""
        self.total_equity = new_equity
        if self.total_equity > self.max_equity:
            self.max_equity = self.total_equity

    def calculate_commission(self, order_value: float) -> float:
        """计算手续费"""
        return order_value * self.config.commission_rate

    def apply_slippage(self, price: float, direction: str) -> float:
        """应用滑点"""
        slippage = price * self.config.slippage_rate
        if direction == "BUY":
            return price + slippage
        else:  # SELL
            return price - slippage


class PositionManager:
    """仓位管理器"""

    def __init__(self, risk_config: RiskConfig) -> Any:
        self.risk_manager = RiskManager(risk_config)
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.closed_positions: List[Position] = []
        self.position_counter = 0
        self.order_counter = 0

    def open_position(self,
                     signal: TradingSignal,
                     current_price: float,
                     symbol: str = "DEFAULT") -> Optional[Position]:
        """
        根据信号开仓

        Args:
            signal: 交易信号
            current_price: 当前价格
            symbol: 交易标的

        Returns:
            新开的持仓或None
        """
        # 检查是否可以开仓
        if not self._can_open_position(signal, symbol):
            return None

        # 计算仓位大小
        available_equity = self._calculate_available_equity()
        position_quantity = self.risk_manager.calculate_position_size(
            signal, current_price, available_equity
        )

        if position_quantity <= 0:
            logger.warning("计算得出的仓位大小为零或负数", quantity=position_quantity)
            return None

        # 确定持仓类型
        if signal.signal_type == SignalType.BUY:
            position_type = PositionType.LONG
        elif signal.signal_type == SignalType.SELL:
            position_type = PositionType.SHORT
        else:
            logger.warning("无效的开仓信号类型", signal_type=signal.signal_type)
            return None

        # 应用滑点
        entry_price = self.risk_manager.apply_slippage(current_price, signal.signal_type.value)

        # 创建持仓
        self.position_counter += 1
        position_id = f"POS_{self.position_counter:06d}"

        position = Position(
            position_id=position_id,
            symbol=symbol,
            position_type=position_type,
            quantity=position_quantity,
            entry_price=entry_price,
            current_price=entry_price,
            entry_time=signal.timestamp,
            metadata={
                'signal': signal.to_dict(),
                'commission_rate': self.risk_manager.config.commission_rate,
                'slippage_rate': self.risk_manager.config.slippage_rate
            }
        )

        # 计算手续费
        order_value = position_quantity * entry_price
        commission = self.risk_manager.calculate_commission(order_value)
        position.commission = commission

        self.positions[position_id] = position
        logger.info("开仓成功",
                   position_id=position_id,
                   symbol=symbol,
                   position_type=position_type.value,
                   quantity=position_quantity,
                   entry_price=entry_price,
                   commission=commission)

        return position

    def close_position(self,
                      position_id: str,
                      current_price: float,
                      reason: str = "manual") -> Optional[Position]:
        """
        平仓

        Args:
            position_id: 持仓ID
            current_price: 当前价格
            reason: 平仓原因

        Returns:
            已平仓的持仓或None
        """
        if position_id not in self.positions:
            logger.warning("持仓不存在", position_id=position_id)
            return None

        position = self.positions[position_id]
        if not position.is_open:
            logger.warning("持仓已经关闭", position_id=position_id)
            return position

        # 应用滑点
        if position.position_type == PositionType.LONG:
            exit_price = self.risk_manager.apply_slippage(current_price, "SELL")
        else:  # SHORT
            exit_price = self.risk_manager.apply_slippage(current_price, "BUY")

        # 平仓
        current_time = int(datetime.now(tz=timezone.utc).timestamp())
        position.close_position(exit_price, current_time)

        # 计算手续费
        order_value = position.quantity * exit_price
        commission = self.risk_manager.calculate_commission(order_value)
        position.commission += commission

        # 移动到已平仓列表
        if position.is_closed:
            self.closed_positions.append(position)
            del self.positions[position_id]

            # 更新风险管理器的资金
            net_pnl = position.realized_pnl - position.commission
            self.risk_manager.update_equity(self.risk_manager.total_equity + net_pnl)

        logger.info("平仓成功",
                   position_id=position_id,
                   exit_price=exit_price,
                   realized_pnl=position.realized_pnl,
                   commission=position.commission,
                   reason=reason)

        return position

    def update_positions(self, current_prices: Dict[str, float]) -> Any:
        """
        更新所有持仓的当前价格

        Args:
            current_prices: 当前价格字典 {symbol: price}
        """
        for position in self.positions.values():
            if position.symbol in current_prices:
                position.update_current_price(current_prices[position.symbol])

    def check_risk_conditions(self, current_prices: Dict[str, float]) -> List[str]:
        """
        检查风险条件，返回需要平仓的持仓ID列表

        Args:
            current_prices: 当前价格字典

        Returns:
            需要平仓的持仓ID列表
        """
        close_signals = []

        # 检查最大回撤
        if self.risk_manager.check_max_drawdown():
            logger.warning("触发最大回撤限制", drawdown=self.risk_manager.current_drawdown)
            # 平仓所有持仓
            close_signals.extend(list(self.positions.keys()))
            return close_signals

        # 检查各个持仓的风险条件
        for position_id, position in self.positions.items():
            if position.symbol not in current_prices:
                continue

            current_price = current_prices[position.symbol]

            # 检查止损
            if self.risk_manager.check_stop_loss(position, current_price):
                close_signals.append((position_id, "stop_loss"))
                continue

            # 检查止盈
            if self.risk_manager.check_take_profit(position, current_price):
                close_signals.append((position_id, "take_profit"))
                continue

        return [signal[0] for signal in close_signals]

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """获取开放持仓列表"""
        positions = list(self.positions.values())
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        return positions

    def get_position(self, position_id: str) -> Optional[Position]:
        """获取指定持仓"""
        return self.positions.get(position_id)

    def get_position_summary(self) -> Dict[str, Any]:
        """获取持仓摘要信息"""
        open_positions = self.get_open_positions()

        total_unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        total_realized_pnl = sum(p.realized_pnl for p in self.closed_positions)
        total_commission = sum(p.commission for p in self.positions.values()) + \
                          sum(p.commission for p in self.closed_positions)

        return {
            'open_positions_count': len(open_positions),
            'closed_positions_count': len(self.closed_positions),
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_commission': total_commission,
            'net_pnl': total_unrealized_pnl + total_realized_pnl - total_commission,
            'total_equity': self.risk_manager.total_equity,
            'current_drawdown': self.risk_manager.current_drawdown,
            'max_equity': self.risk_manager.max_equity
        }

    def _can_open_position(self, signal: TradingSignal, symbol: str) -> bool:
        """检查是否可以开仓"""
        # 检查持仓数量限制
        if not self.risk_manager.check_position_limit(self.get_open_positions(), symbol):
            logger.info("超过最大持仓数量限制", symbol=symbol)
            return False

        # 检查最大回撤
        if self.risk_manager.check_max_drawdown():
            logger.info("超过最大回撤限制，暂停开仓")
            return False

        return True

    def _calculate_available_equity(self) -> float:
        """计算可用资金"""
        total_equity = self.risk_manager.total_equity
        used_equity = sum(p.quantity * p.current_price for p in self.get_open_positions())
        return total_equity - used_equity

    def reset(self) -> Any:
        """重置仓位管理器"""
        self.positions.clear()
        self.orders.clear()
        self.closed_positions.clear()
        self.position_counter = 0
        self.order_counter = 0
        self.risk_manager.total_equity = 100000.0
        self.risk_manager.max_equity = 100000.0
        self.risk_manager.current_drawdown = 0.0