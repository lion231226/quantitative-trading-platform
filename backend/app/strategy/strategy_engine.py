"""
策略执行引擎
整合移动平均线计算、信号生成和交易执行的核心引擎
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import pandas as pd
import numpy as np
import structlog

from .indicators import MovingAverageCalculator, MAType
from .signals import SignalGenerator, SignalConfig, TradingSignal, SignalType
from .trading import PositionManager, RiskConfig, Position
from .config import StrategyConfig

# Strategy execution engine
logger = structlog.get_logger()


class EngineState(Enum):
    """引擎状态"""
    STOPPED = "STOPPED"          # 已停止
    RUNNING = "RUNNING"          # 运行中
    PAUSED = "PAUSED"            # 已暂停
    ERROR = "ERROR"              # 错误状态


class MarketDataUpdate:
    """市场数据更新"""
    def __init__(self, symbol: str, price: float, timestamp: int,
                 volume: Optional[float] = None, metadata: Optional[Dict] = None) -> Any:
        self.symbol = symbol
        self.price = price
        self.timestamp = timestamp
        self.volume = volume
        self.metadata = metadata or {}


@dataclass
class StrategyState:
    """策略状态"""
    current_positions: List[Position] = field(default_factory=list)
    last_signal: Optional[TradingSignal] = None
    last_update_time: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    equity_curve: List[Tuple[int, float]] = field(default_factory=list)

    def update_position_summary(self, position_manager: PositionManager) -> Any:
        """更新持仓摘要"""
        summary = position_manager.get_position_summary()
        self.total_trades = summary['closed_positions_count']
        self.total_pnl = summary['net_pnl']
        self.max_drawdown = summary['current_drawdown']
        self.current_positions = position_manager.get_open_positions()

        # 更新胜负统计
        closed_positions = position_manager.closed_positions
        self.winning_trades = sum(1 for p in closed_positions if p.realized_pnl > 0)
        self.losing_trades = sum(1 for p in closed_positions if p.realized_pnl < 0)

    def add_equity_point(self, timestamp: int, equity: float) -> Any:
        """添加权益曲线点"""
        self.equity_curve.append((timestamp, equity))
        # 限制权益曲线长度，避免内存过大
        if len(self.equity_curve) > 10000:
            self.equity_curve = self.equity_curve[-5000:]


class StrategyEngine:
    """策略执行引擎"""

    def __init__(self, config: StrategyConfig) -> Any:
        """
        初始化策略引擎

        Args:
            config: 策略配置
        """
        # 验证配置
        is_valid, errors = config.validate()
        if not is_valid:
            raise ValueError(f"策略配置无效: {', '.join(errors)}")

        self.config = config
        self.state = EngineState.STOPPED
        self.strategy_state = StrategyState()

        # 初始化组件
        self.ma_calculator = MovingAverageCalculator()
        self.signal_generator: Optional[SignalGenerator] = None
        self.position_manager: Optional[PositionManager] = None

        # 数据存储
        self.price_history: Dict[str, List[float]] = {}
        self.timestamp_history: Dict[str, List[int]] = {}
        self.volume_history: Dict[str, List[float]] = {}

        # 运行控制
        self._running = False
        self._pause_requested = False
        self._stop_requested = False

        # 初始化引擎
        self._initialize_engine()

    def _initialize_engine(self) -> Any:
        """初始化引擎组件"""
        try:
            # 创建信号生成器
            signal_config = self._create_signal_config()
            self.signal_generator = SignalGenerator(signal_config)

            # 创建仓位管理器
            risk_config = self._create_risk_config()
            self.position_manager = PositionManager(risk_config)

            # 创建移动平均线指标
            self._setup_moving_averages()

            logger.info("策略引擎初始化成功",
                       strategy_name=self.config.strategy_name,
                       strategy_type=self.config.strategy_type.value)

        except Exception as e:
            logger.error("策略引擎初始化失败", error=str(e))
            self.state = EngineState.ERROR
            raise

    def _create_signal_config(self) -> SignalConfig:
        """从策略配置创建信号配置"""
        ma_config = self.config.ma_configs[0] if self.config.ma_configs else None
        if not ma_config:
            raise ValueError("至少需要配置一个移动平均线")

        signal_cfg = self.config.signal_config
        return SignalConfig(
            ma_type=ma_config.ma_type,
            ma_period=ma_config.period,
            min_cross_percentage=signal_cfg.min_cross_percentage,
            confirmation_periods=signal_cfg.confirmation_periods,
            volume_threshold=signal_cfg.volume_threshold,
            min_price_change=signal_cfg.min_price_change,
            max_signals_per_day=signal_cfg.max_signals_per_day,
            signal_cooldown=signal_cfg.signal_cooldown,
            max_position_size=signal_cfg.max_position_size,
            stop_loss_pct=signal_cfg.stop_loss_pct,
            take_profit_pct=signal_cfg.take_profit_pct
        )

    def _create_risk_config(self) -> RiskConfig:
        """从策略配置创建风险管理配置"""
        risk_cfg = self.config.risk_config
        return RiskConfig(
            max_position_size=risk_cfg.max_position_size,
            max_positions=risk_cfg.max_positions,
            stop_loss_pct=risk_cfg.stop_loss_pct,
            take_profit_pct=risk_cfg.take_profit_pct,
            max_drawdown_pct=risk_cfg.max_drawdown_pct,
            max_loss_per_trade=risk_cfg.max_loss_per_trade,
            commission_rate=risk_cfg.commission_rate,
            slippage_rate=risk_cfg.slippage_rate
        )

    def _setup_moving_averages(self) -> Any:
        """设置移动平均线指标"""
        for ma_config in self.config.ma_configs:
            if ma_config.enabled:
                self.ma_calculator.create_indicator(
                    ma_type=ma_config.ma_type,
                    period=ma_config.period,
                    name=f"{ma_config.ma_type.value}_{ma_config.period}"
                )

    async def start(self, symbols: List[str]) -> bool:
        """
        启动策略引擎

        Args:
            symbols: 交易标的列表

        Returns:
            是否启动成功
        """
        if self.state == EngineState.RUNNING:
            logger.warning("策略引擎已在运行中")
            return True

        try:
            self._running = True
            self._pause_requested = False
            self._stop_requested = False
            self.state = EngineState.RUNNING

            logger.info("策略引擎启动", symbols=symbols)
            return True

        except Exception as e:
            logger.error("策略引擎启动失败", error=str(e))
            self.state = EngineState.ERROR
            return False

    async def stop(self) -> Any:
        """停止策略引擎"""
        if self.state != EngineState.RUNNING and self.state != EngineState.PAUSED:
            return

        self._stop_requested = True
        self._running = False
        self.state = EngineState.STOPPED

        logger.info("策略引擎已停止")

    async def pause(self) -> Any:
        """暂停策略引擎"""
        if self.state != EngineState.RUNNING:
            return

        self._pause_requested = True
        self.state = EngineState.PAUSED

        logger.info("策略引擎已暂停")

    async def resume(self) -> Any:
        """恢复策略引擎"""
        if self.state != EngineState.PAUSED:
            return

        self._pause_requested = False
        self.state = EngineState.RUNNING

        logger.info("策略引擎已恢复")

    def process_market_data(self, market_data: MarketDataUpdate) -> List[Position]:
        """
        处理市场数据更新

        Args:
            market_data: 市场数据更新

        Returns:
            新开仓的持仓列表
        """
        if self.state != EngineState.RUNNING or not self._running:
            return []

        try:
            # 更新历史数据
            self._update_price_history(market_data)

            # 更新现有持仓
            if self.position_manager:
                current_prices = {market_data.symbol: market_data.price}
                self.position_manager.update_positions(current_prices)

                # 检查风险条件并执行平仓
                close_signals = self.position_manager.check_risk_conditions(current_prices)
                new_positions = []
                for position_id in close_signals:
                    closed_position = self.position_manager.close_position(
                        position_id, market_data.price, "risk_management"
                    )
                    if closed_position:
                        logger.info("风险触发平仓",
                                  position_id=position_id,
                                  price=market_data.price,
                                  reason="risk_management")

            # 生成交易信号
            signals = self._generate_signals(market_data.symbol)

            # 执行交易信号
            new_positions = []
            if signals and self.position_manager:
                for signal in signals:
                    position = self.position_manager.open_position(
                        signal, market_data.price, market_data.symbol
                    )
                    if position:
                        new_positions.append(position)
                        self.strategy_state.last_signal = signal
                        logger.info("执行交易信号",
                                   signal_type=signal.signal_type.value,
                                   price=market_data.price,
                                   position_id=position.position_id)

            # 更新策略状态
            self._update_strategy_state()

            return new_positions

        except Exception as e:
            logger.error("处理市场数据时发生错误", error=str(e))
            self.state = EngineState.ERROR
            return []

    def _update_price_history(self, market_data: MarketDataUpdate) -> Any:
        """更新价格历史数据"""
        symbol = market_data.symbol

        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.timestamp_history[symbol] = []
            self.volume_history[symbol] = []

        # 添加新数据
        self.price_history[symbol].append(market_data.price)
        self.timestamp_history[symbol].append(market_data.timestamp)
        self.volume_history[symbol].append(market_data.volume or 0.0)

        # 限制历史数据长度，避免内存过大
        max_history = 1000
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
            self.timestamp_history[symbol] = self.timestamp_history[symbol][-max_history:]
            self.volume_history[symbol] = self.volume_history[symbol][-max_history:]

    def _generate_signals(self, symbol: str) -> List[TradingSignal]:
        """生成交易信号"""
        if not self.signal_generator or symbol not in self.price_history:
            return []

        prices = self.price_history[symbol]
        timestamps = self.timestamp_history[symbol]
        volumes = self.volume_history[symbol]

        if len(prices) < self.config.ma_configs[0].period:
            return []

        try:
            signals = self.signal_generator.generate_signals_from_data(
                prices, timestamps, volumes
            )
            return signals

        except Exception as e:
            logger.error("生成交易信号失败", error=str(e), symbol=symbol)
            return []

    def _update_strategy_state(self) -> Any:
        """更新策略状态"""
        if self.position_manager:
            self.strategy_state.update_position_summary(self.position_manager)

            # 添加权益曲线点
            current_equity = self.position_manager.risk_manager.total_equity
            current_time = int(datetime.now(tz=timezone.utc).timestamp())
            self.strategy_state.add_equity_point(current_time, current_equity)

        self.strategy_state.last_update_time = int(datetime.now(tz=timezone.utc).timestamp())

    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        if not self.position_manager:
            return {"state": self.state.value, "initialized": False}

        position_summary = self.position_manager.get_position_summary()

        return {
            "state": self.state.value,
            "initialized": True,
            "strategy_name": self.config.strategy_name,
            "strategy_type": self.config.strategy_type.value,
            "last_update_time": self.strategy_state.last_update_time,
            "position_summary": position_summary,
            "last_signal": self.strategy_state.last_signal.to_dict() if self.strategy_state.last_signal else None,
            "total_trades": self.strategy_state.total_trades,
            "winning_trades": self.strategy_state.winning_trades,
            "losing_trades": self.strategy_state.losing_trades,
            "win_rate": (self.strategy_state.winning_trades / max(self.strategy_state.total_trades, 1)) * 100,
            "total_pnl": self.strategy_state.total_pnl,
            "max_drawdown": self.strategy_state.max_drawdown,
            "equity_curve_length": len(self.strategy_state.equity_curve)
        }

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """获取开放持仓"""
        if not self.position_manager:
            return []
        return self.position_manager.get_open_positions(symbol)

    def get_equity_curve(self) -> List[Tuple[int, float]]:
        """获取权益曲线"""
        return self.strategy_state.equity_curve.copy()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.position_manager or len(self.strategy_state.equity_curve) < 2:
            return {}

        # 计算基本指标
        equity_curve = self.strategy_state.equity_curve
        initial_equity = equity_curve[0][1]
        current_equity = equity_curve[-1][1]
        total_return = (current_equity - initial_equity) / initial_equity

        # 计算最大回撤
        max_equity = initial_equity
        max_drawdown = 0.0
        for _, equity in equity_curve:
            if equity > max_equity:
                max_equity = equity
            drawdown = (max_equity - equity) / max_equity
            max_drawdown = max(max_drawdown, drawdown)

        # 计算夏普比率（简化版）
        returns = []
        for i in range(1, len(equity_curve)):
            period_return = (equity_curve[i][1] - equity_curve[i-1][1]) / equity_curve[i-1][1]
            returns.append(period_return)

        sharpe_ratio = 0.0
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0

        return {
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": self.strategy_state.total_trades,
            "win_rate": (self.strategy_state.winning_trades / max(self.strategy_state.total_trades, 1)) * 100,
            "profit_factor": (self.strategy_state.winning_trades / max(self.strategy_state.losing_trades, 1)),
            "current_equity": current_equity,
            "initial_equity": initial_equity
        }

    def update_config(self, new_config: StrategyConfig) -> bool:
        """更新策略配置"""
        try:
            # 验证新配置
            is_valid, errors = new_config.validate()
            if not is_valid:
                raise ValueError(f"新配置无效: {', '.join(errors)}")

            # 停止当前运行
            was_running = self.state == EngineState.RUNNING
            if was_running:
                self.stop()

            # 更新配置
            self.config = new_config

            # 重新初始化引擎
            self._initialize_engine()

            # 恢复运行
            if was_running:
                self.start([])

            logger.info("策略配置更新成功")
            return True

        except Exception as e:
            logger.error("策略配置更新失败", error=str(e))
            return False

    def reset(self) -> Any:
        """重置策略引擎"""
        # 停止引擎
        self._running = False
        self.state = EngineState.STOPPED

        # 重置组件
        if self.signal_generator:
            self.signal_generator.reset()
        if self.position_manager:
            self.position_manager.reset()

        # 清空数据
        self.price_history.clear()
        self.timestamp_history.clear()
        self.volume_history.clear()

        # 重置状态
        self.strategy_state = StrategyState()

        logger.info("策略引擎已重置")

    async def run_single_ma_strategy(self, symbol: str, start_date: str, end_date: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """运行单均线策略"""
        # 修复: 添加DataFrame转换逻辑以处理列表数据
        try:
            from ..services.market_data_service import MarketDataService
            import asyncio
            import pandas as pd

            # 获取市场数据
            market_data_service = MarketDataService()

            # 获取历史数据
            historical_data = await market_data_service.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            # 将列表数据转换为pandas DataFrame
            if isinstance(historical_data, list):
                if not historical_data:
                    raise ValueError(f"无法获取 {symbol} 的历史数据：数据为空")

                df = pd.DataFrame(historical_data)
                # 确保日期列存在并设为索引
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                historical_data = df

            # 检查historical_data是否为DataFrame且不为空
            if not isinstance(historical_data, pd.DataFrame):
                raise ValueError(f"无法获取 {symbol} 的历史数据：数据类型错误")
            if historical_data.empty:
                raise ValueError(f"无法获取 {symbol} 的历史数据：数据为空")

            # 获取参数
            ma_period = parameters.get('ma_period', 20)
            initial_capital = parameters.get('initial_capital', 100000)
            stop_loss = parameters.get('stop_loss', 0.05)

            # 计算移动平均线
            close_prices = historical_data['close'].values
            dates = historical_data.index

            # 使用SMA计算移动平均线
            from .indicators import MovingAverageCalculator, MAType
            ma_calculator = MovingAverageCalculator()

            # 生成时间戳列表
            timestamps = [(int(d.timestamp()) if hasattr(d, 'timestamp') else int(pd.Timestamp(d).timestamp()))
                         for d in dates]

            ma_result = ma_calculator.calculate_batch(
                prices=close_prices.tolist(),
                timestamps=timestamps,
                ma_type=MAType.SMA,
                period=ma_period
            )

            # 生成交易信号
            signals = []
            positions = []
            equity_curve = []
            current_position = None
            current_capital = initial_capital

            for i in range(ma_period, len(close_prices)):
                current_price = close_prices[i]
                current_ma = ma_result.values[i - ma_period]
                current_date = dates[i]

                # 生成信号
                if current_price > current_ma and not current_position:
                    # 买入信号
                    current_position = {
                        'entry_price': current_price,
                        'entry_date': current_date,
                        'quantity': current_capital / current_price,
                        'type': 'long'
                    }
                    signals.append({
                        'date': current_date,
                        'type': 'buy',
                        'price': current_price,
                        'quantity': current_position['quantity']
                    })

                elif current_price < current_ma and current_position:
                    # 卖出信号
                    exit_price = current_price
                    exit_date = current_date
                    quantity = current_position['quantity']
                    entry_price = current_position['entry_price']

                    # 计算收益
                    pnl = (exit_price - entry_price) * quantity
                    pnl_percentage = (exit_price - entry_price) / entry_price

                    # 更新资金
                    current_capital = current_capital * (1 + pnl_percentage)

                    # 记录交易
                    trade = {
                        'entry_date': current_position['entry_date'],
                        'exit_date': exit_date,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': quantity,
                        'pnl': pnl,
                        'pnl_percentage': pnl_percentage
                    }
                    positions.append(trade)

                    signals.append({
                        'date': current_date,
                        'type': 'sell',
                        'price': exit_price,
                        'quantity': quantity
                    })

                    current_position = None

                # 记录权益曲线
                if current_position:
                    unrealized_pnl = (current_price - current_position['entry_price']) * current_position['quantity']
                    equity = current_capital + unrealized_pnl
                else:
                    equity = current_capital

                equity_curve.append({
                    'date': current_date,
                    'equity': equity
                })

            # 计算性能指标
            if positions:
                total_trades = len(positions)
                winning_trades = len([p for p in positions if p['pnl'] > 0])
                losing_trades = total_trades - winning_trades
                win_rate = winning_trades / total_trades if total_trades > 0 else 0

                total_pnl = sum(p['pnl'] for p in positions)
                total_return = (current_capital - initial_capital) / initial_capital

                # 计算最大回撤
                peak_equity = initial_capital
                max_drawdown = 0
                for point in equity_curve:
                    if point['equity'] > peak_equity:
                        peak_equity = point['equity']
                    drawdown = (peak_equity - point['equity']) / peak_equity
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                # 计算夏普比率（简化版）
                if len(positions) > 1:
                    returns = [p['pnl_percentage'] for p in positions]
                    avg_return = sum(returns) / len(returns)
                    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                    sharpe_ratio = avg_return / std_return if std_return > 0 else 0
                else:
                    sharpe_ratio = 0
            else:
                total_trades = 0
                winning_trades = 0
                losing_trades = 0
                win_rate = 0
                total_pnl = 0
                total_return = 0
                max_drawdown = 0
                sharpe_ratio = 0

            result = {
                'symbol': symbol,
                'strategy_type': 'single_ma',
                'parameters': parameters,
                'performance': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'total_return': total_return,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'initial_capital': initial_capital,
                    'final_capital': current_capital
                },
                'trades': positions,
                'signals': signals,
                'equity_curve': equity_curve,
                'data_points': len(historical_data)
            }

            logger.info("单均线策略执行完成",
                       symbol=symbol,
                       trades=total_trades,
                       total_return=total_return)

            return result

        except Exception as e:
            logger.error("单均线策略执行失败", error=str(e), symbol=symbol)
            raise


# 便捷函数
def create_strategy_engine(strategy_config: StrategyConfig) -> StrategyEngine:
    """创建策略引擎"""
    return StrategyEngine(strategy_config)