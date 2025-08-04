"""
Configuration Validation Module.

This module provides comprehensive validation for CloudWAN MCP configurations,
including cross-component validation, environment-specific checks, and
security validation.
"""

import os
import re
import logging
from typing import Dict, List, Any
from pathlib import Path
from dataclasses import dataclass, field

from .centralized_config import CentralizedConfig, Environment, SecurityLevel, LogLevel

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)


class ConfigurationValidator:
    """
    Comprehensive configuration validator.

    Validates configuration for:
    - Value ranges and constraints
    - Cross-component consistency
    - Environment-specific requirements
    - Security best practices
    - Performance optimization
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: CentralizedConfig) -> ValidationResult:
        """
        Perform comprehensive configuration validation.

        Args:
            config: Configuration to validate

        Returns:
            Validation results with errors, warnings, and recommendations
        """
        result = ValidationResult(valid=True)

        # Run all validation checks
        self._validate_basic_constraints(config, result)
        self._validate_cross_component_consistency(config, result)
        self._validate_environment_specific(config, result)
        self._validate_security_settings(config, result)
        self._validate_performance_settings(config, result)
        self._validate_aws_configuration(config, result)
        self._validate_file_paths(config, result)
        self._validate_network_settings(config, result)

        # Set overall validity
        result.valid = len(result.errors) == 0

        return result

    def _validate_basic_constraints(self, config: CentralizedConfig, result: ValidationResult):
        """Validate basic value constraints."""

        # Agent constraints
        if config.agents.max_agents > 20:
            result.warnings.append(
                f"High agent count ({config.agents.max_agents}) may impact performance"
            )

        if config.agents.consensus_threshold < 0.5:
            result.errors.append(
                "Consensus threshold must be at least 0.5 for meaningful consensus"
            )

        # AWS constraints
        if not config.aws.regions:
            result.errors.append("At least one AWS region must be specified")

        if config.aws.timeout_seconds < 5:
            result.errors.append("AWS timeout must be at least 5 seconds")

        # Diagram constraints
        if config.diagrams.max_elements_default > 500:
            result.warnings.append(
                f"High element count ({config.diagrams.max_elements_default}) "
                "may cause performance issues"
            )

        if config.diagrams.default_width * config.diagrams.default_height > 10_000_000:
            result.warnings.append("Large diagram dimensions may consume excessive memory")

        # Security constraints
        if config.security.max_memory_mb > config.performance.memory_limit_mb:
            result.errors.append("Security memory limit exceeds performance memory limit")

        # Performance constraints
        if config.performance.max_workers > 50:
            result.warnings.append(
                f"High worker count ({config.performance.max_workers}) "
                "may cause thread contention"
            )

    def _validate_cross_component_consistency(
        self, config: CentralizedConfig, result: ValidationResult
    ):
        """Validate consistency across components."""

        # Timeout consistency
        if config.agents.agent_timeout_seconds > config.diagrams.generation_timeout_seconds:
            result.warnings.append(
                "Agent timeout exceeds diagram generation timeout - "
                "agents may timeout before diagrams complete"
            )

        if config.aws.timeout_seconds > config.performance.request_timeout_seconds:
            result.warnings.append("AWS timeout exceeds performance request timeout")

        # Worker and agent consistency
        if config.agents.max_agents > config.performance.max_workers:
            result.warnings.append(
                "More agents than workers configured - may cause resource contention"
            )

        # Cache consistency
        if config.diagrams.enable_caching != config.performance.enable_caching:
            result.warnings.append(
                "Caching settings inconsistent between diagram and performance configs"
            )

        if (
            config.diagrams.enable_caching
            and config.performance.enable_caching
            and config.diagrams.cache_ttl_seconds != config.performance.cache_ttl_seconds
        ):
            result.warnings.append("Different cache TTL values may cause inconsistent behavior")

        # Security and performance balance
        if (
            config.security.default_security_level == SecurityLevel.CRITICAL
            and config.performance.max_workers > 10
        ):
            result.recommendations.append(
                "Consider reducing worker count with critical security level"
            )

    def _validate_environment_specific(self, config: CentralizedConfig, result: ValidationResult):
        """Validate environment-specific requirements."""

        if config.environment == Environment.PRODUCTION:
            # Production-specific validations
            if config.debug:
                result.security_issues.append("Debug mode should not be enabled in production")

            if config.logging.level == LogLevel.DEBUG:
                result.warnings.append(
                    "Debug logging in production may impact performance and expose sensitive data"
                )

            if config.security.default_security_level == SecurityLevel.LOW:
                result.security_issues.append(
                    "Low security level inappropriate for production environment"
                )

            if not config.security.enable_sandbox:
                result.security_issues.append(
                    "Sandbox should be enabled in production for security"
                )

            if not config.mcp.enable_cors:
                result.recommendations.append(
                    "CORS disabled in production - ensure this is intentional"
                )

        elif config.environment == Environment.DEVELOPMENT:
            # Development-specific recommendations
            if config.security.default_security_level == SecurityLevel.CRITICAL:
                result.recommendations.append(
                    "Critical security level may slow development iteration"
                )

            if not config.debug:
                result.recommendations.append("Consider enabling debug mode for development")

        elif config.environment == Environment.TESTING:
            # Testing-specific validations
            if config.performance.enable_caching:
                result.warnings.append(
                    "Caching in testing may cause non-deterministic test results"
                )

            if config.agents.max_retries > 1:
                result.recommendations.append(
                    "Consider reducing retries in testing for faster test execution"
                )

    def _validate_security_settings(self, config: CentralizedConfig, result: ValidationResult):
        """Validate security configuration."""

        # Sandbox validation
        if not config.security.enable_sandbox and config.environment != Environment.DEVELOPMENT:
            result.security_issues.append(
                "Sandbox should be enabled in non-development environments"
            )

        # Memory limits validation
        if config.security.max_memory_mb > 2048:
            result.security_issues.append(
                "High memory limits may allow resource exhaustion attacks"
            )

        # Allowed packages validation
        dangerous_packages = {"subprocess", "os", "sys", "importlib"}
        allowed_set = set(config.security.allowed_packages)

        if dangerous_packages & allowed_set:
            result.security_issues.append(
                f"Dangerous packages in allowed list: {dangerous_packages & allowed_set}"
            )

        # Blocked modules validation
        if not config.security.blocked_modules:
            result.security_issues.append(
                "No blocked modules specified - consider blocking dangerous modules"
            )

        # Timeout validation
        if config.security.sandbox_timeout_seconds > 300:
            result.security_issues.append("Long sandbox timeout may allow resource exhaustion")

        # Code scanning validation
        if (
            not config.security.enable_code_scanning
            and config.environment == Environment.PRODUCTION
        ):
            result.security_issues.append("Code scanning should be enabled in production")

    def _validate_performance_settings(self, config: CentralizedConfig, result: ValidationResult):
        """Validate performance configuration."""

        # Worker limits
        import os

        cpu_count = os.cpu_count() or 4

        if config.performance.max_workers > cpu_count * 2:
            result.performance_issues.append(
                f"Worker count ({config.performance.max_workers}) exceeds 2x CPU count ({cpu_count})"
            )

        # Memory validation
        if config.performance.memory_limit_mb < 256:
            result.performance_issues.append("Low memory limit may cause out-of-memory errors")

        # Cache validation
        if config.performance.cache_max_size > 10000:
            result.performance_issues.append("Large cache size may consume excessive memory")

        if config.performance.cache_ttl_seconds < 60:
            result.warnings.append("Short cache TTL may reduce performance benefits")

        # Batch size validation
        if config.performance.batch_size > 1000:
            result.performance_issues.append("Large batch size may cause memory issues")

        # GC threshold validation
        if config.performance.gc_threshold > 0.95:
            result.warnings.append("High GC threshold may delay memory cleanup")

    def _validate_aws_configuration(self, config: CentralizedConfig, result: ValidationResult):
        """Validate AWS-specific configuration."""

        # Region validation
        valid_region_pattern = re.compile(r"^[a-z]{2}-[a-z]+-\d+$")

        for region in config.aws.regions:
            if not valid_region_pattern.match(region):
                result.errors.append(f"Invalid AWS region format: {region}")

        # Network Manager region validation
        if config.aws.network_manager_region not in config.aws.regions:
            result.warnings.append(
                f"Network Manager region ({config.aws.network_manager_region}) "
                f"not in configured regions: {config.aws.regions}"
            )

        # Custom endpoint validation
        if config.aws.custom_endpoint:
            if not config.aws.custom_endpoint.startswith("https://"):
                result.security_issues.append("Custom AWS endpoint must use HTTPS")

            if not config.aws.custom_endpoint.endswith(".amazonaws.com"):
                result.security_issues.append("Custom endpoint should be a valid AWS domain")

        # Concurrent request limits
        if config.aws.max_concurrent_requests > 50:
            result.warnings.append("High concurrent request limit may exceed AWS API throttling")

        # Connection pool validation
        if config.aws.connection_pool_size < config.aws.max_concurrent_requests:
            result.performance_issues.append(
                "Connection pool size should be >= max concurrent requests"
            )

    def _validate_file_paths(self, config: CentralizedConfig, result: ValidationResult):
        """Validate file paths and directories."""

        # Output directory validation
        try:
            output_path = Path(config.diagrams.output_directory)
            if output_path.exists() and not output_path.is_dir():
                result.errors.append(f"Output directory path is not a directory: {output_path}")

            # Check write permissions
            if output_path.exists():
                test_file = output_path / ".write_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                except (PermissionError, OSError):
                    result.errors.append(f"No write permission for output directory: {output_path}")
        except Exception as e:
            result.errors.append(f"Invalid output directory path: {e}")

        # Log file validation
        if config.logging.file_path:
            try:
                log_path = Path(config.logging.file_path)
                log_dir = log_path.parent

                if not log_dir.exists():
                    result.warnings.append(f"Log directory does not exist: {log_dir}")
                elif log_path.exists() and not log_path.is_file():
                    result.errors.append(f"Log path is not a file: {log_path}")
            except Exception as e:
                result.errors.append(f"Invalid log file path: {e}")

    def _validate_network_settings(self, config: CentralizedConfig, result: ValidationResult):
        """Validate network and MCP settings."""

        # Port validation
        if config.mcp.port < 1024 and os.geteuid() != 0:
            result.warnings.append(f"Port {config.mcp.port} requires root privileges")

        if config.mcp.port > 65535:
            result.errors.append(f"Invalid port number: {config.mcp.port}")

        # Host validation
        if config.mcp.host == "0.0.0.0" and config.environment == Environment.DEVELOPMENT:
            result.warnings.append(
                "Binding to 0.0.0.0 in development may expose service to network"
            )

        # Connection limits
        if config.mcp.max_connections > 1000:
            result.performance_issues.append("High connection limit may cause resource exhaustion")

        # Timeout validation
        if config.mcp.request_timeout_seconds < config.diagrams.generation_timeout_seconds:
            result.warnings.append("MCP request timeout less than diagram generation timeout")


def validate_configuration_file(file_path: str) -> ValidationResult:
    """
    Validate a configuration file without loading it globally.

    Args:
        file_path: Path to configuration file

    Returns:
        Validation results
    """
    result = ValidationResult(valid=False)

    try:
        # Load configuration from file
        config = CentralizedConfig.load_from_file(file_path)

        # Validate the loaded configuration
        validator = ConfigurationValidator()
        result = validator.validate_config(config)

    except FileNotFoundError:
        result.errors.append(f"Configuration file not found: {file_path}")
    except Exception as e:
        result.errors.append(f"Error loading configuration file: {str(e)}")

    return result


def validate_environment_variables() -> ValidationResult:
    """
    Validate environment variables for configuration.

    Returns:
        Validation results for environment variables
    """
    result = ValidationResult(valid=True)

    # Check for required environment variables
    env_vars = {
        "CLOUDWAN_ENVIRONMENT": os.getenv("CLOUDWAN_ENVIRONMENT"),
        "AWS_PROFILE": os.getenv("AWS_PROFILE"),
        "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
    }

    # Validate environment
    if env_vars["CLOUDWAN_ENVIRONMENT"]:
        valid_envs = {"development", "testing", "staging", "production"}
        if env_vars["CLOUDWAN_ENVIRONMENT"].lower() not in valid_envs:
            result.warnings.append(f"Unknown environment: {env_vars['CLOUDWAN_ENVIRONMENT']}")

    # Validate AWS region
    if env_vars["AWS_DEFAULT_REGION"]:
        region_pattern = re.compile(r"^[a-z]{2}-[a-z]+-\d+$")
        if not region_pattern.match(env_vars["AWS_DEFAULT_REGION"]):
            result.errors.append(f"Invalid AWS region format: {env_vars['AWS_DEFAULT_REGION']}")

    # Check for configuration-specific environment variables
    config_prefixes = [
        "CLOUDWAN_AGENT_",
        "CLOUDWAN_AWS_",
        "CLOUDWAN_DIAGRAM_",
        "CLOUDWAN_SECURITY_",
        "CLOUDWAN_PERF_",
        "CLOUDWAN_LOG_",
        "CLOUDWAN_MCP_",
    ]

    config_vars = {}
    for key, value in os.environ.items():
        for prefix in config_prefixes:
            if key.startswith(prefix):
                config_vars[key] = value
                break

    if config_vars:
        result.recommendations.append(
            f"Found {len(config_vars)} configuration environment variables"
        )

    return result


def generate_validation_report(result: ValidationResult) -> str:
    """
    Generate a human-readable validation report.

    Args:
        result: Validation results

    Returns:
        Formatted validation report
    """
    report = []
    report.append("CloudWAN MCP Configuration Validation Report")
    report.append("=" * 50)
    report.append("")

    # Overall status
    status = "✅ VALID" if result.valid else "❌ INVALID"
    report.append(f"Status: {status}")
    report.append("")

    # Errors
    if result.errors:
        report.append("🔴 Errors:")
        for error in result.errors:
            report.append(f"  • {error}")
        report.append("")

    # Security issues
    if result.security_issues:
        report.append("🛡️ Security Issues:")
        for issue in result.security_issues:
            report.append(f"  • {issue}")
        report.append("")

    # Performance issues
    if result.performance_issues:
        report.append("⚡ Performance Issues:")
        for issue in result.performance_issues:
            report.append(f"  • {issue}")
        report.append("")

    # Warnings
    if result.warnings:
        report.append("⚠️ Warnings:")
        for warning in result.warnings:
            report.append(f"  • {warning}")
        report.append("")

    # Recommendations
    if result.recommendations:
        report.append("💡 Recommendations:")
        for rec in result.recommendations:
            report.append(f"  • {rec}")
        report.append("")

    # Summary
    report.append("Summary:")
    report.append(f"  Errors: {len(result.errors)}")
    report.append(f"  Security Issues: {len(result.security_issues)}")
    report.append(f"  Performance Issues: {len(result.performance_issues)}")
    report.append(f"  Warnings: {len(result.warnings)}")
    report.append(f"  Recommendations: {len(result.recommendations)}")

    return "\n".join(report)


def get_validation_summary(result: ValidationResult) -> Dict[str, Any]:
    """
    Get validation summary as dictionary.

    Args:
        result: Validation results

    Returns:
        Validation summary dictionary
    """
    return {
        "valid": result.valid,
        "total_issues": (
            len(result.errors)
            + len(result.security_issues)
            + len(result.performance_issues)
            + len(result.warnings)
        ),
        "error_count": len(result.errors),
        "security_issue_count": len(result.security_issues),
        "performance_issue_count": len(result.performance_issues),
        "warning_count": len(result.warnings),
        "recommendation_count": len(result.recommendations),
        "severity": (
            "high"
            if result.errors or result.security_issues
            else "medium" if result.performance_issues or result.warnings else "low"
        ),
    }
