"""
Environment-Specific Configuration Templates.

This module provides pre-configured templates for different deployment environments.
Each template optimizes settings for specific use cases and environments.
"""

from typing import Dict, Any
import os

from .centralized_config import (
    CentralizedConfig,
    Environment,
    LogLevel,
    SecurityLevel,
    DiagramFormat,
)


def create_development_config(**overrides) -> CentralizedConfig:
    """
    Create development environment configuration.

    Optimized for local development with:
    - Debug logging enabled
    - Relaxed security settings
    - Fast cache TTL for quick iteration
    - Smaller resource limits

    Args:
        **overrides: Configuration overrides

    Returns:
        Development configuration instance
    """
    config_data = {
        "environment": Environment.DEVELOPMENT,
        "debug": True,
        # Logging optimized for development
        "logging": {
            "level": LogLevel.DEBUG,
            "format_string": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "enable_structured_logging": False,
        },
        # AWS settings for development
        "aws": {
            "regions": ["eu-west-1"],  # Single region for faster development
            "max_retries": 2,
            "timeout_seconds": 15,
            "max_concurrent_requests": 5,
        },
        # Agent settings for development
        "agents": {
            "max_agents": 2,
            "agent_timeout_seconds": 60,
            "max_retries": 2,
            "enable_consensus": True,
            "consensus_threshold": 0.6,  # Lower threshold for faster testing
        },
        # Diagram settings for development
        "diagrams": {
            "default_width": 1200,
            "default_height": 800,
            "default_dpi": 150,  # Lower DPI for faster generation
            "max_elements_default": 30,
            "generation_timeout_seconds": 60,
            "export_formats": [DiagramFormat.PNG],  # Single format for speed
            "enable_caching": True,
            "cache_ttl_seconds": 60,  # Short cache for development
        },
        # Security settings for development
        "security": {
            "default_security_level": SecurityLevel.LOW,
            "enable_sandbox": True,
            "sandbox_timeout_seconds": 30,
            "max_memory_mb": 256,
            "enable_code_scanning": False,  # Disable for speed
        },
        # Performance settings for development
        "performance": {
            "max_workers": 4,
            "max_concurrent_regions": 2,
            "cache_ttl_seconds": 60,
            "memory_limit_mb": 512,
            "batch_size": 10,
        },
        # MCP settings for development
        "mcp": {"host": "localhost", "port": 8080, "max_connections": 10},
    }

    # Apply any overrides
    config_data.update(overrides)

    return CentralizedConfig(**config_data)


def create_testing_config(**overrides) -> CentralizedConfig:
    """
    Create testing environment configuration.

    Optimized for automated testing with:
    - Debug logging for test diagnostics
    - Strict timeouts for fast test execution
    - Minimal resource usage
    - Deterministic behavior

    Args:
        **overrides: Configuration overrides

    Returns:
        Testing configuration instance
    """
    config_data = {
        "environment": Environment.TESTING,
        "debug": True,
        # Logging for testing
        "logging": {
            "level": LogLevel.DEBUG,
            "format_string": "%(name)s - %(levelname)s - %(message)s",
            "enable_structured_logging": False,
        },
        # AWS settings for testing
        "aws": {
            "regions": ["eu-west-1"],  # Single region for consistent tests
            "max_retries": 1,  # Fast failure for tests
            "timeout_seconds": 10,
            "max_concurrent_requests": 2,
        },
        # Agent settings for testing
        "agents": {
            "max_agents": 2,
            "agent_timeout_seconds": 30,
            "max_retries": 1,
            "retry_backoff_factor": 1.0,  # No backoff for tests
            "message_timeout_seconds": 10,
            "heartbeat_interval_seconds": 5,
            "enable_consensus": True,
            "consensus_threshold": 0.5,
        },
        # Diagram settings for testing
        "diagrams": {
            "default_width": 800,
            "default_height": 600,
            "default_dpi": 72,  # Minimum DPI for speed
            "max_elements_default": 10,
            "generation_timeout_seconds": 30,
            "export_formats": [DiagramFormat.PNG],
            "enable_caching": False,  # Disable caching for deterministic tests
            "output_directory": "/tmp/test_diagrams",
        },
        # Security settings for testing
        "security": {
            "default_security_level": SecurityLevel.LOW,
            "enable_sandbox": True,
            "sandbox_timeout_seconds": 15,
            "max_memory_mb": 128,
            "enable_code_scanning": True,  # Enable for security tests
        },
        # Performance settings for testing
        "performance": {
            "max_workers": 2,
            "max_concurrent_regions": 1,
            "enable_caching": False,  # Disable for consistent tests
            "request_timeout_seconds": 10,
            "memory_limit_mb": 256,
            "batch_size": 5,
        },
        # MCP settings for testing
        "mcp": {
            "host": "localhost",
            "port": 8081,  # Different port to avoid conflicts
            "max_connections": 5,
            "request_timeout_seconds": 30,
        },
    }

    # Apply any overrides
    config_data.update(overrides)

    return CentralizedConfig(**config_data)


