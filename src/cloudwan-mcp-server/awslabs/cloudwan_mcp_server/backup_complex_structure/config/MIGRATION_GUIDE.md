# Configuration Migration Guide

This guide helps migrate from the old scattered configuration approach to the new centralized configuration management system.

## Overview

The new centralized configuration system provides:
- **Type Safety**: Pydantic-based validation with helpful error messages
- **Centralization**: Single source of truth for all configuration parameters
- **Environment Support**: Built-in support for development, testing, staging, and production
- **Validation**: Comprehensive validation with security and performance checks
- **Migration Support**: Backward compatibility and migration tools

## Migration Steps

### 1. Update Imports

**Old Approach:**
```python
from awslabs.cloudwan_mcp_server.config import CloudWANConfig
from some_module import DiagramConfig, AgentConfig

config = CloudWANConfig()
diagram_config = DiagramConfig(max_elements=50)
```

**New Approach:**
```python
from awslabs.cloudwan_mcp_server.config import get_config, get_diagram_config

config = get_config()
diagram_config = get_diagram_config()  # Legacy-compatible
```

### 2. Replace Scattered Configuration Classes

#### Diagram Configuration Migration

**Old:**
```python
@dataclass
class DiagramConfig:
    max_elements: int = 75
    default_format: str = "PNG"
    timeout_seconds: int = 120
    output_dir: str = "/tmp/diagrams"
```

**New:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

config = get_config()
# Access via centralized config
max_elements = config.diagrams.max_elements_default
default_format = config.diagrams.default_format
timeout_seconds = config.diagrams.generation_timeout_seconds
output_dir = config.diagrams.output_directory

# Or use legacy adapter for drop-in replacement
from awslabs.cloudwan_mcp_server.config import get_diagram_config
diagram_config = get_diagram_config()
```

#### Agent Configuration Migration

**Old:**
```python
class AgentManager:
    def __init__(self):
        self.max_agents = 5
        self.timeout = 120
        self.retries = 3
```

**New:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

class AgentManager:
    def __init__(self):
        config = get_config()
        self.max_agents = config.agents.max_agents
        self.timeout = config.agents.agent_timeout_seconds
        self.retries = config.agents.max_retries
```

#### AWS Configuration Migration

**Old:**
```python
def create_aws_session():
    session = boto3.Session(
        profile_name=os.getenv('AWS_PROFILE'),
        region_name='us-west-2'
    )
    return session
```

**New:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

def create_aws_session():
    config = get_config()
    
    # Use centralized AWS environment context
    with config.with_aws_environment():
        session = boto3.Session(
            profile_name=config.aws.default_profile,
            region_name=config.aws.network_manager_region
        )
    return session
```

### 3. Environment Variable Migration

**Old Environment Variables:**
```bash
export AWS_PROFILE=my-profile
export DIAGRAM_MAX_ELEMENTS=50
export AGENT_TIMEOUT=60
export LOG_LEVEL=DEBUG
```

**New Environment Variables:**
```bash
export CLOUDWAN_ENVIRONMENT=development
export CLOUDWAN_AWS__DEFAULT_PROFILE=my-profile
export CLOUDWAN_DIAGRAM__MAX_ELEMENTS_DEFAULT=50
export CLOUDWAN_AGENT__AGENT_TIMEOUT_SECONDS=60
export CLOUDWAN_LOG__LEVEL=DEBUG
```

### 4. Configuration File Migration

**Old Configuration Files:**
```json
{
  "aws_profile": "my-profile",
  "max_elements": 50,
  "agent_timeout": 60,
  "log_level": "DEBUG"
}
```

**New Configuration Files:**
```json
{
  "environment": "development",
  "debug": true,
  "aws": {
    "default_profile": "my-profile",
    "regions": ["eu-west-1", "eu-west-2"]
  },
  "diagrams": {
    "max_elements_default": 50,
    "default_format": "png"
  },
  "agents": {
    "agent_timeout_seconds": 60,
    "max_agents": 5
  },
  "logging": {
    "level": "DEBUG"
  }
}
```

### 5. Component-Specific Migrations

#### Visualization Components

**Before:**
```python
class DiagramGenerator:
    def __init__(self, width=1600, height=1200, dpi=300):
        self.width = width
        self.height = height  
        self.dpi = dpi
        self.max_elements = 75
        self.timeout = 120
