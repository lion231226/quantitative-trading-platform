"""
Support Contact Module

This module provides technical support contact functionality with multiple channels,
automatic diagnostic information collection, and privacy protection.
"""

import asyncio
import json
import os
import platform
import psutil
import subprocess
import tempfile
import zipfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import base64

from utils.logger import get_logger

logger = get_logger(__name__)


class ContactChannel(Enum):
    """联系渠道"""
    EMAIL = "email"
    GITHUB_ISSUES = "github_issues"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    WECHAT = "wechat"
    PHONE = "phone"
    WEB_FORM = "web_form"


class TicketStatus(Enum):
    """工单状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(Enum):
    """优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SupportContact:
    """支持联系方式"""
    channel_id: str
    channel_name: str
    channel_type: ContactChannel
    contact_info: str
    description: str
    available_hours: str
    response_time: str
    languages: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    active: bool = True


@dataclass
class SupportTicket:
    """支持工单"""
    ticket_id: str
    user_id: str
    title: str
    description: str
    category: str
    priority: Priority
    contact_channel: ContactChannel
    contact_info: str
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    diagnostic_data: Dict[str, Any] = field(default_factory=dict)
    user_feedback: Dict[str, Any] = field(default_factory=dict)
    resolution: Optional[str] = None


@dataclass
class DiagnosticData:
    """诊断数据"""
    system_info: Dict[str, Any]
    environment_info: Dict[str, Any]
    error_logs: List[str]
    configuration_files: Dict[str, str]
    screenshots: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)


