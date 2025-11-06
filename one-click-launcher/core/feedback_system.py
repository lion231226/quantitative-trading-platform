"""
User Feedback Collection System Module

This module provides comprehensive user feedback collection, analysis,
and improvement recommendation functionality.
"""

import asyncio
import json
import os
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import statistics
from collections import defaultdict, Counter

from utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    USER_EXPERIENCE = "user_experience"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    SUPPORT_QUALITY = "support_quality"
    SUGGESTION = "suggestion"


class FeedbackCategory(Enum):
    """反馈分类"""
    UI_UX = "ui_ux"
    FUNCTIONALITY = "functionality"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    DOCUMENTATION = "documentation"
    SUPPORT = "support"
    INSTALLATION = "installation"
    CONFIGURATION = "configuration"
    OTHER = "other"


class FeedbackStatus(Enum):
    """反馈状态"""
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class Sentiment(Enum):
    """情感分析结果"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class Priority(Enum):
    """优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Feedback:
    """用户反馈"""
    feedback_id: str
    user_id: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    title: str
    description: str
    rating: int  # 1-5 星评级
    sentiment: Sentiment
    priority: Priority
    status: FeedbackStatus = FeedbackStatus.SUBMITTED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    response: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class FeedbackTrend:
    """反馈趋势"""
    period: str  # daily, weekly, monthly
    date_range: Tuple[datetime, datetime]
    total_feedback: int
    average_rating: float
    sentiment_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    top_issues: List[Dict[str, Any]]
    improvement_areas: List[str]


@dataclass
class ImprovementRecommendation:
    """改进建议"""
    recommendation_id: str
    title: str
    description: str
    category: str
    priority: Priority
    based_on_feedback: List[str]  # 反馈ID列表
    effort_estimate: str  # low, medium, high
    impact_estimate: str  # low, medium, high
    suggested_actions: List[str]
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, approved, in_progress, completed


