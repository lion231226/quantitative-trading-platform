"""
Support Orchestrator Module

This module provides comprehensive user support coordination, extending
the RecoveryOrchestrator patterns for user guidance and assistance.
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import traceback

from core.knowledge_base import EnhancedKnowledgeBase, ContentType, DifficultyLevel
from utils.user_confirmation import UserConfirmation, ConfirmationAction, ConfirmationResult
from utils.logger import get_logger

logger = get_logger(__name__)


class SupportSession(Enum):
    """支持会话状态"""
    IDLE = "idle"
    ACTIVE = "active"
    DIAGNOSIS = "diagnosis"
    GUIDANCE = "guidance"
    ESCALATION = "escalation"
    COMPLETED = "completed"


class SupportPriority(Enum):
    """支持优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SupportRequest:
    """支持请求"""
    request_id: str
    user_id: str
    issue_description: str
    category: str
    priority: SupportPriority
    context: Dict[str, Any] = field(default_factory=dict)
    error_codes: List[str] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: SupportSession = SupportSession.IDLE


@dataclass
class SupportSession:
    """支持会话"""
    session_id: str
    request: SupportRequest
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    resolved_issues: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    feedback: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportAction:
    """支持操作"""
    action_id: str
    title: str
    description: str
    action_type: str  # "guide", "solution", "diagnosis", "escalate"
    content_id: Optional[str] = None
    steps: List[str] = field(default_factory=list)
    estimated_time: int = 0
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    automated: bool = False


