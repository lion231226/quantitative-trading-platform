"""
Multi-Channel Notification System
Comprehensive alert notification via email, Slack, SMS, and other channels
"""

import asyncio
import json
import smtplib
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from pydantic import BaseModel
from logging_config import get_logger


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    name: str
    severity: str
    status: str
    message: str
    description: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    type: str
    enabled: bool
    config: Dict[str, Any]
    rate_limit: Optional[Dict[str, Any]] = None
    escalation_rules: Optional[List[Dict[str, Any]]] = None


class NotificationProvider(ABC):
    """Abstract base class for notification providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"notification.{self.__class__.__name__.lower()}")

    @abstractmethod
    async def send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send notification for an alert"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to the notification service"""
        pass


class EmailNotificationProvider(NotificationProvider):
    """Email notification provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email')
        self.use_tls = config.get('use_tls', True)

    async def send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send email notification"""
        try:
            recipients = channel.config.get('recipients', [])
            if not recipients:
                self.logger.warning("No recipients configured for email channel")
                return False

            # Create email message
            msg = MimeMultipart('alternative')
            msg['Subject'] = self.format_subject(alert)
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)

            # Add plain text and HTML versions
            text_body = self.format_text_body(alert)
            html_body = self.format_html_body(alert)

            msg.attach(MimeText(text_body, 'plain', 'utf-8'))
            msg.attach(MimeText(html_body, 'html', 'utf-8'))

            # Send email
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_email_sync,
                msg,
                recipients
            )

            self.logger.info(f"Email notification sent for alert {alert.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False

    def _send_email_sync(self, msg: MimeMultipart, recipients: List[str]):
        """Send email synchronously"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg, to_addrs=recipients)

    def format_subject(self, alert: Alert) -> str:
        """Format email subject"""
        return f"[{alert.severity.upper()}] {alert.name} - {alert.message}"

    def format_text_body(self, alert: Alert) -> str:
        """Format plain text email body"""
        return f"""
Alert: {alert.name}
Severity: {alert.severity}
Status: {alert.status}
Timestamp: {alert.timestamp}

Description:
{alert.description}

Labels:
{chr(10).join([f'  {k}: {v}' for k, v in alert.labels.items()])}

Annotations:
{chr(10).join([f'  {k}: {v}' for k, v in alert.annotations.items()])}

--
Quantitative Trading Platform Monitoring
"""

    def format_html_body(self, alert: Alert) -> str:
        """Format HTML email body"""
        severity_color = {
            'critical': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        }.get(alert.severity, '#6c757d')

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert-header {{ background-color: {severity_color}; color: white; padding: 20px; }}
        .alert-body {{ padding: 20px; }}
        .label {{ background-color: #f8f9fa; padding: 5px; margin: 2px; border-radius: 3px; }}
        .runbook {{ background-color: #e9ecef; padding: 10px; border-radius: 5px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="alert-header">
        <h2>{alert.name}</h2>
        <p><strong>Severity:</strong> {alert.severity.upper()}</p>
        <p><strong>Status:</strong> {alert.status}</p>
        <p><strong>Timestamp:</strong> {alert.timestamp}</p>
    </div>
    <div class="alert-body">
        <h3>Description</h3>
        <p>{alert.description}</p>

        <h3>Labels</h3>
        {chr(10).join([f'<span class="label">{k}: {v}</span>' for k, v in alert.labels.items()])}

        <h3>Annotations</h3>
        <ul>
        {chr(10).join([f'<li><strong>{k}:</strong> {v}</li>' for k, v in alert.annotations.items()])}
        </ul>

        <div class="runbook">
            <strong>Runbook:</strong>
            <a href="{alert.annotations.get('runbook_url', '#')}">View Runbook</a>
        </div>
    </div>
</body>
</html>
"""

    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._test_connection_sync
            )
            return True
        except Exception as e:
            self.logger.error(f"Email connection test failed: {e}")
            return False

    def _test_connection_sync(self):
        """Test SMTP connection synchronously"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)


class SlackNotificationProvider(NotificationProvider):
    """Slack notification provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.bot_token = config.get('bot_token')
        self.channel = config.get('channel')

    async def send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send Slack notification"""
        try:
            webhook_url = channel.config.get('webhook_url') or self.webhook_url
            if not webhook_url:
                self.logger.warning("No webhook URL configured for Slack channel")
                return False

            payload = self.format_slack_payload(alert, channel)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack notification sent for alert {alert.id}")
                        return True
                    else:
                        self.logger.error(f"Slack API returned status {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return False

    def format_slack_payload(self, alert: Alert, channel: NotificationChannel) -> Dict[str, Any]:
        """Format Slack message payload"""
        severity_color = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }.get(alert.severity, 'good')

        payload = {
            "attachments": [
                {
                    "color": severity_color,
                    "title": f"{alert.severity.upper()}: {alert.name}",
                    "text": alert.description,
                    "fields": [
                        {"title": "Service", "value": alert.labels.get('service', 'unknown'), "short": True},
                        {"title": "Team", "value": alert.labels.get('team', 'unknown'), "short": True},
                        {"title": "Severity", "value": alert.severity.upper(), "short": True},
                        {"title": "Status", "value": alert.status, "short": True},
                    ],
                    "footer": "Quantitative Trading Platform",
                    "ts": int(alert.timestamp.timestamp()),
                }
            ]
        }

        # Add action buttons if available
        runbook_url = alert.annotations.get('runbook_url')
        dashboard_url = alert.annotations.get('dashboard_url')

        if runbook_url or dashboard_url:
            actions = []

            if dashboard_url:
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard"},
                    "url": dashboard_url
                })

            if runbook_url:
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Runbook"},
                    "url": runbook_url
                })

            if actions:
                payload["attachments"][0]["actions"] = actions

        return payload

    async def test_connection(self) -> bool:
        """Test Slack webhook connection"""
        try:
            test_payload = {
                "text": "Test message from Quantitative Trading Platform monitoring",
                "attachments": [
                    {
                        "color": "good",
                        "title": "Connection Test",
                        "text": "This is a test message to verify Slack integration",
                    }
                ]
            }

            if not self.webhook_url:
                return False

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=test_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Slack connection test failed: {e}")
            return False


class SMSNotificationProvider(NotificationProvider):
    """SMS notification provider (placeholder implementation)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.provider = config.get('provider', 'twilio')  # or other SMS providers

    async def send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send SMS notification"""
        try:
            recipients = channel.config.get('phone_numbers', [])
            if not recipients:
                self.logger.warning("No phone numbers configured for SMS channel")
                return False

            message = self.format_sms_message(alert)

            # This would integrate with actual SMS provider API
            # For now, just log the message
            self.logger.info(f"SMS would be sent to {recipients}: {message}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to send SMS notification: {e}")
            return False

    def format_sms_message(self, alert: Alert) -> str:
        """Format SMS message"""
        return f"[{alert.severity.upper()}] {alert.name}: {alert.message}. Service: {alert.labels.get('service', 'unknown')}"

    async def test_connection(self) -> bool:
        """Test SMS provider connection"""
        # This would test actual SMS provider connectivity
        return True


class NotificationManager:
    """Central notification management system"""

    def __init__(self):
        self.logger = get_logger("notification.manager")
        self.providers: Dict[str, NotificationProvider] = {}
        self.channels: Dict[str, NotificationChannel] = {}
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.alert_history: Dict[str, List[datetime]] = {}

        # Initialize providers
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize notification providers"""
        self.providers = {
            'email': EmailNotificationProvider({}),
            'slack': SlackNotificationProvider({}),
            'sms': SMSNotificationProvider({}),
        }

    def add_channel(self, channel: NotificationChannel):
        """Add notification channel"""
        self.channels[channel.name] = channel
        self.logger.info(f"Added notification channel: {channel.name}")

    def remove_channel(self, channel_name: str):
        """Remove notification channel"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            self.logger.info(f"Removed notification channel: {channel_name}")

    async def send_alert(self, alert: Alert) -> Dict[str, bool]:
        """Send alert notification through configured channels"""
        results = {}

        # Determine which channels to use based on alert severity
        target_channels = self._get_target_channels(alert)

        for channel_name in target_channels:
            channel = self.channels.get(channel_name)
            if not channel or not channel.enabled:
                continue

            # Check rate limiting
            if not self._check_rate_limit(channel, alert):
                self.logger.warning(f"Rate limited for channel {channel_name}, alert {alert.id}")
                results[channel_name] = False
                continue

            # Get provider
            provider = self.providers.get(channel.type)
            if not provider:
                self.logger.error(f"No provider found for channel type {channel.type}")
                results[channel_name] = False
                continue

            # Send notification
            success = await provider.send_notification(alert, channel)
            results[channel_name] = success

            if success:
                self._update_rate_limit(channel, alert)

        return results

    def _get_target_channels(self, alert: Alert) -> List[str]:
        """Determine target channels based on alert severity"""
        severity_channels = {
            'critical': ['email', 'slack', 'sms'],
            'warning': ['email', 'slack'],
            'info': ['slack'],
        }

        return severity_channels.get(alert.severity, ['email'])

    def _check_rate_limit(self, channel: NotificationChannel, alert: Alert) -> bool:
        """Check if notification is rate limited"""
        if not channel.rate_limit:
            return True

        limit_key = f"{channel.name}_{alert.id}"
        now = datetime.utcnow()

        if limit_key not in self.rate_limits:
            self.rate_limits[limit_key] = []

        # Clean old entries
        self.rate_limits[limit_key] = [
            timestamp for timestamp in self.rate_limits[limit_key]
            if now - timestamp < timedelta(minutes=channel.rate_limit.get('window_minutes', 60))
        ]

        # Check limit
        max_notifications = channel.rate_limit.get('max_notifications', 5)
        return len(self.rate_limits[limit_key]) < max_notifications

    def _update_rate_limit(self, channel: NotificationChannel, alert: Alert):
        """Update rate limit tracking"""
        if not channel.rate_limit:
            return

        limit_key = f"{channel.name}_{alert.id}"
        if limit_key not in self.rate_limits:
            self.rate_limits[limit_key] = []

        self.rate_limits[limit_key].append(datetime.utcnow())

    async def test_all_channels(self) -> Dict[str, bool]:
        """Test all configured channels"""
        results = {}

        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue

            provider = self.providers.get(channel.type)
            if not provider:
                results[channel_name] = False
                continue

            results[channel_name] = await provider.test_connection()

        return results

    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all channels"""
        status = {}

        for channel_name, channel in self.channels.items():
            status[channel_name] = {
                'type': channel.type,
                'enabled': channel.enabled,
                'rate_limit': channel.rate_limit,
                'escalation_rules': channel.escalation_rules,
            }

        return status


# Global notification manager instance
notification_manager = NotificationManager()