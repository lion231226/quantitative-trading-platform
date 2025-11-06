"""
Log Exporter Module

This module provides comprehensive log export functionality with support
for multiple formats, privacy filtering, and packaging.
"""

import json
import csv
import io
import zipfile
import gzip
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import re
from dataclasses import dataclass
from enum import Enum

from core.log_manager import LogManager, LogEntry, LogFilter, LogLevel, LogCategory
from utils.logger import get_logger


class ExportFormat(Enum):
    """导出格式"""
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    XML = "xml"


class PrivacyLevel(Enum):
    """隐私级别"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    CUSTOM = "custom"


@dataclass
class ExportConfig:
    """导出配置"""
    format: ExportFormat = ExportFormat.JSON
    include_system_info: bool = True
    include_statistics: bool = True
    privacy_level: PrivacyLevel = PrivacyLevel.BASIC
    compress: bool = False
    include_metadata: bool = True
    max_file_size_mb: int = 100
    custom_filters: Dict[str, Any] = None


@dataclass
class ExportMetadata:
    """导出元数据"""
    export_time: datetime
    source_system: str
    version: str
    total_entries: int
    time_range: Tuple[datetime, datetime]
    filters_applied: Dict[str, Any]
    privacy_level: PrivacyLevel
    format: ExportFormat
    compressed: bool
    file_size_bytes: int


class LogExporter:
    """
    日志导出器，提供多格式导出、隐私过滤和打包功能
    """

    def __init__(self, log_manager: LogManager, config: Dict[str, Any] = None):
        """
        初始化日志导出器

        Args:
            log_manager: 日志管理器实例
            config: 导出器配置
        """
        self.logger = get_logger(self.__class__.__name__)
        self.log_manager = log_manager
        self.config = config or self._get_default_config()

        # 隐私过滤器
        self.privacy_filters = self._initialize_privacy_filters()

        self.logger.info("Log Exporter initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_export_entries": 100000,
            "temp_directory": "temp",
            "default_privacy_level": PrivacyLevel.BASIC,
            "supported_formats": [fmt.value for fmt in ExportFormat],
            "compression_enabled": True,
            "include_sensitive_data_warning": True
        }

    def _initialize_privacy_filters(self) -> Dict[PrivacyLevel, List[Dict[str, Any]]]:
        """初始化隐私过滤器"""
        return {
            PrivacyLevel.NONE: [],

            PrivacyLevel.BASIC: [
                {
                    "name": "email_addresses",
                    "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "replacement": "[EMAIL_REDACTED]",
                    "description": "Email address filtering"
                },
                {
                    "name": "ip_addresses",
                    "pattern": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                    "replacement": "[IP_REDACTED]",
                    "description": "IP address filtering"
                },
                {
                    "name": "phone_numbers",
                    "pattern": r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b',
                    "replacement": "[PHONE_REDACTED]",
                    "description": "Phone number filtering"
                }
            ],

            PrivacyLevel.STRICT: [
                {
                    "name": "email_addresses",
                    "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "replacement": "[EMAIL_REDACTED]",
                    "description": "Email address filtering"
                },
                {
                    "name": "ip_addresses",
                    "pattern": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                    "replacement": "[IP_REDACTED]",
                    "description": "IP address filtering"
                },
                {
                    "name": "phone_numbers",
                    "pattern": r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b',
                    "replacement": "[PHONE_REDACTED]",
                    "description": "Phone number filtering"
                },
                {
                    "name": "user_ids",
                    "pattern": r'\buser[_-]?id[:\s=]*\w+\b|\busername[:\s=]*\w+\b',
                    "replacement": "[USER_ID_REDACTED]",
                    "description": "User ID filtering"
                },
                {
                    "name": "session_ids",
                    "pattern": r'\bsession[_-]?id[:\s=]*\w+\b',
                    "replacement": "[SESSION_ID_REDACTED]",
                    "description": "Session ID filtering"
                },
                {
                    "name": "passwords",
                    "pattern": r'\bpassword[:\s=]*\w+\b|\bpwd[:\s=]*\w+\b',
                    "replacement": "[PASSWORD_REDACTED]",
                    "description": "Password filtering"
                },
                {
                    "name": "api_keys",
                    "pattern": r'\bapi[_-]?key[:\s=]*\w+\b|\bsecret[_-]?key[:\s=]*\w+\b',
                    "replacement": "[API_KEY_REDACTED]",
                    "description": "API key filtering"
                },
                {
                    "name": "file_paths",
                    "pattern": r'\b[a-zA-Z]:\\[^\\s]*\b|\b/[^\\s]*\b',
                    "replacement": "[PATH_REDACTED]",
                    "description": "File path filtering"
                }
            ],

            PrivacyLevel.CUSTOM: []  # 由用户自定义
        }

    def export_logs(self, log_filter: LogFilter = None,
                   export_config: ExportConfig = None) -> bytes:
        """
        导出日志

        Args:
            log_filter: 日志过滤器
            export_config: 导出配置

        Returns:
            导出的数据字节
        """
        try:
            # 使用默认配置
            if export_config is None:
                export_config = ExportConfig()

            # 收集日志
            logs = self.log_manager.collect_logs(log_filter)

            # 限制导出数量
            max_entries = self.config.get("max_export_entries", 100000)
            if len(logs) > max_entries:
                self.logger.warning(f"Limiting export to {max_entries} entries (found {len(logs)})")
                logs = logs[-max_entries:]  # 保留最新的日志

            # 应用隐私过滤
            filtered_logs = self._apply_privacy_filtering(logs, export_config.privacy_level)

            # 导出为指定格式
            export_data = self._export_to_format(filtered_logs, export_config.format, export_config)

            # 添加元数据
            if export_config.include_metadata:
                metadata = self._create_metadata(filtered_logs, log_filter, export_config)
                export_data = self._add_metadata_to_export(export_data, metadata, export_config)

            # 压缩（如果需要）
            if export_config.compress:
                export_data = self._compress_data(export_data)

            return export_data

        except Exception as e:
            self.logger.error(f"Error exporting logs: {e}")
            raise

    def _apply_privacy_filtering(self, logs: List[LogEntry],
                                privacy_level: PrivacyLevel) -> List[LogEntry]:
        """应用隐私过滤"""
        if privacy_level == PrivacyLevel.NONE:
            return logs

        filters = self.privacy_filters.get(privacy_level, [])
        if not filters:
            return logs

        filtered_logs = []
        for log in logs:
            # 创建日志条目的副本
            filtered_log = LogEntry(
                timestamp=log.timestamp,
                level=log.level,
                category=log.category,
                component=log.component,
                message=self._apply_text_filters(log.message, filters),
                details=self._apply_dict_filters(log.details, filters),
                user_id="[USER_ID_REDACTED]" if log.user_id and privacy_level == PrivacyLevel.STRICT else log.user_id,
                session_id=self._apply_text_filters(log.session_id, filters) if log.session_id else None,
                request_id=self._apply_text_filters(log.request_id, filters) if log.request_id else None,
                tags=[self._apply_text_filters(tag, filters) for tag in log.tags],
                exception_info=self._apply_text_filters(log.exception_info, filters) if log.exception_info else None,
                stack_trace=self._apply_text_filters(log.stack_trace, filters) if log.stack_trace else None
            )
            filtered_logs.append(filtered_log)

        return filtered_logs

    def _apply_text_filters(self, text: str, filters: List[Dict[str, Any]]) -> str:
        """对文本应用过滤器"""
        if not text:
            return text

        filtered_text = text
        for filter_config in filters:
            pattern = filter_config["pattern"]
            replacement = filter_config["replacement"]
            filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)

        return filtered_text

    def _apply_dict_filters(self, data: Dict[str, Any], filters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对字典数据应用过滤器"""
        if not data:
            return data

        filtered_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                filtered_data[key] = self._apply_text_filters(value, filters)
            elif isinstance(value, dict):
                filtered_data[key] = self._apply_dict_filters(value, filters)
            elif isinstance(value, list):
                filtered_data[key] = [
                    self._apply_text_filters(item, filters) if isinstance(item, str)
                    else self._apply_dict_filters(item, filters) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                filtered_data[key] = value

        return filtered_data

    def _export_to_format(self, logs: List[LogEntry],
                         format: ExportFormat,
                         config: ExportConfig) -> bytes:
        """导出为指定格式"""
        if format == ExportFormat.JSON:
            return self._export_to_json(logs, config)
        elif format == ExportFormat.CSV:
            return self._export_to_csv(logs, config)
        elif format == ExportFormat.TXT:
            return self._export_to_txt(logs, config)
        elif format == ExportFormat.XML:
            return self._export_to_xml(logs, config)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_to_json(self, logs: List[LogEntry], config: ExportConfig) -> bytes:
        """导出为JSON格式"""
        export_data = {
            "logs": [log.to_dict() for log in logs]
        }

        # 添加统计信息
        if config.include_statistics:
            export_data["statistics"] = self.log_manager.get_log_statistics()

        # 添加系统信息
        if config.include_system_info:
            export_data["system_info"] = self._get_system_info()

        return json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')

    def _export_to_csv(self, logs: List[LogEntry], config: ExportConfig) -> bytes:
        """导出为CSV格式"""
        output = io.StringIO()

        if not logs:
            return "".encode('utf-8')

        # 定义字段
        fieldnames = [
            'timestamp', 'level', 'category', 'component', 'message',
            'user_id', 'session_id', 'request_id', 'tags'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for log in logs:
            row = {
                'timestamp': log.timestamp.isoformat(),
                'level': log.level.value,
                'category': log.category.value,
                'component': log.component,
                'message': log.message,
                'user_id': log.user_id or '',
                'session_id': log.session_id or '',
                'request_id': log.request_id or '',
                'tags': ', '.join(log.tags) if log.tags else ''
            }
            writer.writerow(row)

        return output.getvalue().encode('utf-8')

    def _export_to_txt(self, logs: List[LogEntry], config: ExportConfig) -> bytes:
        """导出为文本格式"""
        lines = []

        # 添加标题
        lines.append("=" * 80)
        lines.append("LOG EXPORT")
        lines.append("=" * 80)
        lines.append(f"Export Time: {datetime.now().isoformat()}")
        lines.append(f"Total Entries: {len(logs)}")
        lines.append("")

        # 添加统计信息
        if config.include_statistics:
            stats = self.log_manager.get_log_statistics()
            lines.append("STATISTICS")
            lines.append("-" * 40)
            lines.append(f"Total Logs: {stats.get('total_logs', 0)}")

            level_dist = stats.get('by_level', {})
            if level_dist:
                lines.append("By Level:")
                for level, count in level_dist.items():
                    lines.append(f"  {level}: {count}")

            lines.append("")

        # 添加日志条目
        lines.append("LOG ENTRIES")
        lines.append("-" * 40)

        for i, log in enumerate(logs, 1):
            lines.append(f"[{i}] {log.timestamp.isoformat()} [{log.level.value}] {log.category.value}:{log.component}")
            lines.append(f"    Message: {log.message}")

            if log.user_id:
                lines.append(f"    User ID: {log.user_id}")
            if log.session_id:
                lines.append(f"    Session ID: {log.session_id}")
            if log.tags:
                lines.append(f"    Tags: {', '.join(log.tags)}")
            if log.exception_info:
                lines.append(f"    Exception: {log.exception_info}")

            lines.append("")

        return "\n".join(lines).encode('utf-8')

    def _export_to_xml(self, logs: List[LogEntry], config: ExportConfig) -> bytes:
        """导出为XML格式"""
        import xml.etree.ElementTree as ET

        # 创建根元素
        root = ET.Element("log_export")

        # 添加元数据
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "export_time").text = datetime.now().isoformat()
        ET.SubElement(metadata, "total_entries").text = str(len(logs))

        # 添加统计信息
        if config.include_statistics:
            stats = self.log_manager.get_log_statistics()
            stats_elem = ET.SubElement(root, "statistics")
            for key, value in stats.items():
                if isinstance(value, dict):
                    sub_elem = ET.SubElement(stats_elem, key)
                    for sub_key, sub_value in value.items():
                        ET.SubElement(sub_elem, sub_key).text = str(sub_value)
                else:
                    ET.SubElement(stats_elem, key).text = str(value)

        # 添加日志条目
        logs_elem = ET.SubElement(root, "logs")
        for log in logs:
            log_elem = ET.SubElement(logs_elem, "log")
            ET.SubElement(log_elem, "timestamp").text = log.timestamp.isoformat()
            ET.SubElement(log_elem, "level").text = log.level.value
            ET.SubElement(log_elem, "category").text = log.category.value
            ET.SubElement(log_elem, "component").text = log.component
            ET.SubElement(log_elem, "message").text = log.message

            if log.user_id:
                ET.SubElement(log_elem, "user_id").text = log.user_id
            if log.session_id:
                ET.SubElement(log_elem, "session_id").text = log.session_id
            if log.request_id:
                ET.SubElement(log_elem, "request_id").text = log.request_id
            if log.tags:
                tags_elem = ET.SubElement(log_elem, "tags")
                for tag in log.tags:
                    ET.SubElement(tags_elem, "tag").text = tag
            if log.exception_info:
                ET.SubElement(log_elem, "exception").text = log.exception_info

        # 转换为字符串
        xml_str = ET.tostring(root, encoding='unicode', method='xml')

        # 添加XML声明
        xml_with_decl = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

        return xml_with_decl.encode('utf-8')

    def _create_metadata(self, logs: List[LogEntry],
                        log_filter: LogFilter,
                        config: ExportConfig) -> ExportMetadata:
        """创建导出元数据"""
        if logs:
            timestamps = [log.timestamp for log in logs]
            time_range = (min(timestamps), max(timestamps))
        else:
            time_range = (datetime.now(), datetime.now())

        filter_info = {}
        if log_filter:
            filter_info = {
                "level_min": log_filter.level_min.value if log_filter.level_min else None,
                "level_max": log_filter.level_max.value if log_filter.level_max else None,
                "categories": [c.value for c in log_filter.categories] if log_filter.categories else None,
                "components": log_filter.components,
                "start_time": log_filter.start_time.isoformat() if log_filter.start_time else None,
                "end_time": log_filter.end_time.isoformat() if log_filter.end_time else None,
                "keywords": log_filter.keywords
            }

        return ExportMetadata(
            export_time=datetime.now(),
            source_system="One-Click Launcher",
            version="1.0.0",
            total_entries=len(logs),
            time_range=time_range,
            filters_applied=filter_info,
            privacy_level=config.privacy_level,
            format=config.format,
            compressed=config.compress,
            file_size_bytes=0  # 将在后续设置
        )

    def _add_metadata_to_export(self, data: bytes,
                               metadata: ExportMetadata,
                               config: ExportConfig) -> bytes:
        """添加元数据到导出数据"""
        if config.format == ExportFormat.JSON:
            # 解析JSON数据并添加元数据
            try:
                json_data = json.loads(data.decode('utf-8'))
                json_data["metadata"] = {
                    "export_time": metadata.export_time.isoformat(),
                    "source_system": metadata.source_system,
                    "version": metadata.version,
                    "total_entries": metadata.total_entries,
                    "time_range": {
                        "start": metadata.time_range[0].isoformat(),
                        "end": metadata.time_range[1].isoformat()
                    },
                    "filters_applied": metadata.filters_applied,
                    "privacy_level": metadata.privacy_level.value,
                    "format": metadata.format.value,
                    "compressed": metadata.compressed
                }
                return json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')
            except Exception as e:
                self.logger.error(f"Error adding metadata to JSON: {e}")
                return data

        elif config.format == ExportFormat.TXT:
            # 添加元数据到文本文件开头
            metadata_text = f"""
# LOG EXPORT METADATA
# Export Time: {metadata.export_time.isoformat()}
# Source System: {metadata.source_system}
# Version: {metadata.version}
# Total Entries: {metadata.total_entries}
# Time Range: {metadata.time_range[0].isoformat()} to {metadata.time_range[1].isoformat()}
# Privacy Level: {metadata.privacy_level.value}
# Format: {metadata.format.value}
# Compressed: {metadata.compressed}
#
"""
            return metadata_text.encode('utf-8') + data

        else:
            # 对于其他格式，暂时不添加元数据
            return data

    def _compress_data(self, data: bytes) -> bytes:
        """压缩数据"""
        try:
            return gzip.compress(data)
        except Exception as e:
            self.logger.error(f"Error compressing data: {e}")
            return data

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            import platform
            import psutil

            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": {
                    "total": psutil.disk_usage('/').total if platform.system() != 'Windows' else psutil.disk_usage('C:\\').total
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    def create_export_package(self, logs: List[LogEntry] = None,
                             formats: List[ExportFormat] = None,
                             privacy_level: PrivacyLevel = PrivacyLevel.BASIC) -> bytes:
        """
        创建导出包（包含多种格式）

        Args:
            logs: 日志列表（如果为None，则从log_manager获取所有日志）
            formats: 导出格式列表
            privacy_level: 隐私级别

        Returns:
            压缩包数据
        """
        try:
            # 如果没有提供日志，从log_manager获取
            if logs is None:
                logs = self.log_manager.collect_logs()

            if formats is None:
                formats = [ExportFormat.JSON, ExportFormat.CSV, ExportFormat.TXT]

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # 导出各种格式
                for format in formats:
                    config = ExportConfig(
                        format=format,
                        privacy_level=privacy_level,
                        include_metadata=True,
                        include_statistics=True
                    )

                    data = self.export_logs(export_config=config)
                    filename = f"logs.{format.value}"
                    if config.compress:
                        filename += ".gz"

                    file_path = temp_path / filename
                    file_path.write_bytes(data)

                # 创建README文件
                readme_content = self._create_readme(logs, formats, privacy_level)
                readme_path = temp_path / "README.txt"
                readme_path.write_text(readme_content, encoding='utf-8')

                # 创建ZIP文件
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in temp_path.iterdir():
                        zip_file.write(file_path, file_path.name)

                return zip_buffer.getvalue()

        except Exception as e:
            self.logger.error(f"Error creating export package: {e}")
            raise

    def _create_readme(self, logs: List[LogEntry],
                      formats: List[ExportFormat],
                      privacy_level: PrivacyLevel) -> str:
        """创建README文件"""
        content = f"""
Log Export Package
==================

Export Information:
- Export Time: {datetime.now().isoformat()}
- Total Log Entries: {len(logs)}
- Privacy Level: {privacy_level.value}
- Formats Included: {', '.join(f.value for f in formats)}

File Descriptions:
"""

        for format in formats:
            content += f"""
- logs.{format.value}: {format.value.upper()} format log data
  - Suitable for: {self._get_format_description(format)}
"""

        content += f"""
Privacy Filtering:
- Level: {privacy_level.value}
- Applied filters: {len(self.privacy_filters.get(privacy_level, []))} filters

Security Notice:
This export contains sensitive system information. Handle with care and
share only with authorized personnel.

Generated by: One-Click Launcher Log Exporter
Version: 1.0.0
"""

        return content

    def _get_format_description(self, format: ExportFormat) -> str:
        """获取格式描述"""
        descriptions = {
            ExportFormat.JSON: "Programmatic processing, data analysis",
            ExportFormat.CSV: "Spreadsheet applications, data analysis",
            ExportFormat.TXT: "Human reading, simple text processing",
            ExportFormat.XML: "Structured data exchange, web services"
        }
        return descriptions.get(format, "Data export")

    def validate_export_integrity(self, data: bytes,
                                 expected_format: ExportFormat) -> Dict[str, Any]:
        """
        验证导出完整性

        Args:
            data: 导出数据
            expected_format: 期望的格式

        Returns:
            验证结果
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }

        try:
            # 检查数据是否为空
            if not data:
                validation_result["valid"] = False
                validation_result["errors"].append("Export data is empty")
                return validation_result

            # 如果是压缩数据，先解压
            try:
                # 检查是否是gzip压缩
                if data.startswith(b'\x1f\x8b'):
                    data = gzip.decompress(data)
                    validation_result["warnings"].append("Data was compressed")
            except Exception as e:
                validation_result["warnings"].append(f"Could not decompress data: {e}")

            # 根据格式验证数据
            if expected_format == ExportFormat.JSON:
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    validation_result["statistics"]["json_entries"] = len(json_data.get("logs", []))
                except json.JSONDecodeError as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Invalid JSON format: {e}")

            elif expected_format == ExportFormat.CSV:
                try:
                    csv_text = data.decode('utf-8')
                    lines = csv_text.strip().split('\n')
                    validation_result["statistics"]["csv_lines"] = len(lines)
                    if len(lines) < 2:
                        validation_result["warnings"].append("CSV has no data rows")
                except Exception as e:
                    validation_result["errors"].append(f"Invalid CSV format: {e}")

            elif expected_format == ExportFormat.TXT:
                try:
                    text = data.decode('utf-8')
                    validation_result["statistics"]["text_characters"] = len(text)
                    validation_result["statistics"]["text_lines"] = len(text.split('\n'))
                except Exception as e:
                    validation_result["errors"].append(f"Invalid text format: {e}")

            elif expected_format == ExportFormat.XML:
                try:
                    xml_text = data.decode('utf-8')
                    import xml.etree.ElementTree as ET
                    ET.fromstring(xml_text)
                    validation_result["statistics"]["xml_valid"] = True
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Invalid XML format: {e}")

            # 添加文件大小信息
            validation_result["statistics"]["file_size_bytes"] = len(data)

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")

        return validation_result

    def add_custom_privacy_filter(self, privacy_level: PrivacyLevel,
                                 name: str, pattern: str,
                                 replacement: str, description: str = ""):
        """
        添加自定义隐私过滤器

        Args:
            privacy_level: 隐私级别
            name: 过滤器名称
            pattern: 正则表达式模式
            replacement: 替换文本
            description: 描述
        """
        try:
            # 验证正则表达式
            re.compile(pattern)

            filter_config = {
                "name": name,
                "pattern": pattern,
                "replacement": replacement,
                "description": description
            }

            if privacy_level == PrivacyLevel.CUSTOM:
                # 如果是自定义级别，直接添加
                if PrivacyLevel.CUSTOM not in self.privacy_filters:
                    self.privacy_filters[PrivacyLevel.CUSTOM] = []
                self.privacy_filters[PrivacyLevel.CUSTOM].append(filter_config)
            else:
                # 其他级别需要确认
                self.logger.warning(f"Adding filter to existing privacy level {privacy_level.value}")

            self.logger.info(f"Added custom privacy filter: {name}")

        except re.error as e:
            self.logger.error(f"Invalid regex pattern in custom filter: {e}")
            raise ValueError(f"Invalid regex pattern: {e}")

    def get_privacy_filter_summary(self, privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """获取隐私过滤器摘要"""
        filters = self.privacy_filters.get(privacy_level, [])

        return {
            "privacy_level": privacy_level.value,
            "filter_count": len(filters),
            "filters": [
                {
                    "name": f["name"],
                    "description": f["description"],
                    "replacement": f["replacement"]
                }
                for f in filters
            ]
        }