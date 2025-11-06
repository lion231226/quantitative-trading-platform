"""
Log Analyzer Module

This module provides comprehensive log analysis and search functionality
for filtering, pattern detection, and statistical analysis of logs.
"""

import re
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
import json

from core.log_manager import LogManager, LogEntry, LogFilter, LogLevel, LogCategory
from utils.logger import get_logger


class AnalysisType(Enum):
    """分析类型"""
    FREQUENCY = "frequency"
    PATTERN = "pattern"
    TREND = "trend"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"
    PERFORMANCE = "performance"


@dataclass
class PatternMatch:
    """模式匹配结果"""
    pattern: str
    matches: List[LogEntry]
    count: int
    first_seen: datetime
    last_seen: datetime
    frequency: float  # 每分钟匹配次数

@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: AnalysisType
    timestamp: datetime = field(default_factory=datetime.now)
    summary: Dict[str, Any] = field(default_factory=dict)
    details: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[PatternMatch] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class LogStatistics:
    """日志统计信息"""
    total_entries: int
    time_range: Tuple[datetime, datetime]
    level_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    component_distribution: Dict[str, int]
    hourly_distribution: Dict[int, int]
    error_patterns: List[PatternMatch]
    performance_metrics: Dict[str, float]


class LogAnalyzer:
    """
    日志分析器，提供高级日志搜索、模式识别和统计分析功能
    """

    def __init__(self, log_manager: LogManager, config: Dict[str, Any] = None):
        """
        初始化日志分析器

        Args:
            log_manager: 日志管理器实例
            config: 分析器配置
        """
        self.logger = get_logger(self.__class__.__name__)
        self.log_manager = log_manager
        self.config = config or self._get_default_config()

        # 预定义模式
        self.patterns = self._initialize_patterns()

        # 分析缓存
        self._analysis_cache: Dict[str, AnalysisResult] = {}
        self._cache_timeout = self.config.get("cache_timeout", 300)  # 5分钟

        # 异步分析
        self._analysis_threads: Dict[str, threading.Thread] = {}
        self._analysis_results: Dict[str, AnalysisResult] = {}

        self.logger.info("Log Analyzer initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "cache_timeout": 300,
            "max_patterns": 100,
            "min_pattern_frequency": 3,
            "anomaly_threshold": 2.0,  # 标准差倍数
            "trend_window_minutes": 60,
            "correlation_threshold": 0.7,
            "performance_slow_threshold": 5.0,  # 秒
            "enable_async_analysis": True,
            "max_analysis_threads": 3
        }

    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """初始化预定义模式"""
        return {
            "error_patterns": {
                "connection_failed": {
                    "regex": r"connection.*failed|connection.*refused|unable.*connect",
                    "severity": "high",
                    "category": "network"
                },
                "permission_denied": {
                    "regex": r"permission.*denied|access.*denied|unauthorized",
                    "severity": "high",
                    "category": "security"
                },
                "file_not_found": {
                    "regex": r"file.*not.*found|no.*such.*file|path.*not.*found",
                    "severity": "medium",
                    "category": "filesystem"
                },
                "timeout": {
                    "regex": r"timeout|timed.*out|deadline.*exceeded",
                    "severity": "medium",
                    "category": "performance"
                },
                "out_of_memory": {
                    "regex": r"out.*of.*memory|memory.*exhausted|cannot.*allocate",
                    "severity": "critical",
                    "category": "system"
                },
                "disk_full": {
                    "regex": r"disk.*full|no.*space.*left|storage.*full",
                    "severity": "critical",
                    "category": "system"
                },
                "database_error": {
                    "regex": r"database.*error|sql.*error|connection.*pool.*exhausted",
                    "severity": "high",
                    "category": "database"
                },
                "api_error": {
                    "regex": r"api.*error|http.*error|status.*code.*[45]\\d\\d",
                    "severity": "medium",
                    "category": "api"
                }
            },
            "performance_patterns": {
                "slow_request": {
                    "regex": r"slow.*request|request.*took|response.*time.*\\d+s",
                    "severity": "medium",
                    "category": "performance"
                },
                "high_cpu": {
                    "regex": r"cpu.*usage.*high|high.*cpu.*usage",
                    "severity": "medium",
                    "category": "performance"
                },
                "high_memory": {
                    "regex": r"memory.*usage.*high|high.*memory.*usage",
                    "severity": "medium",
                    "category": "performance"
                }
            },
            "security_patterns": {
                "login_failed": {
                    "regex": r"login.*failed|authentication.*failed|invalid.*credentials",
                    "severity": "high",
                    "category": "security"
                },
                "suspicious_activity": {
                    "regex": r"suspicious.*activity|unusual.*access|potential.*attack",
                    "severity": "critical",
                    "category": "security"
                },
                "brute_force": {
                    "regex": r"brute.*force|multiple.*failed.*login|too.*many.*attempts",
                    "severity": "critical",
                    "category": "security"
                }
            }
        }

    def search_logs(self, query: str, filters: LogFilter = None,
                   use_regex: bool = False, case_sensitive: bool = False) -> List[LogEntry]:
        """
        搜索日志

        Args:
            query: 搜索查询
            filters: 日志过滤器
            use_regex: 是否使用正则表达式
            case_sensitive: 是否区分大小写

        Returns:
            匹配的日志条目列表
        """
        try:
            # 收集日志
            logs = self.log_manager.collect_logs(filters)

            if not query:
                return logs

            # 准备搜索模式
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(query, flags)
            else:
                if case_sensitive:
                    pattern = lambda text: query in text
                else:
                    query_lower = query.lower()
                    pattern = lambda text: query_lower in text.lower()

            # 执行搜索
            matches = []
            for log in logs:
                # 搜索消息
                if use_regex:
                    if pattern.search(log.message):
                        matches.append(log)
                        continue
                else:
                    if pattern(log.message):
                        matches.append(log)
                        continue

                # 搜索详细信息
                details_str = str(log.details)
                if use_regex:
                    if pattern.search(details_str):
                        matches.append(log)
                        continue
                else:
                    if pattern(details_str):
                        matches.append(log)
                        continue

                # 搜索异常信息
                if log.exception_info:
                    if use_regex:
                        if pattern.search(log.exception_info):
                            matches.append(log)
                            continue
                    else:
                        if pattern(log.exception_info):
                            matches.append(log)
                            continue

            return matches

        except Exception as e:
            self.logger.error(f"Error searching logs: {e}")
            return []

    def analyze_patterns(self, logs: List[LogEntry] = None,
                        pattern_types: List[str] = None) -> AnalysisResult:
        """
        分析日志模式

        Args:
            logs: 日志列表（如果为None则使用所有日志）
            pattern_types: 要分析的模式类型列表

        Returns:
            分析结果
        """
        try:
            start_time = time.time()

            # 获取日志
            if logs is None:
                logs = self.log_manager.collect_logs()

            if not logs:
                return AnalysisResult(
                    analysis_type=AnalysisType.PATTERN,
                    summary={"total_logs": 0, "patterns_found": 0}
                )

            # 确定要分析的模式类型
            if pattern_types is None:
                pattern_types = list(self.patterns.keys())

            # 分析每种模式
            all_matches = []
            pattern_stats = defaultdict(int)

            for pattern_type in pattern_types:
                if pattern_type not in self.patterns:
                    continue

                type_patterns = self.patterns[pattern_type]
                for pattern_name, pattern_config in type_patterns.items():
                    try:
                        matches = self._find_pattern_matches(logs, pattern_config)
                        if matches:
                            all_matches.extend(matches)
                            pattern_stats[pattern_name] = len(matches)
                    except Exception as e:
                        self.logger.error(f"Error analyzing pattern {pattern_name}: {e}")

            # 计算统计信息
            total_patterns = len(all_matches)
            unique_patterns = len(set(match.pattern for match in all_matches))

            # 生成建议
            recommendations = self._generate_pattern_recommendations(all_matches)

            analysis_time = time.time() - start_time

            return AnalysisResult(
                analysis_type=AnalysisType.PATTERN,
                summary={
                    "total_logs": len(logs),
                    "patterns_found": total_patterns,
                    "unique_patterns": unique_patterns,
                    "analysis_time_seconds": analysis_time
                },
                patterns=all_matches,
                statistics=dict(pattern_stats),
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.PATTERN,
                summary={"error": str(e)}
            )

    def _find_pattern_matches(self, logs: List[LogEntry],
                            pattern_config: Dict[str, Any]) -> List[PatternMatch]:
        """查找模式匹配"""
        regex = pattern_config["regex"]
        severity = pattern_config["severity"]
        category = pattern_config["category"]

        try:
            pattern = re.compile(regex, re.IGNORECASE)
        except re.error as e:
            self.logger.error(f"Invalid regex pattern {regex}: {e}")
            return []

        matches = []
        for log in logs:
            # 在消息中搜索
            if pattern.search(log.message):
                matches.append(log)
                continue

            # 在详细信息中搜索
            details_str = str(log.details)
            if pattern.search(details_str):
                matches.append(log)
                continue

            # 在异常信息中搜索
            if log.exception_info and pattern.search(log.exception_info):
                matches.append(log)

        if not matches:
            return []

        # 计算时间范围和频率
        timestamps = [log.timestamp for log in matches]
        first_seen = min(timestamps)
        last_seen = max(timestamps)
        time_span_minutes = (last_seen - first_seen).total_seconds() / 60
        frequency = len(matches) / max(time_span_minutes, 1)

        return [PatternMatch(
            pattern=regex,
            matches=matches,
            count=len(matches),
            first_seen=first_seen,
            last_seen=last_seen,
            frequency=frequency
        )]

    def _generate_pattern_recommendations(self, pattern_matches: List[PatternMatch]) -> List[str]:
        """生成模式分析建议"""
        recommendations = []

        if not pattern_matches:
            return recommendations

        # 分析高频错误模式
        high_freq_patterns = [p for p in pattern_matches if p.frequency > 1.0]
        if high_freq_patterns:
            recommendations.append(
                f"发现 {len(high_freq_patterns)} 个高频错误模式，建议优先处理"
            )

        # 分析最近错误
        recent_time = datetime.now() - timedelta(hours=1)
        recent_patterns = [p for p in pattern_matches if p.last_seen > recent_time]
        if recent_patterns:
            recommendations.append(
                f"最近1小时内发现 {len(recent_patterns)} 个错误模式，需要立即关注"
            )

        # 分析重复模式
        if len(set(p.pattern for p in pattern_matches)) < len(pattern_matches):
            recommendations.append("检测到重复的错误模式，建议查找根本原因")

        return recommendations

    def analyze_trends(self, logs: List[LogEntry] = None,
                      window_minutes: int = None) -> AnalysisResult:
        """
        分析日志趋势

        Args:
            logs: 日志列表
            window_minutes: 时间窗口（分钟）

        Returns:
            分析结果
        """
        try:
            if logs is None:
                logs = self.log_manager.collect_logs()

            if not logs:
                return AnalysisResult(
                    analysis_type=AnalysisType.TREND,
                    summary={"total_logs": 0}
                )

            # 设置时间窗口
            if window_minutes is None:
                window_minutes = self.config.get("trend_window_minutes", 60)

            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_logs = [log for log in logs if log.timestamp >= cutoff_time]

            if not recent_logs:
                return AnalysisResult(
                    analysis_type=AnalysisType.TREND,
                    summary={"total_logs": 0, "window_minutes": window_minutes}
                )

            # 按时间分组统计
            time_buckets = defaultdict(lambda: defaultdict(int))
            for log in recent_logs:
                # 按分钟分组
                minute_bucket = log.timestamp.replace(second=0, microsecond=0)
                time_buckets[minute_bucket][log.level.value] += 1
                time_buckets[minute_bucket][log.category.value] += 1

            # 转换为时间序列数据
            timeline = []
            for minute in sorted(time_buckets.keys()):
                bucket_data = dict(time_buckets[minute])
                bucket_data["timestamp"] = minute.isoformat()
                bucket_data["total"] = sum(bucket_data.get(level, 0)
                                        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                                        if level in bucket_data)
                timeline.append(bucket_data)

            # 计算趋势
            trend_analysis = self._calculate_trends(timeline)

            # 生成建议
            recommendations = self._generate_trend_recommendations(trend_analysis)

            return AnalysisResult(
                analysis_type=AnalysisType.TREND,
                summary={
                    "total_logs": len(recent_logs),
                    "window_minutes": window_minutes,
                    "time_buckets": len(time_buckets)
                },
                details=timeline,
                statistics=trend_analysis,
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.TREND,
                summary={"error": str(e)}
            )

    def _calculate_trends(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算趋势统计"""
        if len(timeline) < 2:
            return {"trend": "insufficient_data"}

        # 计算总日志数的趋势
        totals = [bucket["total"] for bucket in timeline]
        total_trend = self._calculate_simple_trend(totals)

        # 计算错误级别的趋势
        error_totals = [bucket.get("ERROR", 0) + bucket.get("CRITICAL", 0) for bucket in timeline]
        error_trend = self._calculate_simple_trend(error_totals)

        # 计算平均和峰值
        avg_total = sum(totals) / len(totals)
        peak_total = max(totals)
        peak_time = timeline[totals.index(peak_total)]["timestamp"]

        return {
            "total_trend": total_trend,
            "error_trend": error_trend,
            "average_per_minute": avg_total,
            "peak_per_minute": peak_total,
            "peak_time": peak_time,
            "data_points": len(timeline)
        }

    def _calculate_simple_trend(self, values: List[float]) -> str:
        """计算简单趋势"""
        if len(values) < 2:
            return "unknown"

        # 简单的线性趋势计算
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        change_percent = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        if change_percent > 20:
            return "increasing"
        elif change_percent < -20:
            return "decreasing"
        else:
            return "stable"

    def _generate_trend_recommendations(self, trend_analysis: Dict[str, Any]) -> List[str]:
        """生成趋势分析建议"""
        recommendations = []

        if trend_analysis.get("total_trend") == "increasing":
            recommendations.append("日志总量呈上升趋势，建议关注系统负载")

        if trend_analysis.get("error_trend") == "increasing":
            recommendations.append("错误日志呈上升趋势，建议立即检查系统状态")

        if trend_analysis.get("peak_per_minute", 0) > trend_analysis.get("average_per_minute", 0) * 3:
            recommendations.append("检测到日志峰值异常，可能存在突发问题")

        return recommendations

    def get_statistics(self, logs: List[LogEntry] = None) -> LogStatistics:
        """
        获取日志统计信息

        Args:
            logs: 日志列表

        Returns:
            统计信息
        """
        try:
            if logs is None:
                logs = self.log_manager.collect_logs()

            if not logs:
                return LogStatistics(
                    total_entries=0,
                    time_range=(datetime.now(), datetime.now()),
                    level_distribution={},
                    category_distribution={},
                    component_distribution={},
                    hourly_distribution={},
                    error_patterns=[],
                    performance_metrics={}
                )

            # 基本统计
            total_entries = len(logs)
            timestamps = [log.timestamp for log in logs]
            time_range = (min(timestamps), max(timestamps))

            # 级别分布
            level_distribution = Counter(log.level.value for log in logs)

            # 分类分布
            category_distribution = Counter(log.category.value for log in logs)

            # 组件分布
            component_distribution = Counter(log.component for log in logs)

            # 小时分布
            hourly_distribution = Counter(log.timestamp.hour for log in logs)

            # 错误模式分析
            error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
            error_pattern_result = self.analyze_patterns(error_logs, ["error_patterns"])
            error_patterns = error_pattern_result.patterns

            # 性能指标
            performance_metrics = self._calculate_performance_metrics(logs)

            return LogStatistics(
                total_entries=total_entries,
                time_range=time_range,
                level_distribution=dict(level_distribution),
                category_distribution=dict(category_distribution),
                component_distribution=dict(component_distribution),
                hourly_distribution=dict(hourly_distribution),
                error_patterns=error_patterns,
                performance_metrics=performance_metrics
            )

        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            return LogStatistics(
                total_entries=0,
                time_range=(datetime.now(), datetime.now()),
                level_distribution={},
                category_distribution={},
                component_distribution={},
                hourly_distribution={},
                error_patterns=[],
                performance_metrics={}
            )

    def _calculate_performance_metrics(self, logs: List[LogEntry]) -> Dict[str, float]:
        """计算性能指标"""
        metrics = {}

        try:
            # 日志频率（每分钟）
            if len(logs) > 1:
                time_span = (logs[-1].timestamp - logs[0].timestamp).total_seconds() / 60
                metrics["logs_per_minute"] = len(logs) / max(time_span, 1)

            # 错误率
            error_count = sum(1 for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL])
            metrics["error_rate"] = (error_count / len(logs)) * 100 if logs else 0

            # 警告率
            warning_count = sum(1 for log in logs if log.level == LogLevel.WARNING)
            metrics["warning_rate"] = (warning_count / len(logs)) * 100 if logs else 0

            # 唯一组件数
            unique_components = len(set(log.component for log in logs))
            metrics["unique_components"] = unique_components

        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")

        return metrics

    def detect_anomalies(self, logs: List[LogEntry] = None) -> AnalysisResult:
        """
        检测异常

        Args:
            logs: 日志列表

        Returns:
            异常检测结果
        """
        try:
            if logs is None:
                logs = self.log_manager.collect_logs()

            if not logs:
                return AnalysisResult(
                    analysis_type=AnalysisType.ANOMALY,
                    summary={"total_logs": 0, "anomalies_found": 0}
                )

            anomalies = []

            # 检测频率异常
            frequency_anomalies = self._detect_frequency_anomalies(logs)
            anomalies.extend(frequency_anomalies)

            # 检测错误激增
            error_spikes = self._detect_error_spikes(logs)
            anomalies.extend(error_spikes)

            # 检测新错误模式
            new_patterns = self._detect_new_error_patterns(logs)
            anomalies.extend(new_patterns)

            # 生成建议
            recommendations = self._generate_anomaly_recommendations(anomalies)

            return AnalysisResult(
                analysis_type=AnalysisType.ANOMALY,
                summary={
                    "total_logs": len(logs),
                    "anomalies_found": len(anomalies)
                },
                details=anomalies,
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.ANOMALY,
                summary={"error": str(e)}
            )

    def _detect_frequency_anomalies(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """检测频率异常"""
        anomalies = []

        try:
            # 按分钟分组统计日志数量
            minute_counts = defaultdict(int)
            for log in logs:
                minute = log.timestamp.replace(second=0, microsecond=0)
                minute_counts[minute] += 1

            if len(minute_counts) < 3:
                return anomalies

            # 计算平均值和标准差
            counts = list(minute_counts.values())
            mean_count = sum(counts) / len(counts)
            variance = sum((x - mean_count) ** 2 for x in counts) / len(counts)
            std_dev = variance ** 0.5

            threshold = self.config.get("anomaly_threshold", 2.0)

            # 检测异常
            for minute, count in minute_counts.items():
                if abs(count - mean_count) > threshold * std_dev:
                    anomalies.append({
                        "type": "frequency_anomaly",
                        "timestamp": minute.isoformat(),
                        "value": count,
                        "expected": mean_count,
                        "severity": "high" if count > mean_count + threshold * std_dev else "medium"
                    })

        except Exception as e:
            self.logger.error(f"Error detecting frequency anomalies: {e}")

        return anomalies

    def _detect_error_spikes(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """检测错误激增"""
        anomalies = []

        try:
            # 按分钟分组统计错误数量
            error_counts = defaultdict(int)
            for log in logs:
                if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                    minute = log.timestamp.replace(second=0, microsecond=0)
                    error_counts[minute] += 1

            if len(error_counts) < 3:
                return anomalies

            # 检测激增
            error_values = list(error_counts.values())
            mean_errors = sum(error_values) / len(error_values)

            threshold = mean_errors * 2  # 错误数量超过平均值2倍

            for minute, count in error_counts.items():
                if count > threshold:
                    anomalies.append({
                        "type": "error_spike",
                        "timestamp": minute.isoformat(),
                        "value": count,
                        "threshold": threshold,
                        "severity": "critical" if count > threshold * 2 else "high"
                    })

        except Exception as e:
            self.logger.error(f"Error detecting error spikes: {e}")

        return anomalies

    def _detect_new_error_patterns(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """检测新的错误模式"""
        anomalies = []

        try:
            # 获取最近的错误日志
            recent_time = datetime.now() - timedelta(hours=1)
            recent_errors = [log for log in logs
                           if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
                           and log.timestamp >= recent_time]

            if not recent_errors:
                return anomalies

            # 获取历史错误日志
            historical_time = datetime.now() - timedelta(days=7)
            historical_errors = [log for log in logs
                               if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
                               and log.timestamp < recent_time
                               and log.timestamp >= historical_time]

            # 分析最近的错误消息模式
            recent_patterns = set()
            for log in recent_errors:
                # 简单的模式提取（可以改进）
                pattern = self._extract_error_pattern(log.message)
                if pattern:
                    recent_patterns.add(pattern)

            # 检查哪些模式在历史中不存在
            historical_patterns = set()
            for log in historical_errors:
                pattern = self._extract_error_pattern(log.message)
                if pattern:
                    historical_patterns.add(pattern)

            new_patterns = recent_patterns - historical_patterns

            for pattern in new_patterns:
                # 统计这个新模式在最近的错误中出现次数
                count = sum(1 for log in recent_errors
                          if self._extract_error_pattern(log.message) == pattern)

                anomalies.append({
                    "type": "new_error_pattern",
                    "pattern": pattern,
                    "count": count,
                    "first_seen": recent_time.isoformat(),
                    "severity": "medium"
                })

        except Exception as e:
            self.logger.error(f"Error detecting new error patterns: {e}")

        return anomalies

    def _extract_error_pattern(self, message: str) -> str:
        """提取错误模式"""
        # 简单的模式提取：移除具体的数字、路径、时间戳等
        import re
        pattern = re.sub(r'\d+', 'N', message)  # 数字替换为N
        pattern = re.sub(r'[a-zA-Z]:\\[^\\s]*', 'PATH', pattern)  # Windows路径
        pattern = re.sub(r'/[^\\s]*', 'PATH', pattern)  # Unix路径
        pattern = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', 'DATE', pattern)  # 日期
        pattern = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', 'TIME', pattern)  # 时间
        return pattern.strip()

    def _generate_anomaly_recommendations(self, anomalies: List[Dict[str, Any]]) -> List[str]:
        """生成异常检测建议"""
        recommendations = []

        if not anomalies:
            return recommendations

        # 按类型统计异常
        anomaly_types = Counter(anomaly["type"] for anomaly in anomalies)

        if "error_spike" in anomaly_types:
            recommendations.append("检测到错误激增，建议立即检查系统状态")

        if "frequency_anomaly" in anomaly_types:
            recommendations.append("检测到日志频率异常，可能存在系统问题")

        if "new_error_pattern" in anomaly_types:
            recommendations.append("发现新的错误模式，建议分析根本原因")

        # 按严重程度统计
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        if critical_anomalies:
            recommendations.append(f"发现 {len(critical_anomalies)} 个严重异常，需要立即处理")

        return recommendations

    def export_analysis(self, analysis_result: AnalysisResult, format: str = "json") -> str:
        """
        导出分析结果

        Args:
            analysis_result: 分析结果
            format: 导出格式

        Returns:
            导出的字符串
        """
        try:
            if format.lower() == "json":
                # 转换为可序列化的格式
                export_data = {
                    "analysis_type": analysis_result.analysis_type.value,
                    "timestamp": analysis_result.timestamp.isoformat(),
                    "summary": analysis_result.summary,
                    "details": analysis_result.details,
                    "statistics": analysis_result.statistics,
                    "recommendations": analysis_result.recommendations
                }

                # 处理模式匹配
                if analysis_result.patterns:
                    export_data["patterns"] = [
                        {
                            "pattern": match.pattern,
                            "count": match.count,
                            "first_seen": match.first_seen.isoformat(),
                            "last_seen": match.last_seen.isoformat(),
                            "frequency": match.frequency
                        }
                        for match in analysis_result.patterns
                    ]

                return json.dumps(export_data, indent=2, ensure_ascii=False)

            elif format.lower() == "txt":
                lines = []
                lines.append(f"Analysis Type: {analysis_result.analysis_type.value}")
                lines.append(f"Timestamp: {analysis_result.timestamp}")
                lines.append(f"Summary: {analysis_result.summary}")
                lines.append("")

                if analysis_result.recommendations:
                    lines.append("Recommendations:")
                    for rec in analysis_result.recommendations:
                        lines.append(f"  - {rec}")
                    lines.append("")

                if analysis_result.patterns:
                    lines.append("Patterns Found:")
                    for match in analysis_result.patterns:
                        lines.append(f"  - {match.pattern}: {match.count} occurrences")
                    lines.append("")

                return "\n".join(lines)

            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            self.logger.error(f"Error exporting analysis: {e}")
            return f"Error exporting analysis: {e}"