```

**After:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

class DiagramGenerator:
    def __init__(self):
        config = get_config()
        self.width = config.diagrams.default_width
        self.height = config.diagrams.default_height
        self.dpi = config.diagrams.default_dpi
        self.max_elements = config.diagrams.max_elements_default
        self.timeout = config.diagrams.generation_timeout_seconds
```

#### Multi-Agent Systems

**Before:**
```python
class AgentOrchestrator:
    def __init__(self):
        self.max_agents = int(os.getenv('MAX_AGENTS', '5'))
        self.consensus_threshold = 0.75
        self.message_timeout = 30
```

**After:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

class AgentOrchestrator:
    def __init__(self):
        config = get_config()
        self.max_agents = config.agents.max_agents
        self.consensus_threshold = config.agents.consensus_threshold
        self.message_timeout = config.agents.message_timeout_seconds
        self.enable_consensus = config.agents.enable_consensus
```

#### Security Components

**Before:**
```python
class SecurityScanner:
    def __init__(self):
        self.enabled = True
        self.timeout = 30
        self.allowed_packages = ['matplotlib', 'boto3']
        self.memory_limit = 512
```

**After:**
```python
from awslabs.cloudwan_mcp_server.config import get_config

class SecurityScanner:
    def __init__(self):
        config = get_config()
        self.enabled = config.security.enable_code_scanning
        self.timeout = config.security.scan_timeout_seconds
        self.allowed_packages = config.security.allowed_packages
        self.memory_limit = config.security.max_memory_mb
```

## Automated Migration Tools

### Configuration Migration Script

```python
from awslabs.cloudwan_mcp_server.config import migrate_old_config, validate_migration

# Migrate old configuration dictionary
old_config = {
    'aws_profile': 'my-profile',
    'max_elements': 50,
    'agent_timeout': 60
}

new_config = migrate_old_config(old_config)

# Validate migration
validation_result = validate_migration(old_config, new_config)
if validation_result['success']:
    print("Migration successful!")
else:
    print("Migration issues:")
    for error in validation_result['errors']:
        print(f"  - {error}")
```

### Environment-Specific Migration

```python
from awslabs.cloudwan_mcp_server.config import (
    create_development_config, 
    create_production_config,
    validate_configuration_file
)

# Create environment-specific configurations
dev_config = create_development_config(
    aws={'default_profile': 'dev-profile'},
    diagrams={'max_elements_default': 30}
)

prod_config = create_production_config(
    aws={'default_profile': 'prod-profile'},
    security={'default_security_level': 'critical'}
)

# Validate configurations
dev_result = validate_configuration_file('development.json')
prod_result = validate_configuration_file('production.json')
```

## Best Practices for Migration

### 1. Gradual Migration
- Start with less critical components
- Migrate one module at a time
- Keep legacy configurations during transition
- Test each migrated component thoroughly

### 2. Environment Variable Strategy
```bash
# Use environment-specific prefixes
export CLOUDWAN_ENVIRONMENT=development

# Component-specific variables
export CLOUDWAN_AWS__DEFAULT_PROFILE=dev-profile
export CLOUDWAN_AWS__REGIONS="eu-west-1,eu-west-2"

# Override specific settings
export CLOUDWAN_DIAGRAM__MAX_ELEMENTS_DEFAULT=30
export CLOUDWAN_SECURITY__DEFAULT_SECURITY_LEVEL=low
```

### 3. Configuration Validation
```python
from awslabs.cloudwan_mcp_server.config import (
    get_config, 
    ConfigurationValidator,
    generate_validation_report
)

# Validate current configuration
config = get_config()
validator = ConfigurationValidator()
result = validator.validate_config(config)

