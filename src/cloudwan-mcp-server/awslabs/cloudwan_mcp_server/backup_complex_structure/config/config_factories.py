"""
Configuration Factories for CloudWAN MCP Components.

This module provides factory functions to create component-specific configurations
from the centralized configuration system. It helps with migration from the old
scattered configuration approach to the new centralized system.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from .centralized_config import (
    CentralizedConfig,
    DiagramFormat,
    DiagramStyle,
    LayoutStrategy,
    SecurityLevel,
    get_config,
)

logger = logging.getLogger(__name__)


@dataclass
class LegacyDiagramConfig:
    """
    Legacy diagram configuration adapter.

    This class provides backward compatibility with the old DiagramConfig
    classes scattered throughout the codebase.
    """

    default_output_dir: str
    max_elements: int
    default_format: DiagramFormat
    default_diagram_type: str  # Legacy string type
    security_level: SecurityLevel
    timeout_seconds: int
    use_multi_agent: bool
    cache_diagrams: bool
    cache_dir: Optional[str] = None

    # Additional legacy fields for compatibility
    default_width: int = 1600
    default_height: int = 1200
    default_dpi: int = 300
    show_labels: bool = True
    show_ip_addresses: bool = False
    color_code_by_type: bool = True


@dataclass
class LegacyDiagramConfiguration:
    """
    Legacy advanced diagram configuration adapter.

    Compatible with the old DiagramConfiguration class from advanced_diagram_renderer.py
    """

    format: DiagramFormat
    style: DiagramStyle
    layout_strategy: LayoutStrategy
    show_labels: bool
    show_ip_addresses: bool
    show_cidr_blocks: bool
    show_connection_details: bool
    show_health_status: bool
    group_by_region: bool
    group_by_segment: bool
    max_elements_per_group: int
    enable_interactive_elements: bool
    color_code_by_type: bool
    width: int
    height: int
    dpi: int


@dataclass
class LegacyDiagramSuiteConfiguration:
    """
    Legacy diagram suite configuration adapter.

    Compatible with the old DiagramSuiteConfiguration class.
    """

    output_directory: str
    generate_all_formats: bool
    generate_all_layouts: bool
    preferred_format: DiagramFormat
    preferred_style: DiagramStyle
    preferred_layout: LayoutStrategy
    high_resolution: bool
    include_interactive: bool
    include_metadata: bool
    max_elements_per_diagram: int
    filter_by_region: Optional[List[str]]
    filter_by_segment: Optional[List[str]]
    include_health_status: bool
    enable_realtime_updates: bool
    generate_comparison_views: bool
    create_layered_views: bool


class ConfigurationFactory:
    """
    Factory class for creating component-specific configurations
    from the centralized configuration system.
    """

    def __init__(self, config: Optional[CentralizedConfig] = None):
        """
        Initialize factory with configuration.

        Args:
            config: Centralized configuration instance (uses global if None)
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)

    def create_legacy_diagram_config(self) -> LegacyDiagramConfig:
        """
        Create legacy DiagramConfig for backward compatibility.

        Returns:
            Legacy diagram configuration instance
        """
        diagram_config = self.config.diagrams

        return LegacyDiagramConfig(
            default_output_dir=diagram_config.output_directory,
            max_elements=diagram_config.max_elements_default,
            default_format=diagram_config.default_format,
            default_diagram_type=diagram_config.default_layout.value,  # Convert enum to string
            security_level=self.config.security.default_security_level,
            timeout_seconds=diagram_config.generation_timeout_seconds,
            use_multi_agent=self.config.agents.enable_consensus,
            cache_diagrams=diagram_config.enable_caching,
            cache_dir=None,  # Not specified in centralized config
            default_width=diagram_config.default_width,
            default_height=diagram_config.default_height,
            default_dpi=diagram_config.default_dpi,
            show_labels=diagram_config.show_labels,
            show_ip_addresses=diagram_config.show_ip_addresses,
            color_code_by_type=diagram_config.color_code_by_type,
        )

    def create_legacy_diagram_configuration(self) -> LegacyDiagramConfiguration:
        """
        Create legacy DiagramConfiguration for advanced renderer.

        Returns:
            Legacy advanced diagram configuration instance
        """
        diagram_config = self.config.diagrams

        return LegacyDiagramConfiguration(
            format=diagram_config.default_format,
            style=diagram_config.default_style,
            layout_strategy=diagram_config.default_layout,
            show_labels=diagram_config.show_labels,
            show_ip_addresses=diagram_config.show_ip_addresses,
            show_cidr_blocks=True,  # Default value
            show_connection_details=True,  # Default value
            show_health_status=diagram_config.show_health_status,
            group_by_region=True,  # Default value
            group_by_segment=True,  # Default value
            max_elements_per_group=diagram_config.max_elements_per_group,
            enable_interactive_elements=True,  # Default value
            color_code_by_type=diagram_config.color_code_by_type,
            width=diagram_config.default_width,
            height=diagram_config.default_height,
            dpi=diagram_config.default_dpi,
        )

    def create_legacy_suite_configuration(self) -> LegacyDiagramSuiteConfiguration:
        """
        Create legacy DiagramSuiteConfiguration for suite generator.

        Returns:
            Legacy diagram suite configuration instance
        """
        diagram_config = self.config.diagrams

        return LegacyDiagramSuiteConfiguration(
            output_directory=diagram_config.output_directory,
            generate_all_formats=len(diagram_config.export_formats) > 1,
            generate_all_layouts=False,  # Default value
            preferred_format=diagram_config.default_format,
            preferred_style=diagram_config.default_style,
            preferred_layout=diagram_config.default_layout,
            high_resolution=diagram_config.default_dpi >= 300,
            include_interactive=True,  # Default value
            include_metadata=diagram_config.generate_metadata,
            max_elements_per_diagram=diagram_config.max_elements_default,
            filter_by_region=None,  # Not specified in centralized config
            filter_by_segment=None,  # Not specified in centralized config
            include_health_status=diagram_config.show_health_status,
            enable_realtime_updates=False,  # Default value
            generate_comparison_views=False,  # Default value
            create_layered_views=True,  # Default value
        )

    def create_aws_session_config(self) -> Dict[str, Any]:
        """
        Create AWS session configuration dictionary.

        Returns:
            AWS session configuration
        """
        aws_config = self.config.aws

        return {
            "profile_name": aws_config.default_profile,
            "region_name": aws_config.network_manager_region,
            "config": {
                "retries": {"max_attempts": aws_config.max_retries, "mode": "adaptive"},
                "max_pool_connections": aws_config.connection_pool_size,
                "read_timeout": aws_config.timeout_seconds,
                "connect_timeout": 10,  # Fixed connect timeout
            },
        }

    def create_agent_config(self) -> Dict[str, Any]:
        """
        Create agent system configuration dictionary.

        Returns:
            Agent configuration
        """
        agent_config = self.config.agents

        return {
            "max_agents": agent_config.max_agents,
            "timeout_seconds": agent_config.agent_timeout_seconds,
            "max_retries": agent_config.max_retries,
            "backoff_factor": agent_config.retry_backoff_factor,
            "message_timeout": agent_config.message_timeout_seconds,
            "heartbeat_interval": agent_config.heartbeat_interval_seconds,
            "consensus_threshold": agent_config.consensus_threshold,
            "enable_consensus": agent_config.enable_consensus,
        }

    def create_security_config(self) -> Dict[str, Any]:
        """
        Create security configuration dictionary.

        Returns:
            Security configuration
        """
        security_config = self.config.security

        return {
            "enable_sandbox": security_config.enable_sandbox,
            "sandbox_timeout": security_config.sandbox_timeout_seconds,
            "max_memory_mb": security_config.max_memory_mb,
            "security_level": security_config.default_security_level,
            "enable_scanning": security_config.enable_code_scanning,
            "scan_timeout": security_config.scan_timeout_seconds,
            "allowed_packages": security_config.allowed_packages.copy(),
            "blocked_modules": security_config.blocked_modules.copy(),
        }

    def create_performance_config(self) -> Dict[str, Any]:
        """
        Create performance configuration dictionary.

        Returns:
            Performance configuration
        """
        perf_config = self.config.performance

        return {
            "max_workers": perf_config.max_workers,
            "max_concurrent_regions": perf_config.max_concurrent_regions,
            "enable_caching": perf_config.enable_caching,
            "cache_ttl": perf_config.cache_ttl_seconds,
            "cache_max_size": perf_config.cache_max_size,
            "request_timeout": perf_config.request_timeout_seconds,
            "batch_size": perf_config.batch_size,
            "memory_limit_mb": perf_config.memory_limit_mb,
            "gc_threshold": perf_config.gc_threshold,
        }

    def create_logging_config(self) -> Dict[str, Any]:
        """
        Create logging configuration dictionary.

        Returns:
            Logging configuration
        """
        log_config = self.config.logging

        return {
            "level": self.config.get_effective_log_level(),
            "format": log_config.format_string,
            "file_path": log_config.file_path,
            "max_file_size_mb": log_config.max_file_size_mb,
            "backup_count": log_config.backup_count,
            "structured_logging": log_config.enable_structured_logging,
        }

    def create_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """
        Create tool-specific configuration.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool-specific configuration
        """
        base_config = {
            "timeout_seconds": self.config.performance.request_timeout_seconds,
            "max_retries": self.config.aws.max_retries,
            "enable_caching": self.config.performance.enable_caching,
            "cache_ttl": self.config.performance.cache_ttl_seconds,
            "batch_size": self.config.performance.batch_size,
        }

        # Tool-specific overrides
        tool_overrides = {
            "diagram_generator": {
                "max_elements": self.config.diagrams.max_elements_default,
                "output_directory": self.config.diagrams.output_directory,
                "default_format": self.config.diagrams.default_format.value,
                "generation_timeout": self.config.diagrams.generation_timeout_seconds,
            },
            "topology_discovery": {
                "max_workers": self.config.performance.max_workers,
                "concurrent_regions": self.config.performance.max_concurrent_regions,
                "timeout_seconds": self.config.performance.request_timeout_seconds,
            },
            "network_analysis": {
                "max_elements": self.config.diagrams.max_elements_per_group * 2,
                "analysis_timeout": self.config.agents.agent_timeout_seconds,
            },
        }

        if tool_name in tool_overrides:
            base_config.update(tool_overrides[tool_name])

        return base_config


