"""
Configuration File Automatic Repair Module

This module provides comprehensive configuration file validation, corruption detection,
automatic repair, reset functionality, and version management with rollback capabilities.
"""

import os
import sys
import json
import yaml
import xml.etree.ElementTree as ET
import configparser
import shutil
import hashlib
import tempfile
import re
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class ConfigFormat(Enum):
    """Supported configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    INI = "ini"
    XML = "xml"
    PROPERTIES = "properties"
    TOML = "toml"
    ENV = "env"


class RepairStrategy(Enum):
    """Configuration repair strategies"""
    VALIDATE_ONLY = "validate_only"
    AUTO_REPAIR = "auto_repair"
    RESET_TO_DEFAULT = "reset_to_default"
    MERGE_DEFAULT = "merge_default"
    BACKUP_AND_REPAIR = "backup_and_repair"


class ConfigValidationResult(Enum):
    """Configuration validation results"""
    VALID = "valid"
    WARNING = "warning"  # Valid but has issues
    CORRUPTED = "corrupted"
    MISSING = "missing"
    INCOMPATIBLE_VERSION = "incompatible_version"
    SCHEMA_VIOLATION = "schema_violation"


@dataclass
class ConfigIssue:
    """Represents a configuration issue"""
    issue_type: str  # 'syntax', 'schema', 'missing_key', 'invalid_value'
    severity: str  # 'error', 'warning', 'info'
    path: str  # JSON path or config key
    message: str
    suggestion: Optional[str]
    auto_repairable: bool


@dataclass
class ConfigValidationReport:
    """Result of configuration validation"""
    file_path: str
    format: ConfigFormat
    result: ConfigValidationResult
    issues: List[ConfigIssue]
    is_repairable: bool
    suggested_repair_strategy: RepairStrategy
    metadata: Dict[str, Any]


@dataclass
class ConfigRepairOperation:
    """Represents a configuration repair operation"""
    operation_id: str
    file_path: str
    strategy: RepairStrategy
    operation_type: str  # 'validate', 'repair', 'reset', 'backup'
    original_hash: Optional[str]
    new_hash: Optional[str]
    backup_path: Optional[str]
    issues_fixed: List[str]
    status: str  # 'pending', 'completed', 'failed', 'skipped'
    error_message: Optional[str]
    timestamp: datetime


@dataclass
class ConfigTemplate:
    """Configuration template for default values"""
    name: str
    version: str
    format: ConfigFormat
    content: Union[Dict, str]
    schema: Optional[Dict]
    metadata: Dict[str, Any]


class ConfigValidator:
    """Validates configuration files and detects corruption"""

    def __init__(self):
        self.validators = {
            ConfigFormat.JSON: self._validate_json,
            ConfigFormat.YAML: self._validate_yaml,
            ConfigFormat.INI: self._validate_ini,
            ConfigFormat.XML: self._validate_xml,
            ConfigFormat.PROPERTIES: self._validate_properties,
            ConfigFormat.ENV: self._validate_env,
        }

    def validate_config(self, file_path: str,
                       expected_format: Optional[ConfigFormat] = None,
                       schema: Optional[Dict] = None) -> ConfigValidationReport:
        """
        Validate a configuration file
        """
        if not os.path.exists(file_path):
            return ConfigValidationReport(
                file_path=file_path,
                format=expected_format or ConfigFormat.JSON,
                result=ConfigValidationResult.MISSING,
                issues=[ConfigIssue(
                    issue_type="missing_file",
                    severity="error",
                    path="",
                    message="Configuration file does not exist",
                    suggestion="Create the configuration file",
                    auto_repairable=True
                )],
                is_repairable=True,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

        # Detect format if not specified
        if expected_format is None:
            expected_format = self._detect_format(file_path)

        # Get file hash for integrity checking
        file_hash = self._calculate_file_hash(file_path)

        # Validate based on format
        validator = self.validators.get(expected_format, self._validate_unknown)
        result = validator(file_path, schema)

        # Add metadata
        result.metadata['file_hash'] = file_hash
        result.metadata['file_size'] = os.path.getsize(file_path)
        result.metadata['last_modified'] = datetime.fromtimestamp(os.path.getmtime(file_path))

        return result

    def _detect_format(self, file_path: str) -> ConfigFormat:
        """Detect configuration file format from extension and content"""
        ext = Path(file_path).suffix.lower()

        format_map = {
            '.json': ConfigFormat.JSON,
            '.yaml': ConfigFormat.YAML,
            '.yml': ConfigFormat.YAML,
            '.ini': ConfigFormat.INI,
            '.cfg': ConfigFormat.INI,
            '.conf': ConfigFormat.INI,
            '.xml': ConfigFormat.XML,
            '.properties': ConfigFormat.PROPERTIES,
            '.toml': ConfigFormat.TOML,
            '.env': ConfigFormat.ENV,
        }

        detected_format = format_map.get(ext)

        # Try to detect from content if extension is ambiguous
        if detected_format is None:
            detected_format = self._detect_format_from_content(file_path)

        return detected_format or ConfigFormat.JSON  # Default to JSON

    def _detect_format_from_content(self, file_path: str) -> Optional[ConfigFormat]:
        """Detect format from file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024).strip()

            if content.startswith('{') or content.startswith('['):
                return ConfigFormat.JSON
            elif content.startswith('---') or content.startswith('#'):
                return ConfigFormat.YAML
            elif content.startswith('<?xml'):
                return ConfigFormat.XML
            elif '=' in content and not content.startswith('{'):
                return ConfigFormat.PROPERTIES
            elif '[' in content and '=' in content:
                return ConfigFormat.INI
            elif 'KEY=' in content.upper():
                return ConfigFormat.ENV

        except Exception:
            pass

        return None

    def _validate_json(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate JSON configuration file"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Basic structure validation
            if not isinstance(data, (dict, list)):
                issues.append(ConfigIssue(
                    issue_type="structure",
                    severity="error",
                    path="",
                    message="JSON must be an object or array",
                    suggestion="Ensure the JSON file contains a valid object or array",
                    auto_repairable=False
                ))

            # Schema validation if provided
            if schema and isinstance(data, dict):
                schema_issues = self._validate_schema(data, schema)
                issues.extend(schema_issues)

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.JSON,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'type': type(data).__name__}
            )

        except json.JSONDecodeError as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.JSON,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="syntax",
                    severity="error",
                    path="",
                    message=f"Invalid JSON: {e}",
                    suggestion="Fix JSON syntax errors",
                    auto_repairable=True
                )],
                is_repairable=True,
                suggested_repair_strategy=RepairStrategy.AUTO_REPAIR,
                metadata={}
            )
        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.JSON,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading JSON: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_yaml(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate YAML configuration file"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Basic structure validation
            if data is None:
                issues.append(ConfigIssue(
                    issue_type="empty",
                    severity="warning",
                    path="",
                    message="YAML file is empty",
                    suggestion="Add configuration content",
                    auto_repairable=True
                ))

            # Schema validation if provided
            if schema and isinstance(data, dict):
                schema_issues = self._validate_schema(data, schema)
                issues.extend(schema_issues)

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.YAML,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'type': type(data).__name__ if data else 'empty'}
            )

        except yaml.YAMLError as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.YAML,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="syntax",
                    severity="error",
                    path="",
                    message=f"Invalid YAML: {e}",
                    suggestion="Fix YAML syntax errors",
                    auto_repairable=True
                )],
                is_repairable=True,
                suggested_repair_strategy=RepairStrategy.AUTO_REPAIR,
                metadata={}
            )
        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.YAML,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading YAML: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_ini(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate INI configuration file"""
        issues = []

        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')

            # Check if file was read correctly
            if not config.sections():
                issues.append(ConfigIssue(
                    issue_type="empty",
                    severity="warning",
                    path="",
                    message="INI file has no sections",
                    suggestion="Add configuration sections",
                    auto_repairable=True
                ))

            # Schema validation if provided
            if schema:
                schema_issues = self._validate_ini_schema(config, schema)
                issues.extend(schema_issues)

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.INI,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'sections': config.sections()}
            )

        except configparser.Error as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.INI,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="syntax",
                    severity="error",
                    path="",
                    message=f"Invalid INI format: {e}",
                    suggestion="Fix INI syntax errors",
                    auto_repairable=True
                )],
                is_repairable=True,
                suggested_repair_strategy=RepairStrategy.AUTO_REPAIR,
                metadata={}
            )
        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.INI,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading INI: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_xml(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate XML configuration file"""
        issues = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Basic structure validation
            if root is None:
                issues.append(ConfigIssue(
                    issue_type="empty",
                    severity="error",
                    path="",
                    message="XML file has no root element",
                    suggestion="Add valid XML content",
                    auto_repairable=True
                ))

            # Schema validation would require more complex implementation
            # For now, just ensure it's well-formed XML

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.XML,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'root_tag': root.tag if root else None}
            )

        except ET.ParseError as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.XML,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="syntax",
                    severity="error",
                    path="",
                    message=f"Invalid XML: {e}",
                    suggestion="Fix XML syntax errors",
                    auto_repairable=True
                )],
                is_repairable=True,
                suggested_repair_strategy=RepairStrategy.AUTO_REPAIR,
                metadata={}
            )
        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.XML,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading XML: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_properties(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate Java properties file"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#') or line.startswith('!'):
                    continue

                # Check for key=value format
                if '=' not in line and ':' not in line:
                    issues.append(ConfigIssue(
                        issue_type="format",
                        severity="warning",
                        path=f"line_{line_num}",
                        message=f"Line {line_num} may not be in key=value format",
                        suggestion="Use key=value or key:value format",
                        auto_repairable=True
                    ))

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.PROPERTIES,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'lines_count': len(lines)}
            )

        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.PROPERTIES,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading properties: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_env(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Validate environment file (.env)"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Check for KEY=VALUE format
                if '=' not in line:
                    issues.append(ConfigIssue(
                        issue_type="format",
                        severity="warning",
                        path=f"line_{line_num}",
                        message=f"Line {line_num} is not in KEY=VALUE format",
                        suggestion="Use KEY=VALUE format",
                        auto_repairable=True
                    ))
                else:
                    # Check for valid key format
                    key = line.split('=')[0].strip()
                    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                        issues.append(ConfigIssue(
                            issue_type="invalid_key",
                            severity="warning",
                            path=key,
                            message=f"Invalid environment variable key: {key}",
                            suggestion="Use letters, numbers, and underscores only",
                            auto_repairable=True
                        ))

            result = ConfigValidationResult.VALID if not issues else ConfigValidationResult.WARNING

            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.ENV,
                result=result,
                issues=issues,
                is_repairable=any(issue.auto_repairable for issue in issues),
                suggested_repair_strategy=self._get_repair_strategy(issues),
                metadata={'variables_count': len([l for l in lines if '=' in l and not l.strip().startswith('#')])}
            )

        except Exception as e:
            return ConfigValidationReport(
                file_path=file_path,
                format=ConfigFormat.ENV,
                result=ConfigValidationResult.CORRUPTED,
                issues=[ConfigIssue(
                    issue_type="unknown",
                    severity="error",
                    path="",
                    message=f"Error reading .env file: {e}",
                    suggestion="Check file permissions and format",
                    auto_repairable=False
                )],
                is_repairable=False,
                suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
                metadata={}
            )

    def _validate_unknown(self, file_path: str, schema: Optional[Dict] = None) -> ConfigValidationReport:
        """Handle unknown configuration file format"""
        return ConfigValidationReport(
            file_path=file_path,
            format=ConfigFormat.JSON,
            result=ConfigValidationResult.CORRUPTED,
            issues=[ConfigIssue(
                issue_type="unknown_format",
                severity="error",
                path="",
                message="Unknown configuration file format",
                suggestion="Use a supported format (JSON, YAML, INI, XML, Properties, ENV)",
                auto_repairable=False
            )],
            is_repairable=False,
            suggested_repair_strategy=RepairStrategy.RESET_TO_DEFAULT,
            metadata={}
        )

    def _validate_schema(self, data: Dict, schema: Dict, path: str = "") -> List[ConfigIssue]:
        """Validate data against a schema"""
        issues = []

        for key, schema_value in schema.items():
            current_path = f"{path}.{key}" if path else key

            if key not in data:
                required = schema_value.get('required', False)
                if required:
                    issues.append(ConfigIssue(
                        issue_type="missing_key",
                        severity="error",
                        path=current_path,
                        message=f"Required key '{key}' is missing",
                        suggestion=f"Add '{key}' with appropriate value",
                        auto_repairable=True
                    ))
                continue

            value = data[key]
            expected_type = schema_value.get('type')

            if expected_type and not isinstance(value, self._get_python_type(expected_type)):
                issues.append(ConfigIssue(
                    issue_type="invalid_value",
                    severity="error",
                    path=current_path,
                    message=f"Expected {expected_type}, got {type(value).__name__}",
                    suggestion=f"Convert '{key}' to {expected_type}",
                    auto_repairable=True
                ))

            # Recursive validation for nested objects
            if isinstance(value, dict) and 'properties' in schema_value:
                nested_issues = self._validate_schema(value, schema_value['properties'], current_path)
                issues.extend(nested_issues)

        return issues

    def _validate_ini_schema(self, config: configparser.ConfigParser, schema: Dict) -> List[ConfigIssue]:
        """Validate INI config against schema"""
        issues = []

        for section_name, section_schema in schema.items():
            if not config.has_section(section_name):
                required = section_schema.get('required', False)
                if required:
                    issues.append(ConfigIssue(
                        issue_type="missing_section",
                        severity="error",
                        path=section_name,
                        message=f"Required section '{section_name}' is missing",
                        suggestion=f"Add [{section_name}] section",
                        auto_repairable=True
                    ))
                continue

            for key, key_schema in section_schema.get('keys', {}).items():
                if not config.has_option(section_name, key):
                    required = key_schema.get('required', False)
                    if required:
                        issues.append(ConfigIssue(
                            issue_type="missing_key",
                            severity="error",
                            path=f"{section_name}.{key}",
                            message=f"Required key '{key}' is missing in section '{section_name}'",
                            suggestion=f"Add {key}=[value] to section [{section_name}]",
                            auto_repairable=True
                        ))

        return issues

    def _get_python_type(self, type_str: str) -> type:
        """Convert string type to Python type"""
        type_map = {
            'string': str,
            'str': str,
            'integer': int,
            'int': int,
            'number': (int, float),
            'float': float,
            'boolean': bool,
            'bool': bool,
            'array': list,
            'object': dict,
        }

        return type_map.get(type_str.lower(), str)

    def _get_repair_strategy(self, issues: List[ConfigIssue]) -> RepairStrategy:
        """Determine the best repair strategy based on issues"""
        if not issues:
            return RepairStrategy.VALIDATE_ONLY

        has_errors = any(issue.severity == 'error' for issue in issues)
        has_repairable = any(issue.auto_repairable for issue in issues)

        if has_errors and has_repairable:
            return RepairStrategy.AUTO_REPAIR
        elif has_errors:
            return RepairStrategy.RESET_TO_DEFAULT
        else:
            return RepairStrategy.VALIDATE_ONLY

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""


