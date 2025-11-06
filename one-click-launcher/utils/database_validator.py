"""
数据库连接验证器

提供Redis和PostgreSQL数据库连接验证、权限检查和错误处理功能。
"""

import asyncio
import redis

# Try to import asyncpg, make it optional
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseConnectionResult:
    """数据库连接结果"""
    database_type: str
    host: str
    port: int
    is_connected: bool
    connection_time: Optional[float]
    error_message: Optional[str]
    permissions: Dict[str, bool]
    database_info: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'database_type': self.database_type,
            'host': self.host,
            'port': self.port,
            'is_connected': self.is_connected,
            'connection_time': self.connection_time,
            'error_message': self.error_message,
            'permissions': self.permissions,
            'database_info': self.database_info,
            'timestamp': self.timestamp.isoformat()
        }


class DatabaseValidator:
    """数据库验证器"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def validate_redis_connection(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0
    ) -> DatabaseConnectionResult:
        """
        验证Redis连接

        Args:
            host: Redis主机
            port: Redis端口
            password: Redis密码
            db: Redis数据库

        Returns:
            DatabaseConnectionResult: 连接验证结果
        """
        start_time = asyncio.get_event_loop().time()
        permissions = {}
        database_info = {}

        try:
            # 创建Redis连接
            redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout
            )

            # 测试连接
            redis_client.ping()

            connection_time = asyncio.get_event_loop().time() - start_time

            # 检查权限
            try:
                # 测试读权限
                redis_client.info()
                permissions['read'] = True
            except Exception:
                permissions['read'] = False

            try:
                # 测试写权限
                test_key = f"__validation_test_{datetime.now().timestamp()}"
                redis_client.set(test_key, "test", ex=1)
                redis_client.delete(test_key)
                permissions['write'] = True
            except Exception:
                permissions['write'] = False

            # 获取数据库信息
            try:
                info = redis_client.info()
                database_info = {
                    'version': info.get('redis_version'),
                    'uptime_seconds': info.get('uptime_in_seconds'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory': info.get('used_memory_human'),
                    'total_commands_processed': info.get('total_commands_processed')
                }
            except Exception as e:
                database_info = {'error': str(e)}

            # 关闭连接
            redis_client.close()

            result = DatabaseConnectionResult(
                database_type="redis",
                host=host,
                port=port,
                is_connected=True,
                connection_time=connection_time,
                error_message=None,
                permissions=permissions,
                database_info=database_info,
                timestamp=datetime.now()
            )

            logger.info(f"Redis connection validated successfully: {host}:{port}")
            return result

        except redis.ConnectionError as e:
            connection_time = asyncio.get_event_loop().time() - start_time
            error_message = f"Redis connection error: {e}"

            result = DatabaseConnectionResult(
                database_type="redis",
                host=host,
                port=port,
                is_connected=False,
                connection_time=connection_time,
                error_message=error_message,
                permissions={},
                database_info={},
                timestamp=datetime.now()
            )

            logger.error(f"Redis connection validation failed: {host}:{port} - {e}")
            return result

        except Exception as e:
            connection_time = asyncio.get_event_loop().time() - start_time
            error_message = f"Unexpected Redis error: {e}"

            result = DatabaseConnectionResult(
                database_type="redis",
                host=host,
                port=port,
                is_connected=False,
                connection_time=connection_time,
                error_message=error_message,
                permissions={},
                database_info={},
                timestamp=datetime.now()
            )

            logger.error(f"Redis validation error: {host}:{port} - {e}")
            return result

    async def validate_postgresql_connection(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: Optional[str] = None
    ) -> DatabaseConnectionResult:
        """
        验证PostgreSQL连接

        Args:
            host: PostgreSQL主机
            port: PostgreSQL端口
            database: 数据库名称
            username: 用户名
            password: 密码

        Returns:
            DatabaseConnectionResult: 连接验证结果
        """
        if not HAS_ASYNCPG:
            return DatabaseConnectionResult(
                database_type="postgresql",
                host=host,
                port=port,
                is_connected=False,
                connection_time=None,
                error_message="asyncpg module not available - PostgreSQL validation disabled",
                permissions={},
                database_info={},
                timestamp=datetime.now()
            )
        start_time = asyncio.get_event_loop().time()
        permissions = {}
        database_info = {}

        try:
            # 创建PostgreSQL连接
            connection = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                command_timeout=self.timeout
            )

            connection_time = asyncio.get_event_loop().time() - start_time

            # 检查权限
            try:
                # 测试读权限
                await connection.fetchval("SELECT version()")
                permissions['read'] = True
            except Exception:
                permissions['read'] = False

            try:
                # 测试写权限
                await connection.execute("CREATE TEMPORARY TABLE validation_test (id INT)")
                await connection.execute("DROP TABLE validation_test")
                permissions['write'] = True
            except Exception:
                permissions['write'] = False

            try:
                # 测试管理权限
                await connection.fetchval("SELECT current_user")
                permissions['admin'] = True
            except Exception:
                permissions['admin'] = False

            # 获取数据库信息
            try:
                version = await connection.fetchval("SELECT version()")
                db_size = await connection.fetchval("""
                    SELECT pg_size_pretty(pg_database_size($1))
                """, database)
                connection_count = await connection.fetchval("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = $1
                """, database)

                database_info = {
                    'version': version,
                    'database_size': db_size,
                    'active_connections': connection_count,
                    'current_user': await connection.fetchval("SELECT current_user"),
                    'server_encoding': await connection.fetchval("SHOW server_encoding")
                }
            except Exception as e:
                database_info = {'error': str(e)}

            # 关闭连接
            await connection.close()

            result = DatabaseConnectionResult(
                database_type="postgresql",
                host=host,
                port=port,
                is_connected=True,
                connection_time=connection_time,
                error_message=None,
                permissions=permissions,
                database_info=database_info,
                timestamp=datetime.now()
            )

            logger.info(f"PostgreSQL connection validated successfully: {host}:{port}/{database}")
            return result

        except asyncpg.PostgresError as e:
            connection_time = asyncio.get_event_loop().time() - start_time
            error_message = f"PostgreSQL connection error: {e}"

            result = DatabaseConnectionResult(
                database_type="postgresql",
                host=host,
                port=port,
                is_connected=False,
                connection_time=connection_time,
                error_message=error_message,
                permissions={},
                database_info={},
                timestamp=datetime.now()
            )

            logger.error(f"PostgreSQL connection validation failed: {host}:{port}/{database} - {e}")
            return result

        except Exception as e:
            connection_time = asyncio.get_event_loop().time() - start_time
            error_message = f"Unexpected PostgreSQL error: {e}"

            result = DatabaseConnectionResult(
                database_type="postgresql",
                host=host,
                port=port,
                is_connected=False,
                connection_time=connection_time,
                error_message=error_message,
                permissions={},
                database_info={},
                timestamp=datetime.now()
            )

            logger.error(f"PostgreSQL validation error: {host}:{port}/{database} - {e}")
            return result

    async def validate_all_connections(
        self,
        redis_config: Optional[Dict[str, Any]] = None,
        postgresql_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, DatabaseConnectionResult]:
        """
        验证所有数据库连接

        Args:
            redis_config: Redis配置
            postgresql_config: PostgreSQL配置

        Returns:
            Dict[str, DatabaseConnectionResult]: 所有连接验证结果
        """
        results = {}

        # Validate Redis connection
        if redis_config is not None:
            redis_result = await self.validate_redis_connection(**redis_config)
            results['redis'] = redis_result
        else:
            # Use default Redis configuration
            redis_result = await self.validate_redis_connection()
            results['redis'] = redis_result

        # Validate PostgreSQL connection
        if postgresql_config is not None:
            postgresql_result = await self.validate_postgresql_connection(**postgresql_config)
            results['postgresql'] = postgresql_result
        else:
            # Use default PostgreSQL configuration
            postgresql_result = await self.validate_postgresql_connection()
            results['postgresql'] = postgresql_result

        return results

    async def check_database_health(
        self,
        redis_config: Optional[Dict[str, Any]] = None,
        postgresql_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检查数据库健康状态

        Args:
            redis_config: Redis配置
            postgresql_config: PostgreSQL配置

        Returns:
            Dict[str, Any]: 健康检查结果
        """
        connection_results = await self.validate_all_connections(redis_config, postgresql_config)

        # Analyze results
        healthy_databases = []
        unhealthy_databases = []
        total_connection_time = 0.0

        for db_type, result in connection_results.items():
            if result.is_connected:
                healthy_databases.append(db_type)
                if result.connection_time:
                    total_connection_time += result.connection_time
            else:
                unhealthy_databases.append(db_type)

        total_databases = len(connection_results)
        health_percentage = (len(healthy_databases) / total_databases * 100) if total_databases > 0 else 0.0
        avg_connection_time = total_connection_time / len(healthy_databases) if healthy_databases else 0.0

        return {
            'overall_healthy': len(healthy_databases) == total_databases,
            'healthy_databases': healthy_databases,
            'unhealthy_databases': unhealthy_databases,
            'total_databases': total_databases,
            'health_percentage': health_percentage,
            'avg_connection_time': avg_connection_time,
            'connection_results': {k: v.to_dict() for k, v in connection_results.items()},
            'timestamp': datetime.now().isoformat()
        }


# Convenience functions

async def validate_redis(host: str = "localhost", port: int = 6379, **kwargs) -> DatabaseConnectionResult:
    """
    验证Redis连接的便捷函数
    """
    validator = DatabaseValidator()
    return await validator.validate_redis_connection(host=host, port=port, **kwargs)


async def validate_postgresql(
    host: str = "localhost",
    port: int = 5432,
    database: str = "postgres",
    username: str = "postgres",
    **kwargs
) -> DatabaseConnectionResult:
    """
    验证PostgreSQL连接的便捷函数
    """
    validator = DatabaseValidator()
    return await validator.validate_postgresql_connection(
        host=host, port=port, database=database, username=username, **kwargs
    )


async def validate_backend_databases(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_db: str = "quantdb"
) -> Dict[str, Any]:
    """
    验证后端服务所需数据库的便捷函数
    """
    validator = DatabaseValidator()

    redis_config = {
        'host': redis_host,
        'port': redis_port
    }

    postgresql_config = {
        'host': postgres_host,
        'port': postgres_port,
        'database': postgres_db,
        'username': 'postgres'
    }

    return await validator.check_database_health(redis_config, postgresql_config)