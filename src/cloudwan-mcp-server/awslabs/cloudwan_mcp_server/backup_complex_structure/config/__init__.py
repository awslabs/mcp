"""
Centralized Configuration Management for CloudWAN MCP System.

This package provides comprehensive configuration management with:
- Type-safe configuration classes using Pydantic
- Environment variable support with proper prefixes
- Configuration validation and error handling
- Environment-specific configuration templates
- Migration support from legacy configurations
- Configuration factories for component-specific needs

Usage Examples:

Basic usage:
```python
from awslabs.cloudwan_mcp_server.config import get_config

config = get_config()
print(f"Environment: {config.environment}")
print(f"Max agents: {config.agents.max_agents}")
```

Environment-specific configurations:
```python
from awslabs.cloudwan_mcp_server.config import create_production_config, create_development_config

# For production
prod_config = create_production_config()

# For development
dev_config = create_development_config()
```

Configuration validation:
```python
from awslabs.cloudwan_mcp_server.config import validate_configuration_file

result = validate_configuration_file('config.json')
if not result.valid:
    for error in result.errors:
        print(f"Error: {error}")
```

Legacy configuration migration:
```python
from awslabs.cloudwan_mcp_server.config import get_diagram_config, get_aws_config

# Get legacy-compatible configuration objects
diagram_config = get_diagram_config()
aws_config = get_aws_config()
```

Loading from file:
```python
from awslabs.cloudwan_mcp_server.config import load_config_from_file

config = load_config_from_file('production.json')
```
"""

# Legacy imports for backward compatibility
from .main_config import CloudWANConfig, EnvironmentManager

try:
    from .utils import load_config_from_env as legacy_load_config_from_env
except ImportError:
    legacy_load_config_from_env = None

# Core configuration classes
from .centralized_config import (
    CentralizedConfig,
    AgentConfig,
    AWSClientConfig,
    DiagramGenerationConfig,
    SecurityConfig,
    PerformanceConfig,
    LoggingConfig,
    MCPServerConfig,
    # Enums
    Environment,
    DiagramFormat,
    DiagramStyle,
    LayoutStrategy,
    SecurityLevel,
    LogLevel,
    # Factory functions
    get_config,
    set_config,
    load_config_from_env,
    load_config_from_file,
    reset_config,
    # Validation utilities
    validate_config_file,
    # Environment presets
    get_development_config,
    get_testing_config,
    get_production_config,
)

# Backward compatibility aliases
AWSConfig = AWSClientConfig
DiagramConfig = DiagramGenerationConfig

# Configuration factories and legacy support
from .config_factories import (
    ConfigurationFactory,
    LegacyDiagramConfig,
    LegacyDiagramConfiguration,
    LegacyDiagramSuiteConfiguration,
    # Factory functions
    get_factory,
    set_factory,
    # Convenience functions
    get_diagram_config,
    get_advanced_diagram_config,
    get_suite_config,
    get_aws_config,
    get_agent_config,
    get_security_config,
    get_performance_config,
    get_tool_config,
    # Migration utilities
    migrate_old_config,
    validate_migration,
)

# Environment-specific configurations
from .environment_configs import (
    create_development_config,
    create_testing_config,
    create_staging_config,
    create_production_config,
    create_high_performance_config,
    create_minimal_config,
    load_config_from_environment,
    get_config_template_info,
)

# Validation
from .validation import (
    ConfigurationValidator,
    ValidationResult,
    validate_configuration_file,
    validate_environment_variables,
    generate_validation_report,
    get_validation_summary,
)

# Version and metadata
__version__ = "1.0.0"
__author__ = "CloudWAN MCP Team"
__description__ = "Centralized configuration management for CloudWAN MCP System"

