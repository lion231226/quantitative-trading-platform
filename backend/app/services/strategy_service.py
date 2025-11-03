"""
策略服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import numpy as np

logger = structlog.get_logger()

class StrategyService:
    """策略服务类"""

    def __init__(self):
        """初始化策略服务"""
        pass

    async def run_strategy(self, symbol: str, price_data: List[Dict[str, Any]], strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行策略"""
        try:
            strategy_name = strategy_config.get("name", "SMA")
            params = strategy_config.get("params", {})

            if strategy_name == "SMA":
                return await self._run_sma_strategy(price_data, params)
            elif strategy_name == "DMA":
                return await self._run_dma_strategy(price_data, params)
            elif strategy_name == "RSI":
                return await self._run_rsi_strategy(price_data, params)
            else:
                raise ValueError(f"不支持的策略类型: {strategy_name}")

        except Exception as e:
            logger.error("策略运行失败", symbol=symbol, strategy=strategy_name, error=str(e))
            raise

    async def _run_sma_strategy(self, price_data: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """运行单均线策略"""
        window = params.get("window", 20)

        if len(price_data) < window + 1:
            return {"trades": [], "equity": [], "signals": []}

        # 计算均线
        closes = [item["close"] for item in price_data]
        sma_values = []

        for i in range(window):
            sma_values.append(None)

        for i in range(window, len(closes)):
            sma = sum(closes[i-window+1:i+1]) / window
            sma_values.append(sma)

        # 生成交易信号
        trades = []
        signals = []
        position = 0  # 0: 空仓, 1: 多头
        entry_price = 0

        for i in range(window, len(price_data)):
            current_price = closes[i]
            current_sma = sma_values[i]
            prev_sma = sma_values[i-1] if i-1 >= 0 else None

            signal = "HOLD"
            # 金叉买入信号
            if prev_sma is not None and current_price > current_sma and closes[i-1] <= prev_sma and position == 0:
                position = 1
                entry_price = current_price
                signal = "BUY"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "BUY",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001
                })

            # 死叉卖出信号
            elif prev_sma is not None and current_price < current_sma and closes[i-1] >= prev_sma and position == 1:
                position = 0
                pnl = (current_price - entry_price) / entry_price
                signal = "SELL"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "SELL",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001,
                    "pnl": pnl * (1 - 0.002)  # 扣除手续费
                })

            signals.append({
                "date": price_data[i]["date"],
                "signal": signal,
                "price": current_price,
                "indicator": current_sma
            })

        # 计算权益曲线
        equity = []
        current_equity = 100000  # 初始资金

        for i in range(len(price_data)):
            if i < window:
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,
                    "returns": 0
                })
            else:
                # 计算当日盈亏
                daily_pnl = 0
                for trade in trades:
                    if trade["date"] == price_data[i]["date"] and "pnl" in trade:
                        daily_pnl += trade["pnl"] * current_equity

                current_equity += daily_pnl
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,  # 简化处理
                    "returns": daily_pnl / (current_equity - daily_pnl) if current_equity != daily_pnl else 0
                })

        return {
            "trades": trades,
            "equity": equity,
            "signals": signals
        }

    async def _run_dma_strategy(self, price_data: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """运行双均线策略"""
        short_window = params.get("short_window", 5)
        long_window = params.get("long_window", 20)

        if len(price_data) < long_window + 1:
            return {"trades": [], "equity": [], "signals": []}

        # 计算短期和长期均线
        closes = [item["close"] for item in price_data]
        short_sma = []
        long_sma = []

        for i in range(len(closes)):
            if i < short_window - 1:
                short_sma.append(None)
            else:
                short_avg = sum(closes[i-short_window+1:i+1]) / short_window
                short_sma.append(short_avg)

            if i < long_window - 1:
                long_sma.append(None)
            else:
                long_avg = sum(closes[i-long_window+1:i+1]) / long_window
                long_sma.append(long_avg)

        # 生成交易信号（类似SMA策略，但使用双均线交叉）
        trades = []
        signals = []
        position = 0
        entry_price = 0

        for i in range(long_window, len(price_data)):
            current_price = closes[i]
            current_short = short_sma[i]
            current_long = long_sma[i]
            prev_short = short_sma[i-1] if i-1 >= 0 else None
            prev_long = long_sma[i-1] if i-1 >= 0 else None

            signal = "HOLD"

            # 短线上穿长线（金叉）
            if (prev_short is not None and prev_long is not None and
                current_short > current_long and prev_short <= prev_long and position == 0):
                position = 1
                entry_price = current_price
                signal = "BUY"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "BUY",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001
                })

            # 短线下穿长线（死叉）
            elif (prev_short is not None and prev_long is not None and
                  current_short < current_long and prev_short >= prev_long and position == 1):
                position = 0
                pnl = (current_price - entry_price) / entry_price
                signal = "SELL"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "SELL",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001,
                    "pnl": pnl * (1 - 0.002)
                })

            signals.append({
                "date": price_data[i]["date"],
                "signal": signal,
                "price": current_price,
                "indicator": f"短期:{current_short:.2f}, 长期:{current_long:.2f}"
            })

        # 计算权益曲线（与SMA策略相同）
        equity = []
        current_equity = 100000

        for i in range(len(price_data)):
            if i < long_window:
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,
                    "returns": 0
                })
            else:
                daily_pnl = 0
                for trade in trades:
                    if trade["date"] == price_data[i]["date"] and "pnl" in trade:
                        daily_pnl += trade["pnl"] * current_equity

                current_equity += daily_pnl
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,
                    "returns": daily_pnl / (current_equity - daily_pnl) if current_equity != daily_pnl else 0
                })

        return {
            "trades": trades,
            "equity": equity,
            "signals": signals
        }

    async def _run_rsi_strategy(self, price_data: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """运行RSI策略"""
        rsi_period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)

        if len(price_data) < rsi_period + 1:
            return {"trades": [], "equity": [], "signals": []}

        # 计算RSI
        closes = [item["close"] for item in price_data]
        rsi_values = []

        for i in range(rsi_period):
            rsi_values.append(None)

        for i in range(rsi_period, len(closes)):
            gains = []
            losses = []

            for j in range(i - rsi_period + 1, i + 1):
                change = closes[j] - closes[j-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))

            avg_gain = sum(gains) / rsi_period if gains else 0
            avg_loss = sum(losses) / rsi_period if losses else 0

            rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        # 生成交易信号
        trades = []
        signals = []
        position = 0
        entry_price = 0

        for i in range(rsi_period, len(price_data)):
            current_price = closes[i]
            current_rsi = rsi_values[i]

            signal = "HOLD"

            # RSI超卖买入
            if current_rsi < oversold and position == 0:
                position = 1
                entry_price = current_price
                signal = "BUY"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "BUY",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001
                })

            # RSI超买卖出
            elif current_rsi > overbought and position == 1:
                position = 0
                pnl = (current_price - entry_price) / entry_price
                signal = "SELL"
                trades.append({
                    "date": price_data[i]["date"],
                    "type": "SELL",
                    "price": current_price,
                    "quantity": 1,
                    "amount": current_price,
                    "commission": current_price * 0.001,
                    "pnl": pnl * (1 - 0.002)
                })

            signals.append({
                "date": price_data[i]["date"],
                "signal": signal,
                "price": current_price,
                "indicator": current_rsi
            })

        # 计算权益曲线
        equity = []
        current_equity = 100000

        for i in range(len(price_data)):
            if i < rsi_period:
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,
                    "returns": 0
                })
            else:
                daily_pnl = 0
                for trade in trades:
                    if trade["date"] == price_data[i]["date"] and "pnl" in trade:
                        daily_pnl += trade["pnl"] * current_equity

                current_equity += daily_pnl
                equity.append({
                    "date": price_data[i]["date"],
                    "equity": current_equity,
                    "drawdown": 0,
                    "returns": daily_pnl / (current_equity - daily_pnl) if current_equity != daily_pnl else 0
                })

        return {
            "trades": trades,
            "equity": equity,
            "signals": signals
        }