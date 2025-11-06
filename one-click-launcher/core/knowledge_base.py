"""
Enhanced Knowledge Base Module

This module extends the existing ErrorKnowledgeBase to provide comprehensive
user support functionality including guides, FAQs, and advanced search capabilities.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import difflib
import hashlib

from utils.error_knowledge_base import ErrorKnowledgeBase, ErrorSolution, ErrorCategory, Platform
from utils.logger import get_logger

logger = get_logger(__name__)


class ContentType(Enum):
    """内容类型枚举"""
    ERROR_SOLUTION = "error_solution"
    GUIDE = "guide"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICE = "best_practice"
    GLOSSARY = "glossary"


class DifficultyLevel(Enum):
    """难度级别枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class ContentTag:
    """内容标签"""
    tag_id: str
    name: str
    category: str
    description: str
    color: str = "#007acc"
    usage_count: int = 0


@dataclass
class GuideSection:
    """指南章节"""
    section_id: str
    title: str
    content: str
    order: int
    estimated_time: int = 5  # 预估阅读时间（分钟）
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    prerequisites: List[str] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)


@dataclass
class Guide:
    """操作指南"""
    guide_id: str
    title: str
    description: str
    category: str
    tags: List[str]
    sections: List[GuideSection]
    target_audience: List[str]
    estimated_total_time: int
    difficulty: DifficultyLevel
    last_updated: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    related_guides: List[str] = field(default_factory=list)
    author: str = "System"
    review_status: str = "approved"  # draft, review, approved, archived


@dataclass
class FAQ:
    """常见问题"""
    faq_id: str
    question: str
    answer: str
    category: str
    tags: List[str]
    difficulty: DifficultyLevel
    helpful_count: int = 0
    not_helpful_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    related_faqs: List[str] = field(default_factory=list)
    related_error_codes: List[str] = field(default_factory=list)


@dataclass
class SearchIndex:
    """搜索索引项"""
    term: str
    content_ids: Set[str]
    content_types: Set[ContentType]
    frequency: int = 1
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class VersionInfo:
    """版本信息"""
    version: str
    release_date: datetime
    changes: List[str]
    author: str
    content_updates: Dict[str, str] = field(default_factory=dict)  # content_id -> change_description


