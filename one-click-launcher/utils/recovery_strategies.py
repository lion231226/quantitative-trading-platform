"""
Recovery Strategies Module

This module provides various recovery strategies including exponential backoff,
circuit breaker patterns, and intelligent retry mechanisms for automatic
error recovery operations.
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
import json

from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryStrategyEnum(Enum):
    """重试策略枚举"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    RANDOM_JITTER = "random_jitter"


class CircuitBreakerState(Enum):
    """断路器状态枚举"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 断路状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    strategy: RetryStrategyEnum = RetryStrategyEnum.EXPONENTIAL_BACKOFF
    timeout: Optional[float] = None
    retry_on: List[type] = field(default_factory=lambda: [Exception])


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception
    success_threshold: int = 2  # 半开状态下的成功阈值


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    attempts: int
    total_time: float
    result: Optional[Any] = None
    error: Optional[Exception] = None
    strategy_used: str = ""
    delays: List[float] = field(default_factory=list)


class RetryStrategy(Generic[T]):
    """重试策略基类"""

    def __init__(self, config: RetryConfig):
        """初始化重试策略"""
        self.config = config
        self._lock = threading.Lock()

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> RetryResult:
        """执行带重试的函数"""
        start_time = time.time()
        attempts = 0
        delays = []
        last_error = None

        for attempt in range(self.config.max_attempts):
            attempts = attempt + 1
            attempt_start = time.time()

            try:
                # 执行函数
                if self.config.timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
                else:
                    result = await func(*args, **kwargs)

                # 成功执行
                total_time = time.time() - start_time
                return RetryResult(
                    success=True,
                    attempts=attempts,
                    total_time=total_time,
                    result=result,
                    strategy_used=self.config.strategy.value,
                    delays=delays
                )

            except Exception as e:
                last_error = e

                # 检查是否应该重试此异常
                if not any(isinstance(e, exc_type) for exc_type in self.config.retry_on):
                    total_time = time.time() - start_time
                    return RetryResult(
                        success=False,
                        attempts=attempts,
                        total_time=total_time,
                        error=e,
                        strategy_used=self.config.strategy.value,
                        delays=delays
                    )

                # 如果不是最后一次尝试，计算延迟并等待
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    delays.append(delay)
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)

        # 所有尝试都失败
        total_time = time.time() - start_time
        return RetryResult(
            success=False,
            attempts=attempts,
            total_time=total_time,
            error=last_error,
            strategy_used=self.config.strategy.value,
            delays=delays
        )

    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.config.strategy == RetryStrategyEnum.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        elif self.config.strategy == RetryStrategyEnum.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategyEnum.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategyEnum.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        elif self.config.strategy == RetryStrategyEnum.RANDOM_JITTER:
            delay = random.uniform(self.config.base_delay, self.config.max_delay)
        else:
            delay = self.config.base_delay

        # 应用最大延迟限制
        delay = min(delay, self.config.max_delay)

        # 添加抖动
        if self.config.jitter and self.config.strategy != RetryStrategyEnum.RANDOM_JITTER:
            jitter_amount = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    def _fibonacci(self, n: int) -> int:
        """计算斐波那契数列"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