def create_staging_config(**overrides) -> CentralizedConfig:
    """
    Create staging environment configuration.

    Optimized for pre-production testing with:
    - Production-like security settings
    - Comprehensive logging
    - Resource limits similar to production
    - Full feature set enabled

    Args:
        **overrides: Configuration overrides

    Returns:
        Staging configuration instance
    """
    config_data = {
        "environment": Environment.STAGING,
        "debug": False,
        # Logging for staging
        "logging": {
            "level": LogLevel.INFO,
            "format_string": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            "enable_structured_logging": True,
            "file_path": "/var/log/cloudwan_mcp/staging.log",
            "max_file_size_mb": 50,
            "backup_count": 10,
        },
        # AWS settings for staging
        "aws": {
            "regions": ["eu-west-1", "eu-west-2"],
            "max_retries": 3,
            "timeout_seconds": 30,
            "max_concurrent_requests": 15,
        },
        # Agent settings for staging
        "agents": {
            "max_agents": 4,
            "agent_timeout_seconds": 90,
            "max_retries": 3,
            "enable_consensus": True,
            "consensus_threshold": 0.75,
        },
        # Diagram settings for staging
        "diagrams": {
            "default_width": 1600,
            "default_height": 1200,
            "default_dpi": 300,
            "max_elements_default": 75,
            "generation_timeout_seconds": 120,
            "export_formats": [DiagramFormat.PNG, DiagramFormat.HTML],
            "enable_caching": True,
            "cache_ttl_seconds": 300,
        },
        # Security settings for staging
        "security": {
            "default_security_level": SecurityLevel.HIGH,
            "enable_sandbox": True,
            "sandbox_timeout_seconds": 60,
            "max_memory_mb": 512,
            "enable_code_scanning": True,
        },
        # Performance settings for staging
        "performance": {
            "max_workers": 8,
            "max_concurrent_regions": 4,
            "enable_caching": True,
            "cache_ttl_seconds": 300,
            "memory_limit_mb": 1024,
            "batch_size": 25,
        },
        # MCP settings for staging
        "mcp": {
            "host": "0.0.0.0",
            "port": 8080,
            "max_connections": 50,
            "request_timeout_seconds": 180,
        },
    }

    # Apply any overrides
    config_data.update(overrides)

    return CentralizedConfig(**config_data)