# Global factory instance
_factory_instance: Optional[ConfigurationFactory] = None


def get_factory() -> ConfigurationFactory:
    """
    Get the global configuration factory instance.

    Returns:
        Global factory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = ConfigurationFactory()

    return _factory_instance


def set_factory(factory: ConfigurationFactory) -> None:
    """
    Set the global configuration factory instance.

    Args:
        factory: Factory instance to set as global
    """
    global _factory_instance
    _factory_instance = factory


# Convenience functions for common configurations
def get_diagram_config() -> LegacyDiagramConfig:
    """Get legacy diagram configuration."""
    return get_factory().create_legacy_diagram_config()


def get_advanced_diagram_config() -> LegacyDiagramConfiguration:
    """Get legacy advanced diagram configuration."""
    return get_factory().create_legacy_diagram_configuration()


def get_suite_config() -> LegacyDiagramSuiteConfiguration:
    """Get legacy diagram suite configuration."""
    return get_factory().create_legacy_suite_configuration()


def get_aws_config() -> Dict[str, Any]:
    """Get AWS configuration dictionary."""
    return get_factory().create_aws_session_config()


def get_agent_config() -> Dict[str, Any]:
    """Get agent configuration dictionary."""
    return get_factory().create_agent_config()


def get_security_config() -> Dict[str, Any]:
    """Get security configuration dictionary."""
    return get_factory().create_security_config()


def get_performance_config() -> Dict[str, Any]:
    """Get performance configuration dictionary."""
    return get_factory().create_performance_config()


def get_tool_config(tool_name: str) -> Dict[str, Any]:
    """
    Get tool-specific configuration.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool configuration dictionary
    """
    return get_factory().create_tool_config(tool_name)


# Migration helpers
def migrate_old_config(old_config_dict: Dict[str, Any]) -> CentralizedConfig:
    """
    Migrate old configuration dictionary to centralized config.

    Args:
        old_config_dict: Old configuration dictionary

    Returns:
        New centralized configuration
    """
    logger.info("Migrating old configuration to centralized config")

    # Create default config
    new_config = CentralizedConfig()

    # Map old keys to new structure
    migrations = {
        # AWS settings
        "aws_profile": "aws.default_profile",
        "aws_regions": "aws.regions",
        "aws_timeout": "aws.timeout_seconds",
        "aws_retries": "aws.max_retries",
        # Diagram settings
        "diagram_width": "diagrams.default_width",
        "diagram_height": "diagrams.default_height",
        "diagram_dpi": "diagrams.default_dpi",
        "max_elements": "diagrams.max_elements_default",
        "output_dir": "diagrams.output_directory",
        "diagram_timeout": "diagrams.generation_timeout_seconds",
        # Agent settings
        "max_agents": "agents.max_agents",
        "agent_timeout": "agents.agent_timeout_seconds",
        "use_consensus": "agents.enable_consensus",
        # Security settings
        "security_level": "security.default_security_level",
        "sandbox_enabled": "security.enable_sandbox",
        "sandbox_timeout": "security.sandbox_timeout_seconds",
        # Performance settings
        "max_workers": "performance.max_workers",
        "cache_enabled": "performance.enable_caching",
        "cache_ttl": "performance.cache_ttl_seconds",
        # Logging settings
        "log_level": "logging.level",
        "log_format": "logging.format_string",
        "log_file": "logging.file_path",
    }

    # Apply migrations
    config_dict = new_config.model_dump()

    for old_key, new_key_path in migrations.items():
        if old_key in old_config_dict:
            # Navigate to nested key and set value
            keys = new_key_path.split(".")
            current = config_dict

            # Navigate to parent
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Set final value
            current[keys[-1]] = old_config_dict[old_key]
            logger.debug(f"Migrated {old_key} -> {new_key_path}")

    # Create new config from migrated dictionary
    return CentralizedConfig(**config_dict)


def validate_migration(
    old_config_dict: Dict[str, Any], new_config: CentralizedConfig
) -> Dict[str, Any]:
    """
    Validate configuration migration.

    Args:
        old_config_dict: Original configuration dictionary
        new_config: New centralized configuration

    Returns:
        Validation results
    """
    results = {
        "success": True,
        "migrated_keys": [],
        "unmigrated_keys": [],
        "warnings": [],
        "errors": [],
    }

    # Check which keys were migrated
    known_migrations = {
        "aws_profile",
        "aws_regions",
        "aws_timeout",
        "aws_retries",
        "diagram_width",
        "diagram_height",
        "diagram_dpi",
        "max_elements",
        "output_dir",
        "diagram_timeout",
        "max_agents",
        "agent_timeout",
        "use_consensus",
        "security_level",
        "sandbox_enabled",
        "sandbox_timeout",
        "max_workers",
        "cache_enabled",
        "cache_ttl",
        "log_level",
        "log_format",
    }

    for key in old_config_dict:
        if key in known_migrations:
            results["migrated_keys"].append(key)
        else:
            results["unmigrated_keys"].append(key)
            results["warnings"].append(f"Unknown configuration key not migrated: {key}")

    # Validate critical settings
    try:
        if new_config.aws.regions and len(new_config.aws.regions) == 0:
            results["errors"].append("No AWS regions specified after migration")
            results["success"] = False

        if new_config.diagrams.max_elements_default <= 0:
            results["errors"].append("Invalid max_elements value after migration")
            results["success"] = False

    except Exception as e:
        results["errors"].append(f"Migration validation error: {str(e)}")
        results["success"] = False

    return results