if not result.valid:
    report = generate_validation_report(result)
    print(report)
```

### 4. Legacy Compatibility
```python
from awslabs.cloudwan_mcp_server.config import get_diagram_config, get_aws_config

# Use legacy adapters for gradual migration
diagram_config = get_diagram_config()  # Returns LegacyDiagramConfig
aws_config = get_aws_config()          # Returns AWS config dict

# These work with existing code during transition
generator = DiagramGenerator(diagram_config)
session = create_aws_session(**aws_config)
```

## Troubleshooting Common Issues

### Import Errors
```python
# If centralized config imports fail, use legacy imports
try:
    from awslabs.cloudwan_mcp_server.config import get_config
    config = get_config()
except ImportError:
    from awslabs.cloudwan_mcp_server.config import CloudWANConfig
    config = CloudWANConfig()
```

### Configuration Conflicts
```python
from awslabs.cloudwan_mcp_server.config import validate_environment_variables

# Check for conflicting environment variables
env_result = validate_environment_variables()
if env_result.warnings:
    for warning in env_result.warnings:
        print(f"Warning: {warning}")
```

### Performance Issues
```python
from awslabs.cloudwan_mcp_server.config import create_minimal_config

# Use minimal configuration for resource-constrained environments
config = create_minimal_config()
```

### Security Concerns
```python
from awslabs.cloudwan_mcp_server.config import create_production_config

# Use production configuration with maximum security
config = create_production_config()
print(f"Security level: {config.security.default_security_level}")
print(f"Sandbox enabled: {config.security.enable_sandbox}")
```

## Testing Migration

### Unit Tests
```python
import unittest
from awslabs.cloudwan_mcp_server.config import get_config, create_testing_config, set_config

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Use testing configuration for tests
        test_config = create_testing_config()
        set_config(test_config)
    
    def test_diagram_config_migration(self):
        config = get_config()
        self.assertEqual(config.diagrams.max_elements_default, 10)  # Testing value
        self.assertEqual(config.diagrams.generation_timeout_seconds, 30)
    
    def test_agent_config_migration(self):
        config = get_config()
        self.assertEqual(config.agents.max_agents, 2)  # Testing value
        self.assertTrue(config.agents.enable_consensus)
```

### Integration Tests
```python
def test_full_system_with_new_config():
    """Test that the entire system works with new configuration."""
    from awslabs.cloudwan_mcp_server.config import create_development_config, set_config
    
    # Set up development configuration
    config = create_development_config()
    set_config(config)
    
    # Test components use new configuration
    diagram_generator = DiagramGenerator()
    agent_manager = AgentManager()
    
    assert diagram_generator.max_elements == config.diagrams.max_elements_default
    assert agent_manager.max_agents == config.agents.max_agents
```

## Migration Checklist

- [ ] **Audit Current Configuration**: Identify all scattered configuration parameters
- [ ] **Plan Migration Strategy**: Determine migration order and timeline
- [ ] **Update Imports**: Replace old configuration imports with new centralized imports
- [ ] **Migrate Environment Variables**: Update environment variables to use new prefixes
- [ ] **Update Configuration Files**: Convert to new hierarchical structure
- [ ] **Test Each Component**: Ensure each component works with new configuration
- [ ] **Validate Configuration**: Run validation tools to check for issues
- [ ] **Update Documentation**: Update component documentation to reflect new configuration
- [ ] **Performance Testing**: Verify performance with new configuration system
- [ ] **Production Deployment**: Deploy with appropriate environment-specific configuration

## Support and Resources

- **Validation Tools**: Use `validate_configuration_file()` and `ConfigurationValidator`
- **Migration Scripts**: Use `migrate_old_config()` for automated migration
- **Legacy Compatibility**: Use factory functions for gradual migration
- **Environment Templates**: Use `create_*_config()` functions for specific environments
- **Documentation**: Check component docstrings and type hints for configuration details

For additional help, see the configuration module documentation and examples in the `examples/` directory.