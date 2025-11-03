import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
import json
import pickle
import redis
from app.services.cache_service import CacheService
from app.schemas.market_data import MarketDataResponse, SymbolResponse

@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return [
        MarketDataResponse(
            symbol="CU",
            date=datetime(2023, 1, 1),
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=104.0,
            volume=1000,
            turnover=104000.0,
            settlement_price=104.0,
            open_interest=5000
        ),
        MarketDataResponse(
            symbol="CU",
            date=datetime(2023, 1, 2),
            open_price=104.0,
            high_price=109.0,
            low_price=99.0,
            close_price=108.0,
            volume=1100,
            turnover=118800.0,
            settlement_price=108.0,
            open_interest=5200
        )
    ]

@pytest.fixture
def sample_symbols():
    """示例品种数据"""
    return [
        SymbolResponse(
            symbol="CU",
            name="铜",
            exchange="SHFE",
            sector="metal",
            contract_size=5,
            trading_unit="手",
            price_quote="元/吨",
            min_price_change=10,
            is_active=True
        ),
        SymbolResponse(
            symbol="AL",
            name="铝",
            exchange="SHFE",
            sector="metal",
            contract_size=5,
            trading_unit="手",
            price_quote="元/吨",
            min_price_change=10,
            is_active=True
        )
    ]

