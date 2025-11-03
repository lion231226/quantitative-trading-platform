import asyncio
from typing import List, Dict, Any, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, delete, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload
import structlog
import pandas as pd
import time
from dataclasses import dataclass
from app.core.database import get_async_session, db_manager
from app.core.config import settings
from app.models.market_data import MarketDataDB, MarketData
from app.services.data_processor import DataProcessor
from app.utils.errors import APIError, ValidationError, ProcessingError

logger = structlog.get_logger()

@dataclass
class PerformanceMetrics:
    """性能监控指标"""
    operation_type: str
    start_time: float
    end_time: float
    duration_ms: float
    records_processed: int
    success: bool
    error_message: Optional[str] = None
    quality_score: Optional[float] = None
    batch_count: Optional[int] = None

class DataStorageService:
    """数据存储服务"""

    def __init__(self) -> Any:
        self.data_processor = DataProcessor()
        self.batch_size = getattr(settings, 'DATA_STORAGE_BATCH_SIZE', 1000)  # 批量插入大小
        self.max_retry_attempts = getattr(settings, 'DATA_STORAGE_MAX_RETRY_ATTEMPTS', 3)
        self.performance_metrics: List[PerformanceMetrics] = []
        self.max_metrics_history = getattr(settings, 'DATA_STORAGE_MAX_METRICS_HISTORY', 100)

    async def store_market_data(self, raw_data: List[Dict[str, Any]], symbol: str) -> Tuple[int, float]:
        """存储市场数据"""
        start_time = time.time()
        operation_type = "store_market_data"

        try:
            if not raw_data:
                logger.warning("没有数据需要存储", symbol=symbol)
                self._record_performance_metrics(operation_type, start_time, 0, True)
                return 0, 0.0

            logger.info("开始存储市场数据", symbol=symbol, raw_count=len(raw_data))

            # 1. 数据清洗和验证
            cleaned_data = await self.data_processor.clean_and_validate_data(raw_data, symbol)

            if not cleaned_data:
                logger.warning("清洗后没有有效数据", symbol=symbol)
                self._record_performance_metrics(operation_type, start_time, 0, True)
                return 0, 0.0

            # 2. 数据去重和增量更新
            new_data_count = await self._incremental_update(cleaned_data, symbol)

            # 3. 计算质量评分
            quality_score = self.data_processor._calculate_overall_quality_score(cleaned_data)

            logger.info(
                "数据存储完成",
                symbol=symbol,
                cleaned_count=len(cleaned_data),
                new_data_count=new_data_count,
                quality_score=quality_score
            )

            self._record_performance_metrics(
                operation_type,
                start_time,
                len(cleaned_data),
                True,
                quality_score=quality_score,
                batch_count=(len(cleaned_data) + self.batch_size - 1) // self.batch_size
            )

            return new_data_count, quality_score

        except Exception as e:
            logger.error("存储市场数据失败", error=str(e), symbol=symbol)
            self._record_performance_metrics(operation_type, start_time, 0, False, str(e))
            raise ProcessingError(f"存储市场数据失败: {str(e)}")

    def _record_performance_metrics(
        self,
        operation_type: str,
        start_time: float,
        records_processed: int,
        success: bool,
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None,
        batch_count: Optional[int] = None
    ) -> Any:
        """记录性能指标"""
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        metrics = PerformanceMetrics(
            operation_type=operation_type,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            records_processed=records_processed,
            success=success,
            error_message=error_message,
            quality_score=quality_score,
            batch_count=batch_count
        )

        self.performance_metrics.append(metrics)

        # 只保留指定数量的记录
        if len(self.performance_metrics) > self.max_metrics_history:
            self.performance_metrics = self.performance_metrics[-self.max_metrics_history:]

        # 记录日志
        logger.info(
            "性能指标记录",
            operation_type=operation_type,
            duration_ms=duration_ms,
            records_processed=records_processed,
            success=success,
            quality_score=quality_score
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能统计摘要"""
        if not self.performance_metrics:
            return {
                "total_operations": 0,
                "message": "暂无性能数据"
            }

        summary_window = getattr(settings, 'DATA_STORAGE_PERFORMANCE_SUMMARY_WINDOW', 50)
        recent_metrics = self.performance_metrics[-summary_window:]  # 最近N条

        success_operations = [m for m in recent_metrics if m.success]
        failed_operations = [m for m in recent_metrics if not m.success]

        if success_operations:
            avg_duration = sum(m.duration_ms for m in success_operations) / len(success_operations)
            avg_quality = sum(m.quality_score or 0 for m in success_operations) / len(success_operations)
            total_records = sum(m.records_processed for m in success_operations)
            avg_records_per_op = total_records / len(success_operations)
        else:
            avg_duration = 0
            avg_quality = 0
            total_records = 0
            avg_records_per_op = 0

        return {
            "total_operations": len(recent_metrics),
            "success_count": len(success_operations),
            "failure_count": len(failed_operations),
            "success_rate": len(success_operations) / len(recent_metrics) if recent_metrics else 0,
            "average_duration_ms": round(avg_duration, 2),
            "average_quality_score": round(avg_quality, 4),
            "total_records_processed": total_records,
            "average_records_per_operation": round(avg_records_per_op, 1),
            "last_operation_time": recent_metrics[-1].end_time if recent_metrics else None
        }

    async def _incremental_update(self, data_list: List[MarketData], symbol: str) -> int:
        """增量更新数据"""
        try:
            new_data_count = 0

            # 按批次处理数据
            for i in range(0, len(data_list), self.batch_size):
                batch = data_list[i:i + self.batch_size]
                batch_count = await self._process_batch(batch, symbol)
                new_data_count += batch_count

            return new_data_count

        except Exception as e:
            logger.error("增量更新失败", error=str(e), symbol=symbol)
            raise

    async def _process_batch(self, batch: List[MarketData], symbol: str) -> int:
        """处理单个批次的数据"""
        try:
            async with get_async_session() as session:
                # 获取批次中的日期范围
                batch_dates = [d.date.date() if isinstance(d.date, datetime) else d.date for d in batch]
                start_date = min(batch_dates)
                end_date = max(batch_dates)

                # 查询已存在的数据
                existing_query = select(MarketDataDB).where(
                    and_(
                        MarketDataDB.symbol == symbol,
                        MarketDataDB.date >= start_date,
                        MarketDataDB.date <= end_date
                    )
                )
                existing_result = await session.execute(existing_query)
                existing_records = {r.date.date(): r for r in existing_result.scalars().all()}

                # 准备要插入/更新的记录
                records_to_insert = []
                records_to_update = []

                for market_data in batch:
                    data_date = market_data.date.date() if isinstance(market_data.date, datetime) else market_data.date

                    # 转换为数据库模型
                    db_record = MarketDataDB(
                        symbol=market_data.symbol,
                        date=data_date,
                        open_price=market_data.open_price,
                        high_price=market_data.high_price,
                        low_price=market_data.low_price,
                        close_price=market_data.close_price,
                        volume=market_data.volume,
                        turnover=market_data.turnover,
                        settlement_price=market_data.settlement_price,
                        open_interest=market_data.open_interest,
                        updated_at=datetime.utcnow()
                    )

                    if data_date in existing_records:
                        # 更新现有记录
                        db_record.id = existing_records[data_date].id
                        records_to_update.append(db_record)
                    else:
                        # 插入新记录
                        records_to_insert.append(db_record)

                # 执行数据库操作
                new_count = 0

                # 批量插入新记录
                if records_to_insert:
                    session.add_all(records_to_insert)
                    new_count = len(records_to_insert)

                # 批量更新现有记录
                for record in records_to_update:
                    await session.merge(record)

                await session.commit()

                logger.debug(
                    "批次处理完成",
                    symbol=symbol,
                    batch_size=len(batch),
                    new_records=new_count,
                    updated_records=len(records_to_update)
                )

                return new_count

        except Exception as e:
            await session.rollback()
            logger.error("批次处理失败", error=str(e), symbol=symbol, batch_size=len(batch))
            raise

    async def query_market_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[MarketData]:
        """查询市场数据"""
        try:
            logger.info(
                "查询市场数据",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )

            async with get_async_session() as session:
                # 构建查询条件
                conditions = [MarketDataDB.symbol == symbol]

                if start_date:
                    conditions.append(MarketDataDB.date >= start_date)
                if end_date:
                    conditions.append(MarketDataDB.date <= end_date)

                # 构建查询
                query = select(MarketDataDB).where(and_(*conditions))

                # 添加排序
                query = query.order_by(MarketDataDB.date)

                # 添加分页
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)

                # 执行查询
                result = await session.execute(query)
                records = result.scalars().all()

                # 转换为MarketData对象
                market_data_list = []
                for record in records:
                    market_data = MarketData(
                        symbol=record.symbol,
                        date=record.date,
                        open_price=record.open_price,
                        high_price=record.high_price,
                        low_price=record.low_price,
                        close_price=record.close_price,
                        volume=record.volume,
                        turnover=record.turnover,
                        settlement_price=record.settlement_price,
                        open_interest=record.open_interest
                    )
                    market_data_list.append(market_data)

                logger.info(
                    "查询完成",
                    symbol=symbol,
                    count=len(market_data_list)
                )

                return market_data_list

        except Exception as e:
            logger.error("查询市场数据失败", error=str(e), symbol=symbol)
            raise APIError(f"查询市场数据失败: {str(e)}")

    async def query_latest_data(self, symbol: str, days: int = 1) -> List[MarketData]:
        """查询最新数据"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)

            return await self.query_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error("查询最新数据失败", error=str(e), symbol=symbol)
            raise APIError(f"查询最新数据失败: {str(e)}")

    async def query_symbols_latest_date(self, symbols: List[str]) -> Dict[str, Optional[date]]:
        """查询多个品种的最新数据日期"""
        try:
            async with get_async_session() as session:
                # 构建查询
                subquery = (
                    select(
                        MarketDataDB.symbol,
                        func.max(MarketDataDB.date).label('latest_date')
                    )
                    .where(MarketDataDB.symbol.in_(symbols))
                    .group_by(MarketDataDB.symbol)
                    .subquery()
                )

                query = select(subquery.c.symbol, subquery.c.latest_date)
                result = await session.execute(query)

                # 构建结果字典
                latest_dates = {}
                for row in result.all():
                    latest_dates[row.symbol] = row.latest_date

                # 确保所有请求的品种都有结果
                for symbol in symbols:
                    if symbol not in latest_dates:
                        latest_dates[symbol] = None

                return latest_dates

        except Exception as e:
            logger.error("查询最新日期失败", error=str(e), symbols=symbols)
            raise APIError(f"查询最新日期失败: {str(e)}")

    async def get_data_statistics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取数据统计信息"""
        try:
            async with get_async_session() as session:
                # 基础统计查询
                base_conditions = []
                if symbol:
                    base_conditions.append(MarketDataDB.symbol == symbol)

                # 总记录数
                total_count_query = select(func.count(MarketDataDB.id)).where(and_(*base_conditions))
                total_count = (await session.execute(total_count_query)).scalar()

                # 品种数量
                if not symbol:
                    symbol_count_query = select(func.count(func.distinct(MarketDataDB.symbol)))
                    symbol_count = (await session.execute(symbol_count_query)).scalar()
                else:
                    symbol_count = 1

                # 日期范围
                date_range_query = select(
                    func.min(MarketDataDB.date).label('min_date'),
                    func.max(MarketDataDB.date).label('max_date')
                ).where(and_(*base_conditions))
                date_range = (await session.execute(date_range_query)).first()

                # 按品种统计
                if not symbol:
                    symbol_stats_query = (
                        select(
                            MarketDataDB.symbol,
                            func.count(MarketDataDB.id).label('record_count'),
                            func.min(MarketDataDB.date).label('first_date'),
                            func.max(MarketDataDB.date).label('last_date')
                        )
                        .group_by(MarketDataDB.symbol)
                        .order_by(desc('record_count'))
                    )
                    symbol_stats = (await session.execute(symbol_stats_query)).all()
                else:
                    symbol_stats = []

                stats = {
                    'symbol': symbol,
                    'total_records': total_count,
                    'symbol_count': symbol_count,
                    'date_range': {
                        'start': date_range.min_date.isoformat() if date_range.min_date else None,
                        'end': date_range.max_date.isoformat() if date_range.max_date else None
                    },
                    'symbol_statistics': [
                        {
                            'symbol': stat.symbol,
                            'record_count': stat.record_count,
                            'first_date': stat.first_date.isoformat() if stat.first_date else None,
                            'last_date': stat.last_date.isoformat() if stat.last_date else None
                        }
                        for stat in symbol_stats
                    ]
                }

                return stats

        except Exception as e:
            logger.error("获取数据统计失败", error=str(e), symbol=symbol)
            raise APIError(f"获取数据统计失败: {str(e)}")

    async def delete_market_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """删除市场数据"""
        try:
            logger.info(
                "删除市场数据",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            async with get_async_session() as session:
                # 构建删除条件
                conditions = [MarketDataDB.symbol == symbol]

                if start_date:
                    conditions.append(MarketDataDB.date >= start_date)
                if end_date:
                    conditions.append(MarketDataDB.date <= end_date)

                # 执行删除
                delete_query = delete(MarketDataDB).where(and_(*conditions))
                result = await session.execute(delete_query)
                deleted_count = result.rowcount

                await session.commit()

                logger.info(
                    "数据删除完成",
                    symbol=symbol,
                    deleted_count=deleted_count
                )

                return deleted_count

        except Exception as e:
            await session.rollback()
            logger.error("删除市场数据失败", error=str(e), symbol=symbol)
            raise APIError(f"删除市场数据失败: {str(e)}")

    async def export_market_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = "csv"
    ) -> bytes:
        """导出市场数据"""
        try:
            logger.info(
                "导出市场数据",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                format=format
            )

            # 查询数据
            data = await self.query_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if not data:
                logger.warning("没有数据可导出", symbol=symbol)
                return b""

            # 转换为DataFrame
            df_data = []
            for item in data:
                df_data.append({
                    'symbol': item.symbol,
                    'date': item.date,
                    'open_price': item.open_price,
                    'high_price': item.high_price,
                    'low_price': item.low_price,
                    'close_price': item.close_price,
                    'volume': item.volume,
                    'turnover': item.turnover,
                    'settlement_price': item.settlement_price,
                    'open_interest': item.open_interest
                })

            df = pd.DataFrame(df_data)

            # 根据格式导出
            if format.lower() == "csv":
                return df.to_csv(index=False).encode('utf-8')
            elif format.lower() == "json":
                return df.to_json(orient='records', date_format='iso').encode('utf-8')
            elif format.lower() == "excel":
                return df.to_excel(index=False, engine='openpyxl')
            else:
                raise ValidationError(f"不支持的导出格式: {format}")

        except Exception as e:
            logger.error("导出市场数据失败", error=str(e), symbol=symbol)
            raise APIError(f"导出市场数据失败: {str(e)}")

    async def sync_incremental_data(self, symbol: str, new_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """增量同步数据"""
        try:
            if not new_data:
                return {'symbol': symbol, 'new_records': 0, 'updated_records': 0, 'quality_score': 0.0}

            logger.info("开始增量数据同步", symbol=symbol, new_data_count=len(new_data))

            # 查询最新日期
            latest_dates = await self.query_symbols_latest_date([symbol])
            latest_date = latest_dates.get(symbol)

            # 过滤新数据
            if latest_date:
                filtered_new_data = [
                    item for item in new_data
                    if datetime.fromisoformat(item['date'].replace('Z', '+00:00')).date() > latest_date
                ]
            else:
                filtered_new_data = new_data

            if not filtered_new_data:
                logger.info("没有新数据需要同步", symbol=symbol)
                return {'symbol': symbol, 'new_records': 0, 'updated_records': 0, 'quality_score': 100.0}

            # 存储数据
            new_count, quality_score = await self.store_market_data(filtered_new_data, symbol)

            result = {
                'symbol': symbol,
                'new_records': new_count,
                'updated_records': len(filtered_new_data) - new_count,
                'quality_score': quality_score,
                'sync_time': datetime.utcnow().isoformat()
            }

            logger.info("增量同步完成", **result)
            return result

        except Exception as e:
            logger.error("增量同步失败", error=str(e), symbol=symbol)
            raise APIError(f"增量同步失败: {str(e)}")

    async def vacuum_database(self) -> bool:
        """优化数据库（清理碎片）"""
        try:
            logger.info("开始数据库优化")

            async with get_async_session() as session:
                await session.execute("VACUUM")
                await session.commit()

            logger.info("数据库优化完成")
            return True

        except Exception as e:
            logger.error("数据库优化失败", error=str(e))
            return False

    async def get_storage_health_check(self) -> Dict[str, Any]:
        """存储系统健康检查"""
        try:
            health_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'database_connection': db_manager.check_connection(),
                'data_quality': {},
                'storage_stats': {}
            }

            # 获取数据库信息
            db_info = await db_manager.get_database_info()
            health_info['storage_stats'] = db_info

            # 检查数据质量
            if 'market_data_stats' in db_info:
                stats = db_info['market_data_stats']
                total_records = stats.get('total_records', 0)

                if total_records > 0:
                    # 随机抽样检查数据质量
                    sample_symbols = ['CU', 'AL', 'ZN']  # 示例品种
                    for symbol in sample_symbols:
                        try:
                            sample_data = await self.query_latest_data(symbol, days=30)
                            if sample_data:
                                quality_score = self.data_processor._calculate_overall_quality_score(sample_data)
                                health_info['data_quality'][symbol] = {
                                    'recent_records': len(sample_data),
                                    'quality_score': quality_score
                                }
                        except:
                            health_info['data_quality'][symbol] = {
                                'error': '查询失败'
                            }

            return health_info

        except Exception as e:
            logger.error("存储健康检查失败", error=str(e))
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'healthy': False
            }