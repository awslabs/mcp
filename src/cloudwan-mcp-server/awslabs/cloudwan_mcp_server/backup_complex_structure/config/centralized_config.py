"""
Centralized Configuration Management for CloudWAN MCP System.

This module provides a comprehensive, type-safe configuration management system
using Pydantic for validation. It centralizes all configuration parameters
that were previously scattered across the codebase.

Features:
- Hierarchical configuration structure
- Environment variable support with proper prefixes
- Type-safe configuration classes with validation
- Configuration inheritance and overrides
- Support for multiple environments (dev, test, prod)
- Dynamic configuration reloading
- Comprehensive validation with helpful error messages
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DiagramFormat(str, Enum):
    """Supported diagram output formats."""

    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class DiagramStyle(str, Enum):
    """Diagram visual styles."""

    PROFESSIONAL = "professional"
    TECHNICAL = "technical"
    SIMPLIFIED = "simplified"
    DETAILED = "detailed"


class LayoutStrategy(str, Enum):
    """Diagram layout strategies."""

    THREE_PANE = "three_pane"
    HIERARCHICAL = "hierarchical"
    SEGMENT_FOCUSED = "segment_focused"
    GEOGRAPHIC = "geographic"
    CIRCULAR = "circular"


class SecurityLevel(str, Enum):
    """Security levels for diagram generation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AgentConfig(BaseModel):
    """Configuration for multi-agent system."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_AGENT_")

    # Agent behavior settings
    max_agents: int = Field(default=5, ge=1, le=20, description="Maximum number of agents to spawn")

    agent_timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Timeout for individual agent operations",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed operations",
    )

    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="Exponential backoff factor for retries",
    )

    # Agent communication settings
    message_timeout_seconds: int = Field(
        default=30, ge=5, le=300, description="Timeout for inter-agent messages"
    )

    heartbeat_interval_seconds: int = Field(
        default=15, ge=5, le=60, description="Agent heartbeat interval"
    )

    # Consensus settings
    consensus_threshold: float = Field(
        default=0.75,
        ge=0.5,
        le=1.0,
        description="Threshold for agent consensus agreement",
    )

    enable_consensus: bool = Field(default=True, description="Enable multi-agent consensus system")


class AWSClientConfig(BaseModel):
    """Configuration for AWS client settings."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_AWS_")

    # Authentication settings
    default_profile: Optional[str] = Field(default=None, description="Default AWS profile name")

    regions: List[str] = Field(
        default=["eu-west-1", "eu-west-2"], description="AWS regions to operate in"
    )

    # Client behavior settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum AWS API retries")

    timeout_seconds: int = Field(default=30, ge=5, le=300, description="AWS API timeout in seconds")

    # Network Manager specific settings
    network_manager_region: str = Field(
        default="us-west-2", description="Region for AWS Network Manager API"
    )

    custom_endpoint: Optional[str] = Field(
        default=None, description="Custom Network Manager endpoint URL"
    )

    # Performance settings
    max_concurrent_requests: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent AWS API requests"
    )

    connection_pool_size: int = Field(
        default=20, ge=5, le=100, description="HTTP connection pool size"
    )

    @field_validator("regions")
    @classmethod
    def validate_regions(cls, v):
        """Validate AWS regions format."""
        if not v:
            raise ValueError("At least one AWS region must be specified")

        for region in v:
            if not region or len(region.split("-")) < 3:
                raise ValueError(f"Invalid AWS region format: {region}")

        return v

    @field_validator("custom_endpoint")
    @classmethod
    def validate_custom_endpoint(cls, v):
        """Validate custom endpoint format."""
        if v and not v.startswith("https://"):
            raise ValueError("Custom endpoint must use HTTPS")
        return v


