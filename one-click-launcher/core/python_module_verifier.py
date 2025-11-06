"""
Python Module Import Verification System

This module provides comprehensive Python module verification capabilities including
syntax validation, import dependency checking, virtual environment validation,
and missing module detection with installation suggestions.
"""

import ast
import importlib.util
import subprocess
import sys
import venv
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from utils.progress_tracker import ProgressTracker
from utils.logger import get_logger
from core.operating_system_detector import OperatingSystemDetector

logger = get_logger(__name__)


class ImportErrorType(Enum):
    """Types of Python import errors"""
    SYNTAX_ERROR = "syntax_error"
    MODULE_NOT_FOUND = "module_not_found"
    IMPORT_CYCLE = "import_cycle"
    MISSING_DEPENDENCY = "missing_dependency"
    VIRTUAL_ENVIRONMENT_ISSUE = "virtual_environment_issue"
    PYTHON_VERSION_MISMATCH = "python_version_mismatch"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ImportError:
    """Python import error analysis result"""
    error_type: ImportErrorType
    severity: str  # 'critical', 'high', 'medium', 'low'
    file_path: str
    line_number: int
    error_message: str
    module_name: Optional[str] = None
    suggestion: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class ModuleImportResult:
    """Result of Python module import verification"""
    success: bool
    total_files: int
    verified_files: int
    syntax_errors: List[ImportError] = field(default_factory=list)
    import_errors: List[ImportError] = field(default_factory=list)
    missing_modules: List[str] = field(default_factory=list)
    virtual_environment_info: Dict = field(default_factory=dict)
    python_version: str = ""
    recommendations: List[str] = field(default_factory=list)


