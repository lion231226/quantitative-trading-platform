import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Any
from datetime import datetime, date
import structlog
from app.models.market_data import MarketData, MarketDataDB
from app.schemas.market_data import MarketDataResponse
from app.utils.errors import ValidationError, ProcessingError

logger = structlog.get_logger()

class DataProcessor:
    """数据清洗和标准化处理器"""

    def __init__(self) -> Any:
        self.price_columns = ['open_price', 'high_price', 'low_price', 'close_price']
        self.volume_columns = ['volume', 'turnover', 'open_interest']

    async def clean_and_validate_data(self, raw_data: List[Dict[str, Any]], symbol: str) -> List[MarketData]:
        """清洗和验证原始数据"""
        try:
            if not raw_data:
                logger.warning("原始数据为空", symbol=symbol)
                return []

            # 转换为DataFrame便于处理
            df = pd.DataFrame(raw_data)
            original_count = len(df)

            logger.info("开始数据清洗", symbol=symbol, original_count=original_count)

            # 1. 数据格式标准化
            df = self._standardize_columns(df)

            # 2. 处理缺失值
            df = self._handle_missing_values(df, symbol)

            # 3. 数据类型转换和验证
            df = self._convert_and_validate_types(df, symbol)

            # 4. 价格数据合理性检查
            df = self._validate_price_relationships(df, symbol)

            # 5. 异常值检测和处理
            df = self._detect_and_handle_outliers(df, symbol)

            # 6. 时间序列连续性检查
            df = self._check_time_series_continuity(df, symbol)

            # 7. 数据质量评分
            df = self._calculate_quality_score(df)

            # 转换为MarketData对象
            cleaned_data = self._convert_to_market_data(df, symbol)

            cleaned_count = len(cleaned_data)
            quality_score = self._calculate_overall_quality_score(cleaned_data)

            logger.info(
                "数据清洗完成",
                symbol=symbol,
                original_count=original_count,
                cleaned_count=cleaned_count,
                quality_score=quality_score
            )

            return cleaned_data

        except Exception as e:
            logger.error("数据清洗失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"数据清洗失败: {str(e)}")

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        try:
            # 列名映射表
            column_mapping = {
                # 日期列
                'date': 'date',
                'Date': 'date',
                '日期': 'date',
                '交易日期': 'date',
                'time': 'date',
                'Time': 'date',

                # 价格列
                'open': 'open_price',
                'Open': 'open_price',
                '开盘价': 'open_price',
                '开盘': 'open_price',

                'high': 'high_price',
                'High': 'high_price',
                '最高价': 'high_price',
                '最高': 'high_price',

                'low': 'low_price',
                'Low': 'low_price',
                '最低价': 'low_price',
                '最低': 'low_price',

                'close': 'close_price',
                'Close': 'close_price',
                '收盘价': 'close_price',
                '收盘': 'close_price',

                'settlement': 'settlement_price',
                'Settlement': 'settlement_price',
                '结算价': 'settlement_price',
                '结算': 'settlement_price',

                # 成交量列
                'volume': 'volume',
                'Volume': 'volume',
                '成交量': 'volume',
                '成交': 'volume',

                'turnover': 'turnover',
                'Turnover': 'turnover',
                '成交额': 'turnover',

                'open_interest': 'open_interest',
                'Open Interest': 'open_interest',
                'OpenInterest': 'open_interest',
                '持仓量': 'open_interest',
                '持仓': 'open_interest'
            }

            # 应用列名映射
            df = df.rename(columns=column_mapping)

            logger.debug("列名标准化完成", columns=list(df.columns))
            return df

        except Exception as e:
            logger.error("列名标准化失败", error=str(e))
            raise ProcessingError(f"列名标准化失败: {str(e)}")

    def _handle_missing_values(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """处理缺失值"""
        try:
            original_count = len(df)

            # 日期列不能为空
            if 'date' not in df.columns:
                raise ValidationError("缺少日期列")

            # 删除日期为空的行
            df = df.dropna(subset=['date'])

            # 价格数据：如果任何价格为空，删除该行
            price_cols = [col for col in self.price_columns if col in df.columns]
            if price_cols:
                df = df.dropna(subset=price_cols)

            # 成交量数据：填充为0
            volume_cols = [col for col in self.volume_columns if col in df.columns]
            for col in volume_cols:
                df[col] = df[col].fillna(0)

            # 其他数值列：使用前值填充
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col not in volume_cols:
                    df[col] = df[col].fillna(method='ffill')

            # 仍然为空的数值列用0填充
            df = df.fillna(0)

            removed_count = original_count - len(df)
            if removed_count > 0:
                logger.warning(
                    "删除包含缺失值的数据行",
                    symbol=symbol,
                    removed_count=removed_count,
                    remaining_count=len(df)
                )

            return df

        except Exception as e:
            logger.error("处理缺失值失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"处理缺失值失败: {str(e)}")

    def _convert_and_validate_types(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """数据类型转换和验证"""
        try:
            # 确保日期列为datetime类型
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # 删除日期转换失败的行
            df = df.dropna(subset=['date'])

            # 转换价格列为float类型
            for col in self.price_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 转换成交量为int类型
            for col in self.volume_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            # 验证价格数据范围
            for col in self.price_columns:
                if col in df.columns:
                    # 删除负价格
                    df = df[df[col] > 0]

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            logger.debug("数据类型转换完成", symbol=symbol, final_count=len(df))
            return df

        except Exception as e:
            logger.error("数据类型转换失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"数据类型转换失败: {str(e)}")

    def _validate_price_relationships(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """验证价格关系的合理性"""
        try:
            if not all(col in df.columns for col in ['high_price', 'low_price', 'open_price', 'close_price']):
                return df

            original_count = len(df)

            # 验证价格关系：high >= max(open, close) and low <= min(open, close)
            valid_high = df['high_price'] >= df[['open_price', 'close_price']].max(axis=1)
            valid_low = df['low_price'] <= df[['open_price', 'close_price']].min(axis=1)

            # 保留价格关系有效的行
            df = df[valid_high & valid_low].copy()

            removed_count = original_count - len(df)
            if removed_count > 0:
                logger.warning(
                    "删除价格关系异常的数据行",
                    symbol=symbol,
                    removed_count=removed_count,
                    remaining_count=len(df)
                )

            return df

        except Exception as e:
            logger.error("价格关系验证失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"价格关系验证失败: {str(e)}")

    def _detect_and_handle_outliers(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """检测和处理异常值"""
        try:
            if len(df) < 5:  # 数据太少，不进行异常值检测
                return df

            original_count = len(df)

            # 使用IQR方法检测价格异常值
            for col in self.price_columns:
                if col in df.columns:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1

                    # 定义异常值边界
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    # 标记异常值
                    outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                    outlier_count = outliers.sum()

                    if outlier_count > 0:
                        logger.warning(
                            "检测到价格异常值",
                            symbol=symbol,
                            column=col,
                            outlier_count=outlier_count,
                            lower_bound=lower_bound,
                            upper_bound=upper_bound
                        )

                        # 使用移动平均替换异常值
                        if outlier_count > 0:
                            rolling_mean = df[col].rolling(window=5, center=True).mean()
                            df.loc[outliers, col] = rolling_mean[outliers]

            # 检测成交量异常值（可能为数据错误）
            if 'volume' in df.columns:
                volume_median = df['volume'].median()
                volume_threshold = volume_median * 10  # 10倍中位数作为阈值

                volume_outliers = df['volume'] > volume_threshold
                volume_outlier_count = volume_outliers.sum()

                if volume_outlier_count > 0:
                    logger.warning(
                        "检测到成交量异常值",
                        symbol=symbol,
                        outlier_count=volume_outlier_count,
                        threshold=volume_threshold
                    )

                    # 使用中位数替换异常成交量
                    df.loc[volume_outliers, 'volume'] = volume_median

            logger.debug("异常值处理完成", symbol=symbol, final_count=len(df))
            return df

        except Exception as e:
            logger.error("异常值处理失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"异常值处理失败: {str(e)}")

    def _check_time_series_continuity(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """检查时间序列连续性"""
        try:
            if len(df) < 2:
                return df

            df = df.copy()
            df['date_diff'] = df['date'].diff()

            # 检测日期跳跃（超过7天的间隔）
            large_gaps = df['date_diff'] > pd.Timedelta(days=7)
            gap_count = large_gaps.sum()

            if gap_count > 0:
                gap_dates = df[large_gaps]['date'].tolist()
                logger.warning(
                    "检测到时间序列间隙",
                    symbol=symbol,
                    gap_count=gap_count,
                    gap_dates=gap_dates[:5]  # 只记录前5个间隙
                )

            # 检测重复日期
            duplicate_dates = df.duplicated(subset=['date'], keep=False)
            duplicate_count = duplicate_dates.sum()

            if duplicate_count > 0:
                logger.warning(
                    "检测到重复日期",
                    symbol=symbol,
                    duplicate_count=duplicate_count
                )
                # 保留每个日期的最后一条记录
                df = df.drop_duplicates(subset=['date'], keep='last')

            # 删除临时列
            df = df.drop(columns=['date_diff'])

            return df

        except Exception as e:
            logger.error("时间序列连续性检查失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"时间序列连续性检查失败: {str(e)}")

    def _calculate_quality_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算数据质量评分"""
        try:
            df = df.copy()

            # 初始化质量分数
            df['quality_score'] = 100.0

            # 检查数据完整性
            for col in self.price_columns + self.volume_columns:
                if col in df.columns:
                    completeness = (df[col].notna() & (df[col] > 0)).mean()
                    df['quality_score'] *= completeness

            # 检查价格一致性
            if all(col in df.columns for col in ['high_price', 'low_price']):
                price_consistency = (df['high_price'] >= df['low_price']).mean()
                df['quality_score'] *= price_consistency

            # 检查时间连续性（基于日期间隔）
            if len(df) > 1:
                date_gaps = df['date'].diff().dt.days
                normal_gaps = (date_gaps <= 7).mean()  # 7天内为正常间隔
                df['quality_score'] *= normal_gaps

            # 确保分数在0-100之间
            df['quality_score'] = df['quality_score'].clip(0, 100)

            return df

        except Exception as e:
            logger.error("质量评分计算失败", error=str(e))
            df['quality_score'] = 50.0  # 默认分数
            return df

    def _convert_to_market_data(self, df: pd.DataFrame, symbol: str) -> List[MarketData]:
        """转换为MarketData对象列表"""
        try:
            market_data_list = []

            for _, row in df.iterrows():
                try:
                    market_data = MarketData(
                        symbol=symbol,
                        date=row['date'],
                        open_price=float(row.get('open_price', 0)),
                        high_price=float(row.get('high_price', 0)),
                        low_price=float(row.get('low_price', 0)),
                        close_price=float(row.get('close_price', 0)),
                        volume=int(row.get('volume', 0)),
                        turnover=float(row.get('turnover', 0)) if pd.notna(row.get('turnover')) else None,
                        settlement_price=float(row.get('settlement_price', 0)) if pd.notna(row.get('settlement_price')) else None,
                        open_interest=int(row.get('open_interest', 0)) if pd.notna(row.get('open_interest')) else None
                    )
                    market_data_list.append(market_data)

                except Exception as e:
                    logger.warning(
                        "转换单行数据失败",
                        symbol=symbol,
                        date=row.get('date'),
                        error=str(e)
                    )
                    continue

            return market_data_list

        except Exception as e:
            logger.error("数据转换失败", error=str(e), symbol=symbol)
            raise ProcessingError(f"数据转换失败: {str(e)}")

    def _calculate_overall_quality_score(self, data_list: List[MarketData]) -> float:
        """计算整体质量评分"""
        try:
            if not data_list:
                return 0.0

            # 基于数据完整性计算整体评分
            completeness_scores = []
            consistency_scores = []

            for data in data_list:
                # 完整性评分
                completeness = 1.0
                if data.open_price <= 0: completeness -= 0.25
                if data.high_price <= 0: completeness -= 0.25
                if data.low_price <= 0: completeness -= 0.25
                if data.close_price <= 0: completeness -= 0.25
                completeness_scores.append(max(0, completeness))

                # 一致性评分
                consistency = 1.0
                if data.high_price < data.low_price: consistency -= 0.5
                if data.open_price <= 0 or data.close_price <= 0: consistency -= 0.5
                consistency_scores.append(max(0, consistency))

            overall_score = (
                np.mean(completeness_scores) * 0.6 +
                np.mean(consistency_scores) * 0.4
            ) * 100

            return round(overall_score, 2)

        except Exception as e:
            logger.error("整体质量评分计算失败", error=str(e))
            return 50.0

    async def get_data_quality_report(self, symbol: str, data_list: List[MarketData]) -> Dict[str, Any]:
        """生成数据质量报告"""
        try:
            if not data_list:
                return {
                    'symbol': symbol,
                    'total_records': 0,
                    'quality_score': 0.0,
                    'issues': ['无数据']
                }

            report = {
                'symbol': symbol,
                'total_records': len(data_list),
                'date_range': {
                    'start': min(d.date for d in data_list).isoformat(),
                    'end': max(d.date for d in data_list).isoformat()
                },
                'quality_score': self._calculate_overall_quality_score(data_list),
                'completeness': {},
                'consistency': {},
                'issues': []
            }

            # 完整性检查
            total_fields = len(self.price_columns + self.volume_columns)
            for col in self.price_columns + self.volume_columns:
                missing_count = sum(1 for d in data_list if getattr(d, col, None) in [0, None])
                report['completeness'][col] = {
                    'missing_count': missing_count,
                    'missing_rate': missing_count / len(data_list) if data_list else 0
                }

            # 一致性检查
            price_inconsistencies = sum(1 for d in data_list if d.high_price < d.low_price)
            report['consistency']['price_relationship'] = {
                'inconsistencies': price_inconsistencies,
                'inconsistency_rate': price_inconsistencies / len(data_list) if data_list else 0
            }

            # 生成问题列表
            if report['quality_score'] < 80:
                report['issues'].append('数据质量评分较低')

            if any(info['missing_rate'] > 0.1 for info in report['completeness'].values()):
                report['issues'].append('存在较多缺失值')

            if report['consistency']['price_relationship']['inconsistency_rate'] > 0.05:
                report['issues'].append('存在价格关系异常')

            return report

        except Exception as e:
            logger.error("生成数据质量报告失败", error=str(e), symbol=symbol)
            return {
                'symbol': symbol,
                'error': str(e),
                'quality_score': 0.0
            }