class ConfigRepairer:
    """Repairs configuration files automatically"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None,
                 backup_dir: Optional[str] = None):
        self.progress_tracker = progress_tracker
        self.backup_dir = backup_dir or tempfile.mkdtemp(prefix="config_repair_backup_")
        self.validator = ConfigValidator()
        self.templates = self._load_default_templates()
        self.operations: List[ConfigRepairOperation] = []

    def _load_default_templates(self) -> Dict[str, ConfigTemplate]:
        """Load default configuration templates"""
        templates = {}

        # Application configuration template
        templates['app_config'] = ConfigTemplate(
            name="Application Configuration",
            version="1.0",
            format=ConfigFormat.JSON,
            content={
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "demo_platform",
                    "username": "demo_user",
                    "password": "demo_password"
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0
                },
                "api": {
                    "host": "localhost",
                    "port": 8000,
                    "debug": False
                },
                "frontend": {
                    "host": "localhost",
                    "port": 3000,
                    "environment": "development"
                },
                "logging": {
                    "level": "INFO",
                    "file": "logs/app.log",
                    "max_size": "10MB",
                    "backup_count": 5
                }
            },
            schema={
                "database": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "host": {"type": "string", "required": True},
                        "port": {"type": "number", "required": True},
                        "name": {"type": "string", "required": True}
                    }
                },
                "redis": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "host": {"type": "string", "required": True},
                        "port": {"type": "number", "required": True}
                    }
                }
            },
            metadata={
                "description": "Default application configuration template",
                "author": "Automatic Repair System",
                "created": datetime.now().isoformat()
            }
        )

        # Environment variables template
        templates['env_config'] = ConfigTemplate(
            name="Environment Variables",
            version="1.0",
            format=ConfigFormat.ENV,
            content="""# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=demo_platform
