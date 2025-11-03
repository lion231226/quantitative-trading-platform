import redis
import json
import pickle
from typing import List, Optional, Dict, Any, Any
from datetime import datetime, date, timedelta
import asyncio
import structlog
from app.schemas.market_data import MarketDataResponse, SymbolResponse
from app.utils.errors import APIError, ValidationError
import hashlib
from app.core.config import settings

logger = structlog.get_logger()

class CacheService:
    """Redis缓存服务"""

    def __init__(self) -> Any:
        self.redis_config = {
            'host': getattr(settings, 'REDIS_HOST', 'localhost'),
            'port': getattr(settings, 'REDIS_PORT', 6379),
            'db': getattr(settings, 'REDIS_DB', 0),
            'decode_responses': False,  # 使用二进制模式以支持pickle
            'socket_connect_timeout': getattr(settings, 'REDIS_SOCKET_TIMEOUT', 5),
            'socket_timeout': getattr(settings, 'REDIS_SOCKET_TIMEOUT', 5),
            'retry_on_timeout': True
        }

        # 缓存TTL配置
        self.default_market_data_ttl = getattr(settings, 'CACHE_MARKET_DATA_TTL', 86400)  # 24小时
        self.default_symbols_ttl = getattr(settings, 'CACHE_SYMBOLS_TTL', 3600)  # 1小时

        try:
            # Redis连接配置
            self.redis_client = redis.Redis(**self.redis_config)
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis连接成功", **self.redis_config)
        except Exception as e:
            logger.error("Redis连接失败", error=str(e), **self.redis_config)
            # 如果Redis不可用，使用内存缓存作为后备
            self.redis_client = None
            self._memory_cache = {}
            logger.warning("使用内存缓存作为后备方案")

    def _generate_cache_key(self, symbol: str, start_date: date, end_date: date) -> str:
        """生成缓存键"""
        # 使用MD5确保键的唯一性和固定长度
        key_data = f"market_data:{symbol}:{start_date}:{end_date}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _generate_symbols_cache_key(self, sector: Optional[str] = None) -> str:
        """生成品种列表缓存键"""
        if sector:
            return f"symbols:{sector}"
        return "symbols:all"

    async def get_market_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Optional[List[MarketDataResponse]]:
        """从缓存获取市场数据"""
        try:
            cache_key = self._generate_cache_key(symbol, start_date, end_date)

            if self.redis_client:
                # 使用Redis缓存
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # 使用pickle反序列化
                    data = pickle.loads(cached_data)
                    logger.info("从Redis缓存获取数据", symbol=symbol, count=len(data))
                    return data
            else:
                # 使用内存缓存
                if cache_key in self._memory_cache:
                    cached_item = self._memory_cache[cache_key]
                    if datetime.now() < cached_item['expiry']:
                        logger.info("从内存缓存获取数据", symbol=symbol, count=len(cached_item['data']))
                        return cached_item['data']
                    else:
                        # 缓存过期，删除
                        del self._memory_cache[cache_key]

            return None

        except Exception as e:
            logger.error("从缓存获取数据失败", error=str(e), symbol=symbol)
            return None

    async def set_market_data(
        self,
        symbol: str,
        data: List[MarketDataResponse],
        ttl: Optional[int] = None  # 使用配置的默认TTL
    ) -> bool:
        """将市场数据存入缓存"""
        try:
            if not data:
                return True

            # 使用配置的默认TTL
            if ttl is None:
                ttl = self.default_market_data_ttl

            # 从数据中获取日期范围
            dates = [item.date.date() if isinstance(item.date, datetime) else item.date for item in data]
            start_date = min(dates)
            end_date = max(dates)

            cache_key = self._generate_cache_key(symbol, start_date, end_date)

            if self.redis_client:
                # 使用Redis缓存
                serialized_data = pickle.dumps(data)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                logger.info("数据已存入Redis缓存", symbol=symbol, count=len(data), ttl=ttl)
            else:
                # 使用内存缓存
                expiry = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[cache_key] = {
                    'data': data,
                    'expiry': expiry
                }
                logger.info("数据已存入内存缓存", symbol=symbol, count=len(data), ttl=ttl)

            return True

        except Exception as e:
            logger.error("存入缓存失败", error=str(e), symbol=symbol)
            return False

    async def get_symbols(self, sector: Optional[str] = None) -> Optional[List[SymbolResponse]]:
        """从缓存获取品种列表"""
        try:
            cache_key = self._generate_symbols_cache_key(sector)

            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = pickle.loads(cached_data)
                    logger.info("从Redis缓存获取品种列表", sector=sector, count=len(data))
                    return data
            else:
                if cache_key in self._memory_cache:
                    cached_item = self._memory_cache[cache_key]
                    if datetime.now() < cached_item['expiry']:
                        logger.info("从内存缓存获取品种列表", sector=sector, count=len(cached_item['data']))
                        return cached_item['data']
                    else:
                        del self._memory_cache[cache_key]

            return None

        except Exception as e:
            logger.error("从缓存获取品种列表失败", error=str(e), sector=sector)
            return None

    async def set_symbols(
        self,
        symbols: List[SymbolResponse],
        sector: Optional[str] = None,
        ttl: Optional[int] = None  # 使用配置的默认TTL
    ) -> bool:
        """将品种列表存入缓存"""
        try:
            # 使用配置的默认TTL
            if ttl is None:
                ttl = self.default_symbols_ttl

            cache_key = self._generate_symbols_cache_key(sector)

            if self.redis_client:
                serialized_data = pickle.dumps(symbols)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                logger.info("品种列表已存入Redis缓存", sector=sector, count=len(symbols), ttl=ttl)
            else:
                expiry = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[cache_key] = {
                    'data': symbols,
                    'expiry': expiry
                }
                logger.info("品种列表已存入内存缓存", sector=sector, count=len(symbols), ttl=ttl)

            return True

        except Exception as e:
            logger.error("存入品种列表缓存失败", error=str(e), sector=sector)
            return False

    async def delete_market_data(self, symbol: str) -> bool:
        """删除指定品种的缓存数据"""
        try:
            deleted_count = 0

            if self.redis_client:
                # 使用模式匹配删除所有相关缓存
                pattern = f"*{symbol}*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted_count = self.redis_client.delete(*keys)
                    logger.info("已删除Redis缓存数据", symbol=symbol, count=deleted_count)
            else:
                # 删除内存缓存中的相关数据
                keys_to_delete = []
                for key in self._memory_cache.keys():
                    if symbol in key:
                        keys_to_delete.append(key)

                for key in keys_to_delete:
                    del self._memory_cache[key]
                deleted_count = len(keys_to_delete)
                logger.info("已删除内存缓存数据", symbol=symbol, count=deleted_count)

            return deleted_count > 0

        except Exception as e:
            logger.error("删除缓存数据失败", error=str(e), symbol=symbol)
            return False

    async def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
                logger.info("已清空Redis缓存")
            else:
                self._memory_cache.clear()
                logger.info("已清空内存缓存")

            return True

        except Exception as e:
            logger.error("清空缓存失败", error=str(e))
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                'cache_type': 'redis' if self.redis_client else 'memory',
                'timestamp': datetime.now().isoformat()
            }

            if self.redis_client:
                info = self.redis_client.info()
                stats.update({
                    'total_keys': self.redis_client.dbsize(),
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0)
                })
            else:
                stats.update({
                    'total_keys': len(self._memory_cache),
                    'used_memory': 'N/A',  # 内存缓存暂不统计
                    'connected_clients': 0,
                    'uptime_in_seconds': 0
                })

            return stats

        except Exception as e:
            logger.error("获取缓存统计失败", error=str(e))
            return {
                'cache_type': 'unknown',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def cache_warm_up(self, symbols: List[str], days: int = 30) -> Dict[str, bool]:
        """缓存预热 - 为指定品种预加载最近N天的数据"""
        try:
            results = {}
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            for symbol in symbols:
                try:
                    # 检查是否已有缓存
                    cached_data = await self.get_market_data(symbol, start_date, end_date)
                    if cached_data:
                        results[symbol] = True  # 已有缓存
                        logger.info("品种已有缓存", symbol=symbol)
                    else:
                        results[symbol] = False  # 需要加载数据
                        logger.info("品种需要缓存预热", symbol=symbol)
                except Exception as e:
                    results[symbol] = False
                    logger.error("缓存预热检查失败", symbol=symbol, error=str(e))

            return results

        except Exception as e:
            logger.error("缓存预热失败", error=str(e))
            return {}

    async def cleanup_expired_cache(self) -> int:
        """清理过期缓存（主要用于内存缓存）"""
        try:
            if self.redis_client:
                # Redis会自动清理过期键
                logger.info("Redis会自动清理过期键")
                return 0
            else:
                # 清理内存缓存中的过期项
                current_time = datetime.now()
                keys_to_delete = []

                for key, cached_item in self._memory_cache.items():
                    if current_time >= cached_item['expiry']:
                        keys_to_delete.append(key)

                for key in keys_to_delete:
                    del self._memory_cache[key]

                logger.info("清理过期缓存完成", deleted_count=len(keys_to_delete))
                return len(keys_to_delete)

        except Exception as e:
            logger.error("清理过期缓存失败", error=str(e))
            return 0

    async def get_cache_info(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取特定缓存键的信息"""
        try:
            if self.redis_client:
                ttl = self.redis_client.ttl(cache_key)
                exists = self.redis_client.exists(cache_key)
                return {
                    'key': cache_key,
                    'exists': bool(exists),
                    'ttl': ttl,
                    'type': 'redis'
                }
            else:
                if cache_key in self._memory_cache:
                    cached_item = self._memory_cache[cache_key]
                    ttl = (cached_item['expiry'] - datetime.now()).total_seconds()
                    return {
                        'key': cache_key,
                        'exists': True,
                        'ttl': int(ttl),
                        'type': 'memory',
                        'data_count': len(cached_item['data']) if 'data' in cached_item else 0
                    }
                else:
                    return {
                        'key': cache_key,
                        'exists': False,
                        'ttl': -1,
                        'type': 'memory'
                    }

        except Exception as e:
            logger.error("获取缓存信息失败", error=str(e), cache_key=cache_key)
            return None

    # 策略相关缓存方法
    def _generate_strategy_cache_key(self, strategy_id: str) -> str:
        """生成策略结果缓存键"""
        return f"strategy_result:{strategy_id}"

    def _generate_strategy_config_key(self, config_id: str) -> str:
        """生成策略配置缓存键"""
        return f"strategy_config:{config_id}"

    async def get_strategy_result(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """从缓存获取策略结果"""
        try:
            cache_key = self._generate_strategy_cache_key(strategy_id)
            ttl = getattr(settings, 'CACHE_STRATEGY_RESULT_TTL', 3600)  # 1小时

            if self.redis_client:
                # 使用Redis缓存
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # 使用pickle反序列化
                    data = pickle.loads(cached_data)
                    logger.info("从Redis缓存获取策略结果", strategy_id=strategy_id)
                    return data
            else:
                # 使用内存缓存
                if cache_key in self._memory_cache:
                    cached_item = self._memory_cache[cache_key]
                    if datetime.now() < cached_item['expiry']:
                        logger.info("从内存缓存获取策略结果", strategy_id=strategy_id)
                        return cached_item['data']
                    else:
                        # 缓存过期，删除
                        del self._memory_cache[cache_key]

            return None

        except Exception as e:
            logger.error("从缓存获取策略结果失败", error=str(e), strategy_id=strategy_id)
            return None

    async def set_strategy_result(self, strategy_id: str, result: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """将策略结果存入缓存"""
        try:
            cache_key = self._generate_strategy_cache_key(strategy_id)
            if ttl is None:
                ttl = getattr(settings, 'CACHE_STRATEGY_RESULT_TTL', 3600)  # 1小时

            if self.redis_client:
                # 使用Redis缓存
                serialized_data = pickle.dumps(result)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                logger.info("策略结果已存入Redis缓存", strategy_id=strategy_id, ttl=ttl)
            else:
                # 使用内存缓存
                expiry_time = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[cache_key] = {
                    'data': result,
                    'expiry': expiry_time
                }
                logger.info("策略结果已存入内存缓存", strategy_id=strategy_id, ttl=ttl)

            return True

        except Exception as e:
            logger.error("策略结果缓存失败", error=str(e), strategy_id=strategy_id)
            return False

    async def get_strategy_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """从缓存获取策略配置"""
        try:
            cache_key = self._generate_strategy_config_key(config_id)
            ttl = getattr(settings, 'CACHE_STRATEGY_CONFIG_TTL', 1800)  # 30分钟

            if self.redis_client:
                # 使用Redis缓存
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # 使用pickle反序列化
                    data = pickle.loads(cached_data)
                    logger.info("从Redis缓存获取策略配置", config_id=config_id)
                    return data
            else:
                # 使用内存缓存
                if cache_key in self._memory_cache:
                    cached_item = self._memory_cache[cache_key]
                    if datetime.now() < cached_item['expiry']:
                        logger.info("从内存缓存获取策略配置", config_id=config_id)
                        return cached_item['data']
                    else:
                        # 缓存过期，删除
                        del self._memory_cache[cache_key]

            return None

        except Exception as e:
            logger.error("从缓存获取策略配置失败", error=str(e), config_id=config_id)
            return None

    async def set_strategy_config(self, config_id: str, config_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """将策略配置存入缓存"""
        try:
            cache_key = self._generate_strategy_config_key(config_id)
            if ttl is None:
                ttl = getattr(settings, 'CACHE_STRATEGY_CONFIG_TTL', 1800)  # 30分钟

            if self.redis_client:
                # 使用Redis缓存
                serialized_data = pickle.dumps(config_data)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                logger.info("策略配置已存入Redis缓存", config_id=config_id, ttl=ttl)
            else:
                # 使用内存缓存
                expiry_time = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[cache_key] = {
                    'data': config_data,
                    'expiry': expiry_time
                }
                logger.info("策略配置已存入内存缓存", config_id=config_id, ttl=ttl)

            return True

        except Exception as e:
            logger.error("策略配置缓存失败", error=str(e), config_id=config_id)
            return False

    async def delete_strategy_result(self, strategy_id: str) -> bool:
        """删除策略结果缓存"""
        try:
            cache_key = self._generate_strategy_cache_key(strategy_id)

            if self.redis_client:
                deleted_count = self.redis_client.delete(cache_key)
                logger.info("已删除策略结果缓存", strategy_id=strategy_id, deleted=deleted_count)
            else:
                # 删除内存缓存
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    deleted_count = 1
                else:
                    deleted_count = 0
                logger.info("已删除策略结果内存缓存", strategy_id=strategy_id, deleted=deleted_count)

            return deleted_count > 0

        except Exception as e:
            logger.error("删除策略结果缓存失败", error=str(e), strategy_id=strategy_id)
            return False

    async def delete_strategy_config(self, config_id: str) -> bool:
        """删除策略配置缓存"""
        try:
            cache_key = self._generate_strategy_config_key(config_id)

            if self.redis_client:
                deleted_count = self.redis_client.delete(cache_key)
                logger.info("已删除策略配置缓存", config_id=config_id, deleted=deleted_count)
            else:
                # 删除内存缓存
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    deleted_count = 1
                else:
                    deleted_count = 0
                logger.info("已删除策略配置内存缓存", config_id=config_id, deleted=deleted_count)

            return deleted_count > 0

        except Exception as e:
            logger.error("删除策略配置缓存失败", error=str(e), config_id=config_id)
            return False