class PythonModuleVerifier:
    """
    Comprehensive Python module verification system

    Features:
    - Python syntax validation for project modules
    - Import dependency checking and cycle detection
    - Virtual environment validation and activation checks
    - Missing module detection and installation suggestions
    - Progress tracking integration
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize Python module verifier

        Args:
            timeout: Maximum time in seconds for verification operations
        """
        self.timeout = timeout
        self.os_detector = OperatingSystemDetector()
        self.progress_tracker = None

        # Common Python modules and their typical installation commands
        self.module_installation_map = {
            'numpy': 'pip install numpy',
            'pandas': 'pip install pandas',
            'requests': 'pip install requests',
            'flask': 'pip install flask',
            'django': 'pip install django',
            'pytest': 'pip install pytest',
            'fastapi': 'pip install fastapi',
            'uvicorn': 'pip install uvicorn',
            'sqlalchemy': 'pip install sqlalchemy',
            'beautifulsoup4': 'pip install beautifulsoup4',
            'selenium': 'pip install selenium',
            'matplotlib': 'pip install matplotlib',
            'seaborn': 'pip install seaborn',
            'scikit-learn': 'pip install scikit-learn',
            'tensorflow': 'pip install tensorflow',
            'torch': 'pip install torch',
            'plotly': 'pip install plotly',
            'pillow': 'pip install pillow',
            'opencv-python': 'pip install opencv-python'
        }

        # Python version requirements for common modules
        self.module_version_requirements = {
            'typing_extensions': {'min_python': '3.7'},
            'dataclasses': {'min_python': '3.7'},
            'pathlib': {'min_python': '3.4'},
            'asyncio': {'min_python': '3.4'},
            'concurrent.futures': {'min_python': '3.2'}
        }

    def set_progress_tracker(self, progress_tracker: ProgressTracker):
        """Set progress tracker for verification operations"""
        self.progress_tracker = progress_tracker

    def find_python_files(self, project_path: str) -> List[str]:
        """
        Find all Python files in the project directory

        Args:
            project_path: Path to the project directory

        Returns:
            List of Python file paths
        """
        project_path = Path(project_path)
        python_files = []

        # Find all .py files
        for py_file in project_path.rglob('*.py'):
            # Skip hidden files and __pycache__ directories
            if not any(part.startswith('.') for part in py_file.parts) and '__pycache__' not in py_file.parts:
                python_files.append(str(py_file))

        return sorted(python_files)

    def validate_syntax(self, file_path: str) -> Tuple[bool, Optional[ImportError]]:
        """
        Validate Python syntax for a single file

        Args:
            file_path: Path to the Python file

        Returns:
            Tuple of (is_valid, error_if_any)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST to check syntax
            ast.parse(content, filename=file_path)
            return True, None

        except SyntaxError as e:
            error = ImportError(
                error_type=ImportErrorType.SYNTAX_ERROR,
                severity='critical',
                file_path=file_path,
                line_number=e.lineno or 1,
                error_message=str(e),
                suggestion="Fix the syntax error in the file",
                details={
                    'offset': e.offset,
                    'text': e.text
                }
            )
            return False, error
        except Exception as e:
            error = ImportError(
                error_type=ImportErrorType.UNKNOWN_ERROR,
                severity='medium',
                file_path=file_path,
                line_number=1,
                error_message=f"Error reading file: {str(e)}",
                suggestion="Check file permissions and encoding",
                details={'original_error': str(e)}
            )
            return False, error

    def extract_imports(self, file_path: str) -> Tuple[bool, List[str], Optional[ImportError]]:
        """
        Extract all import statements from a Python file

        Args:
            file_path: Path to the Python file

        Returns:
            Tuple of (success, imported_modules, error_if_any)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)
            imported_modules = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.append(node.module.split('.')[0])

            return True, list(set(imported_modules)), None

        except SyntaxError as e:
            error = ImportError(
                error_type=ImportErrorType.SYNTAX_ERROR,
                severity='critical',
                file_path=file_path,
                line_number=e.lineno or 1,
                error_message=str(e),
                suggestion="Fix the syntax error before checking imports",
                details={'offset': e.offset, 'text': e.text}
            )
            return False, [], error
        except Exception as e:
            error = ImportError(
                error_type=ImportErrorType.UNKNOWN_ERROR,
                severity='medium',
                file_path=file_path,
                line_number=1,
                error_message=f"Error extracting imports: {str(e)}",
                suggestion="Check file format and encoding",
                details={'original_error': str(e)}
            )
            return False, [], error

    def check_module_importable(self, module_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a Python module can be imported

        Args:
            module_name: Name of the module to check

        Returns:
            Tuple of (is_importable, error_message_if_any)
        """
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return False, f"Module '{module_name}' not found"
            return True, None
        except ImportError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def detect_virtual_environment(self, project_path: str) -> Dict:
        """
        Detect and analyze virtual environment information

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with virtual environment information
        """
        project_path = Path(project_path)
        venv_info = {
            'has_virtual_env': False,
            'is_activated': False,
            'venv_path': None,
            'python_path': sys.executable,
            'site_packages': None
        }

        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_info['has_virtual_env'] = True
            venv_info['is_activated'] = True
            venv_info['venv_path'] = sys.prefix
            venv_info['site_packages'] = Path(sys.prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'

        # Look for virtual environment directories in project
        venv_dirs = ['venv', 'env', '.venv', '.env', 'environment']
        for venv_dir in venv_dirs:
            venv_path = project_path / venv_dir
            if venv_path.exists():
                venv_info['has_virtual_env'] = True
                venv_info['venv_path'] = str(venv_path)

                # Try to find the Python executable in the venv
                if os.name == 'nt':  # Windows
                    python_exe = venv_path / 'Scripts' / 'python.exe'
                else:  # Unix-like
                    python_exe = venv_path / 'bin' / 'python'

                if python_exe.exists():
                    venv_info['python_path'] = str(python_exe)
                break

        return venv_info

    def check_python_version_compatibility(self, module_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a module is compatible with current Python version

        Args:
            module_name: Name of the module to check

        Returns:
            Tuple of (is_compatible, warning_message_if_any)
        """
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        if module_name in self.module_version_requirements:
            req = self.module_version_requirements[module_name]
            min_python = req['min_python']

            if tuple(map(int, current_version.split('.'))) < tuple(map(int, min_python.split('.'))):
                return False, f"Module '{module_name}' requires Python {min_python}+, current version is {current_version}"

        return True, None

    def generate_installation_suggestion(self, module_name: str) -> str:
        """
        Generate installation suggestion for a missing module

        Args:
            module_name: Name of the missing module

        Returns:
            Installation suggestion string
        """
        # Direct mapping
        if module_name in self.module_installation_map:
            return self.module_installation_map[module_name]

        # Pattern-based suggestions
        if module_name.startswith('django.'):
            return "pip install django"
        elif module_name.startswith('flask'):
            return "pip install flask"
        elif module_name.startswith('tensorflow.'):
            return "pip install tensorflow"
        elif module_name.startswith('torch.'):
            return "pip install torch"

        # Default suggestion
        return f"pip install {module_name}"

    def detect_import_cycles(self, python_files: List[str]) -> List[ImportError]:
        """
        Detect potential import cycles in the project

        Args:
            python_files: List of Python file paths

        Returns:
            List of import cycle errors
        """
        cycles = []
        imports_map = {}  # file -> set of imported modules
        module_to_file = {}  # module -> file

        # Build import mapping
        for file_path in python_files:
            success, modules, error = self.extract_imports(file_path)
            if success:
                imports_map[file_path] = set(modules)

                # Map module names to files
                module_name = Path(file_path).stem
                module_to_file[module_name] = file_path

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(file_path, path):
            if file_path in rec_stack:
                # Found a cycle
                cycle_path = path[path.index(file_path):] + [file_path]
                cycle_str = " -> ".join([Path(f).stem for f in cycle_path])

                error = ImportError(
                    error_type=ImportErrorType.IMPORT_CYCLE,
                    severity='high',
                    file_path=file_path,
                    line_number=1,
                    error_message=f"Import cycle detected: {cycle_str}",
                    suggestion="Refactor code to break the import cycle",
                    details={'cycle_path': cycle_path}
                )
                cycles.append(error)
                return True

            if file_path in visited:
                return False

            visited.add(file_path)
            rec_stack.add(file_path)

            # Check imports
            if file_path in imports_map:
                for module in imports_map[file_path]:
                    if module in module_to_file:
                        if has_cycle(module_to_file[module], path + [file_path]):
                            return True

            rec_stack.remove(file_path)
            return False

        # Check all files for cycles
        for file_path in python_files:
            if file_path not in visited:
                has_cycle(file_path, [])

        return cycles

    async def verify_python_modules(self, project_path: str) -> ModuleImportResult:
        """
        Perform comprehensive Python module verification

        Args:
            project_path: Path to the project directory

        Returns:
            ModuleImportResult with detailed verification information
        """
        project_path = str(Path(project_path).resolve())

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current_step="finding_python_files",
                message="Finding Python files..."
            )

        # Find all Python files
        python_files = self.find_python_files(project_path)
        total_files = len(python_files)

        if total_files == 0:
            return ModuleImportResult(
                success=True,
                total_files=0,
                verified_files=0,
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                recommendations=["No Python files found in the project"]
            )

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current_step="detecting_virtual_env",
                message="Analyzing virtual environment..."
            )

        # Detect virtual environment
        venv_info = self.detect_virtual_environment(project_path)

        # Initialize result
        result = ModuleImportResult(
            success=True,
            total_files=total_files,
            verified_files=0,
            virtual_environment_info=venv_info,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current_step="validating_syntax",
                message="Validating Python syntax..."
            )

        # Step 1: Validate syntax for all files
        syntax_errors = []
        for i, file_path in enumerate(python_files):
            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    current_step="validating_syntax",
                    message=f"Validating syntax ({i+1}/{total_files}): {Path(file_path).name}"
                )

            is_valid, error = self.validate_syntax(file_path)
            if not is_valid and error:
                syntax_errors.append(error)
                result.success = False

        result.syntax_errors = syntax_errors

        # If there are critical syntax errors, we can't proceed with import checking
        critical_syntax_errors = [e for e in syntax_errors if e.severity == 'critical']
        if critical_syntax_errors:
            result.recommendations.append("Fix critical syntax errors before checking imports")
            return result

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current_step="checking_imports",
                message="Analyzing import dependencies..."
            )

        # Step 2: Check imports
        import_errors = []
        missing_modules = set()
        all_imported_modules = set()

        for i, file_path in enumerate(python_files):
            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    current_step="checking_imports",
                    message=f"Checking imports ({i+1}/{total_files}): {Path(file_path).name}"
                )

            success, modules, error = self.extract_imports(file_path)
            if success:
                all_imported_modules.update(modules)
                result.verified_files += 1

                # Check each module
                for module in modules:
                    if module == '__future__':
                        continue  # Skip __future__ imports

                    # Skip relative imports and standard library modules (basic check)
                    if module.startswith('.') or module in ['os', 'sys', 'json', 'pathlib', 'datetime', 'math', 'random']:
                        continue

                    is_importable, error_msg = self.check_module_importable(module)
                    if not is_importable:
                        missing_modules.add(module)

                        error = ImportError(
                            error_type=ImportErrorType.MODULE_NOT_FOUND,
                            severity='high',
                            file_path=file_path,
                            line_number=1,  # Could be improved with AST line numbers
                            error_message=f"Cannot import module '{module}': {error_msg}",
                            suggestion=self.generate_installation_suggestion(module),
                            module_name=module,
                            details={'error_message': error_msg}
                        )
                        import_errors.append(error)
                        result.success = False

                    # Check Python version compatibility
                    is_compatible, warning = self.check_python_version_compatibility(module)
                    if not is_compatible:
                        error = ImportError(
                            error_type=ImportErrorType.PYTHON_VERSION_MISMATCH,
                            severity='medium',
                            file_path=file_path,
                            line_number=1,
                            error_message=warning,
                            suggestion="Upgrade Python version or use an older version of the module",
                            module_name=module,
                            details={'current_python': result.python_version}
                        )
                        import_errors.append(error)
            elif error:
                import_errors.append(error)
                result.success = False

        result.import_errors = import_errors
        result.missing_modules = list(missing_modules)

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current_step="detecting_cycles",
                message="Detecting import cycles..."
            )

        # Step 3: Detect import cycles
        cycle_errors = self.detect_import_cycles(python_files)
        result.import_errors.extend(cycle_errors)
        if cycle_errors:
            result.success = False

        # Step 4: Generate recommendations
        if not venv_info['has_virtual_env']:
            result.recommendations.append("Consider creating a virtual environment for dependency isolation")

        if not venv_info['is_activated'] and venv_info['has_virtual_env']:
            result.recommendations.append(f"Activate the virtual environment: {venv_info['venv_path']}")

        if missing_modules:
            install_commands = list(set(self.generate_installation_suggestion(module) for module in missing_modules))
            result.recommendations.append(f"Install missing modules: {'; '.join(install_commands)}")

        if not import_errors and not syntax_errors:
            result.recommendations.append("All Python modules verified successfully")

        return result

    def get_project_summary(self, result: ModuleImportResult) -> Dict:
        """
        Generate a summary of the verification results

        Args:
            result: ModuleImportResult from verification

        Returns:
            Dictionary with summary information
        """
        return {
            'status': 'PASS' if result.success else 'FAIL',
            'total_files': result.total_files,
            'verified_files': result.verified_files,
            'syntax_errors': len(result.syntax_errors),
            'import_errors': len(result.import_errors),
            'missing_modules_count': len(result.missing_modules),
            'virtual_environment_active': result.virtual_environment_info.get('is_activated', False),
            'python_version': result.python_version,
            'recommendations_count': len(result.recommendations),
            'critical_issues': len([e for e in result.syntax_errors + result.import_errors if e.severity == 'critical'])
        }