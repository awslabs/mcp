"""
Configuration management for CloudWAN MCP Server.

This module provides comprehensive configuration management using Pydantic
for validation and type safety. Supports environment variables, file-based
configuration, and runtime validation.
"""

import os
import logging
import contextlib
from typing import Dict, List, Optional, Any, Iterator, Callable

from pydantic import BaseModel, Field, validator, field_validator
from pydantic_settings import BaseSettings

from dataclasses import dataclass


@dataclass
class WebSocketConfig:
    """WebSocket server configuration"""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8765
    require_authentication: bool = False
    auth_handler: Optional[Callable] = None
    heartbeat_interval_seconds: int = 15
    connection_timeout_seconds: int = 60
    max_connections: int = 1000
    max_message_size: int = 65536  # 64KB
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    # Advanced options
    compression_enabled: bool = True
    ping_interval: int = 20
    ping_timeout: int = 20
    close_timeout: int = 10
    max_queue_size: int = 32

    # Features
    subscription_management_enabled: bool = True
    connection_health_monitoring_enabled: bool = True
    
    # Protocol settings
    handshake_timeout: int = 10
    max_negotiation_attempts: int = 3
    version_grace_period: int = 300  # 5 minutes for version deprecation

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            # Skip callable objects
            if not callable(field_value):
                result[field_name] = field_value
        return result

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "WebSocketConfig":
        """Create configuration from dictionary"""
        # Filter out unknown fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in known_fields}
        return cls(**filtered_dict)
    
    def get_protocol_settings(self) -> Dict[str, Any]:
        return {
            "heartbeat_interval": self.heartbeat_interval_seconds,
            "ping_timeout": self.ping_timeout,
            "handshake_timeout": self.handshake_timeout
        }


logger = logging.getLogger(__name__)

# Import validators - handle ImportError gracefully
try:
    from .utils.validators import (
        ResolutionValidator,
        validate_aws_region,
        TimeoutValidator,
    )

    VALIDATORS_AVAILABLE = True
except ImportError:
    VALIDATORS_AVAILABLE = False