class CircuitBreaker:
    """断路器实现"""

    def __init__(self, config: CircuitBreakerConfig):
        """初始化断路器"""
        self.config = config
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        self._lock = threading.Lock()

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """通过断路器调用函数"""
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.config.recovery_timeout

    def _on_success(self):
        """处理成功调用"""
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker reset to CLOSED state")
            elif self._state == CircuitBreakerState.CLOSED:
                self._failure_count = 0

    def _on_failure(self, exception: Exception):
        """处理失败调用"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if isinstance(exception, self.config.expected_exception):
                if self._state == CircuitBreakerState.HALF_OPEN:
                    self._state = CircuitBreakerState.OPEN
                    logger.info("Circuit breaker opened due to failure in HALF_OPEN state")
                elif (self._state == CircuitBreakerState.CLOSED and
                      self._failure_count >= self.config.failure_threshold):
                    self._state = CircuitBreakerState.OPEN
                    logger.info(f"Circuit breaker opened after {self._failure_count} failures")

    def get_state(self) -> CircuitBreakerState:
        """获取断路器状态"""
        with self._lock:
            return self._state

    def get_stats(self) -> Dict[str, Any]:
        """获取断路器统计信息"""
        with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout
            }


class RetryWithCircuitBreaker(Generic[T]):
    """结合重试和断路器的策略"""

    def __init__(self, retry_config: RetryConfig, circuit_config: CircuitBreakerConfig):
        """初始化"""
        self.retry_strategy = RetryStrategy(retry_config)
        self.circuit_breaker = CircuitBreaker(circuit_config)

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> RetryResult:
        """执行带重试和断路器的函数"""
        start_time = time.time()

        try:
            # 通过断路器调用函数
            result = await self.circuit_breaker.call(func, *args, **kwargs)

            total_time = time.time() - start_time
            return RetryResult(
                success=True,
                attempts=1,
                total_time=total_time,
                result=result,
                strategy_used=f"{self.retry_strategy.config.strategy.value}+circuit_breaker"
            )

        except Exception as e:
            # 如果断路器打开，不进行重试
            if self.circuit_breaker.get_state() == CircuitBreakerState.OPEN:
                total_time = time.time() - start_time
                return RetryResult(
                    success=False,
                    attempts=1,
                    total_time=total_time,
                    error=e,
                    strategy_used="circuit_breaker_open"
                )

            # 否则使用重试策略
            return await self.retry_strategy.execute(func, *args, **kwargs)

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """获取断路器统计信息"""
        return self.circuit_breaker.get_stats()


class RecoveryStrategyManager:
    """恢复策略管理器"""

    def __init__(self):
        """初始化恢复策略管理器"""
        self.strategies: Dict[str, RetryStrategy] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.combined_strategies: Dict[str, RetryWithCircuitBreaker] = {}

    def register_retry_strategy(self, name: str, config: RetryConfig) -> RetryStrategy:
        """注册重试策略"""
        strategy = RetryStrategy(config)
        self.strategies[name] = strategy
        logger.info(f"Registered retry strategy: {name}")
        return strategy

    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """注册断路器"""
        circuit_breaker = CircuitBreaker(config)
        self.circuit_breakers[name] = circuit_breaker
        logger.info(f"Registered circuit breaker: {name}")
        return circuit_breaker

    def register_combined_strategy(
        self,
        name: str,
        retry_config: RetryConfig,
        circuit_config: CircuitBreakerConfig
    ) -> RetryWithCircuitBreaker:
        """注册组合策略"""
        combined = RetryWithCircuitBreaker(retry_config, circuit_config)
        self.combined_strategies[name] = combined
        logger.info(f"Registered combined strategy: {name}")
        return combined

    def get_retry_strategy(self, name: str) -> Optional[RetryStrategy]:
        """获取重试策略"""
        return self.strategies.get(name)

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """获取断路器"""
        return self.circuit_breakers.get(name)

    def get_combined_strategy(self, name: str) -> Optional[RetryWithCircuitBreaker]:
        """获取组合策略"""
        return self.combined_strategies.get(name)

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有策略的统计信息"""
        stats = {
            "retry_strategies": {},
            "circuit_breakers": {},
            "combined_strategies": {}
        }

        for name, strategy in self.strategies.items():
            stats["retry_strategies"][name] = {
                "config": {
                    "max_attempts": strategy.config.max_attempts,
                    "base_delay": strategy.config.base_delay,
                    "max_delay": strategy.config.max_delay,
                    "strategy": strategy.config.strategy.value
                }
            }

        for name, circuit_breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = circuit_breaker.get_stats()

        for name, combined in self.combined_strategies.items():
            stats["combined_strategies"][name] = {
                "retry_config": {
                    "max_attempts": combined.retry_strategy.config.max_attempts,
                    "strategy": combined.retry_strategy.config.strategy.value
                },
                "circuit_breaker": combined.get_circuit_breaker_stats()
            }

        return stats

    def create_default_configs(self) -> Dict[str, Any]:
        """创建默认配置"""
        return {
            "service_restart": {
                "retry_config": RetryConfig(
                    max_attempts=3,
                    base_delay=2.0,
                    max_delay=60.0,
                    backoff_multiplier=2.0,
                    jitter=True,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
                ),
                "circuit_config": CircuitBreakerConfig(
                    failure_threshold=5,
                    recovery_timeout=300.0,  # 5分钟
                    expected_exception=Exception
                )
            },
            "port_resolution": {
                "retry_config": RetryConfig(
                    max_attempts=2,
                    base_delay=1.0,
                    max_delay=30.0,
                    backoff_multiplier=1.5,
                    jitter=True,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
                ),
                "circuit_config": CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=180.0,  # 3分钟
                    expected_exception=Exception
                )
            },
            "permission_fix": {
                "retry_config": RetryConfig(
                    max_attempts=2,
                    base_delay=1.0,
                    max_delay=15.0,
                    backoff_multiplier=1.5,
                    jitter=False,
                    strategy=RetryStrategy.FIXED_DELAY
                ),
                "circuit_config": CircuitBreakerConfig(
                    failure_threshold=2,
                    recovery_timeout=120.0,  # 2分钟
                    expected_exception=PermissionError
                )
            },
            "dependency_install": {
                "retry_config": RetryConfig(
                    max_attempts=3,
                    base_delay=5.0,
                    max_delay=120.0,
                    backoff_multiplier=2.0,
                    jitter=True,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
                ),
                "circuit_config": CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=600.0,  # 10分钟
                    expected_exception=Exception
                )
            }
        }


# 预定义的常用配置
DEFAULT_RETRY_CONFIGS = {
    "conservative": RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=1.5,
        jitter=True,
        strategy=RetryStrategyEnum.EXPONENTIAL_BACKOFF
    ),
    "aggressive": RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        backoff_multiplier=2.0,
        jitter=True,
        strategy=RetryStrategyEnum.EXPONENTIAL_BACKOFF
    ),
    "gentle": RetryConfig(
        max_attempts=2,
        base_delay=2.0,
        max_delay=15.0,
        backoff_multiplier=1.2,
        jitter=False,
        strategy=RetryStrategyEnum.LINEAR_BACKOFF
    ),
    "fast": RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=5.0,
        backoff_multiplier=1.0,
        jitter=False,
        strategy=RetryStrategyEnum.FIXED_DELAY
    )
}

DEFAULT_CIRCUIT_CONFIGS = {
    "sensitive": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        expected_exception=Exception
    ),
    "normal": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=120.0,
        expected_exception=Exception
    ),
    "resilient": CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=300.0,
        expected_exception=Exception
    )
}