"""
数据一致性验证器

验证跨组件的数据一致性，确保数据在不同系统组件之间保持完整和准确。
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsistencyStatus(Enum):
    """一致性状态枚举"""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    PARTIALLY_CONSISTENT = "partially_consistent"
    VALIDATION_ERROR = "validation_error"
    INSUFFICIENT_DATA = "insufficient_data"


class ValidationSeverity(Enum):
    """验证严重性级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataConsistencyConfig:
    """数据一致性配置"""
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    tolerance_thresholds: Dict[str, float] = field(default_factory=dict)
    consistency_checks: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    max_retries: int = 3
    sample_size: int = 1000


@dataclass
class ConsistencyViolation:
    """一致性违规"""
    rule_name: str
    severity: ValidationSeverity
    component_a: str
    component_b: str
    field_name: Optional[str]
    expected_value: Any
    actual_value: Any
    deviation: float
    description: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataConsistencyTestResult:
    """数据一致性测试结果"""
    test_id: str
    status: ConsistencyStatus
    start_time: datetime
    end_time: datetime
    total_records_checked: int
    violations: List[ConsistencyViolation] = field(default_factory=list)
    consistency_score: float = 0.0
    validation_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSnapshot:
    """数据快照"""
    component: str
    timestamp: datetime
    data_hash: str
    record_count: int
    sample_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataConsistencyValidator:
    """数据一致性验证器"""

    def __init__(self, config: DataConsistencyConfig):
        self.config = config
        self.test_history: List[DataConsistencyTestResult] = []
        self.data_snapshots: List[DataSnapshot] = []

    async def validate_cross_component_consistency(
        self,
        components: List[str],
        test_scenarios: Optional[List[Dict[str, Any]]] = None
    ) -> List[DataConsistencyTestResult]:
        """验证跨组件数据一致性"""
        logger.info(f"开始跨组件数据一致性验证，涉及组件: {components}")

        if test_scenarios is None:
            test_scenarios = self._generate_default_consistency_scenarios()

        results = []

        for scenario in test_scenarios:
            result = await self._validate_single_consistency_scenario(components, scenario)
            results.append(result)
            self.test_history.append(result)

        logger.info(f"跨组件一致性验证完成，共 {len(results)} 个测试")
        return results

    def _generate_default_consistency_scenarios(self) -> List[Dict[str, Any]]:
        """生成默认一致性验证场景"""
        return [
            {
                "test_id": "price_data_consistency",
                "data_type": "market_data",
                "key_fields": ["symbol", "timestamp"],
                "value_fields": ["price", "volume"],
                "time_window_minutes": 60,
                "tolerance_percent": 0.01
            },
            {
                "test_id": "strategy_results_consistency",
                "data_type": "strategy_results",
                "key_fields": ["strategy_id", "timestamp"],
                "value_fields": ["return", "sharpe_ratio", "max_drawdown"],
                "time_window_minutes": 1440,  # 24小时
                "tolerance_percent": 0.001
            },
            {
                "test_id": "portfolio_consistency",
                "data_type": "portfolio_data",
                "key_fields": ["portfolio_id", "timestamp"],
                "value_fields": ["total_value", "cash", "positions"],
                "time_window_minutes": 30,
                "tolerance_percent": 0.01
            }
        ]

    async def _validate_single_consistency_scenario(
        self,
        components: List[str],
        scenario: Dict[str, Any]
    ) -> DataConsistencyTestResult:
        """验证单个一致性场景"""
        test_id = scenario["test_id"]
        start_time = datetime.now()

        logger.info(f"验证一致性场景: {test_id}")

        try:
            # 步骤1: 从各组件获取数据快照
            snapshots = await self._capture_data_snapshots(components, scenario)

            if len(snapshots) < 2:
                return DataConsistencyTestResult(
                    test_id=test_id,
                    status=ConsistencyStatus.INSUFFICIENT_DATA,
                    start_time=start_time,
                    end_time=datetime.now(),
                    total_records_checked=0,
                    consistency_score=0.0,
                    validation_summary={"error": "无法获取足够的数据快照"}
                )

            # 步骤2: 执行一致性检查
            violations = await self._perform_consistency_checks(snapshots, scenario)

            # 步骤3: 计算一致性评分
            consistency_score = self._calculate_consistency_score(violations, scenario)

            # 步骤4: 确定总体状态
            status = self._determine_consistency_status(consistency_score, violations)

            end_time = datetime.now()
            total_records = sum(snapshot.record_count for snapshot in snapshots)

            return DataConsistencyTestResult(
                test_id=test_id,
                status=status,
                start_time=start_time,
                end_time=end_time,
                total_records_checked=total_records,
                violations=violations,
                consistency_score=consistency_score,
                validation_summary={
                    "components_tested": components,
                    "snapshots_taken": len(snapshots),
                    "violations_by_severity": self._count_violations_by_severity(violations),
                    "test_duration_seconds": (end_time - start_time).total_seconds()
                }
            )

        except Exception as e:
            logger.error(f"一致性验证 {test_id} 失败: {str(e)}")
            return DataConsistencyTestResult(
                test_id=test_id,
                status=ConsistencyStatus.VALIDATION_ERROR,
                start_time=start_time,
                end_time=datetime.now(),
                total_records_checked=0,
                violations=[],
                consistency_score=0.0,
                validation_summary={"error": str(e)}
            )

    async def _capture_data_snapshots(
        self,
        components: List[str],
        scenario: Dict[str, Any]
    ) -> List[DataSnapshot]:
        """捕获数据快照"""
        snapshots = []

        for component in components:
            try:
                snapshot = await self._capture_component_snapshot(component, scenario)
                if snapshot:
                    snapshots.append(snapshot)
                    self.data_snapshots.append(snapshot)
            except Exception as e:
                logger.error(f"捕获组件 {component} 快照失败: {str(e)}")

        return snapshots

    async def _capture_component_snapshot(
        self,
        component: str,
        scenario: Dict[str, Any]
    ) -> Optional[DataSnapshot]:
        """捕获单个组件的数据快照"""
        try:
            # 模拟数据获取
            await asyncio.sleep(0.1)  # 模拟网络延迟

            # 生成模拟数据
            mock_data = self._generate_mock_data(component, scenario)

            # 计算数据哈希
            data_hash = self._calculate_data_hash(mock_data)

            snapshot = DataSnapshot(
                component=component,
                timestamp=datetime.now(),
                data_hash=data_hash,
                record_count=len(mock_data),
                sample_data=mock_data[:self.config.sample_size],
                metadata={
                    "scenario": scenario["test_id"],
                    "data_type": scenario["data_type"]
                }
            )

            logger.info(f"组件 {component} 快照捕获完成，记录数: {len(mock_data)}")
            return snapshot

        except Exception as e:
            logger.error(f"捕获组件 {component} 快照时出错: {str(e)}")
            return None

    def _generate_mock_data(self, component: str, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成模拟数据"""
        data_type = scenario["data_type"]
        key_fields = scenario["key_fields"]
        value_fields = scenario["value_fields"]
        time_window = scenario["time_window_minutes"]

        # 基础时间戳
        base_time = datetime.now() - timedelta(minutes=time_window)

        mock_data = []

        # 生成不同数量的记录以模拟差异
        if component == "database":
            record_count = 100
        elif component == "backend":
            record_count = 98  # 轻微差异
        elif component == "frontend":
            record_count = 102  # 轻微差异
        else:
            record_count = 100

        for i in range(record_count):
            record = {}

            # 添加键字段
            for field in key_fields:
                if field == "timestamp":
                    record[field] = (base_time + timedelta(minutes=i * time_window // record_count)).isoformat()
                elif field == "symbol":
                    record[field] = f"SYMBOL_{i % 10}"
                elif field == "strategy_id":
                    record[field] = f"STRATEGY_{i % 5}"
                elif field == "portfolio_id":
                    record[field] = f"PORTFOLIO_{i % 3}"
                else:
                    record[field] = f"{field}_{i}"

            # 添加值字段，加入轻微差异以测试一致性
            for field in value_fields:
                if field in ["price", "total_value"]:
                    base_value = 100 + (i % 20)
                    # 为不同组件添加轻微差异
                    if component == "backend":
                        base_value *= 1.001  # 0.1% 差异
                    elif component == "frontend":
                        base_value *= 0.999  # -0.1% 差异
                    record[field] = round(base_value, 2)
                elif field in ["volume", "cash"]:
                    record[field] = 1000000 + (i * 1000)
                elif field in ["return", "sharpe_ratio"]:
                    record[field] = 0.05 + (i % 10) * 0.01
                elif field == "max_drawdown":
                    record[field] = -0.02 - (i % 5) * 0.005
                elif field == "positions":
                    record[field] = [{"symbol": f"SYMBOL_{j}", "quantity": 100 + j} for j in range(i % 5)]
                else:
                    record[field] = f"value_{i}"

            mock_data.append(record)

        return mock_data

    def _calculate_data_hash(self, data: List[Dict[str, Any]]) -> str:
        """计算数据哈希"""
        # 对数据进行排序以确保一致性
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(sorted_data.encode()).hexdigest()

    async def _perform_consistency_checks(
        self,
        snapshots: List[DataSnapshot],
        scenario: Dict[str, Any]
    ) -> List[ConsistencyViolation]:
        """执行一致性检查"""
        violations = []

        # 获取所有键字段
        key_fields = scenario["key_fields"]
        value_fields = scenario["value_fields"]
        tolerance_percent = scenario.get("tolerance_percent", 0.01)

        # 检查数据哈希一致性
        if len(set(snapshot.data_hash for snapshot in snapshots)) > 1:
            violations.append(ConsistencyViolation(
                rule_name="data_hash_consistency",
                severity=ValidationSeverity.ERROR,
                component_a=snapshots[0].component,
                component_b=snapshots[1].component,
                field_name=None,
                expected_value=snapshots[0].data_hash,
                actual_value=snapshots[1].data_hash,
                deviation=1.0,
                description="不同组件的数据哈希不一致"
            ))

        # 检查记录数量一致性
        record_counts = [snapshot.record_count for snapshot in snapshots]
        if len(set(record_counts)) > 1:
            max_count = max(record_counts)
            min_count = min(record_counts)
            deviation = (max_count - min_count) / max_count if max_count > 0 else 1.0

            violations.append(ConsistencyViolation(
                rule_name="record_count_consistency",
                severity=ValidationSeverity.WARNING if deviation < 0.05 else ValidationSeverity.ERROR,
                component_a=snapshots[record_counts.index(min_count)].component,
                component_b=snapshots[record_counts.index(max_count)].component,
                field_name="record_count",
                expected_value=max_count,
                actual_value=min_count,
                deviation=deviation,
                description=f"记录数量差异: {min_count} vs {max_count}"
            ))

        # 检查数值字段一致性
        for i in range(len(snapshots)):
            for j in range(i + 1, len(snapshots)):
                snapshot_a = snapshots[i]
                snapshot_b = snapshots[j]

                value_violations = await self._check_value_consistency(
                    snapshot_a, snapshot_b, value_fields, tolerance_percent
                )
                violations.extend(value_violations)

        return violations

    async def _check_value_consistency(
        self,
        snapshot_a: DataSnapshot,
        snapshot_b: DataSnapshot,
        value_fields: List[str],
        tolerance_percent: float
    ) -> List[ConsistencyViolation]:
        """检查数值字段一致性"""
        violations = []

        # 创建数据映射以便比较
        data_map_a = self._create_data_mapping(snapshot_a.sample_data)
        data_map_b = self._create_data_mapping(snapshot_b.sample_data)

        # 找到共同的键
        common_keys = set(data_map_a.keys()) & set(data_map_b.keys())

        for key in common_keys:
            record_a = data_map_a[key]
            record_b = data_map_b[key]

            for field in value_fields:
                if field in record_a and field in record_b:
                    try:
                        value_a = float(record_a[field])
                        value_b = float(record_b[field])

                        if abs(value_a) > 0.001:  # 避免除零
                            deviation = abs(value_a - value_b) / abs(value_a)

                            if deviation > tolerance_percent:
                                severity = ValidationSeverity.WARNING if deviation < tolerance_percent * 2 else ValidationSeverity.ERROR

                                violations.append(ConsistencyViolation(
                                    rule_name="value_consistency",
                                    severity=severity,
                                    component_a=snapshot_a.component,
                                    component_b=snapshot_b.component,
                                    field_name=field,
                                    expected_value=value_a,
                                    actual_value=value_b,
                                    deviation=deviation,
                                    description=f"字段 {field} 值差异超过阈值: {value_a} vs {value_b}"
                                ))

                    except (ValueError, TypeError):
                        # 非数值字段无法比较
                        violations.append(ConsistencyViolation(
                            rule_name="type_consistency",
                            severity=ValidationSeverity.WARNING,
                            component_a=snapshot_a.component,
                            component_b=snapshot_b.component,
                            field_name=field,
                            expected_value=str(type(record_a[field])),
                            actual_value=str(type(record_b[field])),
                            deviation=1.0,
                            description=f"字段 {field} 类型不一致"
                        ))

        return violations

    def _create_data_mapping(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """创建数据映射以便比较"""
        mapping = {}

        for record in data:
            # 使用记录的键字段作为映射键
            key_parts = []
            for field in ["symbol", "timestamp", "strategy_id", "portfolio_id"]:
                if field in record:
                    key_parts.append(str(record[field]))

            key = "|".join(key_parts) if key_parts else str(hash(json.dumps(record, sort_keys=True, default=str)))
            mapping[key] = record

        return mapping

    def _calculate_consistency_score(
        self,
        violations: List[ConsistencyViolation],
        scenario: Dict[str, Any]
    ) -> float:
        """计算一致性评分"""
        if not violations:
            return 100.0

        # 根据违规严重性计算扣分
        total_deduction = 0.0

        for violation in violations:
            if violation.severity == ValidationSeverity.CRITICAL:
                total_deduction += 20.0
            elif violation.severity == ValidationSeverity.ERROR:
                total_deduction += 10.0
            elif violation.severity == ValidationSeverity.WARNING:
                total_deduction += 5.0
            elif violation.severity == ValidationSeverity.INFO:
                total_deduction += 1.0

        # 基础分数100分，减去扣分
        score = max(0.0, 100.0 - total_deduction)

        return score

    def _determine_consistency_status(
        self,
        consistency_score: float,
        violations: List[ConsistencyViolation]
    ) -> ConsistencyStatus:
        """确定一致性状态"""
        # 检查是否有严重违规
        has_critical = any(v.severity == ValidationSeverity.CRITICAL for v in violations)
        has_errors = any(v.severity == ValidationSeverity.ERROR for v in violations)

        if has_critical:
            return ConsistencyStatus.INCONSISTENT
        elif has_errors:
            return ConsistencyStatus.PARTIALLY_CONSISTENT if consistency_score >= 70.0 else ConsistencyStatus.INCONSISTENT
        elif consistency_score >= 95.0:
            return ConsistencyStatus.CONSISTENT
        elif consistency_score >= 80.0:
            return ConsistencyStatus.PARTIALLY_CONSISTENT
        else:
            return ConsistencyStatus.PARTIALLY_CONSISTENT

    def _count_violations_by_severity(self, violations: List[ConsistencyViolation]) -> Dict[str, int]:
        """按严重性统计违规数量"""
        counts = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0
        }

        for violation in violations:
            counts[violation.severity.value] += 1

        return counts

    async def generate_consistency_report(
        self,
        test_results: Optional[List[DataConsistencyTestResult]] = None
    ) -> Dict[str, Any]:
        """生成一致性报告"""
        if test_results is None:
            test_results = self.test_history

        if not test_results:
            return {"error": "没有可用的测试结果"}

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "total_tests": len(test_results),
            "summary": self._generate_test_summary(test_results),
            "detailed_results": [],
            "recommendations": self._generate_recommendations(test_results)
        }

        for result in test_results:
            result_dict = {
                "test_id": result.test_id,
                "status": result.status.value,
                "consistency_score": result.consistency_score,
                "total_records_checked": result.total_records_checked,
                "violation_count": len(result.violations),
                "violations_by_severity": self._count_violations_by_severity(result.violations),
                "test_duration_seconds": (result.end_time - result.start_time).total_seconds(),
                "key_violations": [
                    {
                        "rule": v.rule_name,
                        "severity": v.severity.value,
                        "components": f"{v.component_a} vs {v.component_b}",
                        "field": v.field_name,
                        "deviation": v.deviation,
                        "description": v.description
                    }
                    for v in result.violations[:5]  # 只显示前5个违规
                ]
            }
            report["detailed_results"].append(result_dict)

        return report

    def _generate_test_summary(self, test_results: List[DataConsistencyTestResult]) -> Dict[str, Any]:
        """生成测试摘要"""
        total_tests = len(test_results)
        consistent_tests = sum(1 for r in test_results if r.status == ConsistencyStatus.CONSISTENT)
        partially_consistent = sum(1 for r in test_results if r.status == ConsistencyStatus.PARTIALLY_CONSISTENT)
        inconsistent_tests = sum(1 for r in test_results if r.status == ConsistencyStatus.INCONSISTENT)

        avg_consistency_score = sum(r.consistency_score for r in test_results) / total_tests if total_tests > 0 else 0.0

        total_violations = sum(len(r.violations) for r in test_results)

        return {
            "total_tests": total_tests,
            "consistent_tests": consistent_tests,
            "partially_consistent_tests": partially_consistent,
            "inconsistent_tests": inconsistent_tests,
            "consistency_rate": (consistent_tests / total_tests * 100) if total_tests > 0 else 0.0,
            "average_consistency_score": avg_consistency_score,
            "total_violations": total_violations
        }

    def _generate_recommendations(self, test_results: List[DataConsistencyTestResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 分析常见问题
        all_violations = []
        for result in test_results:
            all_violations.extend(result.violations)

        # 按规则类型分组
        violations_by_rule = {}
        for violation in all_violations:
            if violation.rule_name not in violations_by_rule:
                violations_by_rule[violation.rule_name] = []
            violations_by_rule[violation.rule_name].append(violation)

        # 根据违规类型生成建议
        if "data_hash_consistency" in violations_by_rule:
            recommendations.append("建议实施数据同步机制以确保各组件数据版本一致")

        if "record_count_consistency" in violations_by_rule:
            recommendations.append("检查数据传输过程中的完整性，避免数据丢失或重复")

        if "value_consistency" in violations_by_rule:
            recommendations.append("优化数据转换和舍入策略，确保数值精度一致")

        if "type_consistency" in violations_by_rule:
            recommendations.append("统一各组件的数据类型定义和转换规则")

        # 根据一致性评分生成建议
        avg_score = sum(r.consistency_score for r in test_results) / len(test_results) if test_results else 0.0

        if avg_score < 80.0:
            recommendations.append("系统整体数据一致性需要改进，建议进行全面的数据质量审查")
        elif avg_score < 95.0:
            recommendations.append("系统数据一致性基本满足要求，建议针对特定问题进行优化")

        if not recommendations:
            recommendations.append("系统数据一致性表现良好，建议保持现有的数据质量管控措施")

        return recommendations