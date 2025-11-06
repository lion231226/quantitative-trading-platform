"""
Comprehensive User Support System Tests

This test suite validates all components of the user support and guidance system,
including knowledge base, diagnostic wizard, support contact, and feedback systems.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import the modules we're testing
from core.knowledge_base import EnhancedKnowledgeBase, Guide, FAQ, GuideSection, DifficultyLevel
from core.diagnostic_wizard import DiagnosticWizard, DiagnosticSession, DiagnosisResult
from core.support_contact import SupportContactSystem, SupportTicket, Priority as SupportPriority, ContactChannel, TicketStatus
from core.feedback_system import FeedbackSystem, FeedbackType, FeedbackCategory, Sentiment, FeedbackStatus, Priority


class TestEnhancedKnowledgeBase:
    """测试增强型知识库"""

    @pytest.fixture
    def knowledge_base(self):
        """创建知识库测试实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            kb = EnhancedKnowledgeBase(temp_dir)
            yield kb

    def test_initialization(self, knowledge_base):
        """测试知识库初始化"""
        assert knowledge_base is not None
        assert len(knowledge_base.guides) == 0
        assert len(knowledge_base.faqs) == 0
        assert len(knowledge_base.search_index) > 0  # 应该有错误解决方案的索引

    def test_add_guide(self, knowledge_base):
        """测试添加指南"""
        guide = Guide(
            guide_id="test_guide_1",
            title="测试指南",
            description="这是一个测试指南",
            category="测试",
            tags=["测试", "指南"],
            sections=[
                GuideSection(
                    section_id="section_1",
                    title="第一节",
                    content="这是第一节的内容",
                    order=1,
                    estimated_time=5,
                    difficulty=DifficultyLevel.BEGINNER
                )
            ],
            target_audience=["开发者"],
            estimated_total_time=10,
            difficulty=DifficultyLevel.BEGINNER
        )

        result = knowledge_base.add_guide(guide)
        assert result is True
        assert "test_guide_1" in knowledge_base.guides

    def test_add_faq(self, knowledge_base):
        """测试添加FAQ"""
        faq = FAQ(
            faq_id="test_faq_1",
            question="这是一个测试问题吗？",
            answer="是的，这是一个测试问题",
            category="测试",
            tags=["测试", "FAQ"],
            difficulty=DifficultyLevel.BEGINNER
        )

        result = knowledge_base.add_faq(faq)
        assert result is True
        assert "test_faq_1" in knowledge_base.faqs

    def test_search_functionality(self, knowledge_base):
        """测试搜索功能"""
        # 添加测试数据
        guide = Guide(
            guide_id="search_test_guide",
            title="端口冲突解决指南",
            description="解决端口冲突问题的详细指南",
            category="网络",
            tags=["端口", "冲突"],
            sections=[
                GuideSection(
                    section_id="section_1",
                    title="识别端口冲突",
                    content="如何识别端口占用问题",
                    order=1,
                    estimated_time=5,
                    difficulty=DifficultyLevel.BEGINNER
                )
            ],
            target_audience=["开发者"],
            estimated_total_time=10,
            difficulty=DifficultyLevel.BEGINNER
        )

        knowledge_base.add_guide(guide)

        # 测试搜索
        result = knowledge_base.search("端口冲突")
        assert result["total"] > 0
        assert len(result["results"]) > 0
        assert any(r["title"] == "端口冲突解决指南" for r in result["results"])

    def test_get_popular_content(self, knowledge_base):
        """测试获取热门内容"""
        # 添加一些测试数据
        for i in range(5):
            faq = FAQ(
                faq_id=f"faq_{i}",
                question=f"测试问题 {i}",
                answer=f"测试答案 {i}",
                category="测试",
                tags=["测试"],
                difficulty=DifficultyLevel.BEGINNER,
                helpful_count=i * 2  # 模拟不同的有用性评分
            )
            knowledge_base.add_faq(faq)

        # 模拟一些访问
        knowledge_base.analytics["content_access"] = {
            "faq:faq_3": 10,
            "faq:faq_1": 5,
            "faq:faq_2": 3
        }

        popular = knowledge_base.get_popular_content("faq", limit=3)
        assert len(popular) <= 3
        # 应该按访问次数排序
        if len(popular) >= 2:
            assert popular[0]["access_count"] >= popular[1]["access_count"]

    def test_content_rating(self, knowledge_base):
        """测试内容评分功能"""
        faq = FAQ(
            faq_id="rating_test_faq",
            question="评分测试问题",
            answer="评分测试答案",
            category="测试",
            tags=["测试"],
            difficulty=DifficultyLevel.BEGINNER
        )
        knowledge_base.add_faq(faq)

        # 测试有用评分
        knowledge_base.rate_content_helpful("rating_test_faq", "faq", True)
        assert knowledge_base.faqs["rating_test_faq"].helpful_count == 1

        knowledge_base.rate_content_helpful("rating_test_faq", "faq", False)
        assert knowledge_base.faqs["rating_test_faq"].not_helpful_count == 1


