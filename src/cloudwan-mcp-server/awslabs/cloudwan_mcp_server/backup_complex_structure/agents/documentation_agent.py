"""
Documentation Agent for CloudWAN MCP CLI.

This agent provides documentation generation capabilities for CLI commands,
integrating with the multi-agent architecture for comprehensive documentation
support.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import AbstractAgent, AgentExecutionError, AgentInitializationError
from .models import (
    AgentType,
    AgentStatus,
    AgentCapability,
    CommandType,
    CommandContext
)

logger = logging.getLogger(__name__)


class DocumentationAgent(AbstractAgent):
    """
    Documentation agent for generating CLI command documentation.
    
    This agent provides comprehensive documentation generation capabilities
    including help text, usage examples, and integration guides.
    """
    
    def __init__(self, model=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DocumentationAgent.
        
        Args:
            model: The model for documentation generation (optional)
            config: Agent configuration
        """
        super().__init__(
            agent_id="documentation_agent",
            agent_type=AgentType.DOCUMENTATION,
            config=config
        )
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.agent_id}")
        
        # Documentation cache
        self.documentation_cache: Dict[str, str] = {}
        
    async def initialize(self) -> None:
        """Initialize the documentation agent."""
        try:
            self.logger.info("Initializing documentation agent")
            
            # Set up capabilities
            self.capabilities = self.get_capabilities()
            
            # Initialize model if provided
            if self.model and hasattr(self.model, 'initialize'):
                await self.model.initialize()
            
            # Set status to ready
            self.status = AgentStatus.READY
            self.logger.info("Documentation agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize documentation agent: {e}")
            self.status = AgentStatus.ERROR
            raise AgentInitializationError(f"Documentation agent initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the documentation agent."""
        try:
            self.logger.info("Shutting down documentation agent")
            
            # Cleanup model if needed
            if self.model and hasattr(self.model, 'shutdown'):
                await self.model.shutdown()
            
            # Clear cache
            self.documentation_cache.clear()
            
            self.status = AgentStatus.STOPPED
            self.logger.info("Documentation agent shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during documentation agent shutdown: {e}")
    
    async def execute_capability(
        self,
        capability_name: str,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Execute a documentation capability.
        
        Args:
            capability_name: Name of the capability to execute
            context: Command execution context
            parameters: Parameters for the capability
            
        Returns:
            Generated documentation or result
        """
        try:
            if capability_name == "generate_documentation":
                return await self._generate_documentation(context, parameters)
            elif capability_name == "generate_help":
                return await self._generate_help(context, parameters)
            elif capability_name == "generate_examples":
                return await self._generate_examples(context, parameters)
            elif capability_name == "validate_documentation":
                return await self._validate_documentation(context, parameters)
            else:
                raise AgentExecutionError(f"Unknown capability: {capability_name}")
                
        except Exception as e:
            self.logger.error(f"Error executing capability {capability_name}: {e}")
            raise AgentExecutionError(f"Capability execution failed: {e}")
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get the list of capabilities this agent provides."""
        return [
            AgentCapability(
                name="generate_documentation",
                command_types=[CommandType.HELP, CommandType.SHOW],
                description="Generate comprehensive documentation for CLI commands",
                priority=1,
                supports_async=True,
                timeout_seconds=60
            ),
            AgentCapability(
                name="generate_help",
                command_types=[CommandType.HELP],
                description="Generate help text for specific commands",
                priority=2,
                supports_async=True,
                timeout_seconds=30
            ),
            AgentCapability(
                name="generate_examples",
                command_types=[CommandType.HELP, CommandType.SHOW],
                description="Generate usage examples for CLI commands",
                priority=3,
                supports_async=True,
                timeout_seconds=45
            ),
            AgentCapability(
                name="validate_documentation",
                command_types=[CommandType.HELP],
                description="Validate existing documentation for accuracy",
                priority=4,
                supports_async=True,
                timeout_seconds=30
            )
        ]
    
    async def _generate_documentation(
        self,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate comprehensive documentation for a command."""
        command = parameters.get('command', '')
        
        if not command:
            raise AgentExecutionError("Command parameter is required for documentation generation")
        
        # Check cache first
        cache_key = f"doc_{command}"
        if cache_key in self.documentation_cache:
            self.logger.debug(f"Using cached documentation for command: {command}")
            return self.documentation_cache[cache_key]
        
        # Generate documentation
        try:
            if self.model:
                documentation = self.model.generate_documentation(command)
            else:
                # Fallback documentation generation
                documentation = await self._generate_fallback_documentation(command)
            
            # Cache the result
            self.documentation_cache[cache_key] = documentation
            
            self.logger.info(f"Generated documentation for command: {command}")
            return documentation
            
        except Exception as e:
            self.logger.error(f"Failed to generate documentation for {command}: {e}")
            raise AgentExecutionError(f"Documentation generation failed: {e}")
    
    async def _generate_help(
        self,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate help text for a command."""
        command = parameters.get('command', '')
        
        if not command:
            raise AgentExecutionError("Command parameter is required for help generation")
        
        try:
            if self.model and hasattr(self.model, 'generate_help'):
                help_text = self.model.generate_help(command)
            else:
                # Fallback help generation
                help_text = await self._generate_fallback_help(command)
            
            self.logger.info(f"Generated help for command: {command}")
            return help_text
            
        except Exception as e:
            self.logger.error(f"Failed to generate help for {command}: {e}")
            raise AgentExecutionError(f"Help generation failed: {e}")
    
    async def _generate_examples(
        self,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Generate usage examples for a command."""
        command = parameters.get('command', '')
        
        if not command:
            raise AgentExecutionError("Command parameter is required for examples generation")
        
        try:
            if self.model and hasattr(self.model, 'generate_examples'):
                examples = self.model.generate_examples(command)
            else:
                # Fallback examples generation
                examples = await self._generate_fallback_examples(command)
            
            self.logger.info(f"Generated {len(examples)} examples for command: {command}")
            return examples
            
        except Exception as e:
            self.logger.error(f"Failed to generate examples for {command}: {e}")
            raise AgentExecutionError(f"Examples generation failed: {e}")
    
    async def _validate_documentation(
        self,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate existing documentation for accuracy."""
        documentation = parameters.get('documentation', '')
        command = parameters.get('command', '')
        
        if not documentation:
            raise AgentExecutionError("Documentation parameter is required for validation")
        
        try:
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': []
            }
            
            # Basic validation checks
            if len(documentation) < 50:
                validation_result['warnings'].append("Documentation seems too short")
            
            if not any(keyword in documentation.lower() for keyword in ['usage', 'example', 'description']):
                validation_result['warnings'].append("Documentation lacks common sections")
            
            if command and command.lower() not in documentation.lower():
                validation_result['errors'].append(f"Command '{command}' not mentioned in documentation")
                validation_result['is_valid'] = False
            
            # Additional validation with model if available
            if self.model and hasattr(self.model, 'validate_documentation'):
                model_validation = self.model.validate_documentation(documentation, command)
                validation_result.update(model_validation)
            
            self.logger.info(f"Validated documentation for command: {command}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Failed to validate documentation: {e}")
            raise AgentExecutionError(f"Documentation validation failed: {e}")
    
    async def _generate_fallback_documentation(self, command: str) -> str:
        """Generate fallback documentation when no model is available."""
        return f"""
# {command.upper()} Command Documentation

## Description
The {command} command provides CloudWAN MCP functionality.

## Usage
```bash
cloudwan {command} [options]
```

## Options
- `--help`: Show help information
- `--verbose`: Enable verbose output
- `--profile`: AWS profile to use

## Examples
```bash
# Basic usage
cloudwan {command}

# With verbose output
cloudwan {command} --verbose

# Using specific AWS profile
cloudwan {command} --profile myprofile
```

## Notes
This is auto-generated documentation. For detailed information, 
please refer to the official CloudWAN MCP documentation.
"""
    
    async def _generate_fallback_help(self, command: str) -> str:
        """Generate fallback help text when no model is available."""
        return f"""
{command.upper()} - CloudWAN MCP Command

Usage: cloudwan {command} [options]

Options:
  --help     Show this help message
  --verbose  Enable verbose output
  --profile  AWS profile to use

For more information, run: cloudwan {command} --help
"""
    
    async def _generate_fallback_examples(self, command: str) -> List[str]:
        """Generate fallback examples when no model is available."""
        return [
            f"cloudwan {command}",
            f"cloudwan {command} --verbose",
            f"cloudwan {command} --profile myprofile"
        ]
    
    # Legacy method for backward compatibility
    def generate_documentation(self, command: str) -> str:
        """
        Legacy method for backward compatibility.
        
        Args:
            command (str): Name of the command.
            
        Returns:
            str: Generated documentation.
        """
        if self.model:
            return self.model.generate_documentation(command)
        else:
            # Return basic documentation
            return f"Documentation for {command} command"