class DiagramGenerationConfig(BaseModel):
    """Configuration for diagram generation."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_DIAGRAM_")

    # Output settings
    default_format: DiagramFormat = Field(
        default=DiagramFormat.PNG, description="Default diagram output format"
    )

    default_style: DiagramStyle = Field(
        default=DiagramStyle.PROFESSIONAL, description="Default diagram style"
    )

    default_layout: LayoutStrategy = Field(
        default=LayoutStrategy.THREE_PANE, description="Default layout strategy"
    )

    output_directory: str = Field(
        default="cloudwan_diagrams", description="Default output directory for diagrams"
    )

    # Quality and size settings
    default_width: int = Field(
        default=1600, ge=800, le=4000, description="Default diagram width in pixels"
    )

    default_height: int = Field(
        default=1200, ge=600, le=3000, description="Default diagram height in pixels"
    )

    default_dpi: int = Field(
        default=300, ge=72, le=600, description="Default DPI for high-quality output"
    )

    # Element and complexity limits
    max_elements_default: int = Field(
        default=75, ge=10, le=500, description="Default maximum elements per diagram"
    )

    max_elements_per_group: int = Field(
        default=20, ge=5, le=100, description="Maximum elements per group/region"
    )

    # Generation settings
    generation_timeout_seconds: int = Field(
        default=120, ge=30, le=600, description="Timeout for diagram generation"
    )

    enable_caching: bool = Field(default=True, description="Enable diagram result caching")

    cache_ttl_seconds: int = Field(
        default=300, ge=60, le=3600, description="Cache time-to-live in seconds"
    )

    # Visual settings
    show_labels: bool = Field(default=True, description="Show element labels by default")

    show_ip_addresses: bool = Field(default=False, description="Show IP addresses in diagrams")

    show_health_status: bool = Field(default=True, description="Show health status indicators")

    color_code_by_type: bool = Field(default=True, description="Use color coding for element types")

    # Segment color mapping
    segment_colors: Dict[str, str] = Field(
        default={
            "Production": "#FF6B6B",
            "NonProduction": "#4ECDC4",
            "Shared": "#45B7D1",
            "Inspection": "#FFA07A",
            "DCExit": "#98D8C8",
            "CrossOrg": "#F7DC6F",
            "Default": "#95A5A6",
        },
        description="Color mapping for network segments",
    )

    # Export settings
    export_formats: List[DiagramFormat] = Field(
        default=[DiagramFormat.PNG, DiagramFormat.HTML],
        description="Formats to export by default",
    )

    generate_metadata: bool = Field(
        default=True, description="Generate metadata files with diagrams"
    )

    @field_validator("output_directory")
    @classmethod
    def validate_output_directory(cls, v):
        """Validate output directory path."""
        if not v:
            raise ValueError("Output directory cannot be empty")

        # Create directory if it doesn't exist
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class SecurityConfig(BaseModel):
    """Configuration for security settings."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_SECURITY_")

    # Sandbox settings
    enable_sandbox: bool = Field(default=True, description="Enable code execution sandbox")

    sandbox_timeout_seconds: int = Field(
        default=60, ge=10, le=300, description="Sandbox execution timeout"
    )

    max_memory_mb: int = Field(
        default=512, ge=128, le=2048, description="Maximum memory usage in MB"
    )

    # Security scanning
    default_security_level: SecurityLevel = Field(
        default=SecurityLevel.MEDIUM,
        description="Default security level for operations",
    )

    enable_code_scanning: bool = Field(default=True, description="Enable security code scanning")

    scan_timeout_seconds: int = Field(default=30, ge=5, le=120, description="Security scan timeout")

    # Access control
    allowed_packages: List[str] = Field(
        default=[
            "matplotlib",
            "plotly",
            "networkx",
            "pydantic",
            "boto3",
            "botocore",
            "requests",
        ],
        description="Allowed Python packages for execution",
    )

    blocked_modules: List[str] = Field(
        default=[
            "os",
            "subprocess",
            "sys",
            "importlib",
            "__builtins__",
            "eval",
            "exec",
        ],
        description="Blocked Python modules",
    )