class TestCacheService:
    """缓存服务测试"""

    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        with patch('redis.Redis') as mock_redis_class:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_redis_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def cache_service_with_redis(self, mock_redis):
        """使用Redis的缓存服务实例"""
        return CacheService()

    @pytest.fixture
    def cache_service_memory_only(self):
        """仅使用内存的缓存服务实例"""
        with patch('redis.Redis', side_effect=Exception("Redis不可用")):
            return CacheService()

    def test_init_with_redis(self, mock_redis):
        """测试使用Redis初始化"""
        cache_service = CacheService()
        assert cache_service.redis_client is not None
        assert not hasattr(cache_service, '_memory_cache') or cache_service._memory_cache == {}

    def test_init_without_redis(self):
        """测试不使用Redis初始化"""
        with patch('redis.Redis', side_effect=Exception("Redis连接失败")):
            cache_service = CacheService()
            assert cache_service.redis_client is None
            assert hasattr(cache_service, '_memory_cache')
            assert cache_service._memory_cache == {}

    def test_generate_cache_key(self, cache_service_with_redis):
        """测试生成缓存键"""
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 5)

        cache_key = cache_service_with_redis._generate_cache_key("CU", start_date, end_date)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5哈希长度

        # 相同参数应生成相同的键
        cache_key2 = cache_service_with_redis._generate_cache_key("CU", start_date, end_date)
        assert cache_key == cache_key2

        # 不同参数应生成不同的键
        cache_key3 = cache_service_with_redis._generate_cache_key("AL", start_date, end_date)
        assert cache_key != cache_key3

    def test_generate_symbols_cache_key(self, cache_service_with_redis):
        """测试生成品种列表缓存键"""
        # 不指定版块
        cache_key = cache_service_with_redis._generate_symbols_cache_key()
        assert cache_key == "symbols:all"

        # 指定版块
        cache_key_metal = cache_service_with_redis._generate_symbols_cache_key("metal")
        assert cache_key_metal == "symbols:metal"

    @pytest.mark.asyncio
    async def test_set_and_get_market_data_redis(self, cache_service_with_redis, sample_market_data):
        """测试使用Redis存储和获取市场数据"""
        symbol = "CU"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)
        ttl = 3600

        # 存储数据
        result = await cache_service_with_redis.set_market_data(symbol, sample_market_data, ttl)
        assert result is True

        # 验证Redis调用
        cache_service_with_redis.redis_client.setex.assert_called_once()
        call_args = cache_service_with_redis.redis_client.setex.call_args
        assert call_args[0][1] == ttl  # TTL参数
        assert call_args[0][2] is not None  # 序列化数据

        # 获取数据
        with patch.object(cache_service_with_redis.redis_client, 'get', return_value=pickle.dumps(sample_market_data)):
            cached_data = await cache_service_with_redis.get_market_data(symbol, start_date, end_date)
            assert cached_data is not None
            assert len(cached_data) == 2
            assert cached_data[0].symbol == "CU"
            assert cached_data[0].close_price == 104.0

    @pytest.mark.asyncio
    async def test_set_and_get_market_data_memory(self, cache_service_memory_only, sample_market_data):
        """测试使用内存缓存存储和获取市场数据"""
        symbol = "CU"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)
        ttl = 3600

        # 存储数据
        result = await cache_service_memory_only.set_market_data(symbol, sample_market_data, ttl)
        assert result is True

        # 获取数据
        cached_data = await cache_service_memory_only.get_market_data(symbol, start_date, end_date)
        assert cached_data is not None
        assert len(cached_data) == 2
        assert cached_data[0].symbol == "CU"

        # 检查内存缓存
        cache_key = cache_service_memory_only._generate_cache_key(symbol, start_date, end_date)
        assert cache_key in cache_service_memory_only._memory_cache
        assert cache_service_memory_only._memory_cache[cache_key]['data'] == sample_market_data

    @pytest.mark.asyncio
    async def test_get_market_data_not_found(self, cache_service_with_redis):
        """测试获取不存在的市场数据"""
        with patch.object(cache_service_with_redis.redis_client, 'get', return_value=None):
            cached_data = await cache_service_with_redis.get_market_data("CU", date(2023, 1, 1), date(2023, 1, 5))
            assert cached_data is None

    @pytest.mark.asyncio
    async def test_get_market_data_expired_memory(self, cache_service_memory_only, sample_market_data):
        """测试获取过期的内存缓存数据"""
        symbol = "CU"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)

        # 存储数据并手动设置过期时间
        await cache_service_memory_only.set_market_data(symbol, sample_market_data, 1)
        cache_key = cache_service_memory_only._generate_cache_key(symbol, start_date, end_date)
        cache_service_memory_only._memory_cache[cache_key]['expiry'] = datetime.now() - timedelta(seconds=1)

        # 获取数据应该返回None
        cached_data = await cache_service_memory_only.get_market_data(symbol, start_date, end_date)
        assert cached_data is None
        assert cache_key not in cache_service_memory_only._memory_cache

    @pytest.mark.asyncio
    async def test_set_and_get_symbols_redis(self, cache_service_with_redis, sample_symbols):
        """测试使用Redis存储和获取品种列表"""
        sector = "metal"
        ttl = 3600

        # 存储数据
        result = await cache_service_with_redis.set_symbols(sample_symbols, sector, ttl)
        assert result is True

        # 获取数据
        with patch.object(cache_service_with_redis.redis_client, 'get', return_value=pickle.dumps(sample_symbols)):
            cached_symbols = await cache_service_with_redis.get_symbols(sector)
            assert cached_symbols is not None
            assert len(cached_symbols) == 2
            assert cached_symbols[0].symbol == "CU"
            assert cached_symbols[1].symbol == "AL"

    @pytest.mark.asyncio
    async def test_set_and_get_symbols_memory(self, cache_service_memory_only, sample_symbols):
        """测试使用内存缓存存储和获取品种列表"""
        sector = "metal"
        ttl = 3600

        # 存储数据
        result = await cache_service_memory_only.set_symbols(sample_symbols, sector, ttl)
        assert result is True

        # 获取数据
        cached_symbols = await cache_service_memory_only.get_symbols(sector)
        assert cached_symbols is not None
        assert len(cached_symbols) == 2
        assert cached_symbols[0].symbol == "CU"

    @pytest.mark.asyncio
    async def test_delete_market_data_redis(self, cache_service_with_redis):
        """测试使用Redis删除市场数据"""
        symbol = "CU"

        with patch.object(cache_service_with_redis.redis_client, 'keys', return_value=[b'market_data:CU:20230101:20230105']) as mock_keys, \
             patch.object(cache_service_with_redis.redis_client, 'delete', return_value=1) as mock_delete:

            result = await cache_service_with_redis.delete_market_data(symbol)
            assert result is True
            mock_keys.assert_called_once_with("*CU*")
            mock_delete.assert_called_once_with(b'market_data:CU:20230101:20230105')

    @pytest.mark.asyncio
    async def test_delete_market_data_memory(self, cache_service_memory_only, sample_market_data):
        """测试从内存缓存删除市场数据"""
        symbol = "CU"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)

        # 先存储数据
        await cache_service_memory_only.set_market_data(symbol, sample_market_data)

        # 验证内存缓存中有数据
        assert len(cache_service_memory_only._memory_cache) > 0

        # 删除数据
        result = await cache_service_memory_only.delete_market_data(symbol)
        assert result is True

        # 验证所有包含symbol的缓存都被删除
        remaining_keys = list(cache_service_memory_only._memory_cache.keys())
        assert all(symbol not in key for key in remaining_keys)

    @pytest.mark.asyncio
    async def test_clear_all_cache_redis(self, cache_service_with_redis):
        """测试清空Redis缓存"""
        with patch.object(cache_service_with_redis.redis_client, 'flushdb') as mock_flushdb:
            result = await cache_service_with_redis.clear_all_cache()
            assert result is True
            mock_flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_cache_memory(self, cache_service_memory_only, sample_market_data):
        """测试清空内存缓存"""
        # 先存储一些数据
        await cache_service_memory_only.set_market_data("CU", sample_market_data)
        assert len(cache_service_memory_only._memory_cache) > 0

        # 清空缓存
        result = await cache_service_memory_only.clear_all_cache()
        assert result is True
        assert len(cache_service_memory_only._memory_cache) == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats_redis(self, cache_service_with_redis):
        """测试获取Redis缓存统计信息"""
        mock_info = {
            'used_memory_human': '1.5M',
            'connected_clients': 2,
            'uptime_in_seconds': 3600
        }

        with patch.object(cache_service_with_redis.redis_client, 'info', return_value=mock_info), \
             patch.object(cache_service_with_redis.redis_client, 'dbsize', return_value=100):

            stats = await cache_service_with_redis.get_cache_stats()

            assert stats['cache_type'] == 'redis'
            assert stats['total_keys'] == 100
            assert stats['used_memory'] == '1.5M'
            assert stats['connected_clients'] == 2
            assert 'timestamp' in stats

    @pytest.mark.asyncio
    async def test_get_cache_stats_memory(self, cache_service_memory_only, sample_market_data):
        """测试获取内存缓存统计信息"""
        # 先存储一些数据
        await cache_service_memory_only.set_market_data("CU", sample_market_data)

        stats = await cache_service_memory_only.get_cache_stats()

        assert stats['cache_type'] == 'memory'
        assert stats['total_keys'] == 1
        assert 'timestamp' in stats

    @pytest.mark.asyncio
    async def test_cache_warm_up(self, cache_service_with_redis):
        """测试缓存预热"""
        symbols = ["CU", "AL"]
        days = 30

        with patch.object(cache_service_with_redis, 'get_market_data', new_callable=AsyncMock) as mock_get:
            # 模拟一个品种有缓存，一个没有
            mock_get.side_effect = [
                [MarketDataResponse(symbol="CU", date=datetime.now(), open_price=100, high_price=105, low_price=95, close_price=104, volume=1000)],  # CU有缓存
                None  # AL没有缓存
            ]

            results = await cache_service_with_redis.cache_warm_up(symbols, days)

            assert results["CU"] is True  # 已有缓存
            assert results["AL"] is False  # 需要加载
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache_redis(self, cache_service_with_redis):
        """测试清理过期Redis缓存"""
        # Redis会自动清理过期键
        result = await cache_service_with_redis.cleanup_expired_cache()
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache_memory(self, cache_service_memory_only, sample_market_data):
        """测试清理过期内存缓存"""
        # 先存储一些数据
        await cache_service_memory_only.set_market_data("CU", sample_market_data, ttl=1)

        # 等待缓存过期
        await asyncio.sleep(1.1)

        # 清理过期缓存
        deleted_count = await cache_service_memory_only.cleanup_expired_cache()
        assert deleted_count == 1
        assert len(cache_service_memory_only._memory_cache) == 0

    @pytest.mark.asyncio
    async def test_get_cache_info_redis(self, cache_service_with_redis):
        """测试获取Redis缓存信息"""
        cache_key = "test_key"

        with patch.object(cache_service_with_redis.redis_client, 'ttl', return_value=3600), \
             patch.object(cache_service_with_redis.redis_client, 'exists', return_value=1):

            cache_info = await cache_service_with_redis.get_cache_info(cache_key)

            assert cache_info is not None
            assert cache_info['key'] == cache_key
            assert cache_info['exists'] is True
            assert cache_info['ttl'] == 3600
            assert cache_info['type'] == 'redis'

    @pytest.mark.asyncio
    async def test_get_cache_info_memory_exists(self, cache_service_memory_only, sample_market_data):
        """测试获取存在的内存缓存信息"""
        await cache_service_memory_only.set_market_data("CU", sample_market_data)
        cache_key = cache_service_memory_only._generate_cache_key("CU", date(2023, 1, 1), date(2023, 1, 2))

        cache_info = await cache_service_memory_only.get_cache_info(cache_key)

        assert cache_info is not None
        assert cache_info['key'] == cache_key
        assert cache_info['exists'] is True
        assert cache_info['ttl'] > 0
        assert cache_info['type'] == 'memory'
        assert cache_info['data_count'] == 2

    @pytest.mark.asyncio
    async def test_get_cache_info_memory_not_exists(self, cache_service_memory_only):
        """测试获取不存在的内存缓存信息"""
        cache_key = "non_existent_key"

        cache_info = await cache_service_memory_only.get_cache_info(cache_key)

        assert cache_info is not None
        assert cache_info['key'] == cache_key
        assert cache_info['exists'] is False
        assert cache_info['ttl'] == -1
        assert cache_info['type'] == 'memory'

    @pytest.mark.asyncio
    async def test_set_market_data_empty_list(self, cache_service_with_redis):
        """测试存储空数据列表"""
        result = await cache_service_with_redis.set_market_data("CU", [])
        assert result is True

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_service_with_redis, sample_market_data):
        """测试缓存错误处理"""
        # 模拟Redis操作失败
        with patch.object(cache_service_with_redis.redis_client, 'setex', side_effect=Exception("Redis错误")):
            result = await cache_service_with_redis.set_market_data("CU", sample_market_data)
            assert result is False

        with patch.object(cache_service_with_redis.redis_client, 'get', side_effect=Exception("Redis错误")):
            cached_data = await cache_service_with_redis.get_market_data("CU", date(2023, 1, 1), date(2023, 1, 5))
            assert cached_data is None

if __name__ == "__main__":
    pytest.main([__file__])