class SupportOrchestrator:
    """
    支持协调器，提供全面的用户支持功能
    """

    def __init__(self, knowledge_base_dir: str = "knowledge_base_data"):
        """
        初始化支持协调器

        Args:
            knowledge_base_dir: 知识库数据目录
        """
        self.logger = get_logger(self.__class__.__name__)

        # 初始化知识库
        self.knowledge_base = EnhancedKnowledgeBase(knowledge_base_dir)

        # 初始化用户确认管理器
        self.user_confirmation = UserConfirmation()

        # 支持会话管理
        self.active_sessions: Dict[str, SupportSession] = {}
        self.support_requests: List[SupportRequest] = []

        # 支持操作模板
        self.action_templates = self._initialize_action_templates()

        # 自动诊断规则
        self.diagnosis_rules = self._initialize_diagnosis_rules()

        # 支持历史
        self.support_history: List[Dict[str, Any]] = []

        self.logger.info("Support Orchestrator initialized")

    def _initialize_action_templates(self) -> Dict[str, SupportAction]:
        """初始化支持操作模板"""
        templates = {}

        # 端口冲突解决模板
        templates["port_conflict"] = SupportAction(
            action_id="port_conflict_solution",
            title="解决端口冲突",
            description="帮助您解决应用程序端口被占用的问题",
            action_type="solution",
            steps=[
                "识别占用端口的进程",
                "停止冲突进程或使用不同端口",
                "验证应用程序能否正常启动"
            ],
            estimated_time=10,
            difficulty=DifficultyLevel.BEGINNER,
            automated=True
        )

        # 权限问题解决模板
        templates["permission_issue"] = SupportAction(
            action_id="permission_solution",
            title="解决权限问题",
            description="帮助您解决文件访问权限不足的问题",
            action_type="solution",
            steps=[
                "检查当前用户权限",
                "修改文件或目录权限",
                "重新运行应用程序"
            ],
            estimated_time=15,
            difficulty=DifficultyLevel.INTERMEDIATE,
            automated=False
        )

        # 网络连接问题模板
        templates["network_issue"] = SupportAction(
            action_id="network_solution",
            title="解决网络连接问题",
            description="帮助您诊断和解决网络连接问题",
            action_type="diagnosis",
            steps=[
                "测试基本网络连接",
                "检查DNS解析",
                "验证代理设置",
                "检查防火墙配置"
            ],
            estimated_time=20,
            difficulty=DifficultyLevel.INTERMEDIATE,
            automated=True
        )

        # 依赖安装模板
        templates["dependency_issue"] = SupportAction(
            action_id="dependency_solution",
            title="解决依赖问题",
            description="帮助您安装缺失的依赖包",
            action_type="solution",
            steps=[
                "识别缺失的依赖",
                "选择合适的安装方法",
                "验证安装结果"
            ],
            estimated_time=25,
            difficulty=DifficultyLevel.BEGINNER,
            automated=True
        )

        return templates

    def _initialize_diagnosis_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """初始化自动诊断规则"""
        rules = {}

        # 端口冲突诊断规则
        rules["port_conflict"] = [
            {
                "pattern": r"port.*already in use|address already in use",
                "keywords": ["port", "3000", "8000", "5432", "6379"],
                "confidence": 0.9,
                "suggested_action": "port_conflict"
            },
            {
                "pattern": r"bind.*failed|connection refused",
                "keywords": ["bind", "connection", "refused"],
                "confidence": 0.7,
                "suggested_action": "port_conflict"
            }
        ]

        # 权限问题诊断规则
        rules["permission_issue"] = [
            {
                "pattern": r"permission denied|access denied",
                "keywords": ["permission", "denied", "access", "forbidden"],
                "confidence": 0.95,
                "suggested_action": "permission_issue"
            },
            {
                "pattern": r"cannot create|cannot write|cannot read",
                "keywords": ["cannot", "create", "write", "read", "directory"],
                "confidence": 0.8,
                "suggested_action": "permission_issue"
            }
        ]

        # 网络问题诊断规则
        rules["network_issue"] = [
            {
                "pattern": r"network.*unreachable|connection timeout",
                "keywords": ["network", "unreachable", "timeout", "connection"],
                "confidence": 0.85,
                "suggested_action": "network_issue"
            },
            {
                "pattern": r"dns.*failed|name resolution",
                "keywords": ["dns", "resolution", "hostname", "lookup"],
                "confidence": 0.9,
                "suggested_action": "network_issue"
            }
        ]

        # 依赖问题诊断规则
        rules["dependency_issue"] = [
            {
                "pattern": r"module.*not found|package.*not found",
                "keywords": ["module", "package", "not", "found", "import"],
                "confidence": 0.9,
                "suggested_action": "dependency_issue"
            },
            {
                "pattern": r"no module named|cannot import",
                "keywords": ["module", "named", "import", "error"],
                "confidence": 0.95,
                "suggested_action": "dependency_issue"
            }
        ]

        return rules

    async def start_support_session(self, user_id: str, issue_description: str,
                                   category: str = "general",
                                   priority: SupportPriority = SupportPriority.MEDIUM,
                                   context: Dict[str, Any] = None) -> str:
        """
        启动支持会话

        Args:
            user_id: 用户ID
            issue_description: 问题描述
            category: 问题分类
            priority: 优先级
            context: 上下文信息

        Returns:
            会话ID
        """
        # 创建支持请求
        request = SupportRequest(
            request_id=f"req_{int(datetime.now().timestamp())}",
            user_id=user_id,
            issue_description=issue_description,
            category=category,
            priority=priority,
            context=context or {}
        )

        # 创建支持会话
        session_id = f"session_{int(datetime.now().timestamp())}"
        session = SupportSession(
            session_id=session_id,
            request=request
        )

        # 存储会话
        self.active_sessions[session_id] = session
        self.support_requests.append(request)

        # 记录交互
        self._record_interaction(session_id, "session_started", {
            "issue_description": issue_description,
            "category": category,
            "priority": priority.value
        })

        self.logger.info(f"Started support session {session_id} for user {user_id}")

        # 根据优先级决定是否立即开始诊断
        if priority in [SupportPriority.HIGH, SupportPriority.URGENT]:
            await self.begin_diagnosis(session_id)

        return session_id

    async def begin_diagnosis(self, session_id: str) -> bool:
        """
        开始问题诊断

        Args:
            session_id: 会话ID

        Returns:
            是否成功开始诊断
        """
        if session_id not in self.active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return False

        session = self.active_sessions[session_id]
        session.request.status = SupportSession.DIAGNOSIS

        # 分析问题描述
        diagnosis_result = await self._analyze_issue(session.request)

        # 记录诊断结果
        self._record_interaction(session_id, "diagnosis_completed", diagnosis_result)

        # 生成推荐操作
        recommended_actions = await self._generate_recommended_actions(diagnosis_result)

        # 呈现诊断结果给用户
        await self._present_diagnosis_results(session_id, diagnosis_result, recommended_actions)

        return True

    async def _analyze_issue(self, request: SupportRequest) -> Dict[str, Any]:
        """分析问题"""
        analysis = {
            "issue_description": request.issue_description,
            "detected_patterns": [],
            "confidence_scores": {},
            "suggested_categories": [],
            "related_error_codes": [],
            "system_context": request.context
        }

        # 使用诊断规则分析
        for category, rules in self.diagnosis_rules.items():
            for rule in rules:
                confidence = self._calculate_pattern_confidence(
                    request.issue_description, rule
                )
                if confidence > 0.5:
                    analysis["detected_patterns"].append({
                        "category": category,
                        "pattern": rule["pattern"],
                        "confidence": confidence,
                        "suggested_action": rule["suggested_action"]
                    })
                    analysis["confidence_scores"][category] = confidence

        # 搜索知识库
        search_result = self.knowledge_base.search(request.issue_description, limit=10)
        analysis["knowledge_base_matches"] = search_result["results"]

        # 提取相关错误代码
        for match in search_result["results"]:
            if match["type"] == "error_solution":
                analysis["related_error_codes"].append(match["id"])

        # 确定建议分类
        if analysis["confidence_scores"]:
            analysis["suggested_categories"] = [
                cat for cat, score in sorted(
                    analysis["confidence_scores"].items(),
                    key=lambda x: x[1],
                    reverse=True
                ) if score > 0.6
            ]

        return analysis

    def _calculate_pattern_confidence(self, text: str, rule: Dict[str, Any]) -> float:
        """计算模式匹配置信度"""
        import re

        # 正则表达式匹配
        pattern_match = re.search(rule["pattern"], text, re.IGNORECASE)
        pattern_score = 1.0 if pattern_match else 0.0

        # 关键词匹配
        keyword_matches = 0
        for keyword in rule["keywords"]:
            if keyword.lower() in text.lower():
                keyword_matches += 1

        keyword_score = keyword_matches / len(rule["keywords"]) if rule["keywords"] else 0.0

        # 综合置信度
        confidence = (pattern_score * 0.7 + keyword_score * 0.3) * rule.get("confidence", 1.0)

        return min(confidence, 1.0)

    async def _generate_recommended_actions(self, diagnosis_result: Dict[str, Any]) -> List[SupportAction]:
        """生成推荐操作"""
        actions = []

        # 基于诊断结果生成操作
        for pattern in diagnosis_result["detected_patterns"]:
            action_key = pattern["suggested_action"]
            if action_key in self.action_templates:
                action = self.action_templates[action_key]
                actions.append(action)

        # 基于知识库匹配生成操作
        for match in diagnosis_result["knowledge_base_matches"]:
            if match["type"] == "guide":
                guide = self.knowledge_base.get_guide(match["id"])
                if guide:
                    action = SupportAction(
                        action_id=f"guide_{match['id']}",
                        title=f"查看指南: {guide.title}",
                        description=guide.description,
                        action_type="guide",
                        content_id=match["id"],
                        estimated_time=guide.estimated_total_time,
                        difficulty=guide.difficulty
                    )
                    actions.append(action)

        return actions

    async def _present_diagnosis_results(self, session_id: str, diagnosis: Dict[str, Any],
                                       actions: List[SupportAction]):
        """呈现诊断结果"""
        print("\n" + "="*80)
        print("🔍 问题诊断结果")
        print("="*80)

        # 显示检测到的问题模式
        if diagnosis["detected_patterns"]:
            print("\n📋 检测到的问题模式:")
            for pattern in diagnosis["detected_patterns"]:
                confidence = pattern["confidence"] * 100
                print(f"  • {pattern['category']} (置信度: {confidence:.1f}%)")

        # 显示推荐操作
        if actions:
            print(f"\n🎯 推荐的解决方案 ({len(actions)} 个):")
            for i, action in enumerate(actions, 1):
                time_text = f" (预估时间: {action.estimated_time}分钟)" if action.estimated_time > 0 else ""
                auto_text = " [自动化]" if action.automated else ""
                print(f"  {i}. {action.title}{time_text}{auto_text}")
                print(f"     {action.description}")

            # 询问用户选择
            print(f"\n请选择要执行的操作 (1-{len(actions)}):")
            try:
                choice = input("输入数字或按回车跳过: ").strip()
                if choice and choice.isdigit():
                    action_index = int(choice) - 1
                    if 0 <= action_index < len(actions):
                        await self.execute_support_action(session_id, actions[action_index])
            except (ValueError, KeyboardInterrupt):
                print("操作已取消")

        else:
            print("\n❓ 未找到明确的解决方案，建议联系技术支持")
            await self._offer_escalation_option(session_id)

    async def execute_support_action(self, session_id: str, action: SupportAction) -> bool:
        """
        执行支持操作

        Args:
            session_id: 会话ID
            action: 支持操作

        Returns:
            是否执行成功
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        print(f"\n🚀 执行操作: {action.title}")
        print(f"📝 描述: {action.description}")

        # 记录操作执行
        self._record_interaction(session_id, "action_executed", {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "title": action.title
        })

        try:
            if action.action_type == "solution":
                success = await self._execute_solution_action(session_id, action)
            elif action.action_type == "guide":
                success = await self._execute_guide_action(session_id, action)
            elif action.action_type == "diagnosis":
                success = await self._execute_diagnosis_action(session_id, action)
            else:
                print(f"未知的操作类型: {action.action_type}")
                success = False

            if success:
                session.resolved_issues.append(action.action_id)
                print("✅ 操作执行成功")
            else:
                print("❌ 操作执行失败")

            return success

        except Exception as e:
            self.logger.error(f"Error executing support action: {e}")
            print(f"❌ 执行过程中出现错误: {e}")
            return False

    async def _execute_solution_action(self, session_id: str, action: SupportAction) -> bool:
        """执行解决方案操作"""
        print(f"\n📋 解决方案步骤:")
        for i, step in enumerate(action.steps, 1):
            print(f"  {i}. {step}")

        # 如果是自动化操作，尝试执行
        if action.automated:
            print("\n🤖 尝试自动化执行...")
            # 这里可以实现具体的自动化逻辑
            print("自动化功能正在开发中，请手动执行上述步骤")

        # 询问用户确认
        confirm_action = ConfirmationAction(
            action_id=f"confirm_{action.action_id}",
            title="确认解决方案执行",
            description=f"您是否已按照上述步骤解决了问题？",
            risk_level="low",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        return response.result == ConfirmationResult.YES

    async def _execute_guide_action(self, session_id: str, action: SupportAction) -> bool:
        """执行指南操作"""
        if not action.content_id:
            print("❌ 缺少指南内容ID")
            return False

        guide = self.knowledge_base.get_guide(action.content_id)
        if not guide:
            print("❌ 未找到指南内容")
            return False

        print(f"\n📖 操作指南: {guide.title}")
        print(f"📝 描述: {guide.description}")
        print(f"⏱️  预估时间: {guide.estimated_total_time}分钟")
        print(f"📊 难度: {guide.difficulty.value}")

        print(f"\n📋 指南章节:")
        for section in guide.sections:
            print(f"  {section.order}. {section.title}")
            if section.estimated_time > 0:
                print(f"     预估时间: {section.estimated_time}分钟")

        # 询问用户是否要查看详细内容
        confirm_action = ConfirmationAction(
            action_id=f"view_guide_{action.content_id}",
            title="查看指南详情",
            description="是否查看详细的指南内容？",
            risk_level="low",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        if response.result == ConfirmationResult.YES:
            self._display_guide_details(guide)

        return True

    async def _execute_diagnosis_action(self, session_id: str, action: SupportAction) -> bool:
        """执行诊断操作"""
        print(f"\n🔍 开始详细诊断...")

        # 收集系统信息
        system_info = await self._collect_system_info()
        print("📊 系统信息已收集")

        # 执行具体诊断步骤
        for step in action.steps:
            print(f"  • {step}")
            # 这里可以实现具体的诊断逻辑

        # 更新会话上下文
        session = self.active_sessions[session_id]
        session.request.system_info.update(system_info)

        return True

    async def _collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        import platform
        import psutil

        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": {
                path: {
                    "total": psutil.disk_usage(path).total,
                    "used": psutil.disk_usage(path).used,
                    "free": psutil.disk_usage(path).free
                }
                for path in ["/"] if platform.system() != "Windows" else ["C:\\\\"]
            }
        }

        return system_info

    def _display_guide_details(self, guide):
        """显示指南详情"""
        print(f"\n{'='*80}")
        print(f"📖 {guide.title}")
        print(f"{'='*80}")

        for section in guide.sections:
            print(f"\n📂 {section.order}. {section.title}")
            print(f"{'-'*60}")
            print(section.content)

            if section.tips:
                print(f"\n💡 提示:")
                for tip in section.tips:
                    print(f"  • {tip}")

            if section.code_examples:
                print(f"\n💻 代码示例:")
                for example in section.code_examples:
                    print(f"```")
                    print(example)
                    print(f"```")

    async def _offer_escalation_option(self, session_id: str):
        """提供升级选项"""
        confirm_action = ConfirmationAction(
            action_id=f"escalate_{session_id}",
            title="联系技术支持",
            description="是否需要联系技术支持团队获得帮助？",
            risk_level="low",
            confirm_type="yes_no"
        )

        response = await self.user_confirmation.request_confirmation(confirm_action)
        if response.result == ConfirmationResult.YES:
            await self.escalate_to_human_support(session_id)

    async def escalate_to_human_support(self, session_id: str) -> bool:
        """升级到人工支持"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        session.request.status = SupportSession.ESCALATION

        print("\n📞 正在为您连接技术支持团队...")
        print("📋 已收集以下信息:")
        print(f"  • 问题描述: {session.request.issue_description}")
        print(f"  • 问题分类: {session.request.category}")
        print(f"  • 优先级: {session.request.priority.value}")

        if session.request.system_info:
            print("  • 系统信息已收集")

        print("\n✅ 您的支持请求已提交，技术支持团队将尽快与您联系")

        # 记录升级操作
        self._record_interaction(session_id, "escalated_to_human", {
            "timestamp": datetime.now().isoformat(),
            "system_info": session.request.system_info
        })

        return True

    def _record_interaction(self, session_id: str, interaction_type: str, details: Dict[str, Any]):
        """记录交互"""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "details": details
        }

        session.interactions.append(interaction)
        session.last_activity = datetime.now()

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话摘要"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "user_id": session.request.user_id,
            "issue_description": session.request.issue_description,
            "status": session.request.status.value,
            "started_at": session.started_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "interactions_count": len(session.interactions),
            "resolved_issues": session.resolved_issues,
            "pending_actions": session.pending_actions
        }

    def end_support_session(self, session_id: str) -> bool:
        """结束支持会话"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        session.request.status = SupportSession.COMPLETED

        # 添加到支持历史
        self.support_history.append({
            "session_id": session_id,
            "user_id": session.request.user_id,
            "issue_description": session.request.issue_description,
            "category": session.request.category,
            "started_at": session.started_at.isoformat(),
            "ended_at": datetime.now().isoformat(),
            "interactions_count": len(session.interactions),
            "resolved_issues_count": len(session.resolved_issues),
            "success": len(session.resolved_issues) > 0
        })

        # 移除活跃会话
        del self.active_sessions[session_id]

        self.logger.info(f"Ended support session {session_id}")
        return True

    async def provide_interactive_help(self, query: str) -> Dict[str, Any]:
        """提供交互式帮助"""
        # 搜索知识库
        search_result = self.knowledge_base.search(query, limit=5)

        # 获取热门内容
        popular_content = self.knowledge_base.get_popular_content(limit=3)

        return {
            "search_results": search_result["results"],
            "popular_content": popular_content,
            "total_results": search_result["total"],
            "query": query
        }