class PerformanceConfig(BaseModel):
    """Configuration for performance settings."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_PERF_")

    # Concurrency settings
    max_workers: int = Field(default=10, ge=1, le=50, description="Maximum worker threads")

    max_concurrent_regions: int = Field(
        default=5, ge=1, le=20, description="Maximum concurrent regions for operations"
    )

    # Caching settings
    enable_caching: bool = Field(default=True, description="Enable performance caching")

    cache_ttl_seconds: int = Field(default=300, ge=60, le=3600, description="Cache time-to-live")

    cache_max_size: int = Field(default=1000, ge=100, le=10000, description="Maximum cache entries")

    # Operation limits
    request_timeout_seconds: int = Field(default=30, ge=5, le=300, description="Request timeout")

    batch_size: int = Field(
        default=50, ge=1, le=1000, description="Default batch size for operations"
    )

    # Memory management
    memory_limit_mb: int = Field(default=1024, ge=256, le=4096, description="Memory limit in MB")

    gc_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Memory threshold for garbage collection",
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_LOG_")

    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")

    format_string: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )

    file_path: Optional[str] = Field(default=None, description="Optional log file path")

    max_file_size_mb: int = Field(
        default=100, ge=1, le=1000, description="Maximum log file size in MB"
    )

    backup_count: int = Field(default=5, ge=1, le=50, description="Number of backup log files")

    enable_structured_logging: bool = Field(
        default=False, description="Enable structured (JSON) logging"
    )


class MCPServerConfig(BaseModel):
    """Configuration for MCP server."""

    model_config = ConfigDict(env_prefix="CLOUDWAN_MCP_")

    server_name: str = Field(default="CloudWAN-MCP-Server", description="MCP server name")

    host: str = Field(default="localhost", description="Server host interface")

    port: int = Field(default=8080, ge=1024, le=65535, description="Server port")

    max_connections: int = Field(
        default=100, ge=1, le=1000, description="Maximum concurrent connections"
    )

    request_timeout_seconds: int = Field(default=300, ge=30, le=3600, description="Request timeout")

    enable_cors: bool = Field(default=True, description="Enable CORS")


class CentralizedConfig(BaseSettings):
    """
    Main centralized configuration class for CloudWAN MCP System.

    This class provides a single source of truth for all configuration
    parameters across the system. It supports:

    - Environment variable loading with proper prefixes
    - Configuration inheritance and overrides
    - Type-safe validation with helpful error messages
    - Environment-specific configurations
    - Dynamic configuration reloading
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",  # Prevent unknown configuration keys
    )

    # Environment settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Deployment environment"
    )

    debug: bool = Field(default=False, description="Enable debug mode")

    config_file: Optional[str] = Field(default=None, description="Path to configuration file")

    # Component configurations
    agents: AgentConfig = Field(
        default_factory=AgentConfig, description="Multi-agent system configuration"
    )

    aws: AWSClientConfig = Field(
        default_factory=AWSClientConfig, description="AWS client configuration"
    )

    diagrams: DiagramGenerationConfig = Field(
        default_factory=DiagramGenerationConfig,
        description="Diagram generation configuration",
    )

    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security configuration"
    )

    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig, description="Performance configuration"
    )

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    mcp: MCPServerConfig = Field(
        default_factory=MCPServerConfig, description="MCP server configuration"
    )

    def __init__(self, **kwargs):
        """Initialize configuration with environment-specific overrides."""
        super().__init__(**kwargs)
        self._apply_environment_overrides()
        self._validate_configuration()

    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides."""
        if self.environment == Environment.PRODUCTION:
            # Production overrides
            self.debug = False
            self.logging.level = LogLevel.INFO
            self.security.default_security_level = SecurityLevel.HIGH
            self.performance.enable_caching = True

        elif self.environment == Environment.TESTING:
            # Testing overrides
            self.debug = True
            self.logging.level = LogLevel.DEBUG
            self.agents.max_agents = 2  # Limit for testing
            self.performance.cache_ttl_seconds = 60  # Short cache for testing

        elif self.environment == Environment.STAGING:
            # Staging overrides
            self.debug = False
            self.logging.level = LogLevel.INFO
            self.security.default_security_level = SecurityLevel.HIGH

        # Development uses defaults

    def _validate_configuration(self):
        """Perform cross-component validation."""

        # Validate timeout consistency
        if self.agents.agent_timeout_seconds > self.diagrams.generation_timeout_seconds:
            logger.warning(
                f"Agent timeout ({self.agents.agent_timeout_seconds}s) exceeds "
                f"diagram generation timeout ({self.diagrams.generation_timeout_seconds}s)"
            )

        # Validate memory settings
        if self.security.max_memory_mb > self.performance.memory_limit_mb:
            logger.warning(
                f"Security memory limit ({self.security.max_memory_mb}MB) exceeds "
                f"performance memory limit ({self.performance.memory_limit_mb}MB)"
            )

        # Validate agent and worker counts
        if self.agents.max_agents > self.performance.max_workers:
            logger.warning(
                f"Max agents ({self.agents.max_agents}) exceeds "
                f"max workers ({self.performance.max_workers})"
            )

    def get_component_config(self, component: str) -> BaseModel:
        """
        Get configuration for a specific component.

        Args:
            component: Component name (agents, aws, diagrams, security, performance, logging, mcp)

        Returns:
            Component configuration object

        Raises:
            ValueError: If component is not found
        """
        component_map = {
            "agents": self.agents,
            "aws": self.aws,
            "diagrams": self.diagrams,
            "security": self.security,
            "performance": self.performance,
            "logging": self.logging,
            "mcp": self.mcp,
        }

        if component not in component_map:
            available = ", ".join(component_map.keys())
            raise ValueError(f"Unknown component '{component}'. Available: {available}")

        return component_map[component]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug or self.environment == Environment.TESTING

    def get_effective_log_level(self) -> str:
        """Get effective logging level considering debug mode."""
        if self.is_debug_enabled():
            return LogLevel.DEBUG.value
        return self.logging.level.value

    def export_to_dict(self) -> Dict[str, Any]:
        """Export configuration to dictionary format."""
        return self.model_dump()

    def export_to_file(self, file_path: str, format: str = "json"):
        """
        Export configuration to file.

        Args:
            file_path: Output file path
            format: Export format ('json' or 'yaml')
        """
        config_dict = self.export_to_dict()

        if format.lower() == "json":
            import json

            with open(file_path, "w") as f:
                json.dump(config_dict, f, indent=2, default=str)
        elif format.lower() == "yaml":
            try:
                import yaml

                with open(file_path, "w") as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML is required for YAML export")
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def load_from_file(cls, file_path: str) -> "CentralizedConfig":
        """
        Load configuration from file.

        Args:
            file_path: Configuration file path (JSON or YAML)

        Returns:
            Loaded configuration instance
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, "r") as f:
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                try:
                    import yaml

                    config_data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required for YAML configuration files")
            else:  # Assume JSON
                import json

                config_data = json.load(f)

        return cls(**config_data)

    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        # Create new instance with updated values and copy to self
        updated = self.__class__(**{**self.model_dump(), **config_dict})

        # Update self with new values
        for field_name, field_value in updated.model_dump().items():
            setattr(self, field_name, field_value)

        # Re-validate after update
        self._validate_configuration()