DB_USER=demo_user
DB_PASSWORD=demo_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API Configuration
API_HOST=localhost
API_PORT=8000
API_DEBUG=false

# Frontend Configuration
FRONTEND_HOST=localhost
FRONTEND_PORT=3000
NODE_ENV=development

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
""",
            schema=None,
            metadata={
                "description": "Default environment variables template",
                "author": "Automatic Repair System",
                "created": datetime.now().isoformat()
            }
        )

        # Logger configuration template
        templates['logger_config'] = ConfigTemplate(
            name="Logger Configuration",
            version="1.0",
            format=ConfigFormat.YAML,
            content={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    },
                    "detailed": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "default",
                        "stream": "ext://sys.stdout"
                    },
                    "file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": "DEBUG",
                        "formatter": "detailed",
                        "filename": "logs/app.log",
                        "maxBytes": 10485760,
                        "backupCount": 5
                    }
                },
                "loggers": {
                    "": {
                        "level": "INFO",
                        "handlers": ["console", "file"]
                    }
                }
            },
            schema=None,
            metadata={
                "description": "Default logging configuration template",
                "author": "Automatic Repair System",
                "created": datetime.now().isoformat()
            }
        )

        return templates

    def repair_config(self, file_path: str,
                     strategy: Optional[RepairStrategy] = None,
                     template_name: Optional[str] = None,
                     schema: Optional[Dict] = None) -> ConfigRepairOperation:
        """
        Repair a configuration file using the specified strategy
        """
        operation_id = f"repair_{int(datetime.now().timestamp())}"

        # Validate the configuration file first
        validation_report = self.validator.validate_config(file_path, schema=schema)

        # Determine strategy if not specified
        if strategy is None:
            strategy = validation_report.suggested_repair_strategy

        # Get original file hash
        original_hash = validation_report.metadata.get('file_hash', '')

        try:
            # Create backup before repair
            backup_path = self._create_backup(file_path, operation_id)

            # Perform repair based on strategy
            if strategy == RepairStrategy.VALIDATE_ONLY:
                result = self._validate_only(validation_report)
            elif strategy == RepairStrategy.AUTO_REPAIR:
                result = self._auto_repair(file_path, validation_report)
            elif strategy == RepairStrategy.RESET_TO_DEFAULT:
                result = self._reset_to_default(file_path, template_name or 'app_config')
            elif strategy == RepairStrategy.MERGE_DEFAULT:
                result = self._merge_with_default(file_path, template_name or 'app_config')
            elif strategy == RepairStrategy.BACKUP_AND_REPAIR:
                result = self._backup_and_repair(file_path, validation_report, template_name)
            else:
                raise ValueError(f"Unsupported repair strategy: {strategy}")

            # Get new file hash after repair
            new_hash = self.validator._calculate_file_hash(file_path) if os.path.exists(file_path) else ''

            # Create repair operation record
            operation = ConfigRepairOperation(
                operation_id=operation_id,
                file_path=file_path,
                strategy=strategy,
                operation_type=strategy.value,
                original_hash=original_hash,
                new_hash=new_hash,
                backup_path=backup_path,
                issues_fixed=[issue.message for issue in validation_report.issues if issue.severity == 'error'],
                status='completed' if result['success'] else 'failed',
                error_message=result.get('error') if not result['success'] else None,
                timestamp=datetime.now()
            )

            self.operations.append(operation)

            # Log repair result
            self._log_repair_result(operation)

            if self.progress_tracker:
                self.progress_tracker._log(f"Configuration repair completed for {file_path}")

            return operation

        except Exception as e:
            error_operation = ConfigRepairOperation(
                operation_id=operation_id,
                file_path=file_path,
                strategy=strategy,
                operation_type=strategy.value,
                original_hash=original_hash,
                new_hash=None,
                backup_path=None,
                issues_fixed=[],
                status='failed',
                error_message=str(e),
                timestamp=datetime.now()
            )

            self.operations.append(operation_id)
            logger.error(f"Configuration repair failed for {file_path}: {e}")

            return error_operation

    def _create_backup(self, file_path: str, operation_id: str) -> Optional[str]:
        """Create a backup of the configuration file"""
        if not os.path.exists(file_path):
            return None

        try:
            os.makedirs(self.backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_filename = f"{operation_id}_{timestamp}_{filename}"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None

    def _validate_only(self, validation_report: ConfigValidationReport) -> Dict[str, Any]:
        """Perform validation only"""
        return {
            'success': validation_report.result != ConfigValidationResult.CORRUPTED,
            'message': 'Validation completed',
            'issues_found': len(validation_report.issues)
        }

    def _auto_repair(self, file_path: str, validation_report: ConfigValidationReport) -> Dict[str, Any]:
        """Attempt to automatically repair configuration issues"""
        try:
            if validation_report.result == ConfigValidationResult.MISSING:
                return self._create_missing_config(file_path)

            # Repair based on format
            if validation_report.format == ConfigFormat.JSON:
                return self._auto_repair_json(file_path, validation_report)
            elif validation_report.format == ConfigFormat.YAML:
                return self._auto_repair_yaml(file_path, validation_report)
            elif validation_report.format == ConfigFormat.INI:
                return self._auto_repair_ini(file_path, validation_report)
            else:
                return {
                    'success': False,
                    'error': f'Auto repair not supported for {validation_report.format.value} format'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Auto repair failed: {e}'
            }

    def _auto_repair_json(self, file_path: str, validation_report: ConfigValidationReport) -> Dict[str, Any]:
        """Auto-repair JSON configuration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to fix common JSON syntax errors
            fixed_content = content

            # Fix trailing commas
            fixed_content = re.sub(r',\s*([}\]])', r'\1', fixed_content)

            # Fix missing quotes around keys
            fixed_content = re.sub(r'(\w+)\s*:', r'"\1":', fixed_content)

            # Fix single quotes to double quotes
            fixed_content = re.sub(r"'([^']*)'", r'"\1"', fixed_content)

            # Validate the fixed content
            try:
                json.loads(fixed_content)
                # Write the fixed content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                return {
                    'success': True,
                    'message': 'JSON syntax errors fixed'
                }
            except json.JSONDecodeError:
                # If still invalid, reset to default
                return self._reset_to_default(file_path, 'app_config')

        except Exception as e:
            return {
                'success': False,
                'error': f'JSON auto-repair failed: {e}'
            }

    def _auto_repair_yaml(self, file_path: str, validation_report: ConfigValidationReport) -> Dict[str, Any]:
        """Auto-repair YAML configuration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to fix common YAML syntax errors
            fixed_content = content

            # Fix indentation issues
            lines = fixed_content.split('\n')
            fixed_lines = []
            for line in lines:
                if line.strip() and not line.startswith(' ') and ':' in line and line.count(':') == 1:
                    # Add proper indentation for top-level keys
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            fixed_content = '\n'.join(fixed_lines)

            # Validate the fixed content
            try:
                yaml.safe_load(fixed_content)
                # Write the fixed content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                return {
                    'success': True,
                    'message': 'YAML syntax errors fixed'
                }
            except yaml.YAMLError:
                # If still invalid, reset to default
                return self._reset_to_default(file_path, 'app_config')

        except Exception as e:
            return {
                'success': False,
                'error': f'YAML auto-repair failed: {e}'
            }

    def _auto_repair_ini(self, file_path: str, validation_report: ConfigValidationReport) -> Dict[str, Any]:
        """Auto-repair INI configuration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Basic INI syntax fixes
            fixed_content = content

            # Ensure sections are properly formatted
            fixed_content = re.sub(r'^(\w+)\s*$', r'[\1]', fixed_content, flags=re.MULTILINE)

            # Write the fixed content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            return {
                'success': True,
                'message': 'INI syntax errors fixed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'INI auto-repair failed: {e}'
            }

    def _reset_to_default(self, file_path: str, template_name: str) -> Dict[str, Any]:
        """Reset configuration to default template"""
        try:
            if template_name not in self.templates:
                return {
                    'success': False,
                    'error': f'Template "{template_name}" not found'
                }

            template = self.templates[template_name]

            # Write default content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(template.content, dict):
                    if template.format == ConfigFormat.JSON:
                        json.dump(template.content, f, indent=2)
                    elif template.format == ConfigFormat.YAML:
                        yaml.dump(template.content, f, default_flow_style=False)
                    else:
                        f.write(str(template.content))
                else:
                    f.write(template.content)

            return {
                'success': True,
                'message': f'Reset to default template "{template_name}"'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Reset to default failed: {e}'
            }

    def _merge_with_default(self, file_path: str, template_name: str) -> Dict[str, Any]:
        """Merge current configuration with default template"""
        try:
            if template_name not in self.templates:
                return {
                    'success': False,
                    'error': f'Template "{template_name}" not found'
                }

            template = self.templates[template_name]

            # Read current configuration
            current_data = {}
            if os.path.exists(file_path):
                if template.format == ConfigFormat.JSON:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_data = json.load(f)
                elif template.format == ConfigFormat.YAML:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_data = yaml.safe_load(f) or {}

            # Merge with template
            if isinstance(template.content, dict):
                merged_data = {**template.content, **current_data}

                # Write merged configuration
                with open(file_path, 'w', encoding='utf-8') as f:
                    if template.format == ConfigFormat.JSON:
                        json.dump(merged_data, f, indent=2)
                    elif template.format == ConfigFormat.YAML:
                        yaml.dump(merged_data, f, default_flow_style=False)

            return {
                'success': True,
                'message': f'Merged with default template "{template_name}"'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Merge with default failed: {e}'
            }

    def _backup_and_repair(self, file_path: str, validation_report: ConfigValidationReport,
                          template_name: Optional[str]) -> Dict[str, Any]:
        """Create backup and then repair configuration"""
        # Backup is already created in the main repair method
        return self._auto_repair(file_path, validation_report)

    def _create_missing_config(self, file_path: str) -> Dict[str, Any]:
        """Create missing configuration file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return self._reset_to_default(file_path, 'app_config')
        except Exception as e:
            return {
                'success': False,
                'error': f'Create missing config failed: {e}'
            }

    def verify_repair(self, file_path: str, operation_id: str,
                     expected_schema: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Verify that a configuration repair was successful
        """
        try:
            # Find the repair operation
            operation = next((op for op in self.operations if op.operation_id == operation_id), None)
            if not operation:
                return {
                    'success': False,
                    'error': f'Repair operation {operation_id} not found'
                }

            # Validate the repaired file
            validation_report = self.validator.validate_config(file_path, schema=expected_schema)

            # Check if file hash changed
            current_hash = self.validator._calculate_file_hash(file_path)
            hash_changed = operation.original_hash != current_hash

            verification = {
                'success': validation_report.result in [ConfigValidationResult.VALID, ConfigValidationResult.WARNING],
                'file_path': file_path,
                'operation_id': operation_id,
                'validation_result': validation_report.result.value,
                'issues_remaining': len(validation_report.issues),
                'hash_changed': hash_changed,
                'backup_exists': operation.backup_path and os.path.exists(operation.backup_path),
                'repair_successful': len([issue for issue in validation_report.issues if issue.severity == 'error']) == 0
            }

            return verification

        except Exception as e:
            return {
                'success': False,
                'error': f'Verification failed: {e}'
            }

    def rollback_config(self, file_path: str, operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback configuration to a previous version
        """
        try:
            if operation_id:
                # Rollback specific operation
                operation = next((op for op in self.operations if op.operation_id == operation_id), None)
                if not operation or not operation.backup_path:
                    return {
                        'success': False,
                        'error': f'No backup found for operation {operation_id}'
                    }

                if not os.path.exists(operation.backup_path):
                    return {
                        'success': False,
                        'error': f'Backup file {operation.backup_path} does not exist'
                    }

                # Restore from backup
                shutil.copy2(operation.backup_path, file_path)
                logger.info(f"Rollback completed for {file_path} using {operation.backup_path}")

                return {
                    'success': True,
                    'message': f'Rollback completed using operation {operation_id}',
                    'backup_path': operation.backup_path
                }

            else:
                # Rollback to the most recent backup
                file_operations = [op for op in self.operations if op.file_path == file_path and op.backup_path]
                if not file_operations:
                    return {
                        'success': False,
                        'error': f'No backups found for {file_path}'
                    }

                # Sort by timestamp and get the most recent
                latest_operation = max(file_operations, key=lambda op: op.timestamp)

                if not os.path.exists(latest_operation.backup_path):
                    return {
                        'success': False,
                        'error': f'Latest backup file {latest_operation.backup_path} does not exist'
                    }

                # Restore from backup
                shutil.copy2(latest_operation.backup_path, file_path)
                logger.info(f"Rollback completed for {file_path} using {latest_operation.backup_path}")

                return {
                    'success': True,
                    'message': 'Rollback completed to latest backup',
                    'backup_path': latest_operation.backup_path,
                    'operation_id': latest_operation.operation_id
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Rollback failed: {e}'
            }

    def _log_repair_result(self, operation: ConfigRepairOperation):
        """Log the repair result"""
        if operation.status == 'completed':
            logger.info(f"Configuration repair successful:")
            logger.info(f"  File: {operation.file_path}")
            logger.info(f"  Strategy: {operation.strategy.value}")
            logger.info(f"  Issues fixed: {len(operation.issues_fixed)}")
            if operation.backup_path:
                logger.info(f"  Backup: {operation.backup_path}")
        else:
            logger.error(f"Configuration repair failed:")
            logger.error(f"  File: {operation.file_path}")
            logger.error(f"  Strategy: {operation.strategy.value}")
            logger.error(f"  Error: {operation.error_message}")

    def get_repair_history(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get repair operation history"""
        operations = self.operations

        if file_path:
            operations = [op for op in operations if op.file_path == file_path]

        return [asdict(op) for op in operations]

    def save_repair_state(self, file_path: str) -> Dict[str, Any]:
        """Save repair state to a file"""
        try:
            state_data = {
                'operations': [asdict(op) for op in self.operations],
                'templates': {name: asdict(template) for name, template in self.templates.items()},
                'backup_dir': self.backup_dir,
                'timestamp': datetime.now().isoformat()
            }

            with open(file_path, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)

            return {
                'success': True,
                'file_path': file_path,
                'operations_count': len(self.operations)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_repair_state(self, file_path: str) -> Dict[str, Any]:
        """Load repair state from a file"""
        try:
            with open(file_path, 'r') as f:
                state_data = json.load(f)

            # Restore operations
            self.operations = [
                ConfigRepairOperation(**op)
                for op in state_data.get('operations', [])
            ]

            # Restore templates
            template_data = state_data.get('templates', {})
            for name, template_dict in template_data.items():
                self.templates[name] = ConfigTemplate(**template_dict)

            # Update backup directory if specified
            if 'backup_dir' in state_data:
                self.backup_dir = state_data['backup_dir']

            return {
                'success': True,
                'operations_loaded': len(self.operations),
                'templates_loaded': len(self.templates)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }