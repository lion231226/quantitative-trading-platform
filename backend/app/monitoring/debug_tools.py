"""
Debug Tools and Diagnostic Utilities
Comprehensive debugging and problem diagnosis tools for production environments
"""

import asyncio
import json
import os
import sys
import time
import traceback
import psutil
import inspect
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from contextlib import asynccontextmanager
from functools import wraps

from fastapi import HTTPException
from pydantic import BaseModel

from sentry_config import sentry_config, capture_error_with_context
from logging_config import get_logger
from metrics import metrics


@dataclass
class DiagnosticInfo:
    """Diagnostic information structure"""
    component: str
    status: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration: float = 0.0


@dataclass
class SystemSnapshot:
    """System state snapshot"""
    timestamp: datetime
    process_info: Dict[str, Any]
    system_resources: Dict[str, Any]
    application_state: Dict[str, Any]
    active_connections: List[Dict[str, Any]]
    recent_errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class DebugContextManager:
    """Debug context manager for operation tracing"""

    def __init__(self, operation_name: str, enabled: bool = True):
        self.operation_name = operation_name
        self.enabled = enabled
        self.start_time = None
        self.context = {}
        self.logger = get_logger("debug.context")

    def __enter__(self):
        if self.enabled:
            self.start_time = time.time()
            self.context['operation_start'] = datetime.utcnow().isoformat()
            self.logger.debug(f"Starting debug context: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled:
            duration = time.time() - self.start_time
            self.context['operation_end'] = datetime.utcnow().isoformat()
            self.context['operation_duration'] = duration
            self.context['operation_success'] = exc_type is None

            if exc_type:
                self.context['error_type'] = exc_type.__name__
                self.context['error_message'] = str(exc_val)
                self.context['error_traceback'] = traceback.format_exception(exc_type, exc_val, exc_tb)

            self.logger.debug(f"Debug context completed: {self.operation_name}", **self.context)


class PerformanceProfiler:
    """Performance profiling utilities"""

    def __init__(self):
        self.logger = get_logger("performance.profiler")
        self.profiles = {}

    @asynccontextmanager
    async def profile_function(self, func_name: str):
        """Profile a function execution"""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()

            profile_data = {
                'function': func_name,
                'duration': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'start_memory': start_memory,
                'end_memory': end_memory,
                'timestamp': datetime.utcnow().isoformat(),
            }

            self.profiles[func_name] = profile_data
            self.logger.debug(f"Profile data for {func_name}", **profile_data)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except:
            return 0.0

    def get_function_stats(self, func_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific function"""
        return self.profiles.get(func_name)

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all profiling statistics"""
        return {
            'functions': dict(self.profiles),
            'total_functions': len(self.profiles),
            'last_updated': datetime.utcnow().isoformat(),
        }


class ErrorAnalyzer:
    """Error analysis and classification utilities"""

    def __init__(self):
        self.logger = get_logger("error.analyzer")
        self.error_patterns = self._load_error_patterns()
        self.error_history = []

    def _load_error_patterns(self) -> Dict[str, Any]:
        """Load error classification patterns"""
        return {
            'database_errors': {
                'patterns': [
                    'connection.*timeout',
                    'database.*connection.*failed',
                    'sql.*error',
                    'deadlock',
                ],
                'severity': 'high',
                'category': 'infrastructure'
            },
            'network_errors': {
                'patterns': [
                    'connection.*refused',
                    'timeout.*occurred',
                    'network.*unreachable',
                    'dns.*resolution.*failed',
                ],
                'severity': 'medium',
                'category': 'infrastructure'
            },
            'authentication_errors': {
                'patterns': [
                    'unauthorized',
                    'authentication.*failed',
                    'invalid.*credentials',
                    'token.*expired',
                ],
                'severity': 'medium',
                'category': 'security'
            },
            'validation_errors': {
                'patterns': [
                    'validation.*failed',
                    'invalid.*input',
                    'required.*field.*missing',
                    'malformed.*request',
                ],
                'severity': 'low',
                'category': 'application'
            },
            'resource_errors': {
                'patterns': [
                    'memory.*exhausted',
                    'disk.*full',
                    'cpu.*overload',
                    'too.*many.*connections',
                ],
                'severity': 'high',
                'category': 'infrastructure'
            }
        }

    def analyze_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze and classify an error"""
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {},
        }

        # Classify error
        classification = self._classify_error(error_info)
        error_info.update(classification)

        # Add to history
        self.error_history.append(error_info)

        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history.pop(0)

        return error_info

    def _classify_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Classify error based on patterns"""
        import re

        error_text = f"{error_info['type']} {error_info['message']} {error_info['traceback']}"

        for category, config in self.error_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, error_text, re.IGNORECASE):
                    return {
                        'category': config['category'],
                        'severity': config['severity'],
                        'pattern_matched': pattern,
                        'classification': category,
                    }

        return {
            'category': 'unknown',
            'severity': 'medium',
            'pattern_matched': None,
            'classification': 'unclassified',
        }

    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends analysis"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [
            error for error in self.error_history
            if datetime.fromisoformat(error['timestamp']) > cutoff_time
        ]

        trends = {
            'total_errors': len(recent_errors),
            'error_rate': len(recent_errors) / hours,
            'categories': {},
            'severities': {},
            'top_errors': {},
        }

        # Categorize errors
        for error in recent_errors:
            category = error.get('category', 'unknown')
            severity = error.get('severity', 'medium')
            error_type = f"{error['type']}: {error['message'][:50]}"

            trends['categories'][category] = trends['categories'].get(category, 0) + 1
            trends['severities'][severity] = trends['severities'].get(severity, 0) + 1
            trends['top_errors'][error_type] = trends['top_errors'].get(error_type, 0) + 1

        # Sort top errors
        trends['top_errors'] = dict(
            sorted(trends['top_errors'].items(), key=lambda x: x[1], reverse=True)[:10]
        )

        return trends

    def get_error_suggestions(self, error: Exception) -> List[str]:
        """Get debugging suggestions for an error"""
        error_type = type(error).__name__
        error_message = str(error).lower()

        suggestions = []

        # Common error suggestions
        if 'connection' in error_message and 'timeout' in error_message:
            suggestions.extend([
                "Check network connectivity",
                "Verify service is running",
                "Increase timeout settings",
                "Check firewall rules"
            ])

        if 'database' in error_message:
            suggestions.extend([
                "Check database server status",
                "Verify connection string",
                "Check connection pool settings",
                "Review query performance"
            ])

        if 'memory' in error_message:
            suggestions.extend([
                "Check for memory leaks",
                "Increase memory allocation",
                "Review large object allocations",
                "Check garbage collection"
            ])

        if 'authentication' in error_message:
            suggestions.extend([
                "Verify credentials",
                "Check token validity",
                "Review authentication flow",
                "Check permission settings"
            ])

        # Add type-specific suggestions
        type_suggestions = {
            'ValueError': "Check input data validity and constraints",
            'TypeError': "Verify data types match expected formats",
            'KeyError': "Check dictionary keys and data structure",
            'IndexError': "Verify array/list indices are within bounds",
            'AttributeError': "Check object attributes and method calls",
            'ImportError': "Verify module imports and dependencies",
            'FileNotFoundError': "Check file paths and permissions",
            'PermissionError': "Verify file/directory access rights",
        }

        if error_type in type_suggestions:
            suggestions.append(type_suggestions[error_type])

        return suggestions