# Global configuration factory
_config_instance: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """
    Get the global configuration instance.

    Returns:
        Global configuration instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = CentralizedConfig()

    return _config_instance


def set_config(config: CentralizedConfig) -> None:
    """
    Set the global configuration instance.

    Args:
        config: Configuration instance to set as global
    """
    global _config_instance
    _config_instance = config


def load_config_from_env() -> CentralizedConfig:
    """
    Load configuration from environment variables.

    Returns:
        Configuration loaded from environment
    """
    config = CentralizedConfig()
    set_config(config)
    return config


def load_config_from_file(file_path: str) -> CentralizedConfig:
    """
    Load configuration from file and set as global.

    Args:
        file_path: Configuration file path

    Returns:
        Loaded configuration
    """
    config = CentralizedConfig.load_from_file(file_path)
    set_config(config)
    return config


def reset_config() -> None:
    """Reset global configuration to default values."""
    global _config_instance
    _config_instance = None


# Configuration validation utilities
def validate_config_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a configuration file without loading it.

    Args:
        file_path: Configuration file path

    Returns:
        Validation result with errors and warnings
    """
    result = {"valid": False, "errors": [], "warnings": [], "config_preview": None}

    try:
        config = CentralizedConfig.load_from_file(file_path)
        result["valid"] = True
        result["config_preview"] = config.export_to_dict()

        # Check for common configuration issues
        if config.environment == Environment.PRODUCTION and config.debug:
            result["warnings"].append("Debug mode enabled in production environment")

        if not config.security.enable_sandbox:
            result["warnings"].append("Code execution sandbox is disabled")

    except Exception as e:
        result["errors"].append(str(e))

    return result


# Environment-specific configuration presets
def get_development_config() -> CentralizedConfig:
    """Get development environment configuration."""
    return CentralizedConfig(environment=Environment.DEVELOPMENT, debug=True)


def get_testing_config() -> CentralizedConfig:
    """Get testing environment configuration."""
    return CentralizedConfig(environment=Environment.TESTING, debug=True)


def get_production_config() -> CentralizedConfig:
    """Get production environment configuration."""
    return CentralizedConfig(environment=Environment.PRODUCTION, debug=False)
