import sqlite3
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import structlog
from app.core.config import settings
from app.models.market_data import Base, MarketDataDB

logger = structlog.get_logger()

class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self):
        self.database_url = settings.get_database_url()
        self.async_database_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        # 同步引擎（用于初始化和迁移）
        self.sync_engine = create_engine(
            self.database_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20
            },
            echo=settings.DEBUG
        )

        # 异步引擎
        self.async_engine = create_async_engine(
            self.async_database_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20
            },
            echo=settings.DEBUG
        )

        # 会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.sync_engine
        )

        # 异步会话工厂
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        self._initialized = False

    def initialize_database(self):
        """初始化数据库（创建表）"""
        if self._initialized:
            return

        try:
            logger.info("初始化数据库")

            # 创建所有表
            Base.metadata.create_all(bind=self.sync_engine)

            # 创建索引
            self._create_indexes()

            self._initialized = True
            logger.info("数据库初始化完成")

        except Exception as e:
            logger.error("数据库初始化失败", error=str(e))
            raise

    def _create_indexes(self):
        """创建数据库索引"""
        try:
            with self.sync_engine.connect() as conn:
                # 确保复合索引存在
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_symbol_date ON market_data(symbol, date)",
                    "CREATE INDEX IF NOT EXISTS idx_date_symbol ON market_data(date, symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_symbol ON market_data(symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_date ON market_data(date)"
                ]

                for index_sql in indexes:
                    conn.execute(text(index_sql))

                conn.commit()
                logger.info("数据库索引创建完成")

        except Exception as e:
            logger.error("创建索引失败", error=str(e))
            raise

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("数据库会话异常", error=str(e))
                raise
            finally:
                await session.close()

    def get_sync_session(self) -> Session:
        """获取同步数据库会话"""
        session = self.SessionLocal()
        try:
            return session
        except Exception as e:
            session.close()
            logger.error("同步数据库会话创建失败", error=str(e))
            raise

    async def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行SQL语句"""
        try:
            async with self.async_engine.connect() as conn:
                result = await conn.execute(sql, params or {})
                await conn.commit()
                return result
        except Exception as e:
            logger.error("执行SQL失败", sql=sql, params=params, error=str(e))
            raise

    async def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            async with self.get_async_session() as session:
                # 获取表信息
                tables_result = await session.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in tables_result.fetchall()]

                # 获取市场数据统计
                if 'market_data' in tables:
                    count_result = await session.execute("SELECT COUNT(*) FROM market_data")
                    total_records = count_result.scalar()

                    # 获取最新数据日期
                    latest_result = await session.execute(
                        "SELECT MAX(date) FROM market_data"
                    )
                    latest_date = latest_result.scalar()

                    # 获取品种数量
                    symbols_result = await session.execute(
                        "SELECT COUNT(DISTINCT symbol) FROM market_data"
                    )
                    symbol_count = symbols_result.scalar()
                else:
                    total_records = 0
                    latest_date = None
                    symbol_count = 0

                return {
                    'database_url': self.database_url,
                    'tables': tables,
                    'market_data_stats': {
                        'total_records': total_records,
                        'latest_date': latest_date.isoformat() if latest_date else None,
                        'symbol_count': symbol_count
                    },
                    'initialized': self._initialized
                }

        except Exception as e:
            logger.error("获取数据库信息失败", error=str(e))
            return {
                'database_url': self.database_url,
                'error': str(e),
                'initialized': self._initialized
            }

    async def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil
            from pathlib import Path

            # 获取数据库文件路径
            db_path = self.database_url.replace("sqlite:///", "")
            source_path = Path(db_path)
            target_path = Path(backup_path)

            if not source_path.exists():
                logger.error("源数据库文件不存在", path=str(source_path))
                return False

            # 确保备份目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制文件
            shutil.copy2(source_path, target_path)

            logger.info("数据库备份成功", source=str(source_path), target=str(target_path))
            return True

        except Exception as e:
            logger.error("数据库备份失败", error=str(e))
            return False

    async def restore_database(self, backup_path: str) -> bool:
        """恢复数据库"""
        try:
            import shutil
            from pathlib import Path

            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error("备份文件不存在", path=str(backup_file))
                return False

            # 获取数据库文件路径
            db_path = self.database_url.replace("sqlite:///", "")
            target_path = Path(db_path)

            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 关闭所有连接
            await self.async_engine.dispose()
            self.sync_engine.dispose()

            # 恢复文件
            shutil.copy2(backup_file, target_path)

            # 重新初始化
            self._initialized = False
            self.initialize_database()

            logger.info("数据库恢复成功", source=str(backup_file), target=str(target_path))
            return True

        except Exception as e:
            logger.error("数据库恢复失败", error=str(e))
            return False

    async def close_connections(self):
        """关闭所有数据库连接"""
        try:
            await self.async_engine.dispose()
            self.sync_engine.dispose()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error("关闭数据库连接失败", error=str(e))

    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.sync_engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("数据库连接检查失败", error=str(e))
            return False

# 创建全局数据库管理器实例
db_manager = DatabaseManager()

# 便捷函数
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话的便捷函数"""
    async with db_manager.get_async_session() as session:
        yield session

def get_sync_session() -> Session:
    """获取同步数据库会话的便捷函数"""
    return db_manager.get_sync_session()

# 初始化数据库
def init_database():
    """初始化数据库的便捷函数"""
    db_manager.initialize_database()

# FastAPI 依赖注入函数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入函数 - 获取数据库会话"""
    async with db_manager.get_async_session() as session:
        yield session