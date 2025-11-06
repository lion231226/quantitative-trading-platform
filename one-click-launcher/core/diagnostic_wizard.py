"""
Diagnostic Wizard Module

This module provides interactive problem diagnosis wizard functionality,
extending UserConfirmation patterns for guided troubleshooting.
"""

import asyncio
import os
import re
import sys
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from utils.user_confirmation import UserConfirmation, ConfirmationAction, ConfirmationResult
from utils.logger import get_logger

logger = get_logger(__name__)


class QuestionType(Enum):
    """问题类型"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    YES_NO = "yes_no"
    NUMERIC_INPUT = "numeric_input"
    FILE_SELECT = "file_select"
    COMMAND_OUTPUT = "command_output"


class DiagnosisResult(Enum):
    """诊断结果"""
    ISSUE_IDENTIFIED = "issue_identified"
    MULTIPLE_ISSUES = "multiple_issues"
    NO_ISSUE_FOUND = "no_issue_found"
    INSUFFICIENT_INFO = "insufficient_info"
    ESCALATION_REQUIRED = "escalation_required"


@dataclass
class DiagnosticQuestion:
    """诊断问题"""
    question_id: str
    text: str
    question_type: QuestionType
    options: List[str] = field(default_factory=list)
    default_value: Any = None
    required: bool = True
    condition: Optional[str] = None  # 前置条件
    help_text: Optional[str] = None
    validation_rule: Optional[str] = None
    weight: float = 1.0  # 权重，用于影响最终诊断结果


@dataclass
class DiagnosticStep:
    """诊断步骤"""
    step_id: str
    title: str
    description: str
    questions: List[DiagnosticQuestion]
    estimated_time: int = 5  # 预估时间（分钟）
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    automated: bool = False  # 是否可以自动化执行


@dataclass
class DiagnosticRule:
    """诊断规则"""
    rule_id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]  # 诊断条件
    conclusions: List[Dict[str, Any]]  # 诊断结论
    confidence: float = 0.8  # 置信度
    priority: int = 1  # 优先级


@dataclass
class DiagnosticSession:
    """诊断会话"""
    session_id: str
    wizard_type: str
    answers: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: DiagnosisResult = DiagnosisResult.INSUFFICIENT_INFO
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DiagnosticWizard:
    """
    诊断向导，提供交互式问题诊断功能
    """

    def __init__(self):
        """初始化诊断向导"""
        self.logger = get_logger(self.__class__.__name__)
        self.user_confirmation = UserConfirmation()

        # 诊断模板
        self.wizard_templates = self._initialize_wizard_templates()

        # 诊断规则
        self.diagnostic_rules = self._initialize_diagnostic_rules()

        # 活跃会话
        self.active_sessions: Dict[str, DiagnosticSession] = {}

        self.logger.info("Diagnostic Wizard initialized")

    def _initialize_wizard_templates(self) -> Dict[str, List[DiagnosticStep]]:
        """初始化诊断向导模板"""
        templates = {}

        # 网络连接问题诊断模板
        templates["network_connectivity"] = [
            DiagnosticStep(
                step_id="basic_connectivity",
                title="基础网络连接检查",
                description="检查基本的网络连接状态",
                questions=[
                    DiagnosticQuestion(
                        question_id="can_access_internet",
                        text="您能正常访问互联网吗？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        weight=1.0,
                        help_text="尝试访问常用网站如 google.com 或 baidu.com"
                    ),
                    DiagnosticQuestion(
                        question_id="specific_sites_error",
                        text="如果是特定网站无法访问，请输入网站地址：",
                        question_type=QuestionType.TEXT_INPUT,
                        required=False,
                        condition="can_access_internet == 'no'"
                    )
                ],
                estimated_time=3,
                automated=True
            ),
            DiagnosticStep(
                step_id="dns_resolution",
                title="DNS解析检查",
                description="检查域名解析是否正常",
                questions=[
                    DiagnosticQuestion(
                        question_id="ping_by_ip",
                        text="能否通过IP地址ping通外部服务器？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        help_text="尝试 ping 8.8.8.8 (Google DNS)"
                    ),
                    DiagnosticQuestion(
                        question_id="ping_by_domain",
                        text="能否通过域名ping通外部服务器？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        help_text="尝试 ping google.com"
                    ),
                    DiagnosticQuestion(
                        question_id="dns_servers",
                        text="您使用的DNS服务器是什么？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["自动获取", "8.8.8.8 (Google)", "114.114.114.114 (114DNS)", "其他"],
                        required=False
                    )
                ],
                estimated_time=5,
                difficulty="intermediate"
            ),
            DiagnosticStep(
                step_id="proxy_firewall",
                title="代理和防火墙检查",
                description="检查代理设置和防火墙配置",
                questions=[
                    DiagnosticQuestion(
                        question_id="using_proxy",
                        text="您是否使用代理服务器？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="proxy_settings",
                        text="请描述您的代理设置：",
                        question_type=QuestionType.TEXT_INPUT,
                        required=False,
                        condition="using_proxy == 'yes'"
                    ),
                    DiagnosticQuestion(
                        question_id="firewall_enabled",
                        text="防火墙是否启用？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    )
                ],
                estimated_time=8,
                difficulty="intermediate"
            )
        ]

        # 端口冲突诊断模板
        templates["port_conflict"] = [
            DiagnosticStep(
                step_id="identify_port",
                title="端口识别",
                description="识别出现问题的端口",
                questions=[
                    DiagnosticQuestion(
                        question_id="error_message",
                        text="请输入完整的错误信息：",
                        question_type=QuestionType.TEXT_INPUT,
                        required=True,
                        help_text="复制粘贴完整的错误消息，包括端口号"
                    ),
                    DiagnosticQuestion(
                        question_id="port_number",
                        text="哪个端口出现了问题？",
                        question_type=QuestionType.NUMERIC_INPUT,
                        required=True,
                        validation_rule=r"^\d{1,5}$"
                    ),
                    DiagnosticQuestion(
                        question_id="application_type",
                        text="出现问题的应用类型是什么？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["前端开发服务器", "后端API服务器", "数据库", "缓存服务", "其他"],
                        required=True
                    )
                ],
                estimated_time=3
            ),
            DiagnosticStep(
                step_id="check_port_usage",
                title="端口使用情况检查",
                description="检查端口占用情况",
                questions=[
                    DiagnosticQuestion(
                        question_id="process_running",
                        text="是否有其他相同应用正在运行？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="recent_restart",
                        text="应用是否最近异常退出？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        help_text="如果应用异常退出，端口可能仍被占用"
                    ),
                    DiagnosticQuestion(
                        question_id="can_change_port",
                        text="是否可以更改应用使用的端口？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    )
                ],
                estimated_time=5,
                automated=True
            ),
            DiagnosticStep(
                step_id="resolution_preference",
                title="解决方式偏好",
                description="了解用户的解决偏好",
                questions=[
                    DiagnosticQuestion(
                        question_id="preferred_solution",
                        text="您更倾向于哪种解决方式？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["停止占用端口的进程", "使用不同的端口", "等待端口释放"],
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="risk_tolerance",
                        text="您对停止系统进程的风险接受程度？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["低风险，只停止明确的应用进程", "中等风险，可以停止可疑进程", "高风险，可以强制释放端口"],
                        required=True
                    )
                ],
                estimated_time=2
            )
        ]

        # 权限问题诊断模板
        templates["permission_issue"] = [
            DiagnosticStep(
                step_id="identify_file_path",
                title="文件路径识别",
                description="识别出现权限问题的文件或目录",
                questions=[
                    DiagnosticQuestion(
                        question_id="file_path",
                        text="请输入出现权限问题的完整文件路径：",
                        question_type=QuestionType.TEXT_INPUT,
                        required=True,
                        help_text="包含文件名和扩展名的完整路径"
                    ),
                    DiagnosticQuestion(
                        question_id="operation_type",
                        text="您尝试执行什么操作时遇到权限问题？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["读取文件", "写入文件", "删除文件", "创建文件", "执行程序", "安装软件"],
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="error_details",
                        text="具体的错误信息是什么？",
                        question_type=QuestionType.TEXT_INPUT,
                        required=True,
                        help_text="复制粘贴完整的错误消息"
                    )
                ],
                estimated_time=5
            ),
            DiagnosticStep(
                step_id="check_user_context",
                title="用户环境检查",
                description="检查用户权限和环境",
                questions=[
                    DiagnosticQuestion(
                        question_id="user_account_type",
                        text="您使用的是什么类型的账户？",
                        question_type=QuestionType.SINGLE_CHOICE,
                        options=["普通用户账户", "管理员账户", "root用户", "不清楚"],
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="file_ownership",
                        text="您是否是文件的所有者？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        help_text="如果不确定，可以选择'不清楚'"
                    ),
                    DiagnosticQuestion(
                        question_id="tried_sudo",
                        text="您是否尝试过使用管理员权限？",
                        question_type=QuestionType.YES_NO,
                        required=True,
                        condition="user_account_type != 'root用户'"
                    )
                ],
                estimated_time=3,
                difficulty="intermediate"
            ),
            DiagnosticStep(
                step_id="solution_assessment",
                title="解决方案评估",
                description="评估合适的解决方案",
                questions=[
                    DiagnosticQuestion(
                        question_id="can_change_permissions",
                        text="您是否可以修改文件权限？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="alternative_location",
                        text="是否可以在其他位置执行相同操作？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    ),
                    DiagnosticQuestion(
                        question_id="admin_access",
                        text="您是否能够获得管理员权限？",
                        question_type=QuestionType.YES_NO,
                        required=True
                    )
                ],
                estimated_time=4
            )
        ]

        return templates

    def _initialize_diagnostic_rules(self) -> Dict[str, List[DiagnosticRule]]:
        """初始化诊断规则"""
        rules = {}

        # 网络连接诊断规则
        rules["network_connectivity"] = [
            DiagnosticRule(
                rule_id="internet_down",
                name="互联网连接中断",
                description="完全无法访问互联网",
                conditions=[
                    {"field": "can_access_internet", "operator": "equals", "value": "no"},
                    {"field": "ping_by_ip", "operator": "equals", "value": "no"}
                ],
                conclusions=[
                    {"issue": "互联网连接问题", "severity": "high", "solution": "check_internet_connection"},
                    {"action": "检查网络硬件", "description": "检查路由器、网线等网络设备"},
                    {"action": "联系ISP", "description": "联系互联网服务提供商"}
                ],
                confidence=0.9,
                priority=1
            ),
            DiagnosticRule(
                rule_id="dns_resolution_failure",
                name="DNS解析失败",
                description="可以访问IP但无法解析域名",
                conditions=[
                    {"field": "can_access_internet", "operator": "equals", "value": "no"},
                    {"field": "ping_by_ip", "operator": "equals", "value": "yes"},
                    {"field": "ping_by_domain", "operator": "equals", "value": "no"}
                ],
                conclusions=[
                    {"issue": "DNS解析问题", "severity": "medium", "solution": "configure_dns"},
                    {"action": "更换DNS服务器", "description": "尝试使用 8.8.8.8 或 114.114.114.114"},
                    {"action": "刷新DNS缓存", "description": "执行 ipconfig /flushdns (Windows) 或 sudo systemctl restart systemd-resolved (Linux)"}
                ],
                confidence=0.95,
                priority=2
            ),
            DiagnosticRule(
                rule_id="proxy_firewall_block",
                name="代理或防火墙阻拦",
                description="代理或防火墙设置导致连接问题",
                conditions=[
                    {"field": "using_proxy", "operator": "equals", "value": "yes"},
                    {"field": "can_access_internet", "operator": "equals", "value": "no"}
                ],
                conclusions=[
                    {"issue": "代理配置问题", "severity": "medium", "solution": "check_proxy_config"},
                    {"action": "检查代理设置", "description": "验证代理服务器地址和端口"},
                    {"action": "临时禁用代理", "description": "尝试临时禁用代理测试连接"}
                ],
                confidence=0.8,
                priority=3
            )
        ]

        # 端口冲突诊断规则
        rules["port_conflict"] = [
            DiagnosticRule(
                rule_id="process_still_running",
                name="进程仍在运行",
                description="相同应用的进程仍在运行导致端口占用",
                conditions=[
                    {"field": "process_running", "operator": "equals", "value": "yes"},
                    {"field": "recent_restart", "operator": "equals", "value": "yes"}
                ],
                conclusions=[
                    {"issue": "端口被占用", "severity": "medium", "solution": "stop_process"},
                    {"action": "停止现有进程", "description": "找到并停止占用端口的进程"},
                    {"action": "检查任务管理器", "description": "使用任务管理器查看相关进程"}
                ],
                confidence=0.9,
                priority=1
            ),
            DiagnosticRule(
                rule_id="can_change_port_solution",
                name="可更换端口",
                description="应用支持端口更换",
                conditions=[
                    {"field": "can_change_port", "operator": "equals", "value": "yes"},
                    {"field": "preferred_solution", "operator": "equals", "value": "使用不同的端口"}
                ],
                conclusions=[
                    {"issue": "端口冲突", "severity": "low", "solution": "change_port"},
                    {"action": "配置新端口", "description": "修改应用配置使用其他端口"},
                    {"action": "更新相关配置", "description": "确保所有相关配置都使用新端口"}
                ],
                confidence=0.95,
                priority=2
            )
        ]

        # 权限问题诊断规则
        rules["permission_issue"] = [
            DiagnosticRule(
                rule_id="file_permission_denied",
                name="文件权限不足",
                description="用户对文件没有足够的权限",
                conditions=[
                    {"field": "user_account_type", "operator": "not_equals", "value": "root用户"},
                    {"field": "file_ownership", "operator": "equals", "value": "no"},
                    {"field": "admin_access", "operator": "equals", "value": "yes"}
                ],
                conclusions=[
                    {"issue": "权限不足", "severity": "medium", "solution": "elevate_privileges"},
                    {"action": "使用管理员权限", "description": "右键以管理员身份运行"},
                    {"action": "修改文件权限", "description": "使用 chmod 或文件属性修改权限"}
                ],
                confidence=0.85,
                priority=1
            ),
            DiagnosticRule(
                rule_id="alternative_location",
                name="使用替代位置",
                description="在其他位置执行操作",
                conditions=[
                    {"field": "alternative_location", "operator": "equals", "value": "yes"},
                    {"field": "admin_access", "operator": "equals", "value": "no"}
                ],
                conclusions=[
                    {"issue": "位置权限限制", "severity": "low", "solution": "use_alternative_location"},
                    {"action": "使用用户目录", "description": "在用户主目录中执行操作"},
                    {"action": "创建临时目录", "description": "在有权限的目录中创建工作空间"}
                ],
                confidence=0.9,
                priority=2
            )
        ]

        return rules

    async def start_diagnostic_session(self, wizard_type: str, session_id: str = None) -> str:
        """
        启动诊断会话

        Args:
            wizard_type: 诊断向导类型
            session_id: 会话ID（可选）

        Returns:
            会话ID
        """
        if wizard_type not in self.wizard_templates:
            raise ValueError(f"Unknown wizard type: {wizard_type}")

        if not session_id:
            session_id = f"diag_{int(datetime.now().timestamp())}"

        # 创建诊断会话
        session = DiagnosticSession(
            session_id=session_id,
            wizard_type=wizard_type
        )

        self.active_sessions[session_id] = session

        self.logger.info(f"Started diagnostic session {session_id} for wizard {wizard_type}")

        return session_id

    async def run_diagnostic_wizard(self, session_id: str) -> Dict[str, Any]:
        """
        运行诊断向导

        Args:
            session_id: 会话ID

        Returns:
            诊断结果
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]
        wizard_steps = self.wizard_templates[session.wizard_type]

        print(f"\n{'='*80}")
        print(f"🔍 {self._get_wizard_title(session.wizard_type)}")
        print(f"{'='*80}")
        print(f"📋 将通过 {len(wizard_steps)} 个步骤来诊断问题")
        print(f"⏱️  预估总时间: {sum(step.estimated_time for step in wizard_steps)} 分钟")

        try:
            # 逐步执行诊断
            for i, step in enumerate(wizard_steps):
                session.current_step = i

                print(f"\n{'─'*60}")
                print(f"步骤 {i+1}/{len(wizard_steps)}: {step.title}")
                print(f"{'─'*60}")
                print(f"📝 {step.description}")

                if step.automated:
                    print("🤖 此步骤可以自动化执行")
                    # 这里可以添加自动化诊断逻辑

                # 收集步骤答案
                step_answers = await self._collect_step_answers(step, session.answers)

                # 更新会话答案
                session.answers.update(step_answers)

                # 分析当前步骤的结果
                step_analysis = self._analyze_step_answers(step, step_answers)
                session.findings.append(step_analysis)

                # 如果已经明确发现问题，可以选择提前结束
                if step_analysis.get("issue_identified", False) and i < len(wizard_steps) - 1:
                    print(f"\n✅ 已识别到问题，是否继续诊断其他可能的问题？")
                    continue_diagnosis = await self._ask_continue_diagnosis()
                    if not continue_diagnosis:
                        break

            # 应用诊断规则
            diagnosis_result = self._apply_diagnostic_rules(session)
            session.result = diagnosis_result["result"]
            session.findings.extend(diagnosis_result["findings"])
            session.recommendations = diagnosis_result["recommendations"]

            # 标记会话完成
            session.completed_at = datetime.now()

            # 生成诊断报告
            report = await self._generate_diagnostic_report(session)

            return report

        except Exception as e:
            self.logger.error(f"Error running diagnostic wizard: {e}")
            session.result = DiagnosisResult.INSUFFICIENT_INFO
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    async def _collect_step_answers(self, step: DiagnosticStep, existing_answers: Dict[str, Any]) -> Dict[str, Any]:
        """收集步骤答案"""
        step_answers = {}

        for question in step.questions:
            # 检查前置条件
            if question.condition and not self._evaluate_condition(question.condition, existing_answers):
                continue

            # 如果已有答案，跳过
            if question.question_id in existing_answers:
                step_answers[question.question_id] = existing_answers[question.question_id]
                continue

            # 收集答案
            answer = await self._ask_question(question)
            if answer is not None:
                step_answers[question.question_id] = answer

        return step_answers

    async def _ask_question(self, question: DiagnosticQuestion) -> Any:
        """询问问题"""
        print(f"\n❓ {question.text}")

        if question.help_text:
            print(f"💡 提示: {question.help_text}")

        try:
            if question.question_type == QuestionType.YES_NO:
                return await self._ask_yes_no_question(question)
            elif question.question_type == QuestionType.SINGLE_CHOICE:
                return await self._ask_single_choice_question(question)
            elif question.question_type == QuestionType.MULTIPLE_CHOICE:
                return await self._ask_multiple_choice_question(question)
            elif question.question_type == QuestionType.TEXT_INPUT:
                return await self._ask_text_input_question(question)
            elif question.question_type == QuestionType.NUMERIC_INPUT:
                return await self._ask_numeric_input_question(question)
            else:
                print(f"不支持的问题类型: {question.question_type}")
                return None

        except Exception as e:
            self.logger.error(f"Error asking question {question.question_id}: {e}")
            return question.default_value

    async def _ask_yes_no_question(self, question: DiagnosticQuestion) -> str:
        """询问是/否问题"""
        confirm_action = ConfirmationAction(
            action_id=f"question_{question.question_id}",
            title=question.text,
            description="",
            risk_level="low",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        return "yes" if response.result == ConfirmationResult.YES else "no"

    async def _ask_single_choice_question(self, question: DiagnosticQuestion) -> str:
        """询问单选题"""
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option}")

        while True:
            try:
                choice = input("请选择 (输入数字): ").strip()
                if not choice and question.default_value:
                    return question.default_value

                choice_num = int(choice)
                if 1 <= choice_num <= len(question.options):
                    return question.options[choice_num - 1]
                else:
                    print(f"请输入 1-{len(question.options)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
            except (KeyboardInterrupt, EOFError):
                return question.default_value

    async def _ask_text_input_question(self, question: DiagnosticQuestion) -> str:
        """询问文本输入问题"""
        while True:
            try:
                answer = input("请输入: ").strip()
                if not answer and question.default_value:
                    return question.default_value

                if not answer and question.required:
                    print("此问题为必填项，请输入答案")
                    continue

                # 验证输入
                if question.validation_rule and not re.match(question.validation_rule, answer):
                    print("输入格式不正确，请重新输入")
                    continue

                return answer

            except (KeyboardInterrupt, EOFError):
                return question.default_value

    async def _ask_numeric_input_question(self, question: DiagnosticQuestion) -> int:
        """询问数字输入问题"""
        while True:
            try:
                answer = input("请输入数字: ").strip()
                if not answer and question.default_value:
                    return question.default_value

                if not answer and question.required:
                    print("此问题为必填项，请输入数字")
                    continue

                # 验证数字格式
                if question.validation_rule and not re.match(question.validation_rule, answer):
                    print("输入格式不正确，请重新输入")
                    continue

                return int(answer)

            except ValueError:
                print("请输入有效的数字")
            except (KeyboardInterrupt, EOFError):
                return question.default_value

    async def _ask_multiple_choice_question(self, question: DiagnosticQuestion) -> List[str]:
        """询问多选题"""
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option}")

        while True:
            try:
                choice = input("请选择 (输入数字，多个用逗号分隔): ").strip()
                if not choice and question.default_value:
                    return question.default_value

                if not choice and question.required:
                    print("此问题为必填项，请选择答案")
                    continue

                choices = [int(x.strip()) for x in choice.split(",")]
                selected_options = []
                for choice_num in choices:
                    if 1 <= choice_num <= len(question.options):
                        selected_options.append(question.options[choice_num - 1])

                return selected_options

            except ValueError:
                print("请输入有效的数字，多个用逗号分隔")
            except (KeyboardInterrupt, EOFError):
                return question.default_value

    async def _ask_continue_diagnosis(self) -> bool:
        """询问是否继续诊断"""
        confirm_action = ConfirmationAction(
            action_id="continue_diagnosis",
            title="继续诊断",
            description="是否继续诊断其他可能的问题？",
            risk_level="low",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        return response.result == ConfirmationResult.YES

    def _evaluate_condition(self, condition: str, answers: Dict[str, Any]) -> bool:
        """评估条件"""
        try:
            # 简单的条件评估实现
            # 格式: field operator value
            parts = condition.split()
            if len(parts) != 3:
                return True

            field, operator, value = parts
            field_value = answers.get(field)

            if field_value is None:
                return False

            # 清理值中的引号
            cleaned_value = value.strip('\'"')

            if operator in ["equals", "=", "=="]:
                return str(field_value) == cleaned_value
            elif operator in ["not_equals", "!="]:
                return str(field_value) != cleaned_value
            elif operator in ["contains"]:
                return cleaned_value in str(field_value)
            else:
                # 未知操作符，返回True以保持兼容性
                return True

        except Exception as e:
            # 记录异常但不应该静默返回True
            self.logger.warning(f"Error evaluating condition '{condition}': {e}")
            return False

    def _analyze_step_answers(self, step: DiagnosticStep, answers: Dict[str, Any]) -> Dict[str, Any]:
        """分析步骤答案"""
        analysis = {
            "step_id": step.step_id,
            "step_title": step.title,
            "issue_identified": False,
            "indicators": [],
            "severity": "low"
        }

        # 基于答案分析问题指标
        for question in step.questions:
            if question.question_id not in answers:
                continue

            answer = answers[question.question_id]

            # 根据问题和答案分析
            if question.question_id == "can_access_internet" and answer == "no":
                analysis["issue_identified"] = True
                analysis["indicators"].append("互联网连接问题")
                analysis["severity"] = "high"

            elif question.question_id == "process_running" and answer == "yes":
                analysis["issue_identified"] = True
                analysis["indicators"].append("进程冲突")
                analysis["severity"] = "medium"

            elif question.question_id == "file_ownership" and answer == "no":
                analysis["issue_identified"] = True
                analysis["indicators"].append("文件权限问题")
                analysis["severity"] = "medium"

        return analysis

    def _apply_diagnostic_rules(self, session: DiagnosticSession) -> Dict[str, Any]:
        """应用诊断规则"""
        wizard_rules = self.diagnostic_rules.get(session.wizard_type, [])

        matched_rules = []
        findings = []
        recommendations = []

        # 评估每个规则
        for rule in wizard_rules:
            if self._evaluate_rule(rule, session.answers):
                matched_rules.append(rule)

                # 添加发现
                for conclusion in rule.conclusions:
                    if "issue" in conclusion:
                        findings.append({
                            "issue": conclusion["issue"],
                            "severity": conclusion.get("severity", "medium"),
                            "confidence": rule.confidence,
                            "rule_id": rule.rule_id
                        })

                    if "action" in conclusion:
                        recommendations.append({
                            "action": conclusion["action"],
                            "description": conclusion["description"],
                            "priority": rule.priority
                        })

        # 确定诊断结果
        if not matched_rules:
            result = DiagnosisResult.NO_ISSUE_FOUND
        elif len(matched_rules) == 1:
            result = DiagnosisResult.ISSUE_IDENTIFIED
        else:
            result = DiagnosisResult.MULTIPLE_ISSUES

        return {
            "result": result,
            "findings": findings,
            "recommendations": recommendations,
            "matched_rules": [rule.rule_id for rule in matched_rules]
        }

    def _evaluate_rule(self, rule: DiagnosticRule, answers: Dict[str, Any]) -> bool:
        """评估诊断规则"""
        for condition in rule.conditions:
            field = condition["field"]
            operator = condition["operator"]
            expected_value = condition["value"]

            if field not in answers:
                return False

            actual_value = answers[field]

            if operator == "equals":
                if str(actual_value) != str(expected_value):
                    return False
            elif operator == "not_equals":
                if str(actual_value) == str(expected_value):
                    return False
            else:
                return False

        return True

    async def _generate_diagnostic_report(self, session: DiagnosticSession) -> Dict[str, Any]:
        """生成诊断报告"""
        print(f"\n{'='*80}")
        print("📋 诊断报告")
        print(f"{'='*80}")

        # 基本信息
        print(f"🆔 会话ID: {session.session_id}")
        print(f"🔍 诊断类型: {self._get_wizard_title(session.wizard_type)}")
        print(f"⏱️  开始时间: {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ 完成时间: {session.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 诊断结果: {session.result.value}")

        # 问题发现
        if session.findings:
            print(f"\n🔍 发现的问题:")
            for finding in session.findings:
                if "issue_identified" in finding and finding["issue_identified"]:
                    for indicator in finding.get("indicators", []):
                        print(f"  • {indicator}")

        # 诊断规则结果
        rule_findings = [f for f in session.findings if "rule_id" in f]
        if rule_findings:
            print(f"\n📊 详细诊断结果:")
            for finding in rule_findings:
                confidence = finding["confidence"] * 100
                severity_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(finding["severity"], "⚪")
                print(f"  {severity_icon} {finding['issue']} (置信度: {confidence:.1f}%)")

        # 推荐操作
        if session.recommendations:
            print(f"\n💡 推荐操作:")
            for i, rec in enumerate(session.recommendations, 1):
                priority_icon = {"1": "🔥", "2": "⚡", "3": "📌"}.get(str(rec["priority"]), "📝")
                print(f"  {i}. {priority_icon} {rec['action']}")
                print(f"     {rec['description']}")

        # 询问用户是否需要自动执行推荐操作
        if session.recommendations:
            print(f"\n🚀 是否需要自动执行推荐操作？")
            auto_execute = await self._ask_auto_execute_recommendations()
            if auto_execute:
                # 这里可以添加自动执行逻辑
                print("自动执行功能正在开发中...")

        return {
            "success": True,
            "session_id": session.session_id,
            "result": session.result.value,
            "findings": session.findings,
            "recommendations": session.recommendations,
            "answers": session.answers
        }

    async def _ask_auto_execute_recommendations(self) -> bool:
        """询问是否自动执行推荐操作"""
        confirm_action = ConfirmationAction(
            action_id="auto_execute",
            title="自动执行操作",
            description="是否自动执行推荐的操作？",
            risk_level="medium",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        return response.result == ConfirmationResult.YES

    def _get_wizard_title(self, wizard_type: str) -> str:
        """获取向导标题"""
        titles = {
            "network_connectivity": "网络连接问题诊断",
            "port_conflict": "端口冲突问题诊断",
            "permission_issue": "权限问题诊断"
        }
        return titles.get(wizard_type, wizard_type)

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话摘要"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "wizard_type": session.wizard_type,
            "result": session.result.value,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "findings_count": len(session.findings),
            "recommendations_count": len(session.recommendations),
            "answers": session.answers
        }

    def end_session(self, session_id: str) -> bool:
        """结束诊断会话"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        if not session.completed_at:
            session.completed_at = datetime.now()
            session.result = DiagnosisResult.INSUFFICIENT_INFO

        del self.active_sessions[session_id]
        self.logger.info(f"Ended diagnostic session {session_id}")
        return True