def create_production_config(**overrides) -> CentralizedConfig:
    """
    Create production environment configuration.

    Optimized for production deployment with:
    - Maximum security settings
    - Comprehensive error handling
    - Optimal resource utilization
    - Full monitoring and logging

    Args:
        **overrides: Configuration overrides

    Returns:
        Production configuration instance
    """
    config_data = {
        "environment": Environment.PRODUCTION,
        "debug": False,
        # Logging for production
        "logging": {
            "level": LogLevel.INFO,
            "format_string": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            "enable_structured_logging": True,
            "file_path": "/var/log/cloudwan_mcp/production.log",
            "max_file_size_mb": 100,
            "backup_count": 20,
        },
        # AWS settings for production
        "aws": {
            "regions": ["eu-west-1", "eu-west-2", "us-east-1"],
            "max_retries": 5,
            "timeout_seconds": 45,
            "max_concurrent_requests": 20,
            "connection_pool_size": 50,
        },
        # Agent settings for production
        "agents": {
            "max_agents": 8,
            "agent_timeout_seconds": 120,
            "max_retries": 5,
            "retry_backoff_factor": 2.0,
            "enable_consensus": True,
            "consensus_threshold": 0.8,  # Higher threshold for production reliability
        },
        # Diagram settings for production
        "diagrams": {
            "default_width": 1600,
            "default_height": 1200,
            "default_dpi": 300,
            "max_elements_default": 100,
            "generation_timeout_seconds": 180,
            "export_formats": [
                DiagramFormat.PNG,
                DiagramFormat.SVG,
                DiagramFormat.HTML,
            ],
            "enable_caching": True,
            "cache_ttl_seconds": 600,  # Longer cache for production
            "generate_metadata": True,
        },
        # Security settings for production
        "security": {
            "default_security_level": SecurityLevel.CRITICAL,
            "enable_sandbox": True,
            "sandbox_timeout_seconds": 90,
            "max_memory_mb": 1024,
            "enable_code_scanning": True,
            "scan_timeout_seconds": 60,
        },
        # Performance settings for production
        "performance": {
            "max_workers": 16,
            "max_concurrent_regions": 8,
            "enable_caching": True,
            "cache_ttl_seconds": 600,
            "cache_max_size": 2000,
            "memory_limit_mb": 2048,
            "batch_size": 50,
            "gc_threshold": 0.85,
        },
        # MCP settings for production
        "mcp": {
            "host": "0.0.0.0",
            "port": 8080,
            "max_connections": 200,
            "request_timeout_seconds": 300,
            "enable_cors": False,  # Disable CORS in production for security
        },
    }

    # Apply any overrides
    config_data.update(overrides)

    return CentralizedConfig(**config_data)


def create_high_performance_config(**overrides) -> CentralizedConfig:
    """
    Create high-performance configuration template.

    Optimized for maximum throughput with:
    - Increased worker counts
    - Aggressive caching
    - Parallel processing
    - Higher resource limits

    Args:
        **overrides: Configuration overrides

    Returns:
        High-performance configuration instance
    """
    base_config = create_production_config()

    performance_overrides = {
        "agents": {"max_agents": 12, "agent_timeout_seconds": 180},
        "aws": {"max_concurrent_requests": 30, "connection_pool_size": 100},
        "diagrams": {"max_elements_default": 150, "generation_timeout_seconds": 240},
        "performance": {
            "max_workers": 24,
            "max_concurrent_regions": 12,
            "cache_max_size": 5000,
            "memory_limit_mb": 4096,
            "batch_size": 100,
        },
        "mcp": {"max_connections": 500},
    }

    # Merge overrides
    config_dict = base_config.model_dump()

    for section, section_overrides in performance_overrides.items():
        if section in config_dict:
            config_dict[section].update(section_overrides)

    config_dict.update(overrides)

    return CentralizedConfig(**config_dict)


