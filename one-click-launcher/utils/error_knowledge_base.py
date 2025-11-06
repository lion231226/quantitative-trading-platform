"""
Error Knowledge Base Module

This module provides a comprehensive knowledge base of error solutions,
troubleshooting guides, and best practices for common issues encountered
during the one-click launch process.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories"""
    PORT_CONFLICT = "port_conflict"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_CONNECTIVITY = "network_connectivity"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    ENVIRONMENT_ERROR = "environment_error"


class Platform(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNIVERSAL = "universal"


@dataclass
class SolutionStep:
    """Single step in a solution"""
    step_number: int
    description: str
    command: Optional[str] = None
    platform: Platform = Platform.UNIVERSAL
    requires_admin: bool = False
    expected_result: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ErrorSolution:
    """Complete solution for an error"""
    error_code: str
    title: str
    description: str
    category: ErrorCategory
    severity: str
    solution_steps: List[SolutionStep]
    alternative_solutions: List[str]
    prevention_tips: List[str]
    related_errors: List[str]
    platforms: List[Platform]


class ErrorKnowledgeBase:
    """
    Comprehensive error knowledge base providing solutions and guidance
    for common errors encountered during application launch and operation.
    """

    def __init__(self):
        """Initialize the error knowledge base"""
        self.logger = get_logger(self.__class__.__name__)
        self.solutions = self._load_solutions()

    def _load_solutions(self) -> Dict[str, ErrorSolution]:
        """Load error solutions from the knowledge base"""
        solutions = {}

        # Port Conflict Solutions
        solutions["PORT_3000_CONFLICT"] = ErrorSolution(
            error_code="PORT_3000_CONFLICT",
            title="Port 3000 Conflict - Frontend Development Server",
            description="Port 3000 is commonly used by frontend development servers (React, Vue, Angular). The port is occupied by another process.",
            category=ErrorCategory.PORT_CONFLICT,
            severity="medium",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Identify the process using port 3000",
                    command="netstat -tulpn | grep :3000",
                    platform=Platform.LINUX
                ),
                SolutionStep(
                    step_number=1,
                    description="Identify the process using port 3000",
                    command="netstat -ano | findstr :3000",
                    platform=Platform.WINDOWS
                ),
                SolutionStep(
                    step_number=1,
                    description="Identify the process using port 3000",
                    command="lsof -i :3000",
                    platform=Platform.MACOS
                ),
                SolutionStep(
                    step_number=2,
                    description="Stop the conflicting process if it's another development server",
                    command="kill -9 <PID>",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    notes="Replace <PID> with the actual process ID from step 1"
                ),
                SolutionStep(
                    step_number=3,
                    description="Alternative: Use a different port for your application",
                    command="PORT=3001 npm start",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    expected_result="Application starts on port 3001"
                )
            ],
            alternative_solutions=[
                "Use port 3001, 3002, or any available port in the 3000-3100 range",
                "Stop other development servers running in the background",
                "Restart your computer to clear stuck processes"
            ],
            prevention_tips=[
                "Always stop development servers when not in use",
                "Use different ports for different projects",
                "Check port availability before starting new servers"
            ],
            related_errors=["PORT_8000_CONFLICT", "PORT_8080_CONFLICT"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX, Platform.UNIVERSAL]
        )

        solutions["PORT_8000_CONFLICT"] = ErrorSolution(
            error_code="PORT_8000_CONFLICT",
            title="Port 8000 Conflict - Backend API Server",
            description="Port 8000 is commonly used by backend API servers (Django, Flask, FastAPI). The port is occupied by another process.",
            category=ErrorCategory.PORT_CONFLICT,
            severity="medium",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Find process using port 8000",
                    command="netstat -tulpn | grep :8000",
                    platform=Platform.LINUX
                ),
                SolutionStep(
                    step_number=1,
                    description="Find process using port 8000",
                    command="netstat -ano | findstr :8000",
                    platform=Platform.WINDOWS
                ),
                SolutionStep(
                    step_number=2,
                    description="Stop the conflicting Python process",
                    command="pkill -f 'python.*8000'",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Alternative: Start your server on a different port",
                    command="python manage.py runserver 8001",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use port 8001, 8002, or any available port in the 8000-8100 range",
                "Configure your application to use dynamic port allocation",
                "Use a process manager to manage multiple services"
            ],
            prevention_tips=[
                "Use different ports for different API services",
                "Document port assignments for your development team",
                "Use environment configuration files to manage ports"
            ],
            related_errors=["PORT_3000_CONFLICT", "PORT_5432_CONFLICT"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        solutions["PORT_5432_CONFLICT"] = ErrorSolution(
            error_code="PORT_5432_CONFLICT",
            title="Port 5432 Conflict - PostgreSQL Database",
            description="Port 5432 is the default port for PostgreSQL database server. The port is occupied by another PostgreSQL instance.",
            category=ErrorCategory.PORT_CONFLICT,
            severity="high",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Check PostgreSQL service status",
                    command="systemctl status postgresql",
                    platform=Platform.LINUX,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=1,
                    description="Check PostgreSQL service status",
                    command="brew services list | grep postgresql",
                    platform=Platform.MACOS,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=1,
                    description="Check PostgreSQL service status",
                    command="Get-Service postgresql*",
                    platform=Platform.WINDOWS,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=2,
                    description="Stop existing PostgreSQL service if not needed",
                    command="systemctl stop postgresql",
                    platform=Platform.LINUX,
                    requires_admin=True
                ),
                SolutionStep(
                    step_number=2,
                    description="Stop existing PostgreSQL service if not needed",
                    command="brew services stop postgresql",
                    platform=Platform.MACOS,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Alternative: Configure new PostgreSQL instance to use different port",
                    command="postgresql -c port=5433",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use port 5433 for the second PostgreSQL instance",
                "Use Docker containers for database isolation",
                "Connect to existing PostgreSQL instance instead of starting new one"
            ],
            prevention_tips=[
                "Use Docker for database services to avoid port conflicts",
                "Document database port configurations",
                "Use database connection strings with explicit port numbers"
            ],
            related_errors=["PORT_6379_CONFLICT", "DATABASE_CONNECTION_ERROR"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        solutions["PORT_6379_CONFLICT"] = ErrorSolution(
            error_code="PORT_6379_CONFLICT",
            title="Port 6379 Conflict - Redis Cache Server",
            description="Port 6379 is the default port for Redis cache server. The port is occupied by another Redis instance.",
            category=ErrorCategory.PORT_CONFLICT,
            severity="medium",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Check Redis process status",
                    command="ps aux | grep redis",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=2,
                    description="Stop existing Redis service",
                    command="redis-cli shutdown",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Alternative: Start Redis on different port",
                    command="redis-server --port 6380",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use port 6380 for the second Redis instance",
                "Use Redis configuration file to specify port",
                "Connect to existing Redis instance if suitable"
            ],
            prevention_tips=[
                "Use different Redis ports for different environments",
                "Use Redis configuration files for port management",
                "Consider using Redis clustering for production"
            ],
            related_errors=["PORT_5432_CONFLICT", "CACHE_CONNECTION_ERROR"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        # Permission Error Solutions
        solutions["PERMISSION_FILE_ACCESS"] = ErrorSolution(
            error_code="PERMISSION_FILE_ACCESS",
            title="File Access Permission Denied",
            description="Application cannot access required files or directories due to insufficient permissions.",
            category=ErrorCategory.PERMISSION_DENIED,
            severity="high",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Check current user permissions",
                    command="ls -la /path/to/file",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    notes="Replace /path/to/file with actual file path"
                ),
                SolutionStep(
                    step_number=2,
                    description="Grant read permissions to current user",
                    command="chmod +r /path/to/file",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Grant write permissions if needed",
                    command="chmod +w /path/to/file",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=4,
                    description="Alternative: Run application with elevated privileges",
                    command="sudo ./application",
                    platform=Platform.UNIVERSAL,
                    requires_admin=True,
                    notes="Use this option only if you trust the application"
                )
            ],
            alternative_solutions=[
                "Change file ownership to current user: chown $USER:$USER /path/to/file",
                "Run application from user's home directory",
                "Create files in a directory with write permissions"
            ],
            prevention_tips=[
                "Install applications in user's home directory when possible",
                "Use proper file permissions during installation",
                "Avoid running applications as root/sa unless necessary"
            ],
            related_errors=["PERMISSION_INSTALLATION", "PERMISSION_SERVICE_START"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        solutions["PERMISSION_INSTALLATION"] = ErrorSolution(
            error_code="PERMISSION_INSTALLATION",
            title="Installation Permission Denied",
            description="Application cannot be installed due to insufficient system permissions.",
            category=ErrorCategory.PERMISSION_DENIED,
            severity="high",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Run installer as administrator (Windows)",
                    command="Right-click installer → Run as administrator",
                    platform=Platform.WINDOWS,
                    requires_admin=True
                ),
                SolutionStep(
                    step_number=1,
                    description="Run installer with sudo (macOS/Linux)",
                    command="sudo ./installer.sh",
                    platform=Platform.UNIVERSAL,
                    requires_admin=True
                ),
                SolutionStep(
                    step_number=2,
                    description="Alternative: Install in user directory",
                    command="mkdir -p ~/local/bin && ./installer --prefix=~/local",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Add user installation directory to PATH",
                    command="echo 'export PATH=$HOME/local/bin:$PATH' >> ~/.bashrc",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use package managers like npm, pip, or brew which handle permissions",
                "Use containerized applications (Docker)",
                "Use portable versions that don't require installation"
            ],
            prevention_tips=[
                "Use user-level package managers when possible",
                "Configure environment variables for user installations",
                "Document installation requirements in project documentation"
            ],
            related_errors=["PERMISSION_FILE_ACCESS", "DEPENDENCY_INSTALL_FAILED"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        # Network Error Solutions
        solutions["NETWORK_NO_INTERNET"] = ErrorSolution(
            error_code="NETWORK_NO_INTERNET",
            title="No Internet Connection",
            description="Application cannot connect to the internet. Check network connectivity and proxy settings.",
            category=ErrorCategory.NETWORK_CONNECTIVITY,
            severity="high",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Test basic internet connectivity",
                    command="ping 8.8.8.8",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    expected_result="Successful ping responses"
                ),
                SolutionStep(
                    step_number=2,
                    description="Test DNS resolution",
                    command="nslookup google.com",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    expected_result="DNS resolution successful"
                ),
                SolutionStep(
                    step_number=3,
                    description="Check network adapter status",
                    command="ipconfig /all",
                    platform=Platform.WINDOWS,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Check network adapter status",
                    command="ifconfig -a",
                    platform=Platform.MACOS,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Check network adapter status",
                    command="ip addr show",
                    platform=Platform.LINUX,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=4,
                    description="Restart network interface",
                    command="sudo systemctl restart NetworkManager",
                    platform=Platform.LINUX,
                    requires_admin=True
                )
            ],
            alternative_solutions=[
                "Connect to different network or WiFi",
                "Disable and re-enable network adapter",
                "Restart computer and router",
                "Check firewall settings blocking internet access"
            ],
            prevention_tips=[
                "Monitor network connectivity during development",
                "Use offline development modes when available",
                "Configure proxy settings for corporate networks"
            ],
            related_errors=["NETWORK_PROXY_ERROR", "NETWORK_FIREWALL_BLOCKED"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        solutions["NETWORK_PROXY_ERROR"] = ErrorSolution(
            error_code="NETWORK_PROXY_ERROR",
            title="Proxy Configuration Error",
            description="Application cannot connect through proxy server. Proxy settings may be incorrect or proxy server is unavailable.",
            category=ErrorCategory.NETWORK_CONNECTIVITY,
            severity="medium",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Check current proxy environment variables",
                    command="echo $HTTP_PROXY $HTTPS_PROXY $NO_PROXY",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=2,
                    description="Test proxy connectivity",
                    command="curl -I --proxy $HTTP_PROXY https://www.google.com",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Clear proxy settings temporarily",
                    command="unset HTTP_PROXY HTTPS_PROXY NO_PROXY",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=4,
                    description="Set correct proxy configuration",
                    command="export HTTP_PROXY=http://proxy.company.com:8080",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    notes="Replace with actual proxy URL and port"
                )
            ],
            alternative_solutions=[
                "Use direct internet connection if possible",
                "Configure application-specific proxy settings",
                "Contact IT support for correct proxy configuration",
                "Use VPN if required by network policy"
            ],
            prevention_tips=[
                "Document proxy configuration for development team",
                "Use configuration files for proxy settings",
                "Test proxy connectivity during setup"
            ],
            related_errors=["NETWORK_NO_INTERNET", "NETWORK_FIREWALL_BLOCKED"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        # Dependency Error Solutions
        solutions["DEPENDENCY_VERSION_CONFLICT"] = ErrorSolution(
            error_code="DEPENDENCY_VERSION_CONFLICT",
            title="Dependency Version Conflict",
            description="Required dependency version conflicts with installed version. Different projects require different versions of the same package.",
            category=ErrorCategory.DEPENDENCY_CONFLICT,
            severity="medium",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Check current dependency version",
                    command="npm list package-name",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=2,
                    description="Check required version in package.json",
                    command="grep package-name package.json",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Install specific version required",
                    command="npm install package-name@version",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False,
                    notes="Replace 'version' with the required version number"
                ),
                SolutionStep(
                    step_number=4,
                    description="Alternative: Use version manager",
                    command="nvm use && npm install",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use virtual environments for Python dependencies",
                "Use Docker containers for dependency isolation",
                "Use npm/yarn workspaces for monorepo management",
                "Update package.json to compatible version ranges"
            ],
            prevention_tips=[
                "Use semantic versioning in package.json",
                "Document dependency requirements in README",
                "Use dependency management tools like npm-check-updates",
                "Regularly update dependencies to compatible versions"
            ],
            related_errors=["DEPENDENCY_INSTALL_FAILED", "DEPENDENCY_MISSING"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        solutions["DEPENDENCY_MISSING"] = ErrorSolution(
            error_code="DEPENDENCY_MISSING",
            title="Missing Dependency",
            description="Required dependency is not installed. Install missing package to continue.",
            category=ErrorCategory.DEPENDENCY_CONFLICT,
            severity="high",
            solution_steps=[
                SolutionStep(
                    step_number=1,
                    description="Install missing dependency with npm",
                    command="npm install package-name",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=2,
                    description="Install missing dependency with pip",
                    command="pip install package-name",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=3,
                    description="Install all dependencies from requirements file",
                    command="npm install",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                ),
                SolutionStep(
                    step_number=4,
                    description="Install all dependencies from requirements file",
                    command="pip install -r requirements.txt",
                    platform=Platform.UNIVERSAL,
                    requires_admin=False
                )
            ],
            alternative_solutions=[
                "Use yarn instead of npm: yarn install",
                "Use pipenv for Python dependencies: pipenv install",
                "Use conda for scientific Python packages: conda install package-name",
                "Install globally if required: npm install -g package-name"
            ],
            prevention_tips=[
                "Always include package.json or requirements.txt in version control",
                "Use dependency locking files (package-lock.json, yarn.lock)",
                "Document installation steps in project README",
                "Use dependency check tools before deployment"
            ],
            related_errors=["DEPENDENCY_VERSION_CONFLICT", "DEPENDENCY_INSTALL_FAILED"],
            platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        )

        return solutions

    def get_solution(self, error_code: str) -> Optional[ErrorSolution]:
        """
        Get solution for a specific error code

        Args:
            error_code: Error code to find solution for

        Returns:
            ErrorSolution if found, None otherwise
        """
        return self.solutions.get(error_code)

    def find_solutions_by_category(self, category: ErrorCategory) -> List[ErrorSolution]:
        """
        Find all solutions for a specific error category

        Args:
            category: Error category to search for

        Returns:
            List of ErrorSolution objects
        """
        return [
            solution for solution in self.solutions.values()
            if solution.category == category
        ]

    def find_solutions_by_platform(self, platform: Platform) -> List[ErrorSolution]:
        """
        Find all solutions for a specific platform

        Args:
            platform: Platform to search for

        Returns:
            List of ErrorSolution objects
        """
        return [
            solution for solution in self.solutions.values()
            if platform in solution.platforms or Platform.UNIVERSAL in solution.platforms
        ]

    def search_solutions(self, query: str) -> List[ErrorSolution]:
        """
        Search solutions by keyword

        Args:
            query: Search query

        Returns:
            List of matching ErrorSolution objects
        """
        query_lower = query.lower()
        matching_solutions = []

        for solution in self.solutions.values():
            # Search in title, description, and error code
            if (query_lower in solution.title.lower() or
                query_lower in solution.description.lower() or
                query_lower in solution.error_code.lower()):
                matching_solutions.append(solution)

        return matching_solutions

    def generate_user_guide(self, error_codes: List[str], platform: Platform = None) -> str:
        """
        Generate a user-friendly guide for resolving multiple errors

        Args:
            error_codes: List of error codes to include in guide
            platform: Target platform for platform-specific guidance

        Returns:
            Formatted user guide string
        """
        guide_lines = [
            "=" * 80,
            "ERROR RESOLUTION GUIDE",
            "=" * 80,
            "This guide provides step-by-step instructions to resolve common errors.",
            "",
            "TABLE OF CONTENTS:",
            "-" * 40
        ]

        # Add table of contents
        for i, error_code in enumerate(error_codes, 1):
            solution = self.get_solution(error_code)
            if solution:
                guide_lines.append(f"{i}. {solution.title}")

        guide_lines.extend(["", "DETAILED SOLUTIONS:", "-" * 40])

        # Add detailed solutions
        for i, error_code in enumerate(error_codes, 1):
            solution = self.get_solution(error_code)
            if not solution:
                continue

            # Filter steps by platform if specified
            relevant_steps = solution.solution_steps
            if platform and platform != Platform.UNIVERSAL:
                relevant_steps = [
                    step for step in solution.solution_steps
                    if step.platform in [platform, Platform.UNIVERSAL]
                ]

            guide_lines.extend([
                f"",
                f"{i}. {solution.title}",
                f"   Error Code: {solution.error_code}",
                f"   Severity: {solution.severity.upper()}",
                f"   Description: {solution.description}",
                "",
                "   SOLUTION STEPS:"
            ])

            for step in relevant_steps:
                step_text = f"   Step {step.step_number}: {step.description}"
                if step.command:
                    step_text += f"\n     Command: {step.command}"
                if step.requires_admin:
                    step_text += " (Requires Administrator Privileges)"
                if step.expected_result:
                    step_text += f"\n     Expected Result: {step.expected_result}"
                if step.notes:
                    step_text += f"\n     Note: {step.notes}"

                guide_lines.append(step_text)

            # Add alternative solutions
            if solution.alternative_solutions:
                guide_lines.extend([
                    "",
                    "   ALTERNATIVE SOLUTIONS:"
                ])
                for alt_solution in solution.alternative_solutions:
                    guide_lines.append(f"   • {alt_solution}")

            # Add prevention tips
            if solution.prevention_tips:
                guide_lines.extend([
                    "",
                    "   PREVENTION TIPS:"
                ])
                for tip in solution.prevention_tips:
                    guide_lines.append(f"   • {tip}")

            guide_lines.append("")

        # Add general troubleshooting section
        guide_lines.extend([
            "GENERAL TROUBLESHOOTING:",
            "-" * 40,
            "• Always read error messages carefully - they contain important clues",
            "• Check application logs for detailed error information",
            "• Try restarting the application or computer",
            "• Ensure all dependencies are properly installed",
            "• Verify network connectivity for network-dependent features",
            "• Check file permissions for file-related errors",
            "• Use the latest version of applications and dependencies",
            "• Consult official documentation for specific error codes",
            "",
            "CONTACT SUPPORT:",
            "-" * 40,
            "If you continue to experience issues after trying these solutions:",
            "• Check the project GitHub repository for known issues",
            "• Search online forums with the specific error message",
            "• Contact the development team with error details and system information",
            "",
            "=" * 80
        ])

        return "\n".join(guide_lines)

    def export_knowledge_base(self, file_path: str) -> bool:
        """
        Export knowledge base to JSON file

        Args:
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "version": "1.0",
                "generated_at": "2025-11-05",
                "solutions": {
                    code: asdict(solution) for code, solution in self.solutions.items()
                }
            }

            # Convert enums to strings for JSON serialization
            for solution_data in export_data["solutions"].values():
                solution_data["category"] = solution_data["category"].value
                solution_data["platforms"] = [p.value for p in solution_data["platforms"]]
                for step in solution_data["solution_steps"]:
                    step["platform"] = step["platform"].value

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Knowledge base exported to: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export knowledge base: {e}")
            return False

    def get_quick_fixes(self, error_codes: List[str]) -> List[str]:
        """
        Get quick fixes for multiple errors (first step of each solution)

        Args:
            error_codes: List of error codes

        Returns:
            List of quick fix suggestions
        """
        quick_fixes = []

        for error_code in error_codes:
            solution = self.get_solution(error_code)
            if solution and solution.solution_steps:
                first_step = solution.solution_steps[0]
                quick_fix = f"For {solution.title}: {first_step.description}"
                if first_step.command:
                    quick_fix += f" (Command: {first_step.command})"
                quick_fixes.append(quick_fix)

        return quick_fixes