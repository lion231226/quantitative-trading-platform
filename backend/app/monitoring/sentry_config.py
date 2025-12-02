"""
Sentry Configuration for Backend Monitoring

Production-ready Sentry integration for FastAPI application
with comprehensive error tracking and performance monitoring.
"""

import os
import logging
from typing import Dict, Any, Optional
from sentry_sdk import configure_scope, capture_exception, capture_message
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration


class SentryConfig:
    """Sentry configuration management for the application"""

    def __init__(self):
        self.dsn = os.getenv('SENTRY_DSN')
        self.environment = os.getenv('NODE_ENV', 'development')
        self.release = os.getenv('RELEASE_VERSION', 'latest')
        self.traces_sample_rate = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
        self.profiles_sample_rate = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1'))
        self.debug = os.getenv('SENTRY_DEBUG', 'false').lower() == 'true'

    @property
    def is_enabled(self) -> bool:
        """Check if Sentry monitoring is enabled"""
        return bool(self.dsn and self.dsn.strip())

    def get_sentry_config(self) -> Dict[str, Any]:
        """Get complete Sentry configuration"""
        if not self.is_enabled:
            return {}

        config = {
            'dsn': self.dsn,
            'environment': self.environment,
            'release': self.release,
            'traces_sample_rate': self.traces_sample_rate,
            'profiles_sample_rate': self.profiles_sample_rate,
            'debug': self.debug,

            # Integrations for comprehensive monitoring
            'integrations': [
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.WARNING
                ),
                ThreadingIntegration(propagate_hub=True),
            ],

            # Error filtering
            'ignore_errors': [
                # Network related errors that might be expected
                'ConnectionError',
                'TimeoutError',
                'HTTPError',
                # Authentication errors that might be normal
                'AuthenticationError',
                'AuthorizationError',
            ],

            # Before send callback for custom error processing
            'before_send': self._before_send,
            'before_breadcrumb': self._before_breadcrumb,

            # Performance settings
            'max_breadcrumbs': 100,
            'attach_stacktrace': True,

            # Security settings
            'send_default_pii': False,

            # Sample rates for different environments
            'traces_sampler': self._traces_sampler,
        }

        return config

    def _before_send(self, event, hint):
        """Custom before send callback for error filtering and enrichment"""
        # Filter out events in development unless debug is enabled
        if self.environment == 'development' and not self.debug:
            return None

        # Add custom context to events
        if 'exception' in event:
            event['contexts'] = event.get('contexts', {})
            event['contexts']['app'] = {
                'name': 'quant-trading-backend',
                'version': os.getenv('APP_VERSION', '0.1.0'),
                'environment': self.environment,
            }

            # Add performance context
            event['contexts']['performance'] = self._get_performance_context()

        # Filter sensitive information
        if 'request' in event:
            event['request'] = self._sanitize_request_data(event['request'])

        return event

    def _before_breadcrumb(self, breadcrumb, hint):
        """Custom before breadcrumb callback"""
        # Filter out sensitive breadcrumb data
        if breadcrumb.get('category') in ['http', 'xhr']:
            breadcrumb['data'] = self._sanitize_breadcrumb_data(breadcrumb.get('data', {}))

        return breadcrumb

    def _traces_sampler(self, sampling_context):
        """Custom trace sampler for different environments and operations"""
        # Higher sampling rate for production transactions
        if self.environment == 'production':
            return 0.2

        # Default sampling rate
        return 0.1

    def _get_performance_context(self) -> Dict[str, Any]:
        """Get performance context information"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
            }
        except ImportError:
            # psutil not available, return empty context
            return {}

    def _sanitize_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data to remove sensitive information"""
        if not isinstance(request_data, dict):
            return request_data

        sanitized = request_data.copy()

        # Remove sensitive headers
        sensitive_headers = ['authorization', 'cookie', 'x-api-key', 'password']
        if 'headers' in sanitized:
            for header in sensitive_headers:
                sanitized['headers'].pop(header, None)

        # Sanitize URL parameters
        if 'url' in sanitized:
            sanitized['url'] = self._sanitize_url(sanitized['url'])

        return sanitized

    def _sanitize_breadcrumb_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize breadcrumb data"""
        if not isinstance(data, dict):
            return data

        sanitized = data.copy()

        # Remove sensitive query parameters
        sensitive_params = ['token', 'key', 'password', 'secret', 'api_key']
        if 'url' in sanitized:
            sanitized['url'] = self._sanitize_url(sanitized['url'], sensitive_params)

        return sanitized

    def _sanitize_url(self, url: str, sensitive_params: Optional[list] = None) -> str:
        """Sanitize URL to remove sensitive information"""
        if not url:
            return url

        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Remove sensitive parameters
            sensitive = sensitive_params or ['token', 'key', 'password', 'secret', 'api_key']
            for param in sensitive:
                query_params.pop(param, None)

            # Reconstruct URL without sensitive parameters
            sanitized_query = urlencode(query_params, doseq=True)
            sanitized_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                sanitized_query,
                parsed.fragment
            ))

            return sanitized_url
        except Exception:
            # If URL parsing fails, return original URL
            return url


# Global Sentry configuration instance
sentry_config = SentryConfig()


def initialize_sentry():
    """Initialize Sentry monitoring for the application"""
    if not sentry_config.is_enabled:
        print("⚠️  Sentry monitoring disabled - no DSN configured")
        return

    try:
        import sentry_sdk

        config = sentry_config.get_sentry_config()
        sentry_sdk.init(**config)

        print(f"✅ Sentry initialized for environment: {sentry_config.environment}")

    except Exception as e:
        print(f"❌ Failed to initialize Sentry: {e}")


def capture_error_with_context(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = 'error'
) -> Optional[str]:
    """Capture error with additional context and tags"""
    if not sentry_config.is_enabled:
        return None

    try:
        import sentry_sdk

        with configure_scope() as scope:
            if tags:
                scope.set_tags(tags)
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)

            return sentry_sdk.capture_exception(error, level=level)
    except Exception:
        return None


def capture_message_with_context(
    message: str,
    level: str = 'info',
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Capture message with additional context and tags"""
    if not sentry_config.is_enabled:
        return None

    try:
        import sentry_sdk

        with configure_scope() as scope:
            if tags:
                scope.set_tags(tags)
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)

            return sentry_sdk.capture_message(message, level=level)
    except Exception:
        return None


def set_user_context(user_info: Dict[str, Any]):
    """Set user context for Sentry"""
    if not sentry_config.is_enabled:
        return

    try:
        import sentry_sdk

        with configure_scope() as scope:
            scope.set_user(user_info)
    except Exception:
        pass


def set_transaction_name(name: str):
    """Set transaction name for better performance monitoring"""
    if not sentry_config.is_enabled:
        return

    try:
        import sentry_sdk

        with configure_scope() as scope:
            scope.set_transaction_name(name)
    except Exception:
        pass


def add_performance_metric(name: str, value: float, unit: str = 'millisecond'):
    """Add custom performance metric"""
    if not sentry_config.is_enabled:
        return

    try:
        import sentry_sdk

        sentry_sdk.set_measurement(name, value, unit)
    except Exception:
        pass