# Backward compatibility exports
__all__ = [
    # Legacy exports
    "CloudWANConfig",
    "EnvironmentManager",
    # Core configuration
    "CentralizedConfig",
    "AgentConfig",
    "AWSClientConfig",
    "AWSConfig",  # Backward compatibility alias
    "DiagramGenerationConfig",
    "DiagramConfig",  # Backward compatibility alias
    "SecurityConfig",
    "PerformanceConfig",
    "LoggingConfig",
    "MCPServerConfig",
    # Enums
    "Environment",
    "DiagramFormat",
    "DiagramStyle",
    "LayoutStrategy",
    "SecurityLevel",
    "LogLevel",
    # Configuration management
    "get_config",
    "set_config",
    "load_config_from_env",
    "load_config_from_file",
    "reset_config",
    # Environment-specific configs
    "create_development_config",
    "create_testing_config",
    "create_staging_config",
    "create_production_config",
    "create_high_performance_config",
    "create_minimal_config",
    "load_config_from_environment",
    "get_config_template_info",
    # Legacy support and factories
    "ConfigurationFactory",
    "LegacyDiagramConfig",
    "LegacyDiagramConfiguration",
    "LegacyDiagramSuiteConfiguration",
    "get_factory",
    "set_factory",
    "get_diagram_config",
    "get_advanced_diagram_config",
    "get_suite_config",
    "get_aws_config",
    "get_agent_config",
    "get_security_config",
    "get_performance_config",
    "get_tool_config",
    "migrate_old_config",
    "validate_migration",
    # Validation
    "ConfigurationValidator",
    "ValidationResult",
    "validate_configuration_file",
    "validate_environment_variables",
    "generate_validation_report",
    "get_validation_summary",
    "validate_config_file",
    # Environment presets
    "get_development_config",
    "get_testing_config",
    "get_production_config",
]

# Add legacy function for backward compatibility
if legacy_load_config_from_env:
    __all__.append("legacy_load_config_from_env")


def setup_logging_from_config(config: CentralizedConfig = None) -> None:
    """
    Configure logging based on configuration settings.

    Args:
        config: Configuration instance (uses global if None)
    """
    import logging
    import logging.handlers

    if config is None:
        config = get_config()

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(config.get_effective_log_level())

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    if config.logging.enable_structured_logging:
        import json
        from datetime import datetime

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)

        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(config.logging.format_string)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if config.logging.file_path:
        try:
            from pathlib import Path

            log_path = Path(config.logging.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=config.logging.max_file_size_mb * 1024 * 1024,
                backupCount=config.logging.backup_count,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")


def get_config_summary(config: CentralizedConfig = None) -> dict:
    """
    Get a summary of current configuration settings.

    Args:
        config: Configuration instance (uses global if None)

    Returns:
        Configuration summary dictionary
    """
    if config is None:
        config = get_config()

    return {
        "environment": config.environment.value,
        "debug": config.debug,
        "components": {
            "agents": {
                "max_agents": config.agents.max_agents,
                "consensus_enabled": config.agents.enable_consensus,
                "timeout_seconds": config.agents.agent_timeout_seconds,
            },
            "aws": {
                "regions": config.aws.regions,
                "profile": config.aws.default_profile,
                "timeout_seconds": config.aws.timeout_seconds,
            },
            "diagrams": {
                "max_elements": config.diagrams.max_elements_default,
                "default_format": config.diagrams.default_format.value,
                "output_directory": config.diagrams.output_directory,
            },
            "security": {
                "level": config.security.default_security_level.value,
                "sandbox_enabled": config.security.enable_sandbox,
                "scanning_enabled": config.security.enable_code_scanning,
            },
            "performance": {
                "max_workers": config.performance.max_workers,
                "caching_enabled": config.performance.enable_caching,
                "memory_limit_mb": config.performance.memory_limit_mb,
            },
        },
    }


def print_config_info(config: CentralizedConfig = None) -> None:
    """
    Print formatted configuration information.

    Args:
        config: Configuration instance (uses global if None)
    """
    if config is None:
        config = get_config()

    summary = get_config_summary(config)

    print("CloudWAN MCP Configuration Summary")
    print("=" * 40)
    print(f"Environment: {summary['environment']}")
    print(f"Debug Mode: {summary['debug']}")
    print()

    print("Component Settings:")
    for component, settings in summary["components"].items():
        print(f"  {component.title()}:")
        for key, value in settings.items():
            print(f"    {key}: {value}")
        print()


# Initialize default configuration on import
try:
    # Only initialize if not already configured
    current_config = get_config()
    if current_config is None:
        # Load from environment
        default_config = load_config_from_environment()
        set_config(default_config)

        # Setup logging
        setup_logging_from_config(default_config)

except Exception:
    # Fallback to basic configuration if initialization fails
    basic_config = CentralizedConfig()
    set_config(basic_config)