class TestDiagnosticWizard:
    """测试诊断向导"""

    @pytest.fixture
    def diagnostic_wizard(self):
        """创建诊断向导测试实例"""
        return DiagnosticWizard()

    def test_initialization(self, diagnostic_wizard):
        """测试诊断向导初始化"""
        assert diagnostic_wizard is not None
        assert len(diagnostic_wizard.wizard_templates) > 0
        assert "network_connectivity" in diagnostic_wizard.wizard_templates
        assert "port_conflict" in diagnostic_wizard.wizard_templates
        assert len(diagnostic_wizard.diagnostic_rules) > 0

    @pytest.mark.asyncio
    async def test_start_diagnostic_session(self, diagnostic_wizard):
        """测试启动诊断会话"""
        session_id = await diagnostic_wizard.start_diagnostic_session("network_connectivity")
        assert session_id is not None
        assert session_id in diagnostic_wizard.active_sessions

        session = diagnostic_wizard.active_sessions[session_id]
        assert session.wizard_type == "network_connectivity"
        assert session.current_step == 0
        assert len(session.answers) == 0

    @pytest.mark.asyncio
    async def test_diagnostic_rule_evaluation(self, diagnostic_wizard):
        """测试诊断规则评估"""
        # 创建测试会话
        session_id = await diagnostic_wizard.start_diagnostic_session("network_connectivity")
        session = diagnostic_wizard.active_sessions[session_id]

        # 设置测试答案
        session.answers = {
            "can_access_internet": "no",
            "ping_by_ip": "no",
            "ping_by_domain": "yes"
        }

        # 应用诊断规则
        rules = diagnostic_wizard.diagnostic_rules["network_connectivity"]
        matched_rules = []

        for rule in rules:
            if diagnostic_wizard._evaluate_rule(rule, session.answers):
                matched_rules.append(rule)

        # 应该匹配到互联网连接问题的规则
        assert len(matched_rules) > 0
        assert any(rule.rule_id == "internet_down" for rule in matched_rules)

    def test_condition_evaluation(self, diagnostic_wizard):
        """测试条件评估"""
        answers = {
            "can_access_internet": "no",
            "using_proxy": "yes"
        }

        # 测试等于条件
        assert diagnostic_wizard._evaluate_condition("can_access_internet == 'no'", answers) is True
        assert diagnostic_wizard._evaluate_condition("can_access_internet == 'yes'", answers) is False

        # 测试不等于条件
        assert diagnostic_wizard._evaluate_condition("using_proxy != 'no'", answers) is True

        # 测试包含条件
        answers["text_field"] = "这是一个端口冲突问题"
        assert diagnostic_wizard._evaluate_condition("text_field contains '端口'", answers) is True

    def test_step_answer_analysis(self, diagnostic_wizard):
        """测试步骤答案分析"""
        step = diagnostic_wizard.wizard_templates["network_connectivity"][0]
        answers = {
            "can_access_internet": "no"
        }

        analysis = diagnostic_wizard._analyze_step_answers(step, answers)
        assert analysis["step_id"] == step.step_id
        assert analysis["issue_identified"] is True
        assert "互联网连接问题" in analysis["indicators"]

    @pytest.mark.asyncio
    async def test_ask_question_methods(self, diagnostic_wizard):
        """测试问题询问方法"""
        # 测试是/否问题
        yes_no_question = Mock()
        yes_no_question.question_id = "test_yes_no"
        yes_no_question.text = "测试问题"
        yes_no_question.question_type = "yes_no"
        yes_no_question.default_value = "yes"

        with patch('builtins.input', return_value='y'):
            answer = await diagnostic_wizard._ask_yes_no_question(yes_no_question)
            assert answer == "yes"

        # 测试单选题
        single_choice_question = Mock()
        single_choice_question.question_id = "test_single_choice"
        single_choice_question.text = "测试单选题"
        single_choice_question.question_type = "single_choice"
        single_choice_question.options = ["选项1", "选项2", "选项3"]
        single_choice_question.default_value = "选项1"

        with patch('builtins.input', return_value='2'):
            answer = await diagnostic_wizard._ask_single_choice_question(single_choice_question)
            assert answer == "选项2"


