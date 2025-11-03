"""
策略引擎基础模块
提供策略执行和管理的基础功能
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class StrategyEngine:
    """策略引擎基础类"""

    def __init__(self):
        """初始化策略引擎"""
        self.strategies: Dict[str, Dict[str, Any]] = {}
        logger.info("策略引擎初始化完成")

    def register_strategy(self, strategy_id: str, strategy_config: Dict[str, Any]) -> bool:
        """
        注册策略

        Args:
            strategy_id: 策略ID
            strategy_config: 策略配置

        Returns:
            注册是否成功
        """
        try:
            self.strategies[strategy_id] = {
                "config": strategy_config,
                "created_at": datetime.now(),
                "status": "registered"
            }
            logger.info("策略注册成功", strategy_id=strategy_id)
            return True
        except Exception as e:
            logger.error("策略注册失败", strategy_id=strategy_id, error=str(e))
            return False

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        获取策略信息

        Args:
            strategy_id: 策略ID

        Returns:
            策略信息或None
        """
        return self.strategies.get(strategy_id)

    def list_strategies(self) -> List[str]:
        """
        列出所有策略ID

        Returns:
            策略ID列表
        """
        return list(self.strategies.keys())

    def remove_strategy(self, strategy_id: str) -> bool:
        """
        移除策略

        Args:
            strategy_id: 策略ID

        Returns:
            移除是否成功
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            logger.info("策略移除成功", strategy_id=strategy_id)
            return True
        return False


# 创建全局策略引擎实例
_strategy_engine_instance = None

def get_strategy_engine() -> StrategyEngine:
    """获取全局策略引擎实例"""
    global _strategy_engine_instance
    if _strategy_engine_instance is None:
        _strategy_engine_instance = StrategyEngine()
    return _strategy_engine_instance