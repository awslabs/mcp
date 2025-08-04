"""
Agent registry system for dynamic agent discovery and management.

This module provides the registry system that discovers, registers, and manages
all CLI agents in the CloudWAN MCP system. It enables dynamic agent discovery
and provides a centralized way to manage agent lifecycles.
"""

import asyncio
import importlib
import inspect
import logging
import os
import pkgutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable

from .base import AbstractAgent, AgentPool, AgentError
from .models import (
    AgentType,
    AgentConfiguration,
    AgentRegistry as AgentRegistryModel,
    CommandType
)

logger = logging.getLogger(__name__)


class RegistryError(AgentError):
    """Error raised by the agent registry."""
    pass


class AgentNotFoundError(RegistryError):
    """Error raised when an agent is not found in the registry."""
    pass


class AgentAlreadyRegisteredError(RegistryError):
    """Error raised when trying to register an already registered agent."""
    pass


class AgentRegistrySystem:
    """
    Central registry system for managing CloudWAN MCP agents.
    
    This class provides:
    - Dynamic agent discovery and registration
    - Agent lifecycle management
    - Health monitoring
    - Load balancing and routing
    - Configuration management
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent registry system.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.agents: Dict[str, AbstractAgent] = {}
        self.agent_pools: Dict[AgentType, AgentPool] = {}
        self.agent_configs: Dict[str, AgentConfiguration] = {}
        self.registry_model = AgentRegistryModel()
        
        # Discovery settings
        self.discovery_paths: List[str] = []
        self.auto_discovery_enabled = self.config.get('auto_discovery', True)
        self.discovery_patterns = self.config.get('discovery_patterns', ['*_agent.py'])
        
        # Health monitoring
        self.health_check_interval = self.config.get('health_check_interval', 60)
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self.event_callbacks: Dict[str, List[Callable]] = {
            'agent_registered': [],
            'agent_unregistered': [],
            'agent_health_changed': [],
            'agent_error': []
        }
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Set up discovery paths
        self._setup_discovery_paths()
    
    def _setup_discovery_paths(self) -> None:
        """Set up default discovery paths."""
        # Add current package path
        current_dir = Path(__file__).parent
        self.discovery_paths = [
            str(current_dir),
            str(current_dir.parent / 'tools'),
            str(current_dir.parent / 'cli' / 'commands'),
        ]
        
        # Add paths from config
        config_paths = self.config.get('discovery_paths', [])
        self.discovery_paths.extend(config_paths)
        
        # Remove duplicates and ensure paths exist
        self.discovery_paths = list(set(path for path in self.discovery_paths if Path(path).exists()))
        
        self.logger.debug(f"Discovery paths configured: {self.discovery_paths}")
    
    async def start(self) -> None:
        """Start the registry system."""
        self.logger.info("Starting agent registry system")
        
        # Discover and register agents
        if self.auto_discovery_enabled:
            await self.discover_agents()
        
        # Start health monitoring
        await self.start_health_monitoring()
        
        self.logger.info(f"Agent registry system started with {len(self.agents)} agents")
    
    async def stop(self) -> None:
        """Stop the registry system."""
        self.logger.info("Stopping agent registry system")
        
        # Stop health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all agents
        for agent in list(self.agents.values()):
            await self.unregister_agent(agent.agent_id)
        
        self.logger.info("Agent registry system stopped")
    
    async def discover_agents(self) -> List[str]:
        """
        Discover agents in the configured discovery paths.
        
        Returns:
            List of discovered agent IDs
        """
        self.logger.info("Starting agent discovery")
        discovered_agents = []
        
        for discovery_path in self.discovery_paths:
            self.logger.debug(f"Discovering agents in {discovery_path}")
            
            try:
                path_obj = Path(discovery_path)
                if not path_obj.exists():
                    self.logger.warning(f"Discovery path does not exist: {discovery_path}")
                    continue
                
                # Discover Python modules
                for module_info in pkgutil.iter_modules([discovery_path]):
                    if self._should_discover_module(module_info.name):
                        try:
                            agent_classes = await self._discover_agents_in_module(
                                module_info.name, discovery_path
                            )
                            for agent_class in agent_classes:
                                agent_id = await self._register_agent_class(agent_class)
                                if agent_id:
                                    discovered_agents.append(agent_id)
                        except Exception as e:
                            self.logger.error(f"Error discovering agents in module {module_info.name}: {e}")
                            
            except Exception as e:
                self.logger.error(f"Error discovering agents in path {discovery_path}: {e}")
        
        self.logger.info(f"Agent discovery completed. Found {len(discovered_agents)} agents")
        return discovered_agents
    
    def _should_discover_module(self, module_name: str) -> bool:
        """Check if a module should be discovered for agents."""
        for pattern in self.discovery_patterns:
            if pattern == '*_agent.py':
                if module_name.endswith('_agent'):
                    return True
            elif pattern in module_name:
                return True
        return False
    
    async def _discover_agents_in_module(self, module_name: str, module_path: str) -> List[Type[AbstractAgent]]:
        """Discover agent classes in a specific module."""
        agent_classes = []
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                module_name, 
                os.path.join(module_path, f"{module_name}.py")
            )
            if spec is None or spec.loader is None:
                return agent_classes
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find agent classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, AbstractAgent) and 
                    obj is not AbstractAgent):
                    agent_classes.append(obj)
                    self.logger.debug(f"Discovered agent class: {name}")
        
        except Exception as e:
            self.logger.error(f"Error importing module {module_name}: {e}")
        
        return agent_classes
    
    async def _register_agent_class(self, agent_class: Type[AbstractAgent]) -> Optional[str]:
        """Register an agent class by creating an instance."""
        try:
            # Create agent instance
            agent_id = f"{agent_class.__name__}_{len(self.agents)}"
            
            # Determine agent type from class name or attributes
            agent_type = self._determine_agent_type(agent_class)
            
            # Create configuration
            config = self.config.get('agents', {}).get(agent_id, {})
            
            # Create agent instance
            agent = agent_class(agent_id, agent_type, config)
            
            # Register the agent
            await self.register_agent(agent)
            
            return agent_id
            
        except Exception as e:
            self.logger.error(f"Error registering agent class {agent_class.__name__}: {e}")
            return None
    
    def _determine_agent_type(self, agent_class: Type[AbstractAgent]) -> AgentType:
        """Determine the agent type from the class."""
        class_name = agent_class.__name__.lower()
        
        # Map class names to agent types
        type_mapping = {
            'documentation': AgentType.DOCUMENTATION,
            'testing': AgentType.TESTING,
            'analysis': AgentType.ANALYSIS,
            'monitoring': AgentType.MONITORING,
            'visualization': AgentType.VISUALIZATION,
            'troubleshooting': AgentType.TROUBLESHOOTING,
            'security': AgentType.SECURITY,
            'networking': AgentType.NETWORKING,
            'core': AgentType.CORE,
            'shared': AgentType.SHARED
        }
        
        for keyword, agent_type in type_mapping.items():
            if keyword in class_name:
                return agent_type
        
        # Default to CORE if no match found
        return AgentType.CORE
    
    async def register_agent(self, agent: AbstractAgent) -> None:
        """
        Register an agent in the registry.
        
        Args:
            agent: The agent to register
            
        Raises:
            AgentAlreadyRegisteredError: If agent is already registered
        """
        if agent.agent_id in self.agents:
            raise AgentAlreadyRegisteredError(f"Agent {agent.agent_id} is already registered")
        
        try:
            # Initialize the agent
            await agent.initialize()
            
            # Store the agent
            self.agents[agent.agent_id] = agent
            
            # Store configuration
            self.agent_configs[agent.agent_id] = agent.get_configuration()
            
            # Update registry model
            self.registry_model.add_agent(agent.get_configuration())
            
            # Add to agent pool
            if agent.agent_type not in self.agent_pools:
                self.agent_pools[agent.agent_type] = AgentPool(agent.agent_type)
            self.agent_pools[agent.agent_type].add_agent(agent)
            
            self.logger.info(f"Agent {agent.agent_id} registered successfully")
            
            # Notify event callbacks
            await self._notify_event_callbacks('agent_registered', agent)
            
        except Exception as e:
            self.logger.error(f"Error registering agent {agent.agent_id}: {e}")
            raise RegistryError(f"Failed to register agent {agent.agent_id}: {e}")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Raises:
            AgentNotFoundError: If agent is not found
        """
        if agent_id not in self.agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        
        try:
            # Shutdown the agent
            await agent.shutdown()
            
            # Remove from registry
            del self.agents[agent_id]
            del self.agent_configs[agent_id]
            
            # Update registry model
            if agent_id in self.registry_model.agents:
                del self.registry_model.agents[agent_id]
            
            # Remove from agent pool
            if agent.agent_type in self.agent_pools:
                pool = self.agent_pools[agent.agent_type]
                pool.agents = [a for a in pool.agents if a.agent_id != agent_id]
            
            self.logger.info(f"Agent {agent_id} unregistered successfully")
            
            # Notify event callbacks
            await self._notify_event_callbacks('agent_unregistered', agent)
            
        except Exception as e:
            self.logger.error(f"Error unregistering agent {agent_id}: {e}")
            raise RegistryError(f"Failed to unregister agent {agent_id}: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[AbstractAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[AbstractAgent]:
        """Get all agents of a specific type."""
        return [agent for agent in self.agents.values() if agent.agent_type == agent_type]
    
    def get_agents_for_command(self, command_type: CommandType) -> List[AbstractAgent]:
        """Get agents that can handle a specific command type."""
        agent_ids = self.registry_model.get_agents_for_command(command_type)
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    def get_agents_for_capability(self, capability_name: str) -> List[AbstractAgent]:
        """Get agents that provide a specific capability."""
        agent_ids = self.registry_model.get_agents_for_capability(capability_name)
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    def get_best_agent_for_command(self, command_type: CommandType) -> Optional[AbstractAgent]:
        """Get the best agent for a specific command type based on health and load."""
        agents = self.get_agents_for_command(command_type)
        
        if not agents:
            return None
        
        # Filter healthy agents
        healthy_agents = [agent for agent in agents if agent.is_healthy()]
        
        if not healthy_agents:
            return None
        
        # Return least loaded agent
        return min(healthy_agents, key=lambda a: len(a.active_requests))
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status."""
        total_agents = len(self.agents)
        healthy_agents = len([a for a in self.agents.values() if a.is_healthy()])
        
        return {
            'total_agents': total_agents,
            'healthy_agents': healthy_agents,
            'health_percentage': (healthy_agents / total_agents * 100) if total_agents > 0 else 0,
            'agent_types': {
                agent_type.value: len(self.get_agents_by_type(agent_type))
                for agent_type in AgentType
            },
            'discovery_paths': self.discovery_paths,
            'auto_discovery_enabled': self.auto_discovery_enabled
        }
    
    async def start_health_monitoring(self) -> None:
        """Start health monitoring for all agents."""
        if self.health_check_task is not None:
            return
        
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Health monitoring started")
    
    async def _health_check_loop(self) -> None:
        """Health check loop for monitoring agent health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                for agent in list(self.agents.values()):
                    try:
                        previous_health = agent.is_healthy()
                        current_health = agent.is_healthy()
                        
                        if previous_health != current_health:
                            await self._notify_event_callbacks('agent_health_changed', agent)
                        
                        # Log unhealthy agents
                        if not current_health:
                            self.logger.warning(f"Agent {agent.agent_id} is unhealthy")
                    
                    except Exception as e:
                        self.logger.error(f"Error checking health of agent {agent.agent_id}: {e}")
                        await self._notify_event_callbacks('agent_error', agent)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    def register_event_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for registry events."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        
        self.event_callbacks[event_type].append(callback)
        self.logger.debug(f"Registered callback for event {event_type}")
    
    async def _notify_event_callbacks(self, event_type: str, agent: AbstractAgent) -> None:
        """Notify all callbacks for a specific event type."""
        callbacks = self.event_callbacks.get(event_type, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(agent)
                else:
                    callback(agent)
            except Exception as e:
                self.logger.error(f"Error in event callback for {event_type}: {e}")
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their details."""
        return [
            {
                'agent_id': agent.agent_id,
                'agent_type': agent.agent_type.value,
                'status': agent.status.value,
                'capabilities': len(agent.capabilities),
                'health': agent.is_healthy(),
                'uptime': int((datetime.utcnow() - agent.start_time).total_seconds()),
                'total_requests': agent.total_requests,
                'success_rate': agent.successful_requests / agent.total_requests * 100 if agent.total_requests > 0 else 0
            }
            for agent in self.agents.values()
        ]


# Global registry instance
_registry_instance: Optional[AgentRegistrySystem] = None


def get_registry() -> AgentRegistrySystem:
    """Get the global registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistrySystem()
    return _registry_instance


async def initialize_registry(config: Optional[Dict[str, Any]] = None) -> AgentRegistrySystem:
    """Initialize the global registry system."""
    global _registry_instance
    _registry_instance = AgentRegistrySystem(config)
    await _registry_instance.start()
    return _registry_instance


async def shutdown_registry() -> None:
    """Shutdown the global registry system."""
    global _registry_instance
    if _registry_instance:
        await _registry_instance.stop()
        _registry_instance = None