class SystemDiagnostics:
    """System-wide diagnostic tools"""

    def __init__(self):
        self.logger = get_logger("system.diagnostics")
        self.error_analyzer = ErrorAnalyzer()
        self.profiler = PerformanceProfiler()

    async def run_comprehensive_diagnostics(self) -> SystemSnapshot:
        """Run comprehensive system diagnostics"""
        start_time = time.time()

        try:
            # Gather system information
            process_info = await self._get_process_info()
            system_resources = await self._get_system_resources()
            application_state = await self._get_application_state()
            active_connections = await self._get_active_connections()
            recent_errors = self._get_recent_errors()
            performance_metrics = await self._get_performance_metrics()

            snapshot = SystemSnapshot(
                timestamp=datetime.utcnow(),
                process_info=process_info,
                system_resources=system_resources,
                application_state=application_state,
                active_connections=active_connections,
                recent_errors=recent_errors,
                performance_metrics=performance_metrics
            )

            duration = time.time() - start_time
            self.logger.info(f"Comprehensive diagnostics completed in {duration:.2f}s")

            return snapshot

        except Exception as e:
            self.logger.error(f"Comprehensive diagnostics failed: {e}")
            raise

    async def _get_process_info(self) -> Dict[str, Any]:
        """Get process information"""
        try:
            process = psutil.Process()
            return {
                'pid': process.pid,
                'name': process.name(),
                'status': process.status(),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                'cpu_percent': process.cpu_percent(),
                'memory_info': {
                    'rss_mb': process.memory_info().rss / (1024 * 1024),
                    'vms_mb': process.memory_info().vms / (1024 * 1024),
                },
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads(),
                'connections': len(process.connections()),
            }
        except Exception as e:
            self.logger.error(f"Failed to get process info: {e}")
            return {'error': str(e)}

    async def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            return {
                'cpu': {
                    'count': psutil.cpu_count(),
                    'usage_percent': psutil.cpu_percent(interval=1),
                    'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
                },
                'memory': {
                    'total_gb': psutil.virtual_memory().total / (1024**3),
                    'available_gb': psutil.virtual_memory().available / (1024**3),
                    'used_gb': psutil.virtual_memory().used / (1024**3),
                    'usage_percent': psutil.virtual_memory().percent,
                },
                'disk': {
                    'total_gb': psutil.disk_usage('/').total / (1024**3),
                    'used_gb': psutil.disk_usage('/').used / (1024**3),
                    'free_gb': psutil.disk_usage('/').free / (1024**3),
                    'usage_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                },
                'network': {
                    'bytes_sent': psutil.net_io_counters().bytes_sent if psutil.net_io_counters() else 0,
                    'bytes_recv': psutil.net_io_counters().bytes_recv if psutil.net_io_counters() else 0,
                    'packets_sent': psutil.net_io_counters().packets_sent if psutil.net_io_counters() else 0,
                    'packets_recv': psutil.net_io_counters().packets_recv if psutil.net_io_counters() else 0,
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get system resources: {e}")
            return {'error': str(e)}

    async def _get_application_state(self) -> Dict[str, Any]:
        """Get application state information"""
        try:
            return {
                'version': '0.1.0',  # This would come from config
                'environment': sentry_config.environment,
                'uptime_seconds': time.time() - psutil.Process().create_time(),
                'active_sessions': 0,  # This would come from session manager
                'background_jobs': 0,  # This would come from job queue
                'cache_size_mb': 0,  # This would come from cache stats
                'database_connections': 0,  # This would come from DB pool stats
            }
        except Exception as e:
            self.logger.error(f"Failed to get application state: {e}")
            return {'error': str(e)}

    async def _get_active_connections(self) -> List[Dict[str, Any]]:
        """Get active connection information"""
        try:
            connections = []
            process = psutil.Process()

            for conn in process.connections():
                connections.append({
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'type': str(conn.type),
                })

            return connections
        except Exception as e:
            self.logger.error(f"Failed to get active connections: {e}")
            return [{'error': str(e)}]

    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """Get recent error information"""
        return self.error_analyzer.error_history[-50:]  # Last 50 errors

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            return {
                'profiling_stats': self.profiler.get_all_stats(),
                'error_trends': self.error_analyzer.get_error_trends(),
                'metrics_stats': {
                    'buffer_size': metrics.enabled,
                    'registry_size': len(metrics.registry._collector_to_names) if metrics.enabled else 0,
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}

    async def generate_debug_report(self) -> Dict[str, Any]:
        """Generate comprehensive debug report"""
        try:
            snapshot = await self.run_comprehensive_diagnostics()

            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'system_snapshot': asdict(snapshot),
                'recommendations': await self._generate_recommendations(snapshot),
                'health_score': await self._calculate_health_score(snapshot),
            }

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate debug report: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }

    async def _generate_recommendations(self, snapshot: SystemSnapshot) -> List[str]:
        """Generate system improvement recommendations"""
        recommendations = []

        # CPU recommendations
        if snapshot.system_resources.get('cpu', {}).get('usage_percent', 0) > 80:
            recommendations.append("High CPU usage detected - consider scaling or optimizing CPU-intensive operations")

        # Memory recommendations
        if snapshot.system_resources.get('memory', {}).get('usage_percent', 0) > 85:
            recommendations.append("High memory usage detected - check for memory leaks or increase memory allocation")

        # Disk recommendations
        if snapshot.system_resources.get('disk', {}).get('usage_percent', 0) > 90:
            recommendations.append("Low disk space - clean up old files or increase storage capacity")

        # Error rate recommendations
        if len(snapshot.recent_errors) > 100:
            recommendations.append("High error rate detected - review recent errors and fix underlying issues")

        # Connection recommendations
        if len(snapshot.active_connections) > 1000:
            recommendations.append("High number of connections - check for connection leaks")

        return recommendations

    async def _calculate_health_score(self, snapshot: SystemSnapshot) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0

        # CPU impact (max 20 points)
        cpu_usage = snapshot.system_resources.get('cpu', {}).get('usage_percent', 0)
        if cpu_usage > 90:
            score -= 20
        elif cpu_usage > 80:
            score -= 10
        elif cpu_usage > 70:
            score -= 5

        # Memory impact (max 20 points)
        memory_usage = snapshot.system_resources.get('memory', {}).get('usage_percent', 0)
        if memory_usage > 95:
            score -= 20
        elif memory_usage > 85:
            score -= 10
        elif memory_usage > 75:
            score -= 5

        # Disk impact (max 15 points)
        disk_usage = snapshot.system_resources.get('disk', {}).get('usage_percent', 0)
        if disk_usage > 95:
            score -= 15
        elif disk_usage > 85:
            score -= 8
        elif disk_usage > 80:
            score -= 3

        # Error impact (max 25 points)
        error_count = len(snapshot.recent_errors)
        if error_count > 50:
            score -= 25
        elif error_count > 20:
            score -= 15
        elif error_count > 10:
            score -= 8
        elif error_count > 5:
            score -= 3

        # Connection impact (max 10 points)
        connection_count = len(snapshot.active_connections)
        if connection_count > 500:
            score -= 10
        elif connection_count > 200:
            score -= 5
        elif connection_count > 100:
            score -= 2

        # Performance impact (max 10 points)
        uptime = snapshot.process_info.get('uptime_seconds', 0)
        if uptime < 300:  # Less than 5 minutes
            score -= 10
        elif uptime < 900:  # Less than 15 minutes
            score -= 5

        return max(0.0, round(score, 2))


# Global diagnostic tools instance
system_diagnostics = SystemDiagnostics()

# Decorators for debugging
def debug_function(func_name: str = None):
    """Decorator for function debugging"""
    def decorator(func: Callable):
        name = func_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with system_diagnostics.profiler.profile_function(name):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_info = system_diagnostics.error_analyzer.analyze_error(
                        e,
                        {'function': name, 'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
                    )
                    system_diagnostics.logger.error("Function error captured", **error_info)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't use async context manager
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                profile_data = {
                    'function': name,
                    'duration': duration,
                    'success': True,
                    'timestamp': datetime.utcnow().isoformat(),
                }
                system_diagnostics.profiler.profiles[name] = profile_data

                return result
            except Exception as e:
                error_info = system_diagnostics.error_analyzer.analyze_error(
                    e,
                    {'function': name, 'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
                )
                system_diagnostics.logger.error("Function error captured", **error_info)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def debug_context(operation_name: str, enabled: bool = True):
    """Context manager for debugging operations"""
    return DebugContextManager(operation_name, enabled)