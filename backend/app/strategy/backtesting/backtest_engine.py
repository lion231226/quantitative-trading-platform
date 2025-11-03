"""
策略回测引擎
实现历史数据回测和性能分析功能
"""

from typing import List, Dict, Any, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import json
import structlog

from ..strategy_engine import StrategyEngine
from ..trading import Position, Order
from ..signals import TradingSignal
from ..config import StrategyConfig
from .backtest_config import BacktestConfig

logger = structlog.get_logger()


class BacktestState(Enum):
    """回测状态"""
    INITIALIZED = "INITIALIZED"    # 已初始化
    RUNNING = "RUNNING"           # 运行中
    COMPLETED = "COMPLETED"       # 已完成
    ERROR = "ERROR"               # 错误状态


@dataclass
class BacktestResult:
    """回测结果"""
    # 基础信息
    strategy_name: str
    start_date: str
    end_date: str
    symbols: List[str]
    initial_capital: float
    final_capital: float
    total_return: float

    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float

    # 风险指标
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 交易记录
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Tuple[int, float]] = field(default_factory=list)
    positions_history: List[Dict[str, Any]] = field(default_factory=list)
    signals_history: List[Dict[str, Any]] = field(default_factory=list)

    # 月度统计
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    annual_returns: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'symbols': self.symbols,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'monthly_returns': self.monthly_returns,
            'annual_returns': self.annual_returns
        }

    def save_to_file(self, file_path: str) -> Any:
        """保存结果到文件"""
        result_dict = self.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    symbol: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    position_type: str
    pnl: float
    pnl_percentage: float
    commission: float
    duration: int
    exit_reason: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'position_type': self.position_type,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'commission': self.commission,
            'duration': self.duration,
            'exit_reason': self.exit_reason
        }