class FeedbackSystem:
    """
    用户反馈收集和分析系统
    """

    def __init__(self, data_dir: str = "feedback_data"):
        """
        初始化反馈系统

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self.logger = get_logger(self.__class__.__name__)

        # 反馈存储
        self.feedback: Dict[str, Feedback] = {}

        # 改进建议
        self.recommendations: Dict[str, ImprovementRecommendation] = {}

        # 情感分析关键词
        self.sentiment_keywords = self._initialize_sentiment_keywords()

        # 反馈模板
        self.feedback_templates = self._initialize_feedback_templates()

        # 自动分类规则
        self.classification_rules = self._initialize_classification_rules()

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        # 加载现有数据
        self._load_data()

        self.logger.info("Feedback System initialized")

    def _initialize_sentiment_keywords(self) -> Dict[str, Dict[str, List[str]]]:
        """初始化情感分析关键词"""
        return {
            "positive": {
                "zh": ["好", "优秀", "满意", "喜欢", "推荐", "棒", "完美", "方便", "快速", "稳定"],
                "en": ["good", "excellent", "satisfied", "like", "recommend", "great", "perfect", "convenient", "fast", "stable"]
            },
            "negative": {
                "zh": ["差", "不好", "失望", "糟糕", "慢", "崩溃", "错误", "问题", "困难", "复杂"],
                "en": ["bad", "poor", "disappointed", "terrible", "slow", "crash", "error", "problem", "difficult", "complex"]
            }
        }

    def _initialize_feedback_templates(self) -> Dict[str, Dict[str, Any]]:
        """初始化反馈模板"""
        return {
            "bug_report": {
                "title": "Bug报告",
                "fields": [
                    {"name": "问题标题", "required": True, "type": "text"},
                    {"name": "问题描述", "required": True, "type": "textarea"},
                    {"name": "复现步骤", "required": True, "type": "textarea"},
                    {"name": "期望结果", "required": True, "type": "text"},
                    {"name": "实际结果", "required": True, "type": "text"},
                    {"name": "环境信息", "required": False, "type": "textarea"},
                    {"name": "附件", "required": False, "type": "file"}
                ]
            },
            "feature_request": {
                "title": "功能请求",
                "fields": [
                    {"name": "功能标题", "required": True, "type": "text"},
                    {"name": "功能描述", "required": True, "type": "textarea"},
                    {"name": "使用场景", "required": True, "type": "textarea"},
                    {"name": "预期收益", "required": True, "type": "text"},
                    {"name": "替代方案", "required": False, "type": "text"}
                ]
            },
            "user_experience": {
                "title": "用户体验反馈",
                "fields": [
                    {"name": "总体评分", "required": True, "type": "rating", "max": 5},
                    {"name": "易用性评分", "required": True, "type": "rating", "max": 5},
                    {"name": "功能完整性评分", "required": True, "type": "rating", "max": 5},
                    {"name": "性能评分", "required": True, "type": "rating", "max": 5},
                    {"name": "最喜欢的地方", "required": False, "type": "textarea"},
                    {"name": "需要改进的地方", "required": False, "type": "textarea"},
                    {"name": "建议", "required": False, "type": "textarea"}
                ]
            }
        }

    def _initialize_classification_rules(self) -> List[Dict[str, Any]]:
        """初始化自动分类规则"""
        return [
            {
                "category": FeedbackCategory.UI_UX,
                "keywords": ["界面", "UI", "用户体验", "易用性", "设计", "布局", "按钮", "菜单"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.FUNCTIONALITY,
                "keywords": ["功能", "特性", "行为", "逻辑", "算法", "计算", "处理"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.PERFORMANCE,
                "keywords": ["性能", "速度", "慢", "快", "延迟", "响应时间", "内存", "CPU"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.RELIABILITY,
                "keywords": ["稳定性", "崩溃", "错误", "异常", "可靠性", "故障", "bug"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.DOCUMENTATION,
                "keywords": ["文档", "说明", "帮助", "指南", "教程", "README"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.SUPPORT,
                "keywords": ["支持", "客服", "帮助", "响应", "服务", "技术支持"],
                "weight": 1.0
            },
            {
                "category": FeedbackCategory.INSTALLATION,
                "keywords": ["安装", "部署", "配置", "环境", "依赖", "setup"],
                "weight": 1.0
            }
        ]

    def _load_data(self):
        """加载数据"""
        try:
            # 加载反馈
            feedback_file = os.path.join(self.data_dir, "feedback.json")
            if os.path.exists(feedback_file):
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    feedback_data = json.load(f)
                    for fb_data in feedback_data:
                        feedback = self._deserialize_feedback(fb_data)
                        self.feedback[feedback.feedback_id] = feedback

            # 加载改进建议
            recommendations_file = os.path.join(self.data_dir, "recommendations.json")
            if os.path.exists(recommendations_file):
                with open(recommendations_file, 'r', encoding='utf-8') as f:
                    rec_data = json.load(f)
                    for rec_item in rec_data:
                        recommendation = self._deserialize_recommendation(rec_item)
                        self.recommendations[recommendation.recommendation_id] = recommendation

        except Exception as e:
            self.logger.warning(f"Error loading feedback data: {e}")

    def _save_data(self):
        """保存数据"""
        try:
            # 保存反馈
            feedback_file = os.path.join(self.data_dir, "feedback.json")
            feedback_data = [self._serialize_feedback(fb) for fb in self.feedback.values()]
            with open(feedback_file, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, indent=2, ensure_ascii=False, default=str)

            # 保存改进建议
            recommendations_file = os.path.join(self.data_dir, "recommendations.json")
            rec_data = [self._serialize_recommendation(rec) for rec in self.recommendations.values()]
            with open(recommendations_file, 'w', encoding='utf-8') as f:
                json.dump(rec_data, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            self.logger.error(f"Error saving feedback data: {e}")

    async def submit_feedback(self, user_id: str, feedback_type: FeedbackType,
                            title: str, description: str, rating: int = 5,
                            category: FeedbackCategory = None,
                            tags: List[str] = None,
                            metadata: Dict[str, Any] = None) -> str:
        """
        提交反馈

        Args:
            user_id: 用户ID
            feedback_type: 反馈类型
            title: 标题
            description: 描述
            rating: 评分 (1-5)
            category: 分类（可选，自动分类）
            tags: 标签
            metadata: 元数据

        Returns:
            反馈ID
        """
        # 生成反馈ID（使用毫秒时间戳+随机数确保唯一性）
        feedback_id = f"fb_{int(datetime.now().timestamp() * 1000)}_{random.randint(1000, 9999)}"

        # 自动分类
        if not category:
            category = self._auto_classify_feedback(title + " " + description)

        # 情感分析
        sentiment = self._analyze_sentiment(title + " " + description)

        # 确定优先级
        priority = self._determine_priority(feedback_type, rating, sentiment)

        # 创建反馈对象
        feedback_obj = Feedback(
            feedback_id=feedback_id,
            user_id=user_id,
            feedback_type=feedback_type,
            category=category,
            title=title,
            description=description,
            rating=rating,
            sentiment=sentiment,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {}
        )

        # 存储反馈
        self.feedback[feedback_id] = feedback_obj
        self._save_data()

        self.logger.info(f"Submitted feedback {feedback_id} from user {user_id}")

        # 自动生成改进建议
        if feedback_obj.priority in [Priority.HIGH, Priority.CRITICAL]:
            await self._generate_improvement_recommendation(feedback_obj)

        return feedback_id

    def _auto_classify_feedback(self, text: str) -> FeedbackCategory:
        """自动分类反馈"""
        text_lower = text.lower()
        category_scores = {}

        for rule in self.classification_rules:
            score = 0
            for keyword in rule["keywords"]:
                if keyword.lower() in text_lower:
                    score += rule["weight"]

            if score > 0:
                category_scores[rule["category"]] = score

        if category_scores:
            # 返回得分最高的分类
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return FeedbackCategory.OTHER

    def _analyze_sentiment(self, text: str) -> Sentiment:
        """分析情感"""
        text_lower = text.lower()

        positive_score = 0
        negative_score = 0

        # 统计积极词汇
        for lang, keywords in self.sentiment_keywords["positive"].items():
            for keyword in keywords:
                positive_score += text_lower.count(keyword.lower())

        # 统计消极词汇
        for lang, keywords in self.sentiment_keywords["negative"].items():
            for keyword in keywords:
                negative_score += text_lower.count(keyword.lower())

        # 确定情感
        if positive_score > negative_score * 1.5:
            return Sentiment.POSITIVE
        elif negative_score > positive_score * 1.5:
            return Sentiment.NEGATIVE
        elif positive_score > 0 and negative_score > 0:
            return Sentiment.MIXED
        else:
            return Sentiment.NEUTRAL

    def _determine_priority(self, feedback_type: FeedbackType, rating: int, sentiment: Sentiment) -> Priority:
        """确定优先级"""
        # Bug报告和高优先级
        if feedback_type == FeedbackType.BUG_REPORT:
            if rating <= 2 or sentiment == Sentiment.NEGATIVE:
                return Priority.CRITICAL
            elif rating <= 3:
                return Priority.HIGH
            else:
                return Priority.MEDIUM

        # 负面情感高优先级
        if sentiment == Sentiment.NEGATIVE and rating <= 2:
            return Priority.HIGH

        # 低评分高优先级
        if rating <= 2:
            return Priority.MEDIUM

        # 其他情况低优先级
        return Priority.LOW

    async def _generate_improvement_recommendation(self, feedback: Feedback):
        """生成改进建议"""
        # 检查是否已有类似建议
        similar_recommendations = self._find_similar_recommendations(feedback)
        if similar_recommendations:
            # 更新现有建议
            for rec_id in similar_recommendations:
                rec = self.recommendations[rec_id]
                if feedback.feedback_id not in rec.based_on_feedback:
                    rec.based_on_feedback.append(feedback.feedback_id)
            return

        # 生成新建议
        recommendation_id = f"rec_{int(datetime.now().timestamp())}"

        recommendation = ImprovementRecommendation(
            recommendation_id=recommendation_id,
            title=f"改进建议: {feedback.title}",
            description=f"基于用户反馈生成的改进建议",
            category=feedback.category.value,
            priority=feedback.priority,
            based_on_feedback=[feedback.feedback_id],
            effort_estimate="medium",
            impact_estimate="medium",
            suggested_actions=self._generate_suggested_actions(feedback)
        )

        self.recommendations[recommendation_id] = recommendation
        self._save_data()

        self.logger.info(f"Generated improvement recommendation {recommendation_id}")

    def _find_similar_recommendations(self, feedback: Feedback) -> List[str]:
        """查找相似的改进建议"""
        similar = []

        for rec_id, rec in self.recommendations.items():
            # 检查分类是否相同
            if rec.category == feedback.category.value:
                # 检查标题相似度
                similarity = self._calculate_text_similarity(rec.title, feedback.title)
                if similarity > 0.6:  # 相似度阈值
                    similar.append(rec_id)

        return similar

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _generate_suggested_actions(self, feedback: Feedback) -> List[str]:
        """生成建议行动"""
        actions = []

        if feedback.category == FeedbackCategory.UI_UX:
            actions.extend([
                "分析用户界面流程",
                "进行可用性测试",
                "优化用户交互设计",
                "改进视觉设计"
            ])
        elif feedback.category == FeedbackCategory.FUNCTIONALITY:
            actions.extend([
                "分析功能需求",
                "设计解决方案",
                "实现功能改进",
                "进行功能测试"
            ])
        elif feedback.category == FeedbackCategory.PERFORMANCE:
            actions.extend([
                "进行性能分析",
                "识别性能瓶颈",
                "优化算法和数据结构",
                "进行性能测试"
            ])
        elif feedback.category == FeedbackCategory.RELIABILITY:
            actions.extend([
                "分析错误原因",
                "改进错误处理",
                "增加测试覆盖",
                "提高系统稳定性"
            ])
        elif feedback.category == FeedbackCategory.DOCUMENTATION:
            actions.extend([
                "更新相关文档",
                "添加使用示例",
                "改进文档结构",
                "增加FAQ内容"
            ])
        else:
            actions.extend([
                "分析反馈内容",
                "制定改进计划",
                "实施改进措施",
                "验证改进效果"
            ])

        return actions

    def get_feedback_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """获取反馈摘要"""
        cutoff_date = datetime.now() - timedelta(days=period_days)

        recent_feedback = [
            fb for fb in self.feedback.values()
            if fb.created_at >= cutoff_date
        ]

        if not recent_feedback:
            return {
                "period": f"Last {period_days} days",
                "total_feedback": 0,
                "average_rating": 0,
                "feedback_by_type": {},
                "feedback_by_category": {},
                "sentiment_distribution": {},
                "priority_distribution": {}
            }

        # 基础统计
        total_feedback = len(recent_feedback)
        average_rating = statistics.mean([fb.rating for fb in recent_feedback])

        # 按类型统计
        feedback_by_type = Counter([fb.feedback_type.value for fb in recent_feedback])

        # 按分类统计
        feedback_by_category = Counter([fb.category.value for fb in recent_feedback])

        # 情感分布
        sentiment_distribution = Counter([fb.sentiment.value for fb in recent_feedback])

        # 优先级分布
        priority_distribution = Counter([fb.priority.value for fb in recent_feedback])

        return {
            "period": f"Last {period_days} days",
            "total_feedback": total_feedback,
            "average_rating": round(average_rating, 2),
            "feedback_by_type": dict(feedback_by_type),
            "feedback_by_category": dict(feedback_by_category),
            "sentiment_distribution": dict(sentiment_distribution),
            "priority_distribution": dict(priority_distribution),
            "top_issues": self._get_top_issues(recent_feedback),
            "improvement_areas": self._identify_improvement_areas(recent_feedback)
        }

    def _get_top_issues(self, feedback_list: List[Feedback], limit: int = 5) -> List[Dict[str, Any]]:
        """获取主要问题"""
        # 按优先级和评分排序
        sorted_feedback = sorted(
            feedback_list,
            key=lambda x: (self._priority_score(x.priority), 6 - x.rating),
            reverse=True
        )

        top_issues = []
        for fb in sorted_feedback[:limit]:
            top_issues.append({
                "feedback_id": fb.feedback_id,
                "title": fb.title,
                "category": fb.category.value,
                "priority": fb.priority.value,
                "rating": fb.rating,
                "sentiment": fb.sentiment.value,
                "created_at": fb.created_at.isoformat()
            })

        return top_issues

    def _priority_score(self, priority: Priority) -> int:
        """优先级评分"""
        scores = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        return scores.get(priority, 1)

    def _identify_improvement_areas(self, feedback_list: List[Feedback]) -> List[str]:
        """识别改进领域"""
        # 统计低评分的分类
        low_rating_feedback = [fb for fb in feedback_list if fb.rating <= 2]

        if not low_rating_feedback:
            return []

        category_counts = Counter([fb.category.value for fb in low_rating_feedback])

        # 返回需要改进最多的领域
        improvement_areas = [
            category for category, count in category_counts.most_common(3)
        ]

        return improvement_areas

    def get_recommendations(self, status: str = None, category: str = None) -> List[ImprovementRecommendation]:
        """获取改进建议"""
        recommendations = list(self.recommendations.values())

        if status:
            recommendations = [rec for rec in recommendations if rec.status == status]

        if category:
            recommendations = [rec for rec in recommendations if rec.category == category]

        # 按优先级排序
        priority_order = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1
        }

        recommendations.sort(
            key=lambda x: priority_order.get(x.priority, 1),
            reverse=True
        )

        return recommendations

    def update_feedback_status(self, feedback_id: str, status: FeedbackStatus,
                             response: str = None, assigned_to: str = None) -> bool:
        """更新反馈状态"""
        if feedback_id not in self.feedback:
            return False

        feedback = self.feedback[feedback_id]
        feedback.status = status
        feedback.updated_at = datetime.now()

        if response:
            feedback.response = response
        if assigned_to:
            feedback.assigned_to = assigned_to

        self._save_data()
        self.logger.info(f"Updated feedback {feedback_id} status to {status.value}")
        return True

    def update_recommendation_status(self, recommendation_id: str, status: str) -> bool:
        """更新改进建议状态"""
        if recommendation_id not in self.recommendations:
            return False

        recommendation = self.recommendations[recommendation_id]
        recommendation.status = status

        self._save_data()
        self.logger.info(f"Updated recommendation {recommendation_id} status to {status}")
        return True

    def generate_feedback_report(self, format_type: str = "text") -> str:
        """生成反馈报告"""
        summary = self.get_feedback_summary()

        if format_type == "text":
            return self._generate_text_report(summary)
        elif format_type == "json":
            return json.dumps(summary, indent=2, ensure_ascii=False, default=str)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def _generate_text_report(self, summary: Dict[str, Any]) -> str:
        """生成文本格式报告"""
        report_lines = [
            "=" * 80,
            "用户反馈分析报告",
            "=" * 80,
            f"报告周期: {summary['period']}",
            f"反馈总数: {summary['total_feedback']}",
            f"平均评分: {summary['average_rating']}/5.0",
            "",
            "反馈类型分布:",
        ]

        for feedback_type, count in summary["feedback_by_type"].items():
            percentage = (count / summary["total_feedback"]) * 100
            report_lines.append(f"  • {feedback_type}: {count} ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "反馈分类分布:",
        ])

        for category, count in summary["feedback_by_category"].items():
            percentage = (count / summary["total_feedback"]) * 100
            report_lines.append(f"  • {category}: {count} ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "情感分析:",
        ])

        for sentiment, count in summary["sentiment_distribution"].items():
            percentage = (count / summary["total_feedback"]) * 100
            report_lines.append(f"  • {sentiment}: {count} ({percentage:.1f}%)")

        if summary["top_issues"]:
            report_lines.extend([
                "",
                "主要问题 (Top 5):",
            ])
            for i, issue in enumerate(summary["top_issues"], 1):
                report_lines.append(f"  {i}. {issue['title']} (优先级: {issue['priority']}, 评分: {issue['rating']}/5)")

        if summary["improvement_areas"]:
            report_lines.extend([
                "",
                "需要改进的领域:",
            ])
            for area in summary["improvement_areas"]:
                report_lines.append(f"  • {area}")

        report_lines.extend([
            "",
            "=" * 80,
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80
        ])

        return "\n".join(report_lines)

    def _serialize_feedback(self, feedback: Feedback) -> Dict[str, Any]:
        """序列化反馈"""
        return {
            "feedback_id": feedback.feedback_id,
            "user_id": feedback.user_id,
            "feedback_type": feedback.feedback_type.value,
            "category": feedback.category.value,
            "title": feedback.title,
            "description": feedback.description,
            "rating": feedback.rating,
            "sentiment": feedback.sentiment.value,
            "priority": feedback.priority.value,
            "status": feedback.status.value,
            "created_at": feedback.created_at.isoformat(),
            "updated_at": feedback.updated_at.isoformat(),
            "tags": feedback.tags,
            "attachments": feedback.attachments,
            "metadata": feedback.metadata,
            "response": feedback.response,
            "assigned_to": feedback.assigned_to,
            "resolution_notes": feedback.resolution_notes
        }

    def _deserialize_feedback(self, data: Dict[str, Any]) -> Feedback:
        """反序列化反馈"""
        return Feedback(
            feedback_id=data["feedback_id"],
            user_id=data["user_id"],
            feedback_type=FeedbackType(data["feedback_type"]),
            category=FeedbackCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            rating=data["rating"],
            sentiment=Sentiment(data["sentiment"]),
            priority=Priority(data["priority"]),
            status=FeedbackStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            tags=data.get("tags", []),
            attachments=data.get("attachments", []),
            metadata=data.get("metadata", {}),
            response=data.get("response"),
            assigned_to=data.get("assigned_to"),
            resolution_notes=data.get("resolution_notes")
        )

    def _serialize_recommendation(self, recommendation: ImprovementRecommendation) -> Dict[str, Any]:
        """序列化改进建议"""
        return {
            "recommendation_id": recommendation.recommendation_id,
            "title": recommendation.title,
            "description": recommendation.description,
            "category": recommendation.category,
            "priority": recommendation.priority.value,
            "based_on_feedback": recommendation.based_on_feedback,
            "effort_estimate": recommendation.effort_estimate,
            "impact_estimate": recommendation.impact_estimate,
            "suggested_actions": recommendation.suggested_actions,
            "metrics": recommendation.metrics,
            "created_at": recommendation.created_at.isoformat(),
            "status": recommendation.status
        }

    def _deserialize_recommendation(self, data: Dict[str, Any]) -> ImprovementRecommendation:
        """反序列化改进建议"""
        return ImprovementRecommendation(
            recommendation_id=data["recommendation_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            priority=Priority(data["priority"]),
            based_on_feedback=data["based_on_feedback"],
            effort_estimate=data["effort_estimate"],
            impact_estimate=data["impact_estimate"],
            suggested_actions=data["suggested_actions"],
            metrics=data.get("metrics", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=data.get("status", "pending")
        )