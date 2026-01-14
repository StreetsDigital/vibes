"""
Quality Gates for Vibecoding Stack
===================================

Integrates testing, verification, and quality checks into the autocoder workflow.

Provides:
1. Pre-implementation checks (requirements, assumptions)
2. Post-implementation verification (tests, lint, types)
3. Dual-agent verification (second Claude reviews first)
4. Quality gate enforcement (block merge if checks fail)

Usage:
    from quality_gates import QualityGateRunner, VerificationAgent
    
    # Run all quality checks
    runner = QualityGateRunner(project_dir)
    result = runner.run_all_checks()
    
    # Spawn verification agent
    verifier = VerificationAgent(project_dir)
    verification = verifier.verify_feature(feature, code_changes)
"""

import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# CONFIGURATION
# =============================================================================

class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class CheckResult:
    """Result of a single quality check."""
    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms
        }


@dataclass
class QualityGateConfig:
    """Configuration for quality gates."""
    
    # Test requirements
    require_tests: bool = True
    min_coverage_percent: float = 70.0
    
    # Lint requirements
    require_lint_pass: bool = True
    lint_command: str = "npm run lint"
    
    # Type checking
    require_type_check: bool = True
    type_check_command: str = "npm run typecheck"
    
    # Formatting
    require_format: bool = True
    format_command: str = "npm run format:check"
    
    # Security
    require_security_scan: bool = True
    security_command: str = "npm audit --audit-level=high"
    
    # Build
    require_build: bool = True
    build_command: str = "npm run build"
    
    # Custom checks
    custom_checks: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_file(cls, path: Path) -> "QualityGateConfig":
        """Load config from JSON file."""
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def to_file(self, path: Path) -> None:
        """Save config to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.__dict__, f, indent=2)


# =============================================================================
# QUALITY GATE RUNNER
# =============================================================================

class QualityGateRunner:
    """
    Runs quality gate checks on the codebase.
    
    Checks include:
    - Tests (unit, integration)
    - Linting
    - Type checking
    - Formatting
    - Security scanning
    - Build verification
    """
    
    def __init__(
        self, 
        project_dir: Path, 
        config: Optional[QualityGateConfig] = None
    ):
        self.project_dir = Path(project_dir)
        self.config = config or self._detect_config()
        self._results: List[CheckResult] = []
        
    def _detect_config(self) -> QualityGateConfig:
        """Auto-detect project configuration."""
        config = QualityGateConfig()
        
        # Check for package.json
        pkg_json = self.project_dir / "package.json"
        if pkg_json.exists():
            with open(pkg_json) as f:
                pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                
                # Detect available commands
                if "lint" in scripts:
                    config.lint_command = "npm run lint"
                elif "eslint" in scripts:
                    config.lint_command = "npm run eslint"
                    
                if "typecheck" in scripts:
                    config.type_check_command = "npm run typecheck"
                elif "tsc" in scripts:
                    config.type_check_command = "npm run tsc"
                else:
                    # Check for TypeScript
                    if (self.project_dir / "tsconfig.json").exists():
                        config.type_check_command = "npx tsc --noEmit"
                    else:
                        config.require_type_check = False
                        
                if "format:check" in scripts:
                    config.format_command = "npm run format:check"
                elif "prettier:check" in scripts:
                    config.format_command = "npm run prettier:check"
                else:
                    config.format_command = "npx prettier --check ."
                    
        # Check for Python project
        elif (self.project_dir / "pyproject.toml").exists() or \
             (self.project_dir / "setup.py").exists():
            config.lint_command = "ruff check . || pylint **/*.py"
            config.type_check_command = "mypy ."
            config.format_command = "black --check ."
            config.security_command = "bandit -r . || safety check"
            config.build_command = "python -m build || pip install -e ."
            
        # Check for Go project
        elif (self.project_dir / "go.mod").exists():
            config.lint_command = "golangci-lint run"
            config.type_check_command = "go vet ./..."
            config.format_command = "gofmt -l ."
            config.security_command = "gosec ./..."
            config.build_command = "go build ./..."
            
        return config
    
    def _run_command(
        self, 
        command: str, 
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        """Run a shell command and return (exit_code, stdout, stderr)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)
    
    def check_tests(self) -> CheckResult:
        """Run test suite and check coverage."""
        import time
        start = time.time()
        
        # Detect test command
        pkg_json = self.project_dir / "package.json"
        if pkg_json.exists():
            test_cmd = "npm test -- --coverage --passWithNoTests"
        elif (self.project_dir / "pytest.ini").exists() or \
             (self.project_dir / "pyproject.toml").exists():
            test_cmd = "pytest --cov=. --cov-report=term-missing"
        elif (self.project_dir / "go.mod").exists():
            test_cmd = "go test -cover ./..."
        else:
            test_cmd = "npm test || pytest || go test ./..."
        
        exit_code, stdout, stderr = self._run_command(test_cmd)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            # Try to extract coverage
            coverage_match = re.search(
                r'(?:coverage|Coverage|COVERAGE)[:\s]+(\d+(?:\.\d+)?)\s*%',
                stdout + stderr
            )
            coverage = float(coverage_match.group(1)) if coverage_match else None
            
            if coverage is not None:
                if coverage >= self.config.min_coverage_percent:
                    return CheckResult(
                        name="tests",
                        status=CheckStatus.PASSED,
                        message=f"Tests passed with {coverage:.1f}% coverage",
                        details=stdout,
                        duration_ms=duration
                    )
                else:
                    return CheckResult(
                        name="tests",
                        status=CheckStatus.WARNING,
                        message=f"Tests passed but coverage ({coverage:.1f}%) below threshold ({self.config.min_coverage_percent}%)",
                        details=stdout,
                        duration_ms=duration
                    )
            else:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.PASSED,
                    message="Tests passed (coverage not reported)",
                    details=stdout,
                    duration_ms=duration
                )
        else:
            return CheckResult(
                name="tests",
                status=CheckStatus.FAILED,
                message="Tests failed",
                details=stderr or stdout,
                duration_ms=duration
            )
    
    def check_lint(self) -> CheckResult:
        """Run linter."""
        import time
        start = time.time()
        
        exit_code, stdout, stderr = self._run_command(self.config.lint_command)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            return CheckResult(
                name="lint",
                status=CheckStatus.PASSED,
                message="Linting passed",
                duration_ms=duration
            )
        else:
            # Count issues
            issues = len(re.findall(r'(error|warning)', stdout + stderr, re.I))
            return CheckResult(
                name="lint",
                status=CheckStatus.FAILED,
                message=f"Linting failed with {issues} issues",
                details=stdout + stderr,
                duration_ms=duration
            )
    
    def check_types(self) -> CheckResult:
        """Run type checker."""
        import time
        start = time.time()
        
        if not self.config.require_type_check:
            return CheckResult(
                name="types",
                status=CheckStatus.SKIPPED,
                message="Type checking not configured"
            )
        
        exit_code, stdout, stderr = self._run_command(self.config.type_check_command)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            return CheckResult(
                name="types",
                status=CheckStatus.PASSED,
                message="Type checking passed",
                duration_ms=duration
            )
        else:
            errors = len(re.findall(r'error', stdout + stderr, re.I))
            return CheckResult(
                name="types",
                status=CheckStatus.FAILED,
                message=f"Type checking failed with {errors} errors",
                details=stdout + stderr,
                duration_ms=duration
            )
    
    def check_format(self) -> CheckResult:
        """Check code formatting."""
        import time
        start = time.time()
        
        exit_code, stdout, stderr = self._run_command(self.config.format_command)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            return CheckResult(
                name="format",
                status=CheckStatus.PASSED,
                message="Formatting check passed",
                duration_ms=duration
            )
        else:
            return CheckResult(
                name="format",
                status=CheckStatus.FAILED,
                message="Formatting issues found",
                details=stdout + stderr,
                duration_ms=duration
            )
    
    def check_security(self) -> CheckResult:
        """Run security scan."""
        import time
        start = time.time()
        
        exit_code, stdout, stderr = self._run_command(self.config.security_command)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            return CheckResult(
                name="security",
                status=CheckStatus.PASSED,
                message="Security scan passed",
                duration_ms=duration
            )
        else:
            # Check for high/critical vulnerabilities
            high_critical = len(re.findall(
                r'(high|critical)', 
                stdout + stderr, 
                re.I
            ))
            if high_critical > 0:
                return CheckResult(
                    name="security",
                    status=CheckStatus.FAILED,
                    message=f"Found {high_critical} high/critical vulnerabilities",
                    details=stdout + stderr,
                    duration_ms=duration
                )
            else:
                return CheckResult(
                    name="security",
                    status=CheckStatus.WARNING,
                    message="Security scan found issues (non-critical)",
                    details=stdout + stderr,
                    duration_ms=duration
                )
    
    def check_build(self) -> CheckResult:
        """Verify build succeeds."""
        import time
        start = time.time()
        
        exit_code, stdout, stderr = self._run_command(self.config.build_command)
        duration = int((time.time() - start) * 1000)
        
        if exit_code == 0:
            return CheckResult(
                name="build",
                status=CheckStatus.PASSED,
                message="Build succeeded",
                duration_ms=duration
            )
        else:
            return CheckResult(
                name="build",
                status=CheckStatus.FAILED,
                message="Build failed",
                details=stderr or stdout,
                duration_ms=duration
            )
    
    def run_all_checks(
        self, 
        checks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run all quality checks.
        
        Args:
            checks: Optional list of specific checks to run.
                    Default runs all: tests, lint, types, format, security, build
        
        Returns:
            Dict with overall status and individual check results
        """
        all_checks = {
            "tests": self.check_tests,
            "lint": self.check_lint,
            "types": self.check_types,
            "format": self.check_format,
            "security": self.check_security,
            "build": self.check_build
        }
        
        checks_to_run = checks or list(all_checks.keys())
        results = []
        
        for check_name in checks_to_run:
            if check_name in all_checks:
                result = all_checks[check_name]()
                results.append(result)
                self._results.append(result)
        
        # Determine overall status
        failed = [r for r in results if r.status == CheckStatus.FAILED]
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        
        if failed:
            overall_status = "failed"
            overall_message = f"{len(failed)} check(s) failed"
        elif warnings:
            overall_status = "warning"
            overall_message = f"Passed with {len(warnings)} warning(s)"
        else:
            overall_status = "passed"
            overall_message = "All checks passed"
        
        return {
            "status": overall_status,
            "message": overall_message,
            "timestamp": datetime.now().isoformat(),
            "checks": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": len([r for r in results if r.status == CheckStatus.PASSED]),
                "failed": len(failed),
                "warnings": len(warnings),
                "skipped": len([r for r in results if r.status == CheckStatus.SKIPPED])
            }
        }
    
    def run_quick_checks(self) -> Dict[str, Any]:
        """Run fast checks only (lint, types, format)."""
        return self.run_all_checks(["lint", "types", "format"])
    
    def run_full_checks(self) -> Dict[str, Any]:
        """Run all checks including slow ones."""
        return self.run_all_checks()


# =============================================================================
# VERIFICATION AGENT
# =============================================================================

class VerificationAgent:
    """
    Spawns a second Claude to verify code produced by the first.
    
    This implements Boris's "most important thing" — giving Claude
    a way to verify its own work.
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.quality_runner = QualityGateRunner(project_dir)
        
    def build_verification_prompt(
        self,
        feature: Dict[str, Any],
        code_changes: str,
        test_results: Optional[Dict] = None
    ) -> str:
        """Build prompt for verification agent."""
        
        prompt_parts = [
            "=" * 60,
            "VERIFICATION TASK",
            "=" * 60,
            "",
            "You are a code reviewer. Your job is to verify that the",
            "implementation below correctly implements the feature spec.",
            "",
            "## FEATURE SPECIFICATION",
            f"**Name:** {feature.get('name', 'Unknown')}",
            f"**Description:** {feature.get('description', 'No description')}",
            "",
            "**Test Cases to Verify:**"
        ]
        
        for i, tc in enumerate(feature.get('test_cases', []), 1):
            if isinstance(tc, dict):
                prompt_parts.append(f"  {i}. {tc.get('name', tc)}")
            else:
                prompt_parts.append(f"  {i}. {tc}")
        
        prompt_parts.extend([
            "",
            "## CODE CHANGES",
            "```",
            code_changes[:10000],  # Limit size
            "```",
            ""
        ])
        
        if test_results:
            prompt_parts.extend([
                "## AUTOMATED TEST RESULTS",
                f"Status: {test_results.get('status', 'unknown')}",
                f"Message: {test_results.get('message', 'No message')}",
                ""
            ])
        
        prompt_parts.extend([
            "## YOUR VERIFICATION CHECKLIST",
            "",
            "1. **Correctness**: Does the code implement all requirements?",
            "2. **Edge Cases**: Are edge cases handled?",
            "3. **Error Handling**: Is error handling complete?",
            "4. **Security**: Any security issues? (injection, auth, etc.)",
            "5. **Performance**: Any obvious performance issues?",
            "6. **Tests**: Are there sufficient tests?",
            "",
            "## OUTPUT FORMAT",
            "",
            "Respond with ONE of:",
            "- VERIFIED: <brief reason>",
            "- ISSUES_FOUND: <list of issues>",
            "- NEEDS_TESTS: <what tests are missing>",
            "- SECURITY_CONCERN: <specific concern>",
            ""
        ])
        
        return "\n".join(prompt_parts)
    
    def verify_feature(
        self,
        feature: Dict[str, Any],
        code_changes: str = None
    ) -> Dict[str, Any]:
        """
        Verify a feature implementation.
        
        Steps:
        1. Run automated quality checks
        2. If code_changes provided, spawn verification agent
        3. Return combined results
        """
        results = {
            "feature": feature.get('name'),
            "timestamp": datetime.now().isoformat(),
            "automated_checks": None,
            "agent_verification": None,
            "overall_status": "pending"
        }
        
        # Step 1: Run automated checks
        try:
            results["automated_checks"] = self.quality_runner.run_quick_checks()
        except Exception as e:
            results["automated_checks"] = {
                "status": "error",
                "message": str(e)
            }
        
        # Step 2: Spawn verification agent if code provided
        if code_changes:
            verification_prompt = self.build_verification_prompt(
                feature, 
                code_changes,
                results["automated_checks"]
            )
            
            # Try to spawn Claude CLI for verification
            try:
                result = subprocess.run(
                    ["claude", "-p", verification_prompt, "--print"],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                output = result.stdout
                
                if "VERIFIED" in output:
                    results["agent_verification"] = {
                        "status": "verified",
                        "message": output
                    }
                elif "ISSUES_FOUND" in output:
                    results["agent_verification"] = {
                        "status": "issues_found",
                        "message": output
                    }
                elif "NEEDS_TESTS" in output:
                    results["agent_verification"] = {
                        "status": "needs_tests",
                        "message": output
                    }
                elif "SECURITY_CONCERN" in output:
                    results["agent_verification"] = {
                        "status": "security_concern",
                        "message": output
                    }
                else:
                    results["agent_verification"] = {
                        "status": "unclear",
                        "message": output
                    }
                    
            except subprocess.TimeoutExpired:
                results["agent_verification"] = {
                    "status": "timeout",
                    "message": "Verification agent timed out"
                }
            except FileNotFoundError:
                results["agent_verification"] = {
                    "status": "skipped",
                    "message": "Claude CLI not available for verification"
                }
            except Exception as e:
                results["agent_verification"] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # Step 3: Determine overall status
        auto_status = results["automated_checks"].get("status", "unknown")
        agent_status = results["agent_verification"].get("status", "skipped") if results["agent_verification"] else "skipped"
        
        if auto_status == "failed":
            results["overall_status"] = "failed"
        elif agent_status in ["issues_found", "security_concern"]:
            results["overall_status"] = "needs_review"
        elif agent_status == "needs_tests":
            results["overall_status"] = "needs_tests"
        elif auto_status == "passed" and agent_status in ["verified", "skipped"]:
            results["overall_status"] = "passed"
        else:
            results["overall_status"] = "warning"
        
        return results


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

_quality_runner: Optional[QualityGateRunner] = None
_verifier: Optional[VerificationAgent] = None


def init_quality_gates(project_dir: str) -> Dict[str, Any]:
    """Initialize quality gates for the project."""
    global _quality_runner, _verifier
    
    path = Path(project_dir)
    _quality_runner = QualityGateRunner(path)
    _verifier = VerificationAgent(path)
    
    return {
        "success": True,
        "project_dir": project_dir,
        "config": _quality_runner.config.__dict__
    }


def run_quality_checks(
    checks: Optional[List[str]] = None,
    quick: bool = False
) -> Dict[str, Any]:
    """
    Run quality gate checks.
    
    Args:
        checks: Specific checks to run (tests, lint, types, format, security, build)
        quick: If True, run only fast checks (lint, types, format)
    """
    if _quality_runner is None:
        return {"error": "Quality gates not initialized"}
    
    if quick:
        return _quality_runner.run_quick_checks()
    elif checks:
        return _quality_runner.run_all_checks(checks)
    else:
        return _quality_runner.run_full_checks()


def verify_feature_implementation(
    feature: Dict[str, Any],
    code_changes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify a feature implementation with automated + agent checks.
    
    Args:
        feature: Feature dict with name, description, test_cases
        code_changes: Optional string of code changes to verify
    """
    if _verifier is None:
        return {"error": "Quality gates not initialized"}
    
    return _verifier.verify_feature(feature, code_changes)


def get_quality_tools() -> List[Dict[str, Any]]:
    """Get MCP tool definitions for quality gates."""
    return [
        {
            "name": "quality_init",
            "description": "Initialize quality gates for the project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to project directory"
                    }
                },
                "required": ["project_dir"]
            }
        },
        {
            "name": "quality_check",
            "description": "Run quality checks (tests, lint, types, format, security, build)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific checks to run"
                    },
                    "quick": {
                        "type": "boolean",
                        "description": "Run only fast checks",
                        "default": False
                    }
                }
            }
        },
        {
            "name": "quality_verify",
            "description": "Verify feature implementation with automated + agent verification",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "object",
                        "description": "Feature dict with name, description, test_cases"
                    },
                    "code_changes": {
                        "type": "string",
                        "description": "Code changes to verify"
                    }
                },
                "required": ["feature"]
            }
        }
    ]


def handle_quality_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a quality gate tool call."""
    handlers = {
        "quality_init": lambda args: init_quality_gates(args["project_dir"]),
        "quality_check": lambda args: run_quality_checks(
            args.get("checks"),
            args.get("quick", False)
        ),
        "quality_verify": lambda args: verify_feature_implementation(
            args["feature"],
            args.get("code_changes")
        )
    }
    
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"Unknown quality tool: {name}"}
    
    try:
        return handler(arguments)
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python quality_gates.py <project_dir> [command]")
        print("Commands: check, quick, full, verify")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "quick"
    
    init_quality_gates(project_dir)
    
    if command == "quick":
        result = run_quality_checks(quick=True)
    elif command == "full":
        result = run_quality_checks()
    elif command == "check":
        checks = sys.argv[3:] if len(sys.argv) > 3 else None
        result = run_quality_checks(checks=checks)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    if result.get("status") == "failed":
        sys.exit(1)
    elif result.get("status") == "warning":
        sys.exit(0)
    else:
        sys.exit(0)