def create_minimal_config(**overrides) -> CentralizedConfig:
    """
    Create minimal resource configuration template.

    Optimized for resource-constrained environments with:
    - Minimal worker counts
    - Reduced memory usage
    - Limited caching
    - Basic features only

    Args:
        **overrides: Configuration overrides

    Returns:
        Minimal configuration instance
    """
    config_data = {
        "environment": Environment.DEVELOPMENT,
        "debug": False,
        # Minimal logging
        "logging": {
            "level": LogLevel.WARNING,
            "format_string": "%(levelname)s - %(message)s",
            "enable_structured_logging": False,
        },
        # Minimal AWS settings
        "aws": {
            "regions": ["eu-west-1"],
            "max_retries": 1,
            "timeout_seconds": 20,
            "max_concurrent_requests": 2,
        },
        # Minimal agent settings
        "agents": {
            "max_agents": 1,
            "agent_timeout_seconds": 60,
            "max_retries": 1,
            "enable_consensus": False,  # Disable for minimal setup
        },
        # Minimal diagram settings
        "diagrams": {
            "default_width": 800,
            "default_height": 600,
            "default_dpi": 150,
            "max_elements_default": 20,
            "generation_timeout_seconds": 60,
            "export_formats": [DiagramFormat.PNG],
            "enable_caching": False,
        },
        # Minimal security settings
        "security": {
            "default_security_level": SecurityLevel.LOW,
            "enable_sandbox": False,  # Disable sandbox for minimal resources
            "enable_code_scanning": False,
        },
        # Minimal performance settings
        "performance": {
            "max_workers": 2,
            "max_concurrent_regions": 1,
            "enable_caching": False,
            "memory_limit_mb": 256,
            "batch_size": 5,
        },
        # Minimal MCP settings
        "mcp": {"max_connections": 5, "request_timeout_seconds": 60},
    }

    # Apply any overrides
    config_data.update(overrides)

    return CentralizedConfig(**config_data)


def load_config_from_environment() -> CentralizedConfig:
    """
    Load configuration based on environment variables.

    Reads CLOUDWAN_ENVIRONMENT to determine which config template to use.
    Falls back to development if not specified.

    Returns:
        Environment-appropriate configuration
    """
    env_name = os.getenv("CLOUDWAN_ENVIRONMENT", "development").lower()

    config_factories = {
        "development": create_development_config,
        "dev": create_development_config,
        "testing": create_testing_config,
        "test": create_testing_config,
        "staging": create_staging_config,
        "stage": create_staging_config,
        "production": create_production_config,
        "prod": create_production_config,
        "performance": create_high_performance_config,
        "perf": create_high_performance_config,
        "minimal": create_minimal_config,
        "min": create_minimal_config,
    }

    factory = config_factories.get(env_name, create_development_config)
    return factory()


def get_config_template_info() -> Dict[str, Dict[str, Any]]:
    """
    Get information about available configuration templates.

    Returns:
        Dictionary with template information
    """
    return {
        "development": {
            "description": "Local development with debug logging and relaxed security",
            "use_case": "Local development and debugging",
            "resource_usage": "Low",
            "security_level": "Low",
            "performance": "Basic",
        },
        "testing": {
            "description": "Automated testing with fast timeouts and minimal resources",
            "use_case": "Unit tests, integration tests, CI/CD",
            "resource_usage": "Minimal",
            "security_level": "Low",
            "performance": "Fast execution",
        },
        "staging": {
            "description": "Pre-production environment with production-like settings",
            "use_case": "Pre-production testing and validation",
            "resource_usage": "Medium-High",
            "security_level": "High",
            "performance": "Good",
        },
        "production": {
            "description": "Production deployment with maximum security and reliability",
            "use_case": "Production workloads",
            "resource_usage": "High",
            "security_level": "Critical",
            "performance": "Optimized",
        },
        "performance": {
            "description": "High-throughput configuration with maximum resources",
            "use_case": "High-volume processing and enterprise deployments",
            "resource_usage": "Maximum",
            "security_level": "Critical",
            "performance": "Maximum",
        },
        "minimal": {
            "description": "Resource-constrained environment with basic features",
            "use_case": "Edge computing, containers, limited resources",
            "resource_usage": "Minimal",
            "security_level": "Low",
            "performance": "Basic",
        },
    }
