"""
Configuration Migration Example.

This module demonstrates how to migrate from the old scattered configuration
approach to the new centralized configuration system.

Example shows migration of CloudWANIntegratedDiagramSystem to use centralized config.
"""

import os
import logging
from typing import Optional
from pathlib import Path

# Old imports (what we're migrating FROM)
"""
from ...config import CloudWANConfig
from dataclasses import dataclass, field

@dataclass
class DiagramConfig:
    default_output_dir: str = field(default_factory=lambda: str(Path(tempfile.gettempdir()) / "cloudwan_diagrams"))
    max_elements: int = 75
    default_format: DiagramFormat = DiagramFormat.PNG
    default_diagram_type: DiagramType = DiagramType.THREE_PANE
    security_level: SecuritySeverity = SecuritySeverity.MEDIUM
    timeout_seconds: int = 120
    use_multi_agent: bool = True
    cache_diagrams: bool = True
    cache_dir: Optional[str] = None
"""

# New imports (what we're migrating TO)
from ..config import (
    get_config,
    get_diagram_config,
    CentralizedConfig,
)


class CloudWANIntegratedDiagramSystemOld:
    """
    OLD VERSION: Using scattered configuration approach.

    This shows the original pattern with multiple configuration sources
    and hardcoded values scattered throughout the code.
    """

    def __init__(self, config=None, diagram_config=None):
        """Old initialization with multiple config objects."""
        self.logger = logging.getLogger(__name__)

        # Old approach: Multiple configuration objects
        from ...config import CloudWANConfig

        self.config = config or CloudWANConfig()

        # Old approach: Separate diagram configuration
        if diagram_config is None:
            # Hardcoded defaults scattered in the code
            import tempfile
            from dataclasses import dataclass

            @dataclass
            class DiagramConfig:
                default_output_dir: str = str(Path(tempfile.gettempdir()) / "cloudwan_diagrams")
                max_elements: int = 75
                timeout_seconds: int = 120
                use_multi_agent: bool = True

            diagram_config = DiagramConfig()

        self.diagram_config = diagram_config

        # Old approach: Hardcoded values throughout initialization
        self.agent_timeout = 120  # Hardcoded
        self.max_workers = 10  # Hardcoded
        self.security_level = "MEDIUM"  # Hardcoded string
        self.enable_caching = True  # Hardcoded

        # Initialize output directory
        os.makedirs(self.diagram_config.default_output_dir, exist_ok=True)

    def generate_diagram(self, diagram_type=None, max_elements=None):
        """Old generation method with scattered configuration."""
        # Old approach: Multiple fallback chains
        diagram_type = diagram_type or "THREE_PANE"  # Hardcoded fallback
        max_elements = max_elements or self.diagram_config.max_elements

        # Old approach: Scattered timeout handling
        timeout = getattr(self.diagram_config, "timeout_seconds", 120)

        self.logger.info(f"Generating diagram with {max_elements} max elements, timeout {timeout}s")

        return {
            "success": True,
            "config_source": "scattered_multiple_sources",
            "max_elements": max_elements,
            "timeout": timeout,
        }


class CloudWANIntegratedDiagramSystemNew:
    """
    NEW VERSION: Using centralized configuration system.

    This shows the migrated version using centralized configuration
    with type safety, validation, and environment-specific settings.
    """

    def __init__(self, config: Optional[CentralizedConfig] = None):
        """New initialization with centralized configuration."""
        self.logger = logging.getLogger(__name__)

        # New approach: Single centralized configuration
        self.config = config or get_config()

        # All configuration comes from centralized source with type safety
        self.agent_timeout = self.config.agents.agent_timeout_seconds
        self.max_workers = self.config.performance.max_workers
        self.security_level = self.config.security.default_security_level
        self.enable_caching = self.config.performance.enable_caching

        # Diagram-specific settings from centralized config
        self.max_elements = self.config.diagrams.max_elements_default
        self.timeout_seconds = self.config.diagrams.generation_timeout_seconds
        self.output_directory = self.config.diagrams.output_directory
        self.default_format = self.config.diagrams.default_format

        # Initialize output directory
        os.makedirs(self.output_directory, exist_ok=True)

        self.logger.info(
            f"Initialized with centralized config: "
            f"env={self.config.environment.value}, "
            f"max_elements={self.max_elements}, "
            f"timeout={self.timeout_seconds}s"
        )

    def generate_diagram(self, diagram_type=None, max_elements=None):
        """New generation method using centralized configuration."""
        # New approach: Centralized defaults with type safety
        diagram_type = diagram_type or self.config.diagrams.default_layout.value
        max_elements = max_elements or self.config.diagrams.max_elements_default

        # New approach: Consistent timeout from centralized source
        timeout = self.config.diagrams.generation_timeout_seconds

        self.logger.info(
            f"Generating diagram: type={diagram_type}, "
            f"max_elements={max_elements}, timeout={timeout}s, "
            f"format={self.config.diagrams.default_format.value}"
        )

        return {
            "success": True,
            "config_source": "centralized_validated",
            "environment": self.config.environment.value,
            "max_elements": max_elements,
            "timeout": timeout,
            "format": self.config.diagrams.default_format.value,
            "security_level": self.config.security.default_security_level.value,
        }


class CloudWANIntegratedDiagramSystemCompatible:
    """
    COMPATIBILITY VERSION: Using legacy adapters for gradual migration.

    This shows how to use legacy adapters to maintain compatibility
    while gradually migrating to the new configuration system.
    """

    def __init__(self, config=None, diagram_config=None):
        """Compatible initialization supporting both old and new approaches."""
        self.logger = logging.getLogger(__name__)

        # Compatible approach: Support both old and new config types
        if config is None:
            # Use new centralized config by default
            self.centralized_config = get_config()
        elif hasattr(config, "agents"):  # New CentralizedConfig
            self.centralized_config = config
        else:  # Old CloudWANConfig
            self.centralized_config = get_config()  # Use default centralized
            self.legacy_config = config  # Keep reference for compatibility

        # Compatible approach: Use legacy adapter if old diagram_config provided
        if diagram_config is None:
            # Use legacy adapter to get compatible configuration
            self.diagram_config = get_diagram_config()
        else:
            # Use provided configuration (old style)
            self.diagram_config = diagram_config

        # New approach underneath: Get settings from centralized config
        self.agent_timeout = self.centralized_config.agents.agent_timeout_seconds
        self.max_workers = self.centralized_config.performance.max_workers
        self.security_level = self.centralized_config.security.default_security_level

        # Initialize output directory
        os.makedirs(self.diagram_config.default_output_dir, exist_ok=True)

        self.logger.info(
            f"Initialized in compatibility mode: "
            f"env={self.centralized_config.environment.value}"
        )

    def generate_diagram(self, diagram_type=None, max_elements=None):
        """Compatible generation method supporting both approaches."""
        # Compatible approach: Use legacy adapter values but centralized fallbacks
        diagram_type = (
            diagram_type
            or getattr(self.diagram_config, "default_diagram_type", None)
            or self.centralized_config.diagrams.default_layout.value
        )

        max_elements = (
            max_elements
            or getattr(self.diagram_config, "max_elements", None)
            or self.centralized_config.diagrams.max_elements_default
        )

        timeout = (
            getattr(self.diagram_config, "timeout_seconds", None)
            or self.centralized_config.diagrams.generation_timeout_seconds
        )

        self.logger.info(f"Compatible generation: type={diagram_type}, elements={max_elements}")

        return {
            "success": True,
            "config_source": "compatible_legacy_adapter",
            "max_elements": max_elements,
            "timeout": timeout,
            "migration_status": "in_progress",
        }


def demonstrate_migration():
    """
    Demonstrate the differences between old and new configuration approaches.
    """
    print("CloudWAN Configuration Migration Demonstration")
    print("=" * 50)

    # 1. Old approach
    print("\n1. Old Approach (Scattered Configuration):")
    old_system = CloudWANIntegratedDiagramSystemOld()
    old_result = old_system.generate_diagram()
    print(f"   Result: {old_result}")

    # 2. New approach
    print("\n2. New Approach (Centralized Configuration):")
    new_system = CloudWANIntegratedDiagramSystemNew()
    new_result = new_system.generate_diagram()
    print(f"   Result: {new_result}")

    # 3. Compatible approach
    print("\n3. Compatible Approach (Legacy Adapters):")
    compatible_system = CloudWANIntegratedDiagramSystemCompatible()
    compatible_result = compatible_system.generate_diagram()
    print(f"   Result: {compatible_result}")

    # 4. Environment-specific configuration
    print("\n4. Environment-Specific Configuration:")
    from ..config import create_production_config, create_development_config

    dev_config = create_development_config()
    prod_config = create_production_config()

    print(
        f"   Development: max_elements={dev_config.diagrams.max_elements_default}, "
        f"security={dev_config.security.default_security_level.value}"
    )
    print(
        f"   Production: max_elements={prod_config.diagrams.max_elements_default}, "
        f"security={prod_config.security.default_security_level.value}"
    )

    # 5. Configuration validation
    print("\n5. Configuration Validation:")
    from ..config import ConfigurationValidator

    validator = ConfigurationValidator()
    dev_result = validator.validate_config(dev_config)
    prod_result = validator.validate_config(prod_config)

    print(f"   Development valid: {dev_result.valid}, issues: {len(dev_result.warnings)}")
    print(f"   Production valid: {prod_result.valid}, issues: {len(prod_result.warnings)}")


def demonstrate_environment_configuration():
    """
    Demonstrate environment-specific configuration usage.
    """
    from ..config import (
        create_development_config,
        create_testing_config,
        create_production_config,
    )

    print("\nEnvironment Configuration Comparison:")
    print("-" * 40)

    configs = {
        "Development": create_development_config(),
        "Testing": create_testing_config(),
        "Production": create_production_config(),
    }

    for env_name, config in configs.items():
        print(f"\n{env_name}:")
        print(f"  Debug: {config.debug}")
        print(f"  Max Agents: {config.agents.max_agents}")
        print(f"  Security Level: {config.security.default_security_level.value}")
        print(f"  Max Elements: {config.diagrams.max_elements_default}")
        print(f"  Cache Enabled: {config.performance.enable_caching}")


def demonstrate_migration_tools():
    """
    Demonstrate migration and validation tools.
    """
    from ..config import migrate_old_config, validate_migration

    print("\nMigration Tools Demonstration:")
    print("-" * 35)

    # Example old configuration
    old_config = {
        "aws_profile": "development",
        "max_elements": 30,
        "agent_timeout": 90,
        "log_level": "DEBUG",
        "security_level": "low",
    }

    print(f"\nOld configuration: {old_config}")

    # Migrate to new format
    new_config = migrate_old_config(old_config)
    print("\nMigrated successfully!")
    print(f"New max elements: {new_config.diagrams.max_elements_default}")
    print(f"New agent timeout: {new_config.agents.agent_timeout_seconds}")
    print(f"New security level: {new_config.security.default_security_level.value}")

    # Validate migration
    validation_result = validate_migration(old_config, new_config)
    print("\nMigration validation:")
    print(f"  Success: {validation_result['success']}")
    print(f"  Migrated keys: {len(validation_result['migrated_keys'])}")
    print(f"  Unmigrated keys: {len(validation_result['unmigrated_keys'])}")


if __name__ == "__main__":
    demonstrate_migration()
    demonstrate_environment_configuration()
    demonstrate_migration_tools()