class EnvironmentManager:
    """Manages environment variables with isolation capabilities."""

    def __init__(self):
        self._env_vars: Dict[str, str] = {}
        self._applied = False
        self._original_values: Dict[str, Optional[str]] = {}

    def set(self, key: str, value: str) -> None:
        self._env_vars[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._env_vars.get(key, os.environ.get(key, default))

    def unset(self, key: str) -> None:
        if key in self._env_vars:
            del self._env_vars[key]

    def clear(self) -> None:
        self._env_vars.clear()

    def get_all(self) -> Dict[str, str]:
        result = dict(os.environ)
        result.update(self._env_vars)
        return result

    def get_isolated(self) -> Dict[str, str]:
        return self._env_vars.copy()

    @contextlib.contextmanager
    def apply(self) -> Iterator[Dict[str, str]]:
        if self._applied:
            yield self.get_all()
            return

        self._original_values = {}
        try:
            for key, value in self._env_vars.items():
                self._original_values[key] = os.environ.get(key)
                os.environ[key] = value

            self._applied = True
            yield self.get_all()
        finally:
            for key, original_value in self._original_values.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value

            self._original_values = {}
            self._applied = False

    def apply_to_callable(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        with self.apply():
            return func(*args, **kwargs)


class NetworkManagerConfig(BaseModel):
    """Network Manager specific configuration."""

    custom_endpoint: Optional[str] = Field(
        default=None,
        description="Custom endpoint for special deployments",
        env="CLOUDWAN_AWS_NETWORK_MANAGER_CUSTOM_ENDPOINT",
    )

    region: str = Field(
        default=None,
        description="NetworkManager API region",
        env="CLOUDWAN_AWS_NETWORK_MANAGER_REGION",
    )

    _env_manager: EnvironmentManager = None

    @field_validator("custom_endpoint")
    @classmethod
    def validate_custom_endpoint(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.startswith("https://"):
                raise ValueError("Must use HTTPS")
            if not v.endswith(".amazonaws.com"):
                raise ValueError("Must be valid AWS endpoint")
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> str:
        if not v:
            v = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
            logger.info(f"Using {v} for NetworkManager region")

        if not isinstance(v, str) or len(v.split("-")) < 3:
            logger.warning(f"Invalid format '{v}'")
            return "us-west-2"

        env_endpoint = os.environ.get("CLOUDWAN_AWS_NETWORK_MANAGER_CUSTOM_ENDPOINT")
        if env_endpoint and "us-west-2" in env_endpoint and v != "us-west-2":
            logger.warning("Changed to 'us-west-2' for custom endpoint compatibility")
            return "us-west-2"

        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._env_manager = EnvironmentManager()

    def get_environment_manager(self) -> EnvironmentManager:
        if self._env_manager is None:
            self._env_manager = EnvironmentManager()
        return self._env_manager

    def set_environment_variables(self) -> None:
        env_manager = self.get_environment_manager()

        if self.custom_endpoint and (
            self.custom_endpoint.startswith("https://")
            and ".amazonaws.com" in self.custom_endpoint
        ):
            env_manager.set("AWS_ENDPOINT_URL_NETWORKMANAGER", self.custom_endpoint)

        if self.region and not os.environ.get("CLOUDWAN_AWS_NETWORK_MANAGER_REGION"):
            env_manager.set("AWS_DEFAULT_REGION", self.region)

    @contextlib.contextmanager
    def with_applied_environment(self) -> Iterator[Dict[str, str]]:
        self.set_environment_variables()
        with self.get_environment_manager().apply() as env:
            yield env


class AWSConfig(BaseModel):
    """AWS-specific configuration."""

    default_profile: str = Field(
        default=None,
        description="Default AWS profile for authentication",
        env="CLOUDWAN_AWS_PROFILE",
    )

    strict_profile_validation: bool = Field(
        default=True,
        description="Enforce strict profile validation",
        env="CLOUDWAN_STRICT_PROFILE_VALIDATION",
    )

    assume_role_arn: Optional[str] = Field(
        default=None,
        description="ARN of role to assume",
        env="CLOUDWAN_ASSUME_ROLE_ARN"
    )
    backup_profile: Optional[str] = Field(
        default=None,
        description="Fallback profile if assumption fails",
        env="CLOUDWAN_BACKUP_AWS_PROFILE"
    )
    min_session_duration: int = Field(
        default=900,
        ge=900,
        le=3600,
        description="Minimum session duration (seconds)"
    )
    max_session_duration: int = Field(
        default=3600,
        ge=900,
        le=43200,
        description="Maximum session duration (seconds)"
    )

    regions: List[str] = Field(
        default=["eu-west-1", "eu-west-2"], description="AWS regions"
    )

    max_retries: int = Field(
        default=3, ge=0, le=10, description="Max API retries"
    )

    timeout_seconds: int = Field(default=30, ge=5, le=300, description="API timeout")

    use_sts: bool = Field(default=True, description="Use STS for role assumption")

    network_manager: NetworkManagerConfig = Field(
        default_factory=NetworkManagerConfig,
        description="Network Manager configuration",
    )

    custom_endpoints: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom service endpoints",
        env="CLOUDWAN_AWS_CUSTOM_ENDPOINTS",
    )

    @validator("regions")
    def validate_regions(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Must specify at least one region")
        valid = set()
        for r in v:
            if not r or len(r.split("-")) < 3:
                raise ValueError(f"Invalid format: {r}")
            valid.add(r)
        return list(valid)


class MCPConfig(BaseModel):
    """MCP server configuration."""

    server_name: str = Field(default="CloudWAN-MCP-Server", description="Server name")
    port: int = Field(default=8080, ge=1024, le=65535, description="Listen port")
    host: str = Field(default="localhost", description="Host interface")
    max_connections: int = Field(default=100, ge=1, le=1000, description="Max connections")
    request_timeout: int = Field(default=300, ge=30, le=3600, description="Timeout")
    enable_cors: bool = Field(default=True, description="Enable CORS")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Format",
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size_mb: int = Field(default=100, ge=1, le=1000, description="Max size")
    backup_count: int = Field(default=5, ge=1, le=50, description="Backup count")

    @validator("level")
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid level: {v}")
        return v.upper()


class ToolsConfig(BaseModel):
    """Tools configuration with memory limits"""

    concurrent_regions: int = Field(
        default=5, ge=1, le=20, description="Max concurrent regions"
    )
    client_cache_memory_mb: int = Field(
        default=64, ge=16, le=1024, description="Max memory for client cache (MB)"
    )
    max_cached_clients: int = Field(
        default=100, ge=10, le=1000, description="Max cached AWS clients"
    )
    cache_ttl_seconds: int = Field(
        default=300, ge=0, le=3600, description="Cache TTL"
    )
    enable_caching: bool = Field(default=True, description="Enable caching")
    default_page_size: int = Field(default=50, ge=1, le=1000, description="Page size")
    max_path_trace_hops: int = Field(default=30, ge=1, le=100, description="Max hops")


class VisualizationConfig(BaseModel):
    """Visualization configuration."""

    default_profile: str = Field(
        default=None,
        description="AWS profile for visualization",
        env="CLOUDWAN_VIZ_AWS_PROFILE",
    )

    custom_endpoint: Optional[str] = Field(
        default=None,
        description="Custom NetworkManager endpoint",
        env="CLOUDWAN_VIZ_NETWORK_MANAGER_ENDPOINT",
    )

    network_manager_region: str = Field(
        default=None,
        description="Region for API calls",
        env="CLOUDWAN_VIZ_NETWORK_MANAGER_REGION",
    )

    @field_validator("custom_endpoint")
    @classmethod
    def validate_custom_endpoint(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.startswith("https://"):
                raise ValueError("Must use HTTPS")
            if not v.endswith(".amazonaws.com"):
                raise ValueError("Invalid AWS endpoint")
        return v

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
        description="Segment colors",
    )

    output_directory: str = Field(
        default="cloudwan_visualization_output",
        description="Output directory",
    )

    export_formats: List[str] = Field(
        default=["html", "png", "json", "report"],
        description="Export formats",
    )

    enable_three_pane_layout: bool = Field(default=True, description="Three-pane layout")
    show_segment_details: bool = Field(default=True, description="Show details")
    show_inspection_flows: bool = Field(default=True, description="Show flows")
    show_tgw_peering: bool = Field(default=True, description="Show peering")
    show_regional_separators: bool = Field(default=True, description="Show separators")

    region_positions: Dict[str, Dict[str, float]] = Field(
        default={
            "eu-west-1": {"lat": 53.35, "lon": -6.26},
            "eu-west-2": {"lat": 51.51, "lon": -0.13},
            "us-east-1": {"lat": 39.04, "lon": -77.49},
            "us-west-2": {"lat": 45.52, "lon": -122.68},
        },
        description="Region positions",
    )

    figure_width: int = Field(default=1600, ge=800, le=3200, description="Width")
    figure_height: int = Field(default=900, ge=600, le=1800, description="Height")
    visualization_export_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Export scale"
    )


class CloudWANConfig(BaseSettings):
    """Main configuration class."""

    aws: AWSConfig = Field(default_factory=AWSConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)

    debug: bool = Field(default=False, description="Debug mode")
    config_file: Optional[str] = Field(default=None, description="Config file path")
    environment: str = Field(
        default="development",
        description="Environment name",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False

    def __init__(self, **kwargs):
        if "strict_profile_validation" in kwargs:
            strict_mode = kwargs.pop("strict_profile_validation")
            if "aws" not in kwargs:
                kwargs["aws"] = {"strict_profile_validation": strict_mode}
            else:
                kwargs["aws"]["strict_profile_validation"] = strict_mode

        # Parse environment variables for AWS config if not provided
        if "aws" not in kwargs:
            kwargs["aws"] = {}
        
        aws_config = kwargs["aws"] 
        
        # Handle CLOUDWAN_AWS_DEFAULT_PROFILE (with fallback to legacy CLOUDWAN_AWS_PROFILE)
        if "default_profile" not in aws_config:
            env_profile = os.environ.get("CLOUDWAN_AWS_DEFAULT_PROFILE") or os.environ.get("CLOUDWAN_AWS_PROFILE")
            if env_profile:
                aws_config["default_profile"] = env_profile
        
        # Handle CLOUDWAN_AWS_CUSTOM_ENDPOINTS with JSON parsing
        if "custom_endpoints" not in aws_config:
            env_endpoints = os.environ.get("CLOUDWAN_AWS_CUSTOM_ENDPOINTS")
            if env_endpoints:
                try:
                    import json
                    parsed_endpoints = json.loads(env_endpoints)
                    if isinstance(parsed_endpoints, dict):
                        aws_config["custom_endpoints"] = parsed_endpoints
                    else:
                        logger.warning("CLOUDWAN_AWS_CUSTOM_ENDPOINTS is not a JSON object")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse CLOUDWAN_AWS_CUSTOM_ENDPOINTS as JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing custom endpoints: {e}")
        
        # Set NetworkManager region based on custom endpoint if provided
        if aws_config.get("custom_endpoints", {}).get("networkmanager"):
            endpoint_url = aws_config["custom_endpoints"]["networkmanager"]
            # Extract region from endpoint URL (e.g., custom-networkmanager.us-west-2.amazonaws.com)
            if "us-west-2" in endpoint_url:
                if "network_manager" not in aws_config:
                    aws_config["network_manager"] = {}
                aws_config["network_manager"]["region"] = "us-west-2"
                logger.info("Set NetworkManager region to us-west-2 based on custom endpoint")

        super().__init__(**kwargs)
        self.aws.network_manager.set_environment_variables()

        if self.aws.strict_profile_validation:
            logger.info("Strict profile validation enabled")
        else:
            logger.warning("Permissive profile validation enabled")

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        valid = {"development", "staging", "production", "test"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid environment: {v}")
        return v.lower()

    def get_log_level(self) -> str:
        return "DEBUG" if self.debug else self.logging.level

    def get_aws_session_name(self) -> str:
        return f"cloudwan-mcp-{self.environment}-{os.getpid()}"

    def is_production(self) -> bool:
        return self.environment == "production"

    def get_cache_key_prefix(self) -> str:
        return f"cloudwan_mcp_{self.environment}_{self.mcp.server_name}"

    def get_tool_settings(self, tool_name: str) -> Dict[str, Any]:
        settings = {
            "concurrent_regions": self.tools.concurrent_regions,
            "cache_ttl": self.tools.cache_ttl_seconds,
            "enable_caching": self.tools.enable_caching,
            "page_size": self.tools.default_page_size,
            "aws_timeout": self.aws.timeout_seconds,
            "aws_retries": self.aws.max_retries,
        }

        overrides = {
            "network_path_trace": {"max_hops": self.tools.max_path_trace_hops},
            "cloudwan_segments": {
                "segment_details": True,
                "include_routing": True,
                "enable_security_analysis": True,
            },
        }

        if tool_name in overrides:
            settings.update(overrides[tool_name])
        return settings

    @classmethod
    def from_file(cls, path: str) -> "CloudWANConfig":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing: {path}")

        _, ext = os.path.splitext(path)
        if ext.lower() == ".json":
            import json
            with open(path, "r") as f:
                return cls(**json.load(f))
        elif ext.lower() in (".yaml", ".yml"):
            import yaml
            with open(path, "r") as f:
                return cls(**yaml.safe_load(f))
        raise ValueError(f"Unsupported format: {ext}")

    def to_file(self, path: str) -> None:
        _, ext = os.path.splitext(path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        if ext.lower() == ".json":
            import json
            with open(path, "w") as f:
                json.dump(self.dict(), f, indent=2)
        elif ext.lower() in (".yaml", ".yml"):
            import yaml
            with open(path, "w") as f:
                yaml.dump(self.dict(), f)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    def validate(self) -> tuple[bool, list[str]]:
        errors = []
        if not self.validate_aws_access().get("success"):
            errors.append("AWS access validation failed")

        if self.logging.file_path and not os.path.exists(
            os.path.dirname(self.logging.file_path)
        ):
            errors.append(f"Log directory missing: {self.logging.file_path}")

        if not os.path.exists(self.visualization.output_directory):
            errors.append("Visualization directory missing")

        return not errors, errors

    def validate_aws_access(self) -> Dict[str, Any]:
        try:
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @contextlib.contextmanager
    def with_aws_environment(self) -> Iterator[Dict[str, str]]:
        with self.aws.network_manager.with_applied_environment() as env:
            yield env

    def apply_aws_environment_to_callable(self, func: Callable, *args, **kwargs) -> Any:
        with self.with_aws_environment():
            return func(*args, **kwargs)

    def get_version_info(self) -> str:
        from . import __version__
        return __version__


def get_default_config() -> CloudWANConfig:
    return CloudWANConfig()


def load_config_from_env() -> CloudWANConfig:
    return CloudWANConfig()