class EnhancedKnowledgeBase:
    """
    增强型知识库，提供综合的用户支持功能
    """

    def __init__(self, data_dir: str = "knowledge_base_data"):
        """
        初始化增强型知识库

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self.logger = get_logger(self.__class__.__name__)

        # 初始化基础错误知识库
        self.error_kb = ErrorKnowledgeBase()

        # 存储各种内容
        self.guides: Dict[str, Guide] = {}
        self.faqs: Dict[str, FAQ] = {}
        self.tags: Dict[str, ContentTag] = {}

        # 搜索索引
        self.search_index: Dict[str, SearchIndex] = {}

        # 版本管理
        self.versions: List[VersionInfo] = []
        self.current_version = "1.0.0"

        # 统计信息
        self.analytics = {
            "search_queries": {},
            "content_access": {},
            "user_feedback": {},
            "popular_tags": {}
        }

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        # 加载现有数据
        self._load_data()

        # 构建搜索索引
        self._build_search_index()

        self.logger.info(f"Enhanced Knowledge Base initialized with {len(self.guides)} guides, {len(self.faqs)} FAQs")

    def _load_data(self):
        """加载知识库数据"""
        try:
            # 加载指南
            guides_file = os.path.join(self.data_dir, "guides.json")
            if os.path.exists(guides_file):
                with open(guides_file, 'r', encoding='utf-8') as f:
                    guides_data = json.load(f)
                    for guide_data in guides_data:
                        guide = self._deserialize_guide(guide_data)
                        self.guides[guide.guide_id] = guide

            # 加载FAQ
            faqs_file = os.path.join(self.data_dir, "faqs.json")
            if os.path.exists(faqs_file):
                with open(faqs_file, 'r', encoding='utf-8') as f:
                    faqs_data = json.load(f)
                    for faq_data in faqs_data:
                        faq = self._deserialize_faq(faq_data)
                        self.faqs[faq.faq_id] = faq

            # 加载标签
            tags_file = os.path.join(self.data_dir, "tags.json")
            if os.path.exists(tags_file):
                with open(tags_file, 'r', encoding='utf-8') as f:
                    tags_data = json.load(f)
                    for tag_data in tags_data:
                        tag = ContentTag(**tag_data)
                        self.tags[tag.tag_id] = tag

            # 加载版本信息
            versions_file = os.path.join(self.data_dir, "versions.json")
            if os.path.exists(versions_file):
                with open(versions_file, 'r', encoding='utf-8') as f:
                    versions_data = json.load(f)
                    for version_data in versions_data:
                        version = VersionInfo(
                            version=version_data["version"],
                            release_date=datetime.fromisoformat(version_data["release_date"]),
                            changes=version_data["changes"],
                            author=version_data["author"],
                            content_updates=version_data.get("content_updates", {})
                        )
                        self.versions.append(version)

            # 加载分析数据
            analytics_file = os.path.join(self.data_dir, "analytics.json")
            if os.path.exists(analytics_file):
                with open(analytics_file, 'r', encoding='utf-8') as f:
                    self.analytics = json.load(f)

        except Exception as e:
            self.logger.warning(f"Error loading knowledge base data: {e}")

    def _save_data(self):
        """保存知识库数据"""
        try:
            # 保存指南
            guides_file = os.path.join(self.data_dir, "guides.json")
            guides_data = [self._serialize_guide(guide) for guide in self.guides.values()]
            with open(guides_file, 'w', encoding='utf-8') as f:
                json.dump(guides_data, f, indent=2, ensure_ascii=False, default=str)

            # 保存FAQ
            faqs_file = os.path.join(self.data_dir, "faqs.json")
            faqs_data = [self._serialize_faq(faq) for faq in self.faqs.values()]
            with open(faqs_file, 'w', encoding='utf-8') as f:
                json.dump(faqs_data, f, indent=2, ensure_ascii=False, default=str)

            # 保存标签
            tags_file = os.path.join(self.data_dir, "tags.json")
            tags_data = [asdict(tag) for tag in self.tags.values()]
            with open(tags_file, 'w', encoding='utf-8') as f:
                json.dump(tags_data, f, indent=2, ensure_ascii=False)

            # 保存版本信息
            versions_file = os.path.join(self.data_dir, "versions.json")
            versions_data = [{
                "version": v.version,
                "release_date": v.release_date.isoformat(),
                "changes": v.changes,
                "author": v.author,
                "content_updates": v.content_updates
            } for v in self.versions]
            with open(versions_file, 'w', encoding='utf-8') as f:
                json.dump(versions_data, f, indent=2, ensure_ascii=False)

            # 保存分析数据
            analytics_file = os.path.join(self.data_dir, "analytics.json")
            with open(analytics_file, 'w', encoding='utf-8') as f:
                json.dump(self.analytics, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Error saving knowledge base data: {e}")

    def _build_search_index(self):
        """构建搜索索引"""
        self.search_index.clear()

        # 索引错误解决方案
        for error_code, solution in self.error_kb.solutions.items():
            self._index_content(error_code, ContentType.ERROR_SOLUTION,
                              f"{solution.title} {solution.description}")

        # 索引指南
        for guide_id, guide in self.guides.items():
            content = f"{guide.title} {guide.description} " + " ".join(
                section.content for section in guide.sections
            )
            self._index_content(guide_id, ContentType.GUIDE, content)

        # 索引FAQ
        for faq_id, faq in self.faqs.items():
            content = f"{faq.question} {faq.answer}"
            self._index_content(faq_id, ContentType.FAQ, content)

    def _index_content(self, content_id: str, content_type: ContentType, content: str):
        """索引内容"""
        # 分词并建立索引
        words = self._tokenize(content)

        for word in words:
            if len(word) < 3:  # 跳过太短的词
                continue

            if word not in self.search_index:
                self.search_index[word] = SearchIndex(
                    term=word,
                    content_ids={content_id},
                    content_types={content_type}
                )
            else:
                self.search_index[word].content_ids.add(content_id)
                self.search_index[word].content_types.add(content_type)
                self.search_index[word].frequency += 1

    def _tokenize(self, text: str) -> List[str]:
        """分词处理"""
        text = text.lower()
        # 移除特殊字符，保留中文、英文、数字
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        words = text.split()

        # 增强的中文分词逻辑 - 生成多级粒度的词汇
        all_words = []

        for word in words:
            if not word.strip():
                continue

            # 添加原始词汇
            all_words.append(word.strip())

            # 对于中文词汇，生成多级粒度的索引词汇
            if re.search(r'[\u4e00-\u9fff]', word):  # 包含中文字符
                # 添加单字索引 - 用于精确匹配
                for char in word:
                    if char.strip():
                        all_words.append(char.strip())

                # 对于较长中文词，生成2-3字的滑动窗口词汇
                if len(word) >= 2:
                    for i in range(len(word) - 1):
                        bigram = word[i:i+2]
                        if bigram.strip():
                            all_words.append(bigram.strip())

                if len(word) >= 3:
                    for i in range(len(word) - 2):
                        trigram = word[i:i+3]
                        if trigram.strip():
                            all_words.append(trigram.strip())

            # 对于英文词汇，生成子词
            elif len(word) >= 4:
                # 添加前缀和后缀
                for i in range(3, len(word) + 1):
                    prefix = word[:i]
                    suffix = word[-i:]
                    if len(prefix) >= 3:
                        all_words.append(prefix)
                    if len(suffix) >= 3 and suffix != word:
                        all_words.append(suffix)

        # 过滤空词和过短的词，但保留单字用于中文搜索
        filtered_words = []
        for word in all_words:
            if word:
                # 中文字符可以单字索引，英文至少3个字符
                if (re.search(r'[\u4e00-\u9fff]', word) and len(word) >= 1) or \
                   (len(word) >= 3):
                    filtered_words.append(word)

        return list(set(filtered_words))  # 去重

    def search(self, query: str, content_types: List[ContentType] = None,
               limit: int = 20) -> Dict[str, Any]:
        """
        搜索知识库内容

        Args:
            query: 搜索查询
            content_types: 内容类型过滤
            limit: 结果限制

        Returns:
            搜索结果字典
        """
        # 记录搜索查询
        self._record_search_query(query)

        query_words = self._tokenize(query)
        if not query_words:
            return {"results": [], "total": 0, "query": query}

        # 计算相关性分数
        content_scores = {}

        for word in query_words:
            if word in self.search_index:
                index = self.search_index[word]
                for content_id in index.content_ids:
                    # 应用内容类型过滤
                    if content_types:
                        content_type = self._get_content_type(content_id)
                        if content_type not in content_types:
                            continue

                    if content_id not in content_scores:
                        content_scores[content_id] = 0

                    # 计算分数（词频 * 位置权重）
                    score = index.frequency * (1.0 / (len(word) + 1))
                    content_scores[content_id] += score

        # 排序结果
        sorted_results = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果详情
        results = []
        for content_id, score in sorted_results[:limit]:
            content_info = self._get_content_info(content_id)
            if content_info:
                content_info["relevance_score"] = score
                results.append(content_info)

        return {
            "results": results,
            "total": len(content_scores),
            "query": query,
            "content_types": content_types
        }

    def _get_content_type(self, content_id: str) -> Optional[ContentType]:
        """获取内容类型"""
        if content_id in self.guides:
            return ContentType.GUIDE
        elif content_id in self.faqs:
            return ContentType.FAQ
        elif content_id in self.error_kb.solutions:
            return ContentType.ERROR_SOLUTION
        return None

    def _get_content_info(self, content_id: str) -> Optional[Dict[str, Any]]:
        """获取内容信息"""
        content_type = self._get_content_type(content_id)
        if not content_type:
            return None

        if content_type == ContentType.GUIDE:
            guide = self.guides[content_id]
            return {
                "id": guide.guide_id,
                "type": "guide",
                "title": guide.title,
                "description": guide.description,
                "category": guide.category,
                "tags": guide.tags,
                "difficulty": guide.difficulty.value,
                "estimated_time": guide.estimated_total_time
            }
        elif content_type == ContentType.FAQ:
            faq = self.faqs[content_id]
            return {
                "id": faq.faq_id,
                "type": "faq",
                "title": faq.question,
                "description": faq.answer,
                "category": faq.category,
                "tags": faq.tags,
                "difficulty": faq.difficulty.value,
                "helpful_count": faq.helpful_count
            }
        elif content_type == ContentType.ERROR_SOLUTION:
            solution = self.error_kb.solutions[content_id]
            return {
                "id": solution.error_code,
                "type": "error_solution",
                "title": solution.title,
                "description": solution.description,
                "category": solution.category.value,
                "severity": solution.severity,
                "platforms": [p.value for p in solution.platforms]
            }

        return None

    def add_guide(self, guide: Guide) -> bool:
        """
        添加指南

        Args:
            guide: 指南对象

        Returns:
            是否添加成功
        """
        try:
            # 验证指南
            if not self._validate_guide(guide):
                return False

            # 添加指南
            self.guides[guide.guide_id] = guide

            # 更新标签
            for tag_id in guide.tags:
                if tag_id in self.tags:
                    self.tags[tag_id].usage_count += 1

            # 立即索引新添加的指南内容
            content = f"{guide.title} {guide.description} " + " ".join(
                section.content for section in guide.sections
            )
            self._index_content(guide.guide_id, ContentType.GUIDE, content)

            # 保存数据
            self._save_data()

            self.logger.info(f"Added guide: {guide.title}")
            return True

        except Exception as e:
            self.logger.error(f"Error adding guide: {e}")
            return False

    def add_faq(self, faq: FAQ) -> bool:
        """
        添加FAQ

        Args:
            faq: FAQ对象

        Returns:
            是否添加成功
        """
        try:
            # 验证FAQ
            if not self._validate_faq(faq):
                return False

            # 添加FAQ
            self.faqs[faq.faq_id] = faq

            # 更新标签
            for tag_id in faq.tags:
                if tag_id in self.tags:
                    self.tags[tag_id].usage_count += 1

            # 重建搜索索引
            self._build_search_index()

            # 保存数据
            self._save_data()

            self.logger.info(f"Added FAQ: {faq.question}")
            return True

        except Exception as e:
            self.logger.error(f"Error adding FAQ: {e}")
            return False

    def get_guide(self, guide_id: str) -> Optional[Guide]:
        """获取指南"""
        # 记录访问
        self._record_content_access(guide_id, "guide")
        return self.guides.get(guide_id)

    def get_faq(self, faq_id: str) -> Optional[FAQ]:
        """获取FAQ"""
        # 记录访问
        self._record_content_access(faq_id, "faq")
        return self.faqs.get(faq_id)

    def get_guides_by_category(self, category: str) -> List[Guide]:
        """按分类获取指南"""
        return [guide for guide in self.guides.values() if guide.category == category]

    def get_faqs_by_category(self, category: str) -> List[FAQ]:
        """按分类获取FAQ"""
        return [faq for faq in self.faqs.values() if faq.category == category]

    def get_popular_content(self, content_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门内容"""
        popular = []

        if content_type in [None, "guide"]:
            for guide in self.guides.values():
                access_count = self.analytics["content_access"].get(guide.guide_id, 0)
                popular.append({
                    "id": guide.guide_id,
                    "type": "guide",
                    "title": guide.title,
                    "access_count": access_count
                })

        if content_type in [None, "faq"]:
            for faq in self.faqs.values():
                access_count = self.analytics["content_access"].get(faq.faq_id, 0)
                helpful_count = faq.helpful_count
                popular.append({
                    "id": faq.faq_id,
                    "type": "faq",
                    "title": faq.question,
                    "access_count": access_count,
                    "helpful_count": helpful_count
                })

        # 按访问次数排序
        popular.sort(key=lambda x: x["access_count"], reverse=True)
        return popular[:limit]

    def rate_content_helpful(self, content_id: str, content_type: str, helpful: bool):
        """评价内容是否有帮助"""
        if content_type == "faq" and content_id in self.faqs:
            faq = self.faqs[content_id]
            if helpful:
                faq.helpful_count += 1
            else:
                faq.not_helpful_count += 1
            faq.last_updated = datetime.now()

            # 记录反馈
            self._record_user_feedback(content_id, content_type, helpful)

            # 保存数据
            self._save_data()

    def get_related_content(self, content_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取相关内容"""
        content_type = self._get_content_type(content_id)
        if not content_type:
            return []

        related = []

        if content_type == ContentType.GUIDE and content_id in self.guides:
            guide = self.guides[content_id]

            # 查找相关指南
            for related_id in guide.related_guides:
                if related_id in self.guides:
                    related_guide = self.guides[related_id]
                    related.append({
                        "id": related_guide.guide_id,
                        "type": "guide",
                        "title": related_guide.title,
                        "description": related_guide.description
                    })

            # 查找同类别的其他指南
            for other_guide in self.guides.values():
                if (other_guide.guide_id != content_id and
                    other_guide.category == guide.category and
                    other_guide.guide_id not in guide.related_guides):
                    related.append({
                        "id": other_guide.guide_id,
                        "type": "guide",
                        "title": other_guide.title,
                        "description": other_guide.description
                    })

        elif content_type == ContentType.FAQ and content_id in self.faqs:
            faq = self.faqs[content_id]

            # 查找相关FAQ
            for related_id in faq.related_faqs:
                if related_id in self.faqs:
                    related_faq = self.faqs[related_id]
                    related.append({
                        "id": related_faq.faq_id,
                        "type": "faq",
                        "title": related_faq.question,
                        "description": related_faq.answer[:100] + "..."
                    })

        return related[:limit]

    def _validate_guide(self, guide: Guide) -> bool:
        """验证指南"""
        if not guide.title or not guide.guide_id:
            return False
        if not guide.sections:
            return False
        return True

    def _validate_faq(self, faq: FAQ) -> bool:
        """验证FAQ"""
        if not faq.question or not faq.faq_id:
            return False
        if not faq.answer:
            return False
        return True

    def _serialize_guide(self, guide: Guide) -> Dict[str, Any]:
        """序列化指南"""
        return {
            "guide_id": guide.guide_id,
            "title": guide.title,
            "description": guide.description,
            "category": guide.category,
            "tags": guide.tags,
            "sections": [asdict(section) for section in guide.sections],
            "target_audience": guide.target_audience,
            "estimated_total_time": guide.estimated_total_time,
            "difficulty": guide.difficulty.value,
            "last_updated": guide.last_updated.isoformat(),
            "version": guide.version,
            "related_guides": guide.related_guides,
            "author": guide.author,
            "review_status": guide.review_status
        }

    def _deserialize_guide(self, data: Dict[str, Any]) -> Guide:
        """反序列化指南"""
        sections = [
            GuideSection(
                section_id=section["section_id"],
                title=section["title"],
                content=section["content"],
                order=section["order"],
                estimated_time=section.get("estimated_time", 5),
                difficulty=self._parse_difficulty_level(section.get("difficulty", "beginner")),
                prerequisites=section.get("prerequisites", []),
                code_examples=section.get("code_examples", []),
                tips=section.get("tips", [])
            )
            for section in data.get("sections", [])
        ]

        return Guide(
            guide_id=data["guide_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            tags=data.get("tags", []),
            sections=sections,
            target_audience=data.get("target_audience", []),
            estimated_total_time=data.get("estimated_total_time", 30),
            difficulty=self._parse_difficulty_level(data.get("difficulty", "beginner")),
            last_updated=datetime.fromisoformat(data.get("last_updated", datetime.now().isoformat())),
            version=data.get("version", "1.0"),
            related_guides=data.get("related_guides", []),
            author=data.get("author", "System"),
            review_status=data.get("review_status", "approved")
        )

    def _serialize_faq(self, faq: FAQ) -> Dict[str, Any]:
        """序列化FAQ"""
        return {
            "faq_id": faq.faq_id,
            "question": faq.question,
            "answer": faq.answer,
            "category": faq.category,
            "tags": faq.tags,
            "difficulty": faq.difficulty.value,
            "helpful_count": faq.helpful_count,
            "not_helpful_count": faq.not_helpful_count,
            "last_updated": faq.last_updated.isoformat(),
            "related_faqs": faq.related_faqs,
            "related_error_codes": faq.related_error_codes
        }

    def _deserialize_faq(self, data: Dict[str, Any]) -> FAQ:
        """反序列化FAQ"""
        return FAQ(
            faq_id=data["faq_id"],
            question=data["question"],
            answer=data["answer"],
            category=data["category"],
            tags=data.get("tags", []),
            difficulty=self._parse_difficulty_level(data.get("difficulty", "beginner")),
            helpful_count=data.get("helpful_count", 0),
            not_helpful_count=data.get("not_helpful_count", 0),
            last_updated=datetime.fromisoformat(data.get("last_updated", datetime.now().isoformat())),
            related_faqs=data.get("related_faqs", []),
            related_error_codes=data.get("related_error_codes", [])
        )

    def _parse_difficulty_level(self, difficulty_str: str) -> DifficultyLevel:
        """解析难度级别字符串"""
        try:
            # 处理可能的格式问题
            if isinstance(difficulty_str, str):
                # 如果是枚举值格式 (如 "DifficultyLevel.BEGINNER")
                if "." in difficulty_str:
                    difficulty_str = difficulty_str.split(".")[-1]
                return DifficultyLevel(difficulty_str.lower())
            else:
                return DifficultyLevel.BEGINNER
        except (ValueError, AttributeError):
            # 如果解析失败，返回默认值
            return DifficultyLevel.BEGINNER

    def _record_search_query(self, query: str):
        """记录搜索查询"""
        if query not in self.analytics["search_queries"]:
            self.analytics["search_queries"][query] = 0
        self.analytics["search_queries"][query] += 1

    def _record_content_access(self, content_id: str, content_type: str):
        """记录内容访问"""
        key = f"{content_type}:{content_id}"
        if key not in self.analytics["content_access"]:
            self.analytics["content_access"][key] = 0
        self.analytics["content_access"][key] += 1

    def _record_user_feedback(self, content_id: str, content_type: str, helpful: bool):
        """记录用户反馈"""
        key = f"{content_type}:{content_id}"
        if key not in self.analytics["user_feedback"]:
            self.analytics["user_feedback"][key] = {"helpful": 0, "not_helpful": 0}

        if helpful:
            self.analytics["user_feedback"][key]["helpful"] += 1
        else:
            self.analytics["user_feedback"][key]["not_helpful"] += 1

    def get_analytics_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "total_guides": len(self.guides),
            "total_faqs": len(self.faqs),
            "total_searches": sum(self.analytics["search_queries"].values()),
            "total_content_access": sum(self.analytics["content_access"].values()),
            "top_search_queries": sorted(
                self.analytics["search_queries"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "popular_content": self.get_popular_content(limit=5)
        }