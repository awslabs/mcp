"""
Base classes and interfaces for CloudWAN MCP agents.

This module provides the abstract base classes and interfaces that all agents
must implement to participate in the multi-agent CLI architecture.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from .models import (
    AgentType,
    AgentStatus,
    AgentCapability,
    AgentConfiguration,
    AgentRequest,
    AgentResponse,
    AgentHealthStatus,
    CommandContext,
    ExecutionStatus,
    InterAgentMessage,
    MessageType
)

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""
    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when agent operation times out."""
    pass


class AbstractAgent(ABC):
    """
    Abstract base class for all CloudWAN MCP agents.
    
    This class defines the standard interface and lifecycle methods that all
    agents must implement to participate in the multi-agent system.
    """
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the abstract agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent (from AgentType enum)
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config or {}
        self.status = AgentStatus.INITIALIZING
        self.capabilities: List[AgentCapability] = []
        self.start_time = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.errors: List[str] = []
        
        # Async handling
        self.active_requests: Dict[str, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        
        # Initialize logger
        self.logger = logging.getLogger(f"{__name__}.{self.agent_id}")
        
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent.
        
        This method should set up any required resources, validate configuration,
        and prepare the agent for operation. It should set self.status to READY
        upon successful initialization.
        
        Raises:
            AgentInitializationError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the agent gracefully.
        
        This method should clean up resources, cancel running tasks, and
        prepare the agent for termination.
        """
        pass
    
    @abstractmethod
    async def execute_capability(
        self, 
        capability_name: str, 
        context: CommandContext, 
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Execute a specific capability.
        
        Args:
            capability_name: Name of the capability to execute
            context: Command execution context
            parameters: Parameters for the capability
            
        Returns:
            Result of the capability execution
            
        Raises:
            AgentExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the list of capabilities this agent provides.
        
        Returns:
            List of capabilities
        """
        pass
    
    async def handle_request(self, request: AgentRequest) -> AgentResponse:
        """
        Handle an incoming request.
        
        This method provides the standard request handling logic and delegates
        to the abstract execute_capability method for actual work.
        
        Args:
            request: The incoming request
            
        Returns:
            Response to the request
        """
        start_time = time.time()
        response = AgentResponse(
            request_id=request.request_id,
            agent_id=self.agent_id,
            status=ExecutionStatus.PENDING
        )
        
        try:
            self.logger.debug(f"Handling request {request.request_id} for capability {request.capability_name}")
            
            # Validate agent status
            if self.status != AgentStatus.READY:
                raise AgentExecutionError(f"Agent {self.agent_id} is not ready (status: {self.status})")
            
            # Validate capability
            if request.capability_name not in [cap.name for cap in self.capabilities]:
                raise AgentExecutionError(f"Capability {request.capability_name} not supported by agent {self.agent_id}")
            
            # Update status
            self.status = AgentStatus.BUSY
            self.total_requests += 1
            
            # Execute capability
            result = await self.execute_capability(
                request.capability_name,
                request.context,
                request.parameters
            )
            
            # Update response
            response.status = ExecutionStatus.SUCCESS
            response.data = result
            self.successful_requests += 1
            
            self.logger.debug(f"Successfully handled request {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling request {request.request_id}: {str(e)}")
            response.status = ExecutionStatus.FAILED
            response.error = str(e)
            self.failed_requests += 1
            self.errors.append(f"{datetime.utcnow()}: {str(e)}")
            
            # Keep only last 100 errors
            if len(self.errors) > 100:
                self.errors = self.errors[-100:]
        
        finally:
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            response.execution_time_ms = int(execution_time)
            self.response_times.append(execution_time)
            
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            # Reset status
            self.status = AgentStatus.READY
            self.last_heartbeat = datetime.utcnow()
        
        return response
    
    async def handle_message(self, message: InterAgentMessage) -> Optional[InterAgentMessage]:
        """
        Handle an inter-agent message.
        
        Args:
            message: The incoming message
            
        Returns:
            Optional response message
        """
        self.logger.debug(f"Received message {message.message_id} from {message.sender_id}")
        
        # Default implementation - agents can override this
        if message.message_type == MessageType.HEARTBEAT:
            return InterAgentMessage(
                message_type=MessageType.HEARTBEAT,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                topic="heartbeat_response",
                payload={"status": self.status.value},
                correlation_id=message.message_id
            )
        
        return None
    
    def get_health_status(self) -> AgentHealthStatus:
        """Get the current health status of the agent."""
        uptime = int((datetime.utcnow() - self.start_time).total_seconds())
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return AgentHealthStatus(
            agent_id=self.agent_id,
            status=self.status,
            last_heartbeat=self.last_heartbeat,
            uptime_seconds=uptime,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            average_response_time_ms=avg_response_time,
            current_load=len(self.active_requests) / self.config.get('max_concurrent_requests', 10),
            errors=self.errors[-10:]  # Last 10 errors
        )
    
    def get_configuration(self) -> AgentConfiguration:
        """Get the agent configuration."""
        return AgentConfiguration(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            max_concurrent_requests=self.config.get('max_concurrent_requests', 10),
            request_timeout_seconds=self.config.get('request_timeout_seconds', 30),
            health_check_interval_seconds=self.config.get('health_check_interval_seconds', 60),
            retry_policy=self.config.get('retry_policy', {}),
            environment=self.config.get('environment', {})
        )
    
    @asynccontextmanager
    async def request_context(self, request_id: str):
        """Context manager for handling request lifecycle."""
        try:
            yield
        except asyncio.TimeoutError:
            raise AgentTimeoutError(f"Request {request_id} timed out")
        except Exception as e:
            self.logger.error(f"Request {request_id} failed: {str(e)}")
            raise AgentExecutionError(f"Request {request_id} failed: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the agent is healthy."""
        # Check if last heartbeat is recent
        if (datetime.utcnow() - self.last_heartbeat).total_seconds() > 120:
            return False
        
        # Check if agent is in a good state
        if self.status in [AgentStatus.ERROR, AgentStatus.STOPPED]:
            return False
        
        # Check error rate
        if self.total_requests > 0:
            error_rate = self.failed_requests / self.total_requests
            if error_rate > 0.5:  # More than 50% errors
                return False
        
        return True
    
    def supports_capability(self, capability_name: str) -> bool:
        """Check if this agent supports a specific capability."""
        return capability_name in [cap.name for cap in self.capabilities]
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"Agent({self.agent_id}, {self.agent_type.value}, {self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of the agent."""
        return (f"Agent(id={self.agent_id}, type={self.agent_type.value}, "
                f"status={self.status.value}, capabilities={len(self.capabilities)})")


class SimpleAgent(AbstractAgent):
    """
    Simple concrete implementation of AbstractAgent.
    
    This class provides a basic implementation that can be used as a starting
    point for simple agents or for testing purposes.
    """
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, agent_type, config)
        self.capability_handlers: Dict[str, Callable] = {}
    
    async def initialize(self) -> None:
        """Initialize the simple agent."""
        self.logger.info(f"Initializing simple agent {self.agent_id}")
        
        # Register default capabilities
        self.capabilities = self.get_capabilities()
        
        # Set status to ready
        self.status = AgentStatus.READY
        self.logger.info(f"Simple agent {self.agent_id} initialized successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the simple agent."""
        self.logger.info(f"Shutting down simple agent {self.agent_id}")
        
        # Cancel any active requests
        for task in self.active_requests.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.active_requests:
            await asyncio.gather(*self.active_requests.values(), return_exceptions=True)
        
        self.status = AgentStatus.STOPPED
        self.logger.info(f"Simple agent {self.agent_id} shutdown complete")
    
    async def execute_capability(
        self, 
        capability_name: str, 
        context: CommandContext, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a capability using registered handlers."""
        if capability_name not in self.capability_handlers:
            raise AgentExecutionError(f"No handler registered for capability {capability_name}")
        
        handler = self.capability_handlers[capability_name]
        
        # Check if handler is async
        if asyncio.iscoroutinefunction(handler):
            return await handler(context, parameters)
        else:
            return handler(context, parameters)
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get capabilities - override in subclasses."""
        return []
    
    def register_capability_handler(self, capability_name: str, handler: Callable):
        """Register a handler for a specific capability."""
        self.capability_handlers[capability_name] = handler
        self.logger.debug(f"Registered handler for capability {capability_name}")


class AgentPool:
    """
    Pool of agents for load balancing and redundancy.
    
    This class manages multiple instances of the same agent type
    to provide load balancing and fault tolerance.
    """
    
    def __init__(self, agent_type: AgentType, pool_size: int = 3):
        self.agent_type = agent_type
        self.pool_size = pool_size
        self.agents: List[AbstractAgent] = []
        self.round_robin_index = 0
        self.logger = logging.getLogger(f"{__name__}.AgentPool.{agent_type.value}")
    
    def add_agent(self, agent: AbstractAgent):
        """Add an agent to the pool."""
        if agent.agent_type != self.agent_type:
            raise ValueError(f"Agent type mismatch: expected {self.agent_type}, got {agent.agent_type}")
        
        self.agents.append(agent)
        self.logger.info(f"Added agent {agent.agent_id} to pool (pool size: {len(self.agents)})")
    
    def get_next_agent(self) -> Optional[AbstractAgent]:
        """Get the next available agent using round-robin selection."""
        if not self.agents:
            return None
        
        # Filter healthy agents
        healthy_agents = [agent for agent in self.agents if agent.is_healthy()]
        
        if not healthy_agents:
            self.logger.warning("No healthy agents available in pool")
            return None
        
        # Round-robin selection
        agent = healthy_agents[self.round_robin_index % len(healthy_agents)]
        self.round_robin_index = (self.round_robin_index + 1) % len(healthy_agents)
        
        return agent
    
    def get_least_loaded_agent(self) -> Optional[AbstractAgent]:
        """Get the agent with the lowest current load."""
        healthy_agents = [agent for agent in self.agents if agent.is_healthy()]
        
        if not healthy_agents:
            return None
        
        # Find agent with lowest load
        return min(healthy_agents, key=lambda a: len(a.active_requests))
    
    def get_pool_health(self) -> Dict[str, Any]:
        """Get overall health statistics for the pool."""
        total_agents = len(self.agents)
        healthy_agents = len([a for a in self.agents if a.is_healthy()])
        
        return {
            'total_agents': total_agents,
            'healthy_agents': healthy_agents,
            'health_percentage': (healthy_agents / total_agents * 100) if total_agents > 0 else 0,
            'agent_statuses': {agent.agent_id: agent.status.value for agent in self.agents}
        }