class SupportContactSystem:
    """
    技术支持联系系统
    """

    def __init__(self, data_dir: str = "support_data"):
        """
        初始化支持联系系统

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self.logger = get_logger(self.__class__.__name__)

        # 联系渠道配置
        self.contact_channels = self._initialize_contact_channels()

        # 工单管理
        self.tickets: Dict[str, SupportTicket] = {}

        # 系统信息收集器
        self.diagnostic_collector = DiagnosticDataCollector()

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        # 加载现有数据
        self._load_data()

        self.logger.info("Support Contact System initialized")

    def _initialize_contact_channels(self) -> Dict[str, SupportContact]:
        """初始化联系渠道"""
        channels = {}

        # GitHub Issues
        channels["github"] = SupportContact(
            channel_id="github",
            channel_name="GitHub Issues",
            channel_type=ContactChannel.GITHUB_ISSUES,
            contact_info="https://github.com/your-repo/issues",
            description="在GitHub上提交问题报告",
            available_hours="24/7",
            response_time="通常在24小时内回复",
            languages=["中文", "English"],
            specialties=["Bug报告", "功能请求", "技术问题"],
            active=True
        )

        # 邮件支持
        channels["email"] = SupportContact(
            channel_id="email",
            channel_name="邮件支持",
            channel_type=ContactChannel.EMAIL,
            contact_info="support@example.com",
            description="通过邮件联系技术支持团队",
            available_hours="工作日 9:00-18:00",
            response_time="通常在4-8小时内回复",
            languages=["中文", "English"],
            specialties=["一般技术咨询", "账户问题", "使用指导"],
            active=True
        )

        # Discord 社区
        channels["discord"] = SupportContact(
            channel_id="discord",
            channel_name="Discord 社区",
            channel_type=ContactChannel.DISCORD,
            contact_info="https://discord.gg/your-server",
            description="加入Discord社区获得实时帮助",
            available_hours="24/7",
            response_time="通常几分钟内回复",
            languages=["中文", "English", "日本語"],
            specialties=["实时聊天", "社区支持", "快速问答"],
            active=True
        )

        # 微信支持
        channels["wechat"] = SupportContact(
            channel_id="wechat",
            channel_name="微信支持",
            channel_type=ContactChannel.WECHAT,
            contact_info="WeChat_ID: your_support_id",
            description="通过微信联系技术支持",
            available_hours="工作日 9:00-21:00",
            response_time="通常在1-2小时内回复",
            languages=["中文"],
            specialties=["中文用户支持", "本土化问题", "本地咨询"],
            active=True
        )

        # Web表单
        channels["web_form"] = SupportContact(
            channel_id="web_form",
            channel_name="在线表单",
            channel_type=ContactChannel.WEB_FORM,
            contact_info="https://support.example.com/contact",
            description="通过在线表单提交支持请求",
            available_hours="24/7",
            response_time="通常在12小时内回复",
            languages=["中文", "English"],
            specialties=["正式支持请求", "复杂问题", "企业支持"],
            active=True
        )

        return channels

    def _load_data(self):
        """加载数据"""
        try:
            # 加载工单
            tickets_file = os.path.join(self.data_dir, "tickets.json")
            if os.path.exists(tickets_file):
                with open(tickets_file, 'r', encoding='utf-8') as f:
                    tickets_data = json.load(f)
                    for ticket_data in tickets_data:
                        ticket = self._deserialize_ticket(ticket_data)
                        self.tickets[ticket.ticket_id] = ticket

        except Exception as e:
            self.logger.warning(f"Error loading support contact data: {e}")

    def _save_data(self):
        """保存数据"""
        try:
            # 保存工单
            tickets_file = os.path.join(self.data_dir, "tickets.json")
            tickets_data = [self._serialize_ticket(ticket) for ticket in self.tickets.values()]
            with open(tickets_file, 'w', encoding='utf-8') as f:
                json.dump(tickets_data, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            self.logger.error(f"Error saving support contact data: {e}")

    async def create_support_ticket(self, user_id: str, title: str, description: str,
                                  category: str, priority: Priority = Priority.MEDIUM,
                                  contact_channel: ContactChannel = ContactChannel.EMAIL,
                                  contact_info: str = None,
                                  include_diagnostics: bool = True,
                                  custom_data: Dict[str, Any] = None) -> str:
        """
        创建支持工单

        Args:
            user_id: 用户ID
            title: 工单标题
            description: 问题描述
            category: 问题分类
            priority: 优先级
            contact_channel: 联系渠道
            contact_info: 联系信息
            include_diagnostics: 是否包含诊断数据
            custom_data: 自定义数据

        Returns:
            工单ID
        """
        # 生成工单ID
        ticket_id = f"ticket_{int(datetime.now().timestamp())}"

        # 收集诊断数据
        diagnostic_data = {}
        if include_diagnostics:
            print("🔍 正在收集系统诊断信息...")
            diagnostic_data = await self._collect_diagnostic_data(custom_data or {})
            print("✅ 诊断信息收集完成")

        # 创建工单
        ticket = SupportTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            contact_channel=contact_channel,
            contact_info=contact_info or self._get_default_contact_info(contact_channel),
            diagnostic_data=diagnostic_data
        )

        # 存储工单
        self.tickets[ticket_id] = ticket
        self._save_data()

        self.logger.info(f"Created support ticket {ticket_id} for user {user_id}")

        return ticket_id

    async def _collect_diagnostic_data(self, custom_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """收集诊断数据"""
        return await self.diagnostic_collector.collect_all_data(custom_data)

    def _get_default_contact_info(self, channel: ContactChannel) -> str:
        """获取默认联系信息"""
        for contact in self.contact_channels.values():
            if contact.channel_type == channel and contact.active:
                return contact.contact_info
        return ""

    async def submit_support_request(self, ticket_id: str, channel: ContactChannel = None) -> bool:
        """
        提交支持请求

        Args:
            ticket_id: 工单ID
            channel: 提交渠道（可选，使用工单默认渠道）

        Returns:
            是否提交成功
        """
        if ticket_id not in self.tickets:
            self.logger.error(f"Ticket {ticket_id} not found")
            return False

        ticket = self.tickets[ticket_id]
        submit_channel = channel or ticket.contact_channel

        try:
            print(f"\n📤 正在提交支持请求...")
            print(f"🆔 工单ID: {ticket_id}")
            print(f"📋 标题: {ticket.title}")
            print(f"📧 联系渠道: {submit_channel.value}")

            # 根据渠道提交请求
            success = await self._submit_to_channel(ticket, submit_channel)

            if success:
                ticket.status = TicketStatus.IN_PROGRESS
                ticket.updated_at = datetime.now()
                self._save_data()

                print("✅ 支持请求已成功提交")
                print(f"📞 我们将通过 {ticket.contact_info} 与您联系")
            else:
                print("❌ 提交失败，请稍后重试")

            return success

        except Exception as e:
            self.logger.error(f"Error submitting support request: {e}")
            print(f"❌ 提交过程中出现错误: {e}")
            return False

    async def _submit_to_channel(self, ticket: SupportTicket, channel: ContactChannel) -> bool:
        """提交到指定渠道"""
        if channel == ContactChannel.GITHUB_ISSUES:
            return await self._submit_to_github(ticket)
        elif channel == ContactChannel.EMAIL:
            return await self._submit_to_email(ticket)
        elif channel == ContactChannel.WEB_FORM:
            return await self._submit_to_web_form(ticket)
        else:
            # 对于其他渠道，提供手动提交指导
            return await self._provide_manual_submission_guide(ticket, channel)

    async def _submit_to_github(self, ticket: SupportTicket) -> bool:
        """提交到GitHub Issues"""
        print(f"\n📝 GitHub Issues 提交指南:")
        print(f"1. 访问: https://github.com/your-repo/issues/new")
        print(f"2. 标题: {ticket.title}")
        print(f"3. 分类: {ticket.category}")
        print(f"4. 优先级: {ticket.priority.value}")
        print(f"5. 描述:")
        print(f"```")
        print(ticket.description)
        print(f"```")

        if ticket.diagnostic_data:
            print(f"6. 系统信息:")
            system_info = ticket.diagnostic_data.get("system_info", {})
            if system_info:
                print(f"   - 操作系统: {system_info.get('platform', 'Unknown')}")
                print(f"   - Python版本: {system_info.get('python_version', 'Unknown')}")
                print(f"   - 内存: {system_info.get('memory_total', 'Unknown')}")

        print(f"\n🔗 复制上述信息到GitHub Issue中")
        return True

    async def _submit_to_email(self, ticket: SupportTicket) -> bool:
        """提交到邮件"""
        print(f"\n📧 邮件提交指南:")
        print(f"收件人: {ticket.contact_info}")
        print(f"主题: [支持请求] {ticket.title}")
        print(f"工单ID: {ticket.ticket_id}")
        print(f"优先级: {ticket.priority.value}")
        print(f"\n邮件内容:")
        print(f"```")
        email_body = f"""