class BacktestEngine:
    """回测引擎"""

    def __init__(self, strategy_config: StrategyConfig, backtest_config: BacktestConfig) -> Any:
        """
        初始化回测引擎

        Args:
            strategy_config: 策略配置
            backtest_config: 回测配置
        """
        # 验证配置
        strategy_valid, strategy_errors = strategy_config.validate()
        if not strategy_valid:
            raise ValueError(f"策略配置无效: {', '.join(strategy_errors)}")

        backtest_valid, backtest_errors = backtest_config.validate()
        if not backtest_valid:
            raise ValueError(f"回测配置无效: {', '.join(backtest_errors)}")

        self.strategy_config = strategy_config
        self.backtest_config = backtest_config
        self.state = BacktestState.INITIALIZED

        # 初始化组件
        self.strategy_engine = StrategyEngine(strategy_config)
        # TODO: 根据需要添加数据存储服务
        # self.data_storage = DataStorageService()

        # 回测数据
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.current_index = 0
        self.total_steps = 0

        # 回测结果
        self.result: Optional[BacktestResult] = None
        self.trade_counter = 0

        # 性能优化
        self.progress_callback = None
        self.batch_size = 1000

    async def load_data(self, data_provider: Optional[callable] = None) -> bool:
        """
        加载回测数据

        Args:
            data_provider: 数据提供函数，签名为 (symbol, start_date, end_date) -> pd.DataFrame

        Returns:
            是否加载成功
        """
        try:
            logger.info("开始加载回测数据",
                       start_date=self.backtest_config.start_date,
                       end_date=self.backtest_config.end_date,
                       symbols=self.backtest_config.symbols)

            for symbol in self.backtest_config.symbols:
                if data_provider:
                    # 使用提供的数据获取函数
                    data = data_provider(symbol, self.backtest_config.start_date, self.backtest_config.end_date)
                else:
                    # 使用示例数据生成（实际应用中应该从数据库或API获取）
                    logger.warning(f"未提供数据源，为 {symbol} 生成示例数据")
                    data = self._generate_sample_data(symbol)

                if data.empty:
                    logger.warning(f"未找到标的 {symbol} 的历史数据")
                    continue

                # 数据预处理
                data = self._preprocess_data(data)
                self.market_data[symbol] = data

                logger.info(f"加载 {symbol} 数据完成",
                           records=len(data),
                           date_range=f"{data.index[0]} to {data.index[-1]}")

            if not self.market_data:
                logger.error("没有加载到任何历史数据")
                self.state = BacktestState.ERROR
                return False

            # 计算总步数
            self.total_steps = max(len(df) for df in self.market_data.values())
            logger.info("历史数据加载完成", total_steps=self.total_steps)

            return True

        except Exception as e:
            logger.error("加载历史数据失败", error=str(e))
            self.state = BacktestState.ERROR
            return False

    def _generate_sample_data(self, symbol: str) -> pd.DataFrame:
        """生成示例数据（仅用于测试）"""
        import numpy as np
        from datetime import datetime, timedelta

        start_dt = datetime.fromisoformat(self.backtest_config.start_date)
        end_dt = datetime.fromisoformat(self.backtest_config.end_date)

        # 生成日期范围
        if self.backtest_config.data_frequency == "1d":
            dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        elif self.backtest_config.data_frequency == "1h":
            dates = pd.date_range(start=start_dt, end=end_dt, freq='H')
        else:
            dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

        # 生成随机价格数据（模拟真实的股票价格走势）
        np.random.seed(hash(symbol) % 1000)  # 基于symbol设置随机种子
        base_price = 100.0 + (hash(symbol) % 50)  # 基础价格

        returns = np.random.normal(0.0001, 0.02, len(dates))  # 日收益率
        prices = [base_price]
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1.0))  # 确保价格不会为负

        # 生成OHLCV数据
        data = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(10000, 100000, len(dates))
        }, index=dates)

        return data

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理市场数据"""
        # 确保数据按时间排序
        data = data.sort_index()

        # 处理缺失值
        data = data.ffill().bfill()

        # 添加时间戳列
        data['timestamp'] = data.index.astype(np.int64) // 10**9

        return data

    async def run_backtest(self, progress_callback=None) -> Optional[BacktestResult]:
        """
        运行回测

        Args:
            progress_callback: 进度回调函数

        Returns:
            回测结果
        """
        if self.state != BacktestState.INITIALIZED:
            logger.error("回测引擎未正确初始化")
            return None

        try:
            self.state = BacktestState.RUNNING
            self.progress_callback = progress_callback

            logger.info("开始运行回测",
                       strategy=self.strategy_config.strategy_name,
                       symbols=self.backtest_config.symbols)

            # 初始化策略引擎
            await self.strategy_engine.start(self.backtest_config.symbols)

            # 设置初始资金
            if self.strategy_engine.position_manager:
                self.strategy_engine.position_manager.risk_manager.total_equity = self.backtest_config.initial_capital
                self.strategy_engine.position_manager.risk_manager.max_equity = self.backtest_config.initial_capital

            # 记录交易历史
            trades_history = []
            positions_history = []
            signals_history = []
            equity_curve = []

            # 获取所有时间点
            all_timestamps = self._get_all_timestamps()

            # 逐步执行回测
            for i, timestamp in enumerate(all_timestamps):
                # 处理所有标的的数据
                current_prices = {}
                for symbol, data in self.market_data.items():
                    if timestamp in data.index:
                        row = data.loc[timestamp]
                        current_prices[symbol] = row['close']

                        # 创建市场数据更新
                        from ..strategy_engine import MarketDataUpdate
                        market_data = MarketDataUpdate(
                            symbol=symbol,
                            price=row['close'],
                            timestamp=int(timestamp.timestamp()),
                            volume=row['volume'],
                            metadata={'open': row['open'], 'high': row['high'], 'low': row['low']}
                        )

                        # 处理市场数据
                        new_positions = self.strategy_engine.process_market_data(market_data)

                        # 记录交易和信号
                        if self.strategy_engine.strategy_state.last_signal:
                            signals_history.append(self.strategy_engine.strategy_state.last_signal.to_dict())

                # 记录权益曲线
                if self.strategy_engine.position_manager:
                    current_equity = self.strategy_engine.position_manager.risk_manager.total_equity
                    equity_curve.append((int(timestamp.timestamp()), current_equity))

                # 进度回调
                if self.progress_callback and i % self.batch_size == 0:
                    progress = (i + 1) / len(all_timestamps)
                    self.progress_callback(progress)

            # 停止策略引擎
            await self.strategy_engine.stop()

            # 生成回测结果
            self.result = self._generate_backtest_result(
                trades_history, positions_history, signals_history, equity_curve
            )

            self.state = BacktestState.COMPLETED
            logger.info("回测完成",
                       total_return=self.result.total_return,
                       total_trades=self.result.total_trades,
                       win_rate=self.result.win_rate)

            return self.result

        except Exception as e:
            logger.error("回测执行失败", error=str(e))
            self.state = BacktestState.ERROR
            return None

    def _get_all_timestamps(self) -> List[datetime]:
        """获取所有时间戳"""
        all_timestamps = set()
        for data in self.market_data.values():
            all_timestamps.update(data.index)

        return sorted(all_timestamps)

    def _generate_backtest_result(self,
                                 trades_history: List[Dict],
                                 positions_history: List[Dict],
                                 signals_history: List[Dict],
                                 equity_curve: List[Tuple[int, float]]) -> BacktestResult:
        """生成回测结果"""
        # 获取交易记录
        closed_positions = self.strategy_engine.position_manager.closed_positions if self.strategy_engine.position_manager else []

        # 转换交易记录
        trades = []
        for i, position in enumerate(closed_positions):
            trade = TradeRecord(
                trade_id=f"TRADE_{i+1:06d}",
                symbol=position.symbol,
                entry_time=position.entry_time,
                exit_time=position.exit_time or 0,
                entry_price=position.entry_price,
                exit_price=position.exit_price or 0.0,
                quantity=position.quantity,
                position_type=position.position_type.value,
                pnl=position.realized_pnl,
                pnl_percentage=((position.exit_price or 0) - position.entry_price) / position.entry_price * 100 if position.entry_price > 0 else 0,
                commission=position.commission,
                duration=(position.exit_time or 0) - position.entry_time,
                exit_reason="strategy_signal"
            )
            trades.append(trade.to_dict())

        # 计算基础指标
        initial_capital = self.backtest_config.initial_capital
        final_capital = self.strategy_engine.position_manager.risk_manager.total_equity if self.strategy_engine.position_manager else initial_capital
        total_return = (final_capital - initial_capital) / initial_capital

        # 计算交易统计
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # 计算盈亏比
        total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # 计算风险指标
        risk_metrics = self._calculate_risk_metrics(equity_curve, initial_capital)

        # 计算时间维度收益
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        annual_returns = self._calculate_annual_returns(monthly_returns)

        return BacktestResult(
            strategy_name=self.strategy_config.strategy_name,
            start_date=self.backtest_config.start_date,
            end_date=self.backtest_config.end_date,
            symbols=self.backtest_config.symbols,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_curve,
            positions_history=positions_history,
            signals_history=signals_history,
            monthly_returns=monthly_returns,
            annual_returns=annual_returns,
            **risk_metrics
        )

    def _calculate_risk_metrics(self, equity_curve: List[Tuple[int, float]], initial_capital: float) -> Dict[str, float]:
        """计算风险指标"""
        if len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0
            }

        # 计算每日收益率
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i][1] - equity_curve[i-1][1]) / equity_curve[i-1][1]
            returns.append(daily_return)

        returns = np.array(returns)

        # 计算最大回撤
        peak = initial_capital
        max_drawdown = 0.0
        max_drawdown_duration = 0
        current_drawdown_duration = 0

        for _, equity in equity_curve:
            if equity > peak:
                peak = equity
                current_drawdown_duration = 0
            else:
                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)
                current_drawdown_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_drawdown_duration)

        # 计算夏普比率 (年化)
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # 假设252个交易日
        else:
            sharpe_ratio = 0.0

        # 计算索提诺比率 (年化)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and np.std(downside_returns) > 0:
            sortino_ratio = np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
        else:
            sortino_ratio = 0.0

        # 计算卡尔玛比率
        calmar_ratio = (equity_curve[-1][1] - initial_capital) / initial_capital / max_drawdown if max_drawdown > 0 else 0.0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio
        }

    def _calculate_monthly_returns(self, equity_curve: List[Tuple[int, float]]) -> Dict[str, float]:
        """计算月度收益"""
        monthly_returns = {}
        if len(equity_curve) < 2:
            return monthly_returns

        # 按月份分组
        monthly_data = {}
        for timestamp, equity in equity_curve:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            month_key = dt.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(equity)

        # 计算月度收益率
        for month, equities in monthly_data.items():
            if len(equities) >= 2:
                monthly_return = (equities[-1] - equities[0]) / equities[0]
                monthly_returns[month] = monthly_return

        return monthly_returns

    def _calculate_annual_returns(self, monthly_returns: Dict[str, float]) -> Dict[str, float]:
        """计算年度收益"""
        annual_returns = {}
        if not monthly_returns:
            return annual_returns

        # 按年份分组
        yearly_data = {}
        for month_key, monthly_return in monthly_returns.items():
            year = month_key.split('-')[0]
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(monthly_return)

        # 计算年度收益率 (复利计算)
        for year, returns in yearly_data.items():
            annual_return = 1.0
            for monthly_return in returns:
                annual_return *= (1 + monthly_return)
            annual_returns[year] = annual_return - 1.0

        return annual_returns

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """生成回测报告"""
        if not self.result:
            return "没有可用的回测结果"

        # 生成HTML报告
        html_report = self._generate_html_report()

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            logger.info(f"回测报告已保存到: {output_path}")

        return html_report

    def _generate_html_report(self) -> str:
        """生成HTML格式的回测报告"""
        if not self.result:
            return "<h1>没有可用的回测结果</h1>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.result.strategy_name} 回测报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                .metric-label {{ font-weight: bold; }}
                .metric-value {{ font-size: 1.2em; color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{self.result.strategy_name} 回测报告</h1>
                <p>回测期间: {self.result.start_date} 至 {self.result.end_date}</p>
                <p>交易标的: {', '.join(self.result.symbols)}</p>
            </div>

            <div class="section">
                <h2>总体表现</h2>
                <div class="metric">
                    <div class="metric-label">总收益率</div>
                    <div class="metric-value {('positive' if self.result.total_return > 0 else 'negative')}">{self.result.total_return:.2%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">最终资金</div>
                    <div class="metric-value">¥{self.result.final_capital:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">总交易次数</div>
                    <div class="metric-value">{self.result.total_trades}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">胜率</div>
                    <div class="metric-value">{self.result.win_rate:.1f}%</div>
                </div>
            </div>

            <div class="section">
                <h2>风险指标</h2>
                <div class="metric">
                    <div class="metric-label">最大回撤</div>
                    <div class="metric-value negative">{self.result.max_drawdown:.2%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">夏普比率</div>
                    <div class="metric-value">{self.result.sharpe_ratio:.3f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">索提诺比率</div>
                    <div class="metric-value">{self.result.sortino_ratio:.3f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">卡尔玛比率</div>
                    <div class="metric-value">{self.result.calmar_ratio:.3f}</div>
                </div>
            </div>

            <div class="section">
                <h2>交易记录</h2>
                <table>
                    <tr>
                        <th>交易ID</th>
                        <th>标的</th>
                        <th>开仓时间</th>
                        <th>平仓时间</th>
                        <th>开仓价格</th>
                        <th>平仓价格</th>
                        <th>数量</th>
                        <th>盈亏</th>
                        <th>盈亏比例</th>
                    </tr>
        """

        # 添加交易记录表格
        for trade in self.result.trades[:20]:  # 只显示前20笔交易
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            html += f"""
                    <tr>
                        <td>{trade['trade_id']}</td>
                        <td>{trade['symbol']}</td>
                        <td>{datetime.fromtimestamp(trade['entry_time'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{datetime.fromtimestamp(trade['exit_time'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}</td>
                        <td>¥{trade['entry_price']:.4f}</td>
                        <td>¥{trade['exit_price']:.4f}</td>
                        <td>{trade['quantity']:.2f}</td>
                        <td class="{pnl_class}">¥{trade['pnl']:.2f}</td>
                        <td class="{pnl_class}">{trade['pnl_percentage']:.2f}%</td>
                    </tr>
            """

        html += """
                </table>
            </div>
        </body>
        </html>
        """

        return html

    def get_result(self) -> Optional[BacktestResult]:
        """获取回测结果"""
        return self.result

    def reset(self) -> Any:
        """重置回测引擎"""
        self.state = BacktestState.INITIALIZED
        self.market_data.clear()
        self.current_index = 0
        self.total_steps = 0
        self.result = None
        self.trade_counter = 0
        self.progress_callback = None

        if self.strategy_engine:
            self.strategy_engine.reset()


# 便捷函数
async def run_backtest(strategy_config: StrategyConfig,
                      backtest_config: BacktestConfig,
                      data_provider: Optional[callable] = None,
                      progress_callback=None) -> Optional[BacktestResult]:
    """运行回测的便捷函数"""
    engine = BacktestEngine(strategy_config, backtest_config)

    # 加载数据
    if not await engine.load_data(data_provider):
        return None

    # 运行回测
    return await engine.run_backtest(progress_callback)