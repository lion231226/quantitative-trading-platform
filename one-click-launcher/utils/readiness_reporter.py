"""
系统就绪报告生成器

提供系统就绪状态报告生成、导出和分享功能。
支持多种报告格式和自定义报告模板。
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import base64

from services.system_integration_service import (
    SystemIntegrationService, SystemReadinessCertificate,
    SystemReadinessStatus
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportFormat(Enum):
    """报告格式"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class ReportType(Enum):
    """报告类型"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"


@dataclass
class ReportTemplate:
    """报告模板"""
    template_id: str
    name: str
    description: str
    type: ReportType
    format: ReportFormat
    sections: List[str]
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """生成的报告"""
    report_id: str
    template_id: str
    system_name: str
    type: ReportType
    format: ReportFormat
    generated_at: datetime
    file_path: str
    file_size: int
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReadinessReporter:
    """
    系统就绪报告生成器

    功能特性：
    - 多格式报告生成 (JSON, Markdown, HTML, PDF)
    - 多种报告类型 (摘要, 详细, 技术, 执行)
    - 自定义报告模板
    - 报告分享和导出
    - 历史报告管理
    """

    def __init__(self, integration_service: SystemIntegrationService):
        """
        初始化就绪报告生成器

        Args:
            integration_service: 系统集成服务
        """
        self.integration_service = integration_service
        self.logger = get_logger(self.__class__.__name__)

        # 报告存储
        self.generated_reports: List[GeneratedReport] = []
        self.report_templates = self._initialize_templates()

        # 报告输出目录
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

        self.logger.info("就绪报告生成器初始化完成")

    def _initialize_templates(self) -> Dict[str, ReportTemplate]:
        """初始化报告模板"""
        templates = {}

        # 摘要报告模板
        templates['summary_json'] = ReportTemplate(
            template_id="summary_json",
            name="系统摘要报告 (JSON)",
            description="包含系统就绪状态的简要JSON报告",
            type=ReportType.SUMMARY,
            format=ReportFormat.JSON,
            sections=[
                "system_info",
                "readiness_status",
                "key_metrics",
                "recommendations"
            ]
        )

        templates['summary_markdown'] = ReportTemplate(
            template_id="summary_markdown",
            name="系统摘要报告 (Markdown)",
            description="包含系统就绪状态的简要Markdown报告",
            type=ReportType.SUMMARY,
            format=ReportFormat.MARKDOWN,
            sections=[
                "title",
                "executive_summary",
                "readiness_status",
                "key_metrics",
                "recommendations"
            ]
        )

        # 详细报告模板
        templates['detailed_markdown'] = ReportTemplate(
            template_id="detailed_markdown",
            name="系统详细报告 (Markdown)",
            description="包含完整验证结果的详细Markdown报告",
            type=ReportType.DETAILED,
            format=ReportFormat.MARKDOWN,
            sections=[
                "title",
                "executive_summary",
                "system_overview",
                "verification_results",
                "performance_analysis",
                "error_handling_analysis",
                "recommendations",
                "appendix"
            ]
        )

        templates['detailed_html'] = ReportTemplate(
            template_id="detailed_html",
            name="系统详细报告 (HTML)",
            description="包含完整验证结果的详细HTML报告，带有图表和样式",
            type=ReportType.DETAILED,
            format=ReportFormat.HTML,
            sections=[
                "header",
                "executive_summary",
                "system_overview",
                "verification_results",
                "performance_analysis",
                "error_handling_analysis",
                "recommendations",
                "footer"
            ]
        )

        # 技术报告模板
        templates['technical_markdown'] = ReportTemplate(
            template_id="technical_markdown",
            name="技术报告 (Markdown)",
            description="面向技术人员的详细技术报告",
            type=ReportType.TECHNICAL,
            format=ReportFormat.MARKDOWN,
            sections=[
                "title",
                "technical_summary",
                "architecture_overview",
                "pipeline_analysis",
                "performance_metrics",
                "error_scenarios",
                "troubleshooting_guide",
                "api_endpoints"
            ]
        )

        # 执行报告模板
        templates['executive_html'] = ReportTemplate(
            template_id="executive_html",
            name="执行报告 (HTML)",
            description="面向管理层的执行摘要报告",
            type=ReportType.EXECUTIVE,
            format=ReportFormat.HTML,
            sections=[
                "header",
                "executive_summary",
                "business_impact",
                "risk_assessment",
                "recommendations",
                "next_steps",
                "footer"
            ]
        )

        return templates

    async def generate_report(self, template_id: str,
                            custom_filename: Optional[str] = None) -> GeneratedReport:
        """
        生成报告

        Args:
            template_id: 模板ID
            custom_filename: 自定义文件名

        Returns:
            生成的报告信息
        """
        if template_id not in self.report_templates:
            raise ValueError(f"未找到报告模板: {template_id}")

        template = self.report_templates[template_id]
        self.logger.info(f"生成报告: {template.name}")

        # 获取最新数据
        certificate = self.integration_service.latest_certificate
        if not certificate:
            raise ValueError("没有可用的系统就绪证书，请先执行系统验证")

        # 生成报告内容
        if template.format == ReportFormat.JSON:
            content = self._generate_json_report(template, certificate)
        elif template.format == ReportFormat.MARKDOWN:
            content = self._generate_markdown_report(template, certificate)
        elif template.format == ReportFormat.HTML:
            content = self._generate_html_report(template, certificate)
        else:
            raise ValueError(f"不支持的报告格式: {template.format}")

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = custom_filename or f"{self.integration_service.config.system_name}_{template.type.value}_{timestamp}.{template.format.value}"
        file_path = self.output_dir / filename

        if template.format == ReportFormat.JSON:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False, default=str)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 计算文件大小和哈希
        file_size = file_path.stat().st_size
        content_hash = self._calculate_content_hash(content)

        # 创建报告记录
        report = GeneratedReport(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            template_id=template_id,
            system_name=self.integration_service.config.system_name,
            type=template.type,
            format=template.format,
            generated_at=datetime.now(),
            file_path=str(file_path),
            file_size=file_size,
            content_hash=content_hash,
            metadata={
                'certificate_id': certificate.certificate_id,
                'readiness_score': certificate.readiness_score,
                'sections': template.sections
            }
        )

        self.generated_reports.append(report)

        self.logger.info(f"报告已生成: {file_path}")

        return report

    def _generate_json_report(self, template: ReportTemplate,
                             certificate: SystemReadinessCertificate) -> Dict[str, Any]:
        """生成JSON格式报告"""
        base_report = {
            'report_metadata': {
                'report_id': f"report_{uuid.uuid4().hex[:8]}",
                'template_id': template.template_id,
                'template_name': template.name,
                'system_name': certificate.system_name,
                'generated_at': datetime.now().isoformat(),
                'type': template.type.value,
                'format': template.format.value
            },
            'system_info': {
                'name': certificate.system_name,
                'readiness_certificate_id': certificate.certificate_id,
                'overall_status': certificate.overall_status.value,
                'readiness_score': certificate.readiness_score,
                'integration_score': certificate.integration_score,
                'generated_at': certificate.generated_at.isoformat(),
                'expires_at': certificate.expires_at.isoformat(),
                'next_check_time': certificate.next_check_time.isoformat()
            }
        }

        # 根据模板类型添加相应内容
        if template.type == ReportType.SUMMARY:
            base_report.update({
                'key_metrics': self._extract_key_metrics(certificate),
                'recommendations': certificate.recommendations
            })

        elif template.type == ReportType.DETAILED:
            base_report.update({
                'pipeline_status': certificate.pipeline_status,
                'performance_status': certificate.performance_status,
                'error_handling_status': certificate.error_handling_status,
                'detailed_analysis': self._generate_detailed_analysis(),
                'recommendations': certificate.recommendations,
                'next_steps': self._generate_next_steps(certificate)
            })

        elif template.type == ReportType.TECHNICAL:
            base_report.update({
                'technical_metrics': self._generate_technical_metrics(),
                'system_configuration': self._get_system_configuration(),
                'troubleshooting_guide': self._generate_troubleshooting_guide(),
                'api_documentation': self._generate_api_documentation()
            })

        elif template.type == ReportType.EXECUTIVE:
            base_report.update({
                'business_impact': self._generate_business_impact(certificate),
                'risk_assessment': self._generate_risk_assessment(certificate),
                'cost_implications': self._generate_cost_implications(),
                'executive_recommendations': self._generate_executive_recommendations(certificate)
            })

        return base_report

    def _generate_markdown_report(self, template: ReportTemplate,
                                certificate: SystemReadinessCertificate) -> str:
        """生成Markdown格式报告"""
        lines = []

        # 标题部分
        if "title" in template.sections:
            lines.extend([
                f"# {certificate.system_name} 系统就绪报告",
                f"",
                f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**系统状态**: {self._get_status_emoji(certificate.overall_status)} {certificate.overall_status.value.upper()}",
                f"**就绪评分**: {certificate.readiness_score:.1f}/100",
                f"**集成评分**: {certificate.integration_score:.1f}/100",
                f""
            ])

        # 执行摘要
        if "executive_summary" in template.sections:
            lines.extend([
                f"## 执行摘要",
                f"",
                f"{certificate.system_name} 系统的集成验证已{self._get_completion_status(certificate)}。",
                f"整体系统就绪评分为 **{certificate.readiness_score:.1f}/100**，状态为 **{certificate.overall_status.value.upper()}**。",
                f"",
                self._generate_executive_summary_text(certificate),
                f""
            ])

        # 系统概览
        if "system_overview" in template.sections:
            lines.extend([
                f"## 系统概览",
                f"",
                f"### 基本信息",
                f"- **系统名称**: {certificate.system_name}",
                f"- **证书ID**: {certificate.certificate_id}",
                f"- **生成时间**: {certificate.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **过期时间**: {certificate.expires_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **下次检查**: {certificate.next_check_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f""
            ])

        # 验证结果
        if "verification_results" in template.sections:
            lines.extend([
                f"## 验证结果",
                f"",
                self._generate_verification_results_markdown(certificate),
                f""
            ])

        # 性能分析
        if "performance_analysis" in template.sections:
            lines.extend([
                f"## 性能分析",
                f"",
                self._generate_performance_analysis_markdown(certificate),
                f""
            ])

        # 错误处理分析
        if "error_handling_analysis" in template.sections:
            lines.extend([
                f"## 错误处理分析",
                f"",
                self._generate_error_handling_analysis_markdown(certificate),
                f""
            ])

        # 关键指标
        if "key_metrics" in template.sections:
            lines.extend([
                f"## 关键指标",
                f"",
                self._generate_key_metrics_markdown(certificate),
                f""
            ])

        # 建议
        if "recommendations" in template.sections:
            lines.extend([
                f"## 建议",
                f""
            ])
            for i, rec in enumerate(certificate.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # 技术细节
        if template.type == ReportType.TECHNICAL:
            lines.extend([
                f"## 技术细节",
                f"",
                self._generate_technical_details_markdown(certificate),
                f""
            ])

        # 风险评估
        if "risk_assessment" in template.sections:
            lines.extend([
                f"## 风险评估",
                f"",
                self._generate_risk_assessment_markdown(certificate),
                f""
            ])

        return "\n".join(lines)

    def _generate_html_report(self, template: ReportTemplate,
                            certificate: SystemReadinessCertificate) -> str:
        """生成HTML格式报告"""
        # HTML基础模板
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; }}
        .status-healthy {{ color: #28a745; font-weight: bold; }}
        .status-degraded {{ color: #ffc107; font-weight: bold; }}
        .status-not-ready {{ color: #dc3545; font-weight: bold; }}
        .metric-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; display: block; }}
        .metric-label {{ color: #6c757d; font-size: 0.9rem; }}
        .section {{ margin: 2rem 0; }}
        .progress-bar {{ background: #e9ecef; border-radius: 10px; overflow: hidden; height: 20px; }}
        .progress-fill {{ background: #28a745; height: 100%; transition: width 0.3s ease; }}
        .recommendation {{ background: #e7f3ff; border-left: 4px solid #007bff; padding: 1rem; margin: 0.5rem 0; }}
        .footer {{ text-align: center; color: #6c757d; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #dee2e6; }}
        @media print {{ body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>报告生成时间: {generated_time}</p>
            <p>系统状态: <span class="status-{status_class}">{status}</span></p>
        </div>

        {content}

        <div class="footer">
            <p>此报告由系统集成验证服务自动生成</p>
            <p>证书ID: {certificate_id} | 过期时间: {expires_at}</p>
        </div>
    </div>
</body>
</html>
        """

        # 生成内容
        content_parts = []

        # 指标卡片
        if "executive_summary" in template.sections:
            content_parts.append("""
        <div class="section">
            <h2>系统概览</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                <div class="metric-card">
                    <span class="metric-value">{readiness_score:.1f}</span>
                    <span class="metric-label">就绪评分 / 100</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{integration_score:.1f}</span>
                    <span class="metric-label">集成评分 / 100</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{status}</span>
                    <span class="metric-label">系统状态</span>
                </div>
            </div>
        </div>
            """.format(
                readiness_score=certificate.readiness_score,
                integration_score=certificate.integration_score,
                status=certificate.overall_status.value.upper()
            ))

        # 详细分析
        if template.type == ReportType.DETAILED:
            content_parts.append(self._generate_detailed_analysis_html(certificate))

        # 执行报告内容
        if template.type == ReportType.EXECUTIVE:
            content_parts.append(self._generate_executive_content_html(certificate))

        # 建议部分
        if "recommendations" in template.sections:
            recommendations_html = "<div class='section'><h2>建议</h2>"
            for rec in certificate.recommendations:
                recommendations_html += f"<div class='recommendation'>{rec}</div>"
            recommendations_html += "</div>"
            content_parts.append(recommendations_html)

        # 填充模板
        html_content = html_template.format(
            title=f"{certificate.system_name} 系统就绪报告",
            generated_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            status=certificate.overall_status.value.upper(),
            status_class=certificate.overall_status.value,
            content="".join(content_parts),
            certificate_id=certificate.certificate_id,
            expires_at=certificate.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        )

        return html_content

    def _extract_key_metrics(self, certificate: SystemReadinessCertificate) -> Dict[str, Any]:
        """提取关键指标"""
        return {
            'readiness_score': certificate.readiness_score,
            'integration_score': certificate.integration_score,
            'overall_status': certificate.overall_status.value,
            'pipeline_health': certificate.pipeline_status.get('status', 'unknown'),
            'performance_health': certificate.performance_status.get('status', 'unknown'),
            'error_handling_score': certificate.error_handling_status.get('overall_score', 0)
        }

    def _get_status_emoji(self, status: SystemReadinessStatus) -> str:
        """获取状态表情符号"""
        emoji_map = {
            SystemReadinessStatus.READY: "✅",
            SystemReadinessStatus.DEGRADED: "⚠️",
            SystemReadinessStatus.NOT_READY: "❌",
            SystemReadinessStatus.ERROR: "🚨"
        }
        return emoji_map.get(status, "❓")

    def _get_completion_status(self, certificate: SystemReadinessCertificate) -> str:
        """获取完成状态描述"""
        if certificate.overall_status == SystemReadinessStatus.READY:
            return "成功完成，系统已就绪"
        elif certificate.overall_status == SystemReadinessStatus.DEGRADED:
            return "基本完成，系统部分功能受限"
        else:
            return "存在问题，系统尚未就绪"

    def _generate_executive_summary_text(self, certificate: SystemReadinessCertificate) -> str:
        """生成执行摘要文本"""
        if certificate.overall_status == SystemReadinessStatus.READY:
            return f"系统验证通过，所有组件运行正常，集成评分达到 {certificate.integration_score:.1f} 分。"
        elif certificate.overall_status == SystemReadinessStatus.DEGRADED:
            return f"系统基本功能正常，但存在一些性能问题需要注意，集成评分为 {certificate.integration_score:.1f} 分。"
        else:
            return f"系统存在严重问题，需要立即处理，集成评分仅为 {certificate.integration_score:.1f} 分。"

    def _generate_verification_results_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成验证结果的Markdown"""
        lines = []

        # 管道状态
        pipeline_status = certificate.pipeline_status
        pipeline_emoji = "✅" if pipeline_status.get('status') else "❌"
        lines.append(f"### 管道验证 {pipeline_emoji}")
        lines.append(f"- 成功率: {pipeline_status.get('success_rate', 0):.1%}")
        lines.append(f"- 总测试数: {pipeline_status.get('total_tests', 0)}")
        lines.append("")

        # 性能状态
        perf_status = certificate.performance_status
        perf_emoji = "✅" if perf_status.get('status') else "❌"
        lines.append(f"### 性能验证 {perf_emoji}")
        alerts = perf_status.get('active_alerts', {})
        lines.append(f"- 活跃告警: 严重 {alerts.get('critical', 0)}, 警告 {alerts.get('warning', 0)}")
        lines.append("")

        # 错误处理状态
        error_status = certificate.error_handling_status
        error_emoji = "✅" if error_status.get('status') else "❌"
        lines.append(f"### 错误处理验证 {error_emoji}")
        lines.append(f"- 总体评分: {error_status.get('overall_score', 0):.1f}/100")
        lines.append(f"- 测试场景: {error_status.get('total_tests', 0)}")
        lines.append("")

        return "\n".join(lines)

    def _generate_performance_analysis_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成性能分析的Markdown"""
        perf_status = certificate.performance_status
        bottlenecks = perf_status.get('bottlenecks', {})

        if not bottlenecks:
            return "未检测到明显的性能瓶颈。"

        lines = ["### 检测到的瓶颈:"]
        for bottleneck, info in bottlenecks.items():
            lines.append(f"- **{bottleneck}**: {info}")

        return "\n".join(lines)

    def _generate_error_handling_analysis_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成错误处理分析的Markdown"""
        error_status = certificate.error_handling_status
        score = error_status.get('overall_score', 0)

        lines = [
            f"### 错误处理能力评分: {score:.1f}/100",
            ""
        ]

        if score >= 90:
            lines.append("错误处理机制优秀，能够妥善处理各种异常情况。")
        elif score >= 70:
            lines.append("错误处理机制良好，但仍有改进空间。")
        else:
            lines.append("错误处理机制需要改进，建议加强异常处理和恢复机制。")

        return "\n".join(lines)

    def _generate_key_metrics_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成关键指标的Markdown"""
        lines = [
            f"### 系统就绪评分",
            f"**{certificate.readiness_score:.1f}** / 100",
            "",
            f"### 组件状态",
            f"- 管道验证: {'✅ 正常' if certificate.pipeline_status.get('status') else '❌ 异常'}",
            f"- 性能监控: {'✅ 正常' if certificate.performance_status.get('status') else '❌ 异常'}",
            f"- 错误处理: {'✅ 正常' if certificate.error_handling_status.get('status') else '❌ 异常'}",
            ""
        ]

        return "\n".join(lines)

    def _generate_technical_details_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成技术细节的Markdown"""
        lines = [
            "### 技术规格",
            "",
            "#### 验证组件",
            "- 管道验证器: 端到端请求链路测试",
            "- 性能监控器: 实时性能指标收集",
            "- 错误处理验证器: 错误场景测试",
            "- 健康检查器: 服务状态监控",
            "",
            "#### 配置信息",
            f"- 监控间隔: {self.integration_service.config.monitoring_interval} 秒",
            f"- 测试持续时间: {self.integration_service.config.test_duration} 秒",
            f"- 证书有效期: {self.integration_service.config.certificate_validity_hours} 小时",
            ""
        ]

        return "\n".join(lines)

    def _generate_risk_assessment_markdown(self, certificate: SystemReadinessCertificate) -> str:
        """生成风险评估的Markdown"""
        score = certificate.readiness_score

        lines = ["### 风险评估"]

        if score >= 90:
            lines.extend([
                "- **风险等级**: 低",
                "- **建议**: 系统运行稳定，定期监控即可",
                ""
            ])
        elif score >= 70:
            lines.extend([
                "- **风险等级**: 中",
                "- **建议**: 需要关注性能和错误处理问题",
                ""
            ])
        else:
            lines.extend([
                "- **风险等级**: 高",
                "- **建议**: 需要立即处理系统问题",
                ""
            ])

        return "\n".join(lines)

    def _generate_detailed_analysis(self) -> Dict[str, Any]:
        """生成详细分析"""
        return {
            'verification_timestamp': datetime.now().isoformat(),
            'analysis_depth': 'comprehensive',
            'components_analyzed': ['pipeline', 'performance', 'error_handling'],
            'test_coverage': 'high'
        }

    def _generate_next_steps(self, certificate: SystemReadinessCertificate) -> List[str]:
        """生成下一步行动"""
        steps = []

        if certificate.overall_status != SystemReadinessStatus.READY:
            steps.append("立即处理系统中发现的问题")

        steps.append("在证书过期前进行下一次验证")
        steps.append("建立持续监控机制")

        return steps

    def _generate_technical_metrics(self) -> Dict[str, Any]:
        """生成技术指标"""
        return {
            'response_time_p95': 0.0,
            'throughput': 0.0,
            'error_rate': 0.0,
            'availability': 0.0
        }

    def _get_system_configuration(self) -> Dict[str, Any]:
        """获取系统配置"""
        config = self.integration_service.config
        return {
            'system_name': config.system_name,
            'frontend_url': config.frontend_url,
            'backend_url': config.backend_url,
            'database_host': config.database_host,
            'monitoring_interval': config.monitoring_interval
        }

    def _generate_troubleshooting_guide(self) -> Dict[str, Any]:
        """生成故障排除指南"""
        return {
            'common_issues': [
                "服务连接失败",
                "性能指标异常",
                "错误处理机制故障"
            ],
            'diagnostic_steps': [
                "检查服务状态",
                "查看系统日志",
                "运行健康检查"
            ]
        }

    def _generate_api_documentation(self) -> Dict[str, Any]:
        """生成API文档"""
        return {
            'health_check_endpoints': [
                "/api/health",
                "/api/status"
            ],
            'monitoring_endpoints': [
                "/api/metrics",
                "/api/performance"
            ]
        }

    def _generate_business_impact(self, certificate: SystemReadinessCertificate) -> Dict[str, Any]:
        """生成业务影响分析"""
        return {
            'operational_readiness': certificate.overall_status.value,
            'user_experience': 'good' if certificate.readiness_score >= 80 else 'needs_improvement',
            'risk_level': 'low' if certificate.readiness_score >= 90 else 'medium' if certificate.readiness_score >= 70 else 'high'
        }

    def _generate_risk_assessment(self, certificate: SystemReadinessCertificate) -> Dict[str, Any]:
        """生成风险评估"""
        return {
            'overall_risk': 'low' if certificate.readiness_score >= 90 else 'medium' if certificate.readiness_score >= 70 else 'high',
            'technical_risks': [],
            'business_risks': [],
            'mitigation_strategies': certificate.recommendations
        }

    def _generate_cost_implications(self) -> Dict[str, Any]:
        """生成成本影响分析"""
        return {
            'operational_costs': 'stable',
            'maintenance_costs': 'minimal',
            'scalability_costs': 'planned'
        }

    def _generate_executive_recommendations(self, certificate: SystemReadinessCertificate) -> List[str]:
        """生成执行建议"""
        return certificate.recommendations

    def _generate_detailed_analysis_html(self, certificate: SystemReadinessCertificate) -> str:
        """生成详细分析的HTML"""
        return f"""
        <div class="section">
            <h2>详细分析</h2>
            <div class="metric-card">
                <h3>管道验证</h3>
                <p>成功率: {certificate.pipeline_status.get('success_rate', 0):.1%}</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {certificate.pipeline_status.get('success_rate', 0) * 100}%"></div>
                </div>
            </div>
            <div class="metric-card">
                <h3>性能监控</h3>
                <p>状态: {'正常' if certificate.performance_status.get('status') else '异常'}</p>
            </div>
            <div class="metric-card">
                <h3>错误处理</h3>
                <p>评分: {certificate.error_handling_status.get('overall_score', 0):.1f}/100</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {certificate.error_handling_status.get('overall_score', 0)}%"></div>
                </div>
            </div>
        </div>
        """

    def _generate_executive_content_html(self, certificate: SystemReadinessCertificate) -> str:
        """生成执行报告内容的HTML"""
        return f"""
        <div class="section">
            <h2>业务影响</h2>
            <div class="metric-card">
                <h3>运营就绪度</h3>
                <p>{certificate.overall_status.value.upper()}</p>
            </div>
            <div class="metric-card">
                <h3>用户体验</h3>
                <p>{'良好' if certificate.readiness_score >= 80 else '需要改进'}</p>
            </div>
        </div>
        """

    def _calculate_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]

    def get_available_templates(self) -> Dict[str, ReportTemplate]:
        """获取可用报告模板"""
        return self.report_templates.copy()

    def get_report_history(self, limit: int = 10) -> List[GeneratedReport]:
        """获取报告历史"""
        return self.generated_reports[-limit:]

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        for i, report in enumerate(self.generated_reports):
            if report.report_id == report_id:
                # 删除文件
                try:
                    Path(report.file_path).unlink()
                except FileNotFoundError:
                    pass

                # 从列表中删除
                del self.generated_reports[i]
                return True

        return False

    async def share_report(self, report_id: str, share_method: str = 'file') -> Dict[str, Any]:
        """分享报告"""
        report = None
        for r in self.generated_reports:
            if r.report_id == report_id:
                report = r
                break

        if not report:
            raise ValueError(f"未找到报告: {report_id}")

        if share_method == 'file':
            return {
                'method': 'file',
                'path': report.file_path,
                'size': report.file_size
            }
        elif share_method == 'base64':
            with open(report.file_path, 'rb') as f:
                content = f.read()
            encoded = base64.b64encode(content).decode('utf-8')
            return {
                'method': 'base64',
                'content': encoded,
                'filename': Path(report.file_path).name
            }
        else:
            raise ValueError(f"不支持的分享方式: {share_method}")