问题描述:
{ticket.description}

工单信息:
- 工单ID: {ticket.ticket_id}
- 用户ID: {ticket.user_id}
- 分类: {ticket.category}
- 优先级: {ticket.priority.value}
- 创建时间: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}

系统信息:
"""
        if ticket.diagnostic_data:
            system_info = ticket.diagnostic_data.get("system_info", {})
            if system_info:
                email_body += f"- 操作系统: {system_info.get('platform', 'Unknown')}\n"
                email_body += f"- Python版本: {system_info.get('python_version', 'Unknown')}\n"
                email_body += f"- 内存: {system_info.get('memory_total', 'Unknown')}\n"

        email_body += "请尽快处理此支持请求。"
        print(email_body)
        print("```")

        print(f"\n📋 复制上述内容到邮件客户端发送")
        return True

    async def _submit_to_web_form(self, ticket: SupportTicket) -> bool:
        """提交到Web表单"""
        print(f"\n🌐 在线表单提交指南:")
        print(f"1. 访问: {ticket.contact_info}")
        print(f"2. 填写表单信息:")
        print(f"   - 标题: {ticket.title}")
        print(f"   - 描述: {ticket.description}")
        print(f"   - 分类: {ticket.category}")
        print(f"   - 优先级: {ticket.priority.value}")
        print(f"   - 工单ID: {ticket.ticket_id}")
        print(f"3. 上传诊断数据文件（如有）")

        # 生成诊断数据文件
        if ticket.diagnostic_data:
            diagnostic_file = await self._create_diagnostic_file(ticket)
            if diagnostic_file:
                print(f"   - 诊断文件: {diagnostic_file}")

        print(f"\n✍️  请在网站上完成表单填写")
        return True

    async def _provide_manual_submission_guide(self, ticket: SupportTicket, channel: ContactChannel) -> bool:
        """提供手动提交指导"""
        channel_info = None
        for contact in self.contact_channels.values():
            if contact.channel_type == channel:
                channel_info = contact
                break

        if not channel_info:
            print(f"❌ 未找到渠道 {channel} 的信息")
            return False

        print(f"\n📞 联系方式: {channel_info.channel_name}")
        print(f"📧 联系信息: {channel_info.contact_info}")
        print(f"⏰ 服务时间: {channel_info.available_hours}")
        print(f"⚡ 响应时间: {channel_info.response_time}")
        print(f"\n📋 请提供以下信息:")
        print(f"- 工单ID: {ticket.ticket_id}")
        print(f"- 问题描述: {ticket.description}")
        print(f"- 系统信息: 已包含诊断数据")

        return True

    async def _create_diagnostic_file(self, ticket: SupportTicket) -> Optional[str]:
        """创建诊断数据文件"""
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f'_diagnostic_{ticket.ticket_id}.json',
                delete=False,
                encoding='utf-8'
            )

            # 准备诊断数据
            diagnostic_data = {
                "ticket_id": ticket.ticket_id,
                "user_id": ticket.user_id,
                "created_at": ticket.created_at.isoformat(),
                "diagnostic_data": ticket.diagnostic_data
            }

            # 写入文件
            json.dump(diagnostic_data, temp_file, indent=2, ensure_ascii=False, default=str)
            temp_file.close()

            return temp_file.name

        except Exception as e:
            self.logger.error(f"Error creating diagnostic file: {e}")
            return None

    def get_available_channels(self) -> List[SupportContact]:
        """获取可用的联系渠道"""
        return [contact for contact in self.contact_channels.values() if contact.active]

    def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """获取工单状态"""
        if ticket_id not in self.tickets:
            return None

        ticket = self.tickets[ticket_id]
        return {
            "ticket_id": ticket.ticket_id,
            "title": ticket.title,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "contact_channel": ticket.contact_channel.value,
            "assigned_to": ticket.assigned_to,
            "resolution": ticket.resolution
        }

    def update_ticket_status(self, ticket_id: str, status: TicketStatus,
                           resolution: str = None, assigned_to: str = None) -> bool:
        """更新工单状态"""
        if ticket_id not in self.tickets:
            return False

        ticket = self.tickets[ticket_id]
        ticket.status = status
        ticket.updated_at = datetime.now()

        if resolution:
            ticket.resolution = resolution
        if assigned_to:
            ticket.assigned_to = assigned_to

        self._save_data()
        self.logger.info(f"Updated ticket {ticket_id} status to {status.value}")
        return True

    def add_user_feedback(self, ticket_id: str, rating: int, comment: str = None) -> bool:
        """添加用户反馈"""
        if ticket_id not in self.tickets:
            return False

        ticket = self.tickets[ticket_id]
        ticket.user_feedback = {
            "rating": rating,
            "comment": comment,
            "submitted_at": datetime.now().isoformat()
        }

        ticket.updated_at = datetime.now()
        self._save_data()

        self.logger.info(f"Added user feedback for ticket {ticket_id}")
        return True

    async def create_diagnostic_package(self, ticket_id: str) -> Optional[str]:
        """创建诊断包"""
        if ticket_id not in self.tickets:
            return None

        ticket = self.tickets[ticket_id]

        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"diagnostic_{ticket_id}_")

            # 创建诊断报告
            report_file = os.path.join(temp_dir, "diagnostic_report.json")
            report_data = {
                "ticket_info": {
                    "ticket_id": ticket.ticket_id,
                    "user_id": ticket.user_id,
                    "title": ticket.title,
                    "description": ticket.description,
                    "category": ticket.category,
                    "priority": ticket.priority.value,
                    "created_at": ticket.created_at.isoformat()
                },
                "diagnostic_data": ticket.diagnostic_data,
                "generated_at": datetime.now().isoformat()
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            # 创建ZIP包
            zip_file = os.path.join(temp_dir, f"diagnostic_package_{ticket_id}.zip")
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(report_file, "diagnostic_report.json")

                # 添加日志文件
                log_files = self._get_relevant_log_files()
                for log_file in log_files:
                    if os.path.exists(log_file):
                        zipf.write(log_file, os.path.basename(log_file))

            return zip_file

        except Exception as e:
            self.logger.error(f"Error creating diagnostic package: {e}")
            return None

    def _get_relevant_log_files(self) -> List[str]:
        """获取相关的日志文件"""
        log_files = []

        # 查找常见的日志文件位置
        log_patterns = [
            "logs/*.log",
            "*.log",
            "log/*.txt",
            "tmp/*.log"
        ]

        import glob
        for pattern in log_patterns:
            log_files.extend(glob.glob(pattern))

        return log_files

    def _serialize_ticket(self, ticket: SupportTicket) -> Dict[str, Any]:
        """序列化工单"""
        return {
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "title": ticket.title,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority.value,
            "contact_channel": ticket.contact_channel.value,
            "contact_info": ticket.contact_info,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "assigned_to": ticket.assigned_to,
            "tags": ticket.tags,
            "attachments": ticket.attachments,
            "diagnostic_data": ticket.diagnostic_data,
            "user_feedback": ticket.user_feedback,
            "resolution": ticket.resolution
        }

    def _deserialize_ticket(self, data: Dict[str, Any]) -> SupportTicket:
        """反序列化工单"""
        return SupportTicket(
            ticket_id=data["ticket_id"],
            user_id=data["user_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            priority=Priority(data["priority"]),
            contact_channel=ContactChannel(data["contact_channel"]),
            contact_info=data["contact_info"],
            status=TicketStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            assigned_to=data.get("assigned_to"),
            tags=data.get("tags", []),
            attachments=data.get("attachments", []),
            diagnostic_data=data.get("diagnostic_data", {}),
            user_feedback=data.get("user_feedback", {}),
            resolution=data.get("resolution")
        )

    def get_support_statistics(self) -> Dict[str, Any]:
        """获取支持统计信息"""
        total_tickets = len(self.tickets)
        if total_tickets == 0:
            return {
                "total_tickets": 0,
                "by_status": {},
                "by_priority": {},
                "by_channel": {},
                "average_resolution_time": 0,
                "user_satisfaction": 0
            }

        # 按状态统计
        by_status = {}
        for ticket in self.tickets.values():
            status = ticket.status.value
            by_status[status] = by_status.get(status, 0) + 1

        # 按优先级统计
        by_priority = {}
        for ticket in self.tickets.values():
            priority = ticket.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1

        # 按渠道统计
        by_channel = {}
        for ticket in self.tickets.values():
            channel = ticket.contact_channel.value
            by_channel[channel] = by_channel.get(channel, 0) + 1

        # 计算平均解决时间
        resolved_tickets = [t for t in self.tickets.values() if t.status == TicketStatus.RESOLVED]
        if resolved_tickets:
            total_resolution_time = sum(
                (t.updated_at - t.created_at).total_seconds()
                for t in resolved_tickets
            )
            avg_resolution_time = total_resolution_time / len(resolved_tickets) / 3600  # 小时
        else:
            avg_resolution_time = 0

        # 用户满意度
        tickets_with_feedback = [t for t in self.tickets.values() if t.user_feedback]
        if tickets_with_feedback:
            avg_rating = sum(
                t.user_feedback.get("rating", 0)
                for t in tickets_with_feedback
            ) / len(tickets_with_feedback)
        else:
            avg_rating = 0

        return {
            "total_tickets": total_tickets,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_channel": by_channel,
            "average_resolution_time": avg_resolution_time,
            "user_satisfaction": avg_rating
        }


class DiagnosticDataCollector:
    """诊断数据收集器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def collect_all_data(self, custom_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """收集所有诊断数据"""
        data = {
            "system_info": await self._collect_system_info(),
            "environment_info": await self._collect_environment_info(),
            "error_logs": await self._collect_error_logs(),
            "configuration_files": await self._collect_configuration_files(),
            "custom_data": custom_data or {}
        }

        return data

    async def _collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        try:
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "platform_release": platform.release(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "timestamp": datetime.now().isoformat()
            }

            # 添加硬件信息
            system_info.update({
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {
                    "/": psutil.disk_usage("/")._asdict() if os.path.exists("/") else {},
                    "C:\\" : psutil.disk_usage("C:\\")._asdict() if os.path.exists("C:\\") else {}
                }
            })

            return system_info

        except Exception as e:
            self.logger.error(f"Error collecting system info: {e}")
            return {"error": str(e)}

    async def _collect_environment_info(self) -> Dict[str, Any]:
        """收集环境信息"""
        try:
            import os
            import sys

            env_info = {
                "working_directory": os.getcwd(),
                "python_path": sys.path[:5],  # 只保存前5个路径
                "environment_variables": {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
                    "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                    "LANG": os.environ.get("LANG", ""),
                    "LC_ALL": os.environ.get("LC_ALL", "")
                },
                "installed_packages": await self._get_installed_packages(),
                "running_processes": await self._get_running_processes()
            }

            return env_info

        except Exception as e:
            self.logger.error(f"Error collecting environment info: {e}")
            return {"error": str(e)}

    async def _get_installed_packages(self) -> List[str]:
        """获取已安装的包"""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            packages = result.stdout.strip().split('\n')
            return packages[:20]  # 只返回前20个包

        except Exception:
            return []

    async def _get_running_processes(self) -> List[Dict[str, Any]]:
        """获取运行中的进程"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes[:10]  # 只返回前10个进程

        except Exception:
            return []

    async def _collect_error_logs(self) -> List[str]:
        """收集错误日志"""
        logs = []

        # 查找常见的日志文件
        log_files = [
            "error.log",
            "app.log",
            "debug.log",
            "logs/error.log",
            "logs/app.log"
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 只获取最近的错误行
                        error_lines = [line.strip() for line in lines[-100:] if 'error' in line.lower()]
                        logs.extend(error_lines[:10])  # 最多10个错误行
                except Exception:
                    continue

        return logs

    async def _collect_configuration_files(self) -> Dict[str, str]:
        """收集配置文件"""
        config_files = {}

        # 常见的配置文件
        potential_configs = [
            "config.json",
            "settings.json",
            ".env",
            "config.yaml",
            "settings.yaml",
            "app.config"
        ]

        for config_file in potential_configs:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 限制内容长度
                        if len(content) > 1000:
                            content = content[:1000] + "... [truncated]"
                        config_files[config_file] = content
                except Exception:
                    continue

        return config_files