class TestSupportContactSystem:
    """测试支持联系系统"""

    @pytest.fixture
    def support_system(self):
        """创建支持系统测试实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = SupportContactSystem(temp_dir)
            yield system

    def test_initialization(self, support_system):
        """测试支持系统初始化"""
        assert support_system is not None
        assert len(support_system.contact_channels) > 0
        assert "email" in support_system.contact_channels
        assert "github" in support_system.contact_channels

    def test_get_available_channels(self, support_system):
        """测试获取可用渠道"""
        channels = support_system.get_available_channels()
        assert len(channels) > 0
        assert all(channel.active for channel in channels)

    @pytest.mark.asyncio
    async def test_create_support_ticket(self, support_system):
        """测试创建支持工单"""
        ticket_id = await support_system.create_support_ticket(
            user_id="test_user",
            title="测试工单",
            description="这是一个测试工单",
            category="测试",
            priority=Priority.MEDIUM,
            include_diagnostics=False
        )

        assert ticket_id is not None
        assert ticket_id in support_system.tickets

        ticket = support_system.tickets[ticket_id]
        assert ticket.user_id == "test_user"
        assert ticket.title == "测试工单"
        assert ticket.priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_collect_diagnostic_data(self, support_system):
        """测试诊断数据收集"""
        diagnostic_data = await support_system._collect_diagnostic_data()

        assert "system_info" in diagnostic_data
        assert "environment_info" in diagnostic_data
        assert "error_logs" in diagnostic_data
        assert "configuration_files" in diagnostic_data

        system_info = diagnostic_data["system_info"]
        assert "platform" in system_info
        assert "python_version" in system_info

    def test_update_ticket_status(self, support_system):
        """测试更新工单状态"""
        # 先创建一个工单
        ticket = SupportTicket(
            ticket_id="test_ticket",
            user_id="test_user",
            title="测试工单",
            description="测试描述",
            category="测试",
            priority=Priority.MEDIUM,
            contact_channel=ContactChannel.EMAIL,
            contact_info="test@example.com"
        )
        support_system.tickets["test_ticket"] = ticket

        # 更新状态
        result = support_system.update_ticket_status(
            "test_ticket",
            TicketStatus.IN_PROGRESS,
            assigned_to="support_agent"
        )

        assert result is True
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.assigned_to == "support_agent"

    def test_user_feedback(self, support_system):
        """测试用户反馈"""
        # 创建工单
        ticket = SupportTicket(
            ticket_id="feedback_test_ticket",
            user_id="test_user",
            title="反馈测试工单",
            description="测试描述",
            category="测试",
            priority=Priority.MEDIUM,
            contact_channel=ContactChannel.EMAIL,
            contact_info="test@example.com"
        )
        support_system.tickets["feedback_test_ticket"] = ticket

        # 添加反馈
        result = support_system.add_user_feedback("feedback_test_ticket", 5, "很好的支持！")
        assert result is True
        assert ticket.user_feedback["rating"] == 5
        assert ticket.user_feedback["comment"] == "很好的支持！"

    def test_support_statistics(self, support_system):
        """测试支持统计"""
        # 添加一些测试工单
        for i in range(5):
            ticket = SupportTicket(
                ticket_id=f"stat_test_ticket_{i}",
                user_id=f"test_user_{i}",
                title=f"测试工单 {i}",
                description=f"测试描述 {i}",
                category="测试",
                priority=Priority.MEDIUM,
                contact_channel=ContactChannel.EMAIL,
                contact_info=f"test{i}@example.com"
            )
            support_system.tickets[ticket.ticket_id] = ticket

        stats = support_system.get_support_statistics()
        assert stats["total_tickets"] == 5
        assert "by_status" in stats
        assert "by_priority" in stats
        assert "by_channel" in stats


class TestFeedbackSystem:
    """测试反馈系统"""

    @pytest.fixture
    def feedback_system(self):
        """创建反馈系统测试实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = FeedbackSystem(temp_dir)
            yield system

    def test_initialization(self, feedback_system):
        """测试反馈系统初始化"""
        assert feedback_system is not None
        assert len(feedback_system.sentiment_keywords) > 0
        assert len(feedback_system.feedback_templates) > 0
        assert len(feedback_system.classification_rules) > 0

    @pytest.mark.asyncio
    async def test_submit_feedback(self, feedback_system):
        """测试提交反馈"""
        feedback_id = await feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.GENERAL_FEEDBACK,
            title="测试反馈",
            description="这是一个测试反馈",
            rating=4
        )

        assert feedback_id is not None
        assert feedback_id in feedback_system.feedback

        feedback = feedback_system.feedback[feedback_id]
        assert feedback.user_id == "test_user"
        assert feedback.title == "测试反馈"
        assert feedback.rating == 4

    def test_auto_classification(self, feedback_system):
        """测试自动分类"""
        # 测试UI/UX相关反馈
        category = feedback_system._auto_classify_feedback("界面设计很好看，按钮位置不太合适")
        assert category == FeedbackCategory.UI_UX

        # 测试性能相关反馈
        category = feedback_system._auto_classify_feedback("应用启动很慢，响应时间太长")
        assert category == FeedbackCategory.PERFORMANCE

        # 测试Bug相关反馈
        category = feedback_system._auto_classify_feedback("程序经常崩溃，有严重错误")
        assert category == FeedbackCategory.RELIABILITY

    def test_sentiment_analysis(self, feedback_system):
        """测试情感分析"""
        # 测试积极情感
        sentiment = feedback_system._analyze_sentiment("这个应用很好用，界面漂亮，功能强大")
        assert sentiment == Sentiment.POSITIVE

        # 测试消极情感
        sentiment = feedback_system._analyze_sentiment("应用经常崩溃，速度很慢，很难用")
        assert sentiment == Sentiment.NEGATIVE

        # 测试中性情感
        sentiment = feedback_system._analyze_sentiment("这是一个应用程序")
        assert sentiment == Sentiment.NEUTRAL

    def test_priority_determination(self, feedback_system):
        """测试优先级确定"""
        # Bug报告，低评分，消极情感 -> 高优先级
        priority = feedback_system._determine_priority(
            FeedbackType.BUG_REPORT, 1, Sentiment.NEGATIVE
        )
        assert priority == Priority.CRITICAL

        # 一般反馈，高评分，积极情感 -> 低优先级
        priority = feedback_system._determine_priority(
            FeedbackType.GENERAL_FEEDBACK, 5, Sentiment.POSITIVE
        )
        assert priority == Priority.LOW

    @pytest.mark.asyncio
    async def test_improvement_recommendations(self, feedback_system):
        """测试改进建议生成"""
        # 提交高优先级反馈
        feedback_id = await feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.BUG_REPORT,
            title="严重Bug",
            description="应用经常崩溃",
            rating=1,
            category=FeedbackCategory.RELIABILITY
        )

        # 检查是否生成了改进建议
        recommendations = feedback_system.get_recommendations()
        related_recs = [rec for rec in recommendations if feedback_id in rec.based_on_feedback]
        assert len(related_recs) > 0

    def test_feedback_summary(self, feedback_system):
        """测试反馈摘要"""
        # 添加一些测试反馈
        for i in range(10):
            asyncio.run(feedback_system.submit_feedback(
                user_id=f"user_{i}",
                feedback_type=FeedbackType.GENERAL_FEEDBACK,
                title=f"反馈 {i}",
                description=f"这是第{i}个反馈",
                rating=i % 5 + 1
            ))

        summary = feedback_system.get_feedback_summary(period_days=30)
        assert summary["total_feedback"] == 10
        assert "average_rating" in summary
        assert "feedback_by_type" in summary
        assert "sentiment_distribution" in summary

    def test_feedback_report_generation(self, feedback_system):
        """测试反馈报告生成"""
        # 添加测试数据
        asyncio.run(feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.GENERAL_FEEDBACK,
            title="测试反馈",
            description="测试描述",
            rating=4
        ))

        # 生成文本报告
        text_report = feedback_system.generate_feedback_report("text")
        assert isinstance(text_report, str)
        assert "用户反馈分析报告" in text_report

        # 生成JSON报告
        json_report = feedback_system.generate_feedback_report("json")
        assert isinstance(json_report, str)
        report_data = json.loads(json_report)
        assert "total_feedback" in report_data

    def test_update_feedback_status(self, feedback_system):
        """测试更新反馈状态"""
        # 创建反馈
        asyncio.run(feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.BUG_REPORT,
            title="状态测试",
            description="测试状态更新",
            rating=3
        ))

        feedback_id = list(feedback_system.feedback.keys())[0]

        # 更新状态
        result = feedback_system.update_feedback_status(
            feedback_id,
            FeedbackStatus.IN_PROGRESS,
            response="我们正在处理这个问题"
        )

        assert result is True
        feedback = feedback_system.feedback[feedback_id]
        assert feedback.status == FeedbackStatus.IN_PROGRESS
        assert feedback.response == "我们正在处理这个问题"


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def integrated_system(self):
        """创建集成系统"""
        with tempfile.TemporaryDirectory() as temp_dir:
            kb = EnhancedKnowledgeBase(os.path.join(temp_dir, "kb"))
            wizard = DiagnosticWizard()
            support_system = SupportContactSystem(os.path.join(temp_dir, "support"))
            feedback_system = FeedbackSystem(os.path.join(temp_dir, "feedback"))

            yield {
                "knowledge_base": kb,
                "diagnostic_wizard": wizard,
                "support_system": support_system,
                "feedback_system": feedback_system
            }

    @pytest.mark.asyncio
    async def test_complete_user_support_flow(self, integrated_system):
        """测试完整的用户支持流程"""
        kb = integrated_system["knowledge_base"]
        wizard = integrated_system["diagnostic_wizard"]
        support_system = integrated_system["support_system"]
        feedback_system = integrated_system["feedback_system"]

        # 1. 用户搜索知识库
        search_result = kb.search("端口冲突")
        assert search_result["total"] >= 0

        # 2. 启动诊断会话
        session_id = await wizard.start_diagnostic_session("port_conflict")
        assert session_id is not None

        # 3. 模拟诊断过程
        session = wizard.active_sessions[session_id]
        session.answers = {
            "port_number": "3000",
            "process_running": "yes",
            "preferred_solution": "停止占用端口的进程"
        }

        # 4. 创建支持工单
        ticket_id = await support_system.create_support_ticket(
            user_id="test_user",
            title="端口冲突问题",
            description="端口3000被占用",
            category="端口冲突",
            priority=Priority.HIGH,
            include_diagnostics=True
        )
        assert ticket_id is not None

        # 5. 提交反馈
        feedback_id = await feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.BUG_REPORT,
            title="端口冲突问题反馈",
            description="端口冲突功能很有用",
            rating=4
        )
        assert feedback_id is not None

        # 6. 验证所有系统都有数据
        assert len(kb.search_index) > 0
        assert len(wizard.active_sessions) > 0
        assert len(support_system.tickets) > 0
        assert len(feedback_system.feedback) > 0

    def test_cross_system_data_consistency(self, integrated_system):
        """测试跨系统数据一致性"""
        kb = integrated_system["knowledge_base"]
        feedback_system = integrated_system["feedback_system"]

        # 在知识库中添加内容
        guide = Guide(
            guide_id="consistency_test_guide",
            title="一致性测试指南",
            description="测试系统间数据一致性",
            category="测试",
            tags=["测试", "一致性"],
            sections=[
                GuideSection(
                    section_id="section_1",
                    title="第一节",
                    content="测试内容",
                    order=1,
                    estimated_time=5,
                    difficulty=DifficultyLevel.BEGINNER
                )
            ],
            target_audience=["开发者"],
            estimated_total_time=5,
            difficulty=DifficultyLevel.BEGINNER
        )
        kb.add_guide(guide)

        # 在反馈系统中提交相关反馈
        asyncio.run(feedback_system.submit_feedback(
            user_id="test_user",
            feedback_type=FeedbackType.DOCUMENTATION,
            title="文档反馈",
            description="一致性测试指南很有用",
            rating=5,
            category=FeedbackCategory.DOCUMENTATION
        ))

        # 验证数据独立性和一致性
        assert "consistency_test_guide" in kb.guides
        assert len(feedback_system.feedback) > 0

        # 搜索应该能找到新添加的指南
        search_result = kb.search("一致性测试")
        assert search_result["total"] > 0


# 运行测试的主函数
def run_user_support_tests():
    """运行用户支持系统测试"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])


if __name__ == "__main__":
    run_user_support_tests()