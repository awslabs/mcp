"""
Shared data models for multi-agent CLI architecture.

This module provides the core data structures and models used across all agents
in the CloudWAN MCP CLI system. These models enable consistent communication
and data exchange between different agents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import uuid
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the system."""
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ANALYSIS = "analysis"
    MONITORING = "monitoring"
    VISUALIZATION = "visualization"
    TROUBLESHOOTING = "troubleshooting"
    SECURITY = "security"
    NETWORKING = "networking"
    CORE = "core"
    SHARED = "shared"


class CommandType(Enum):
    """Types of CLI commands."""
    SHOW = "show"
    TRACE = "trace"
    DEBUG = "debug"
    ANALYSIS = "analysis"
    MONITOR = "monitor"
    DIAGRAM = "diagram"
    CONFIG = "config"
    HELP = "help"


class AgentStatus(Enum):
    """Status of an agent."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class ExecutionStatus(Enum):
    """Status of command execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentCapability:
    """Represents a capability that an agent can provide."""
    name: str
    command_types: List[CommandType]
    description: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    supports_async: bool = True
    timeout_seconds: int = 30
    
    def __post_init__(self):
        """Validate capability data."""
        if not self.name:
            raise ValueError("Capability name cannot be empty")
        if not self.command_types:
            raise ValueError("Capability must support at least one command type")


@dataclass
class CommandContext:
    """Context for command execution."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_type: CommandType = CommandType.SHOW
    command_args: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # AWS context
    aws_profile: Optional[str] = None
    aws_regions: List[str] = field(default_factory=list)
    
    # CLI context
    output_format: str = "pretty"
    verbose: bool = False
    quiet: bool = False
    
    # Execution context
    timeout_seconds: int = 30
    max_retries: int = 3
    
    # Parent context for nested commands
    parent_context: Optional['CommandContext'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'command_id': self.command_id,
            'command_type': self.command_type.value,
            'command_args': self.command_args,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'aws_profile': self.aws_profile,
            'aws_regions': self.aws_regions,
            'output_format': self.output_format,
            'verbose': self.verbose,
            'quiet': self.quiet,
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries
        }


@dataclass
class AgentRequest:
    """Request sent to an agent."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    capability_name: str = ""
    context: CommandContext = field(default_factory=CommandContext)
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate request data."""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        if not self.capability_name:
            raise ValueError("Capability name cannot be empty")


@dataclass
class AgentResponse:
    """Response from an agent."""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    agent_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: int = 0
    
    def __post_init__(self):
        """Validate response data."""
        if not self.request_id:
            raise ValueError("Request ID cannot be empty")
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
    
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.status == ExecutionStatus.SUCCESS and self.error is None
    
    def is_error(self) -> bool:
        """Check if response indicates error."""
        return self.status == ExecutionStatus.FAILED or self.error is not None


@dataclass
class InterAgentMessage:
    """Message for inter-agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    receiver_id: str = ""
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate message data."""
        if not self.sender_id:
            raise ValueError("Sender ID cannot be empty")
        if not self.receiver_id:
            raise ValueError("Receiver ID cannot be empty")
        if not self.topic:
            raise ValueError("Topic cannot be empty")


@dataclass
class AgentHealthStatus:
    """Health status of an agent."""
    agent_id: str
    status: AgentStatus
    last_heartbeat: datetime
    uptime_seconds: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    current_load: float
    errors: List[str] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


@dataclass
class AgentConfiguration:
    """Configuration for an agent."""
    agent_id: str
    agent_type: AgentType
    capabilities: List[AgentCapability]
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 30
    health_check_interval_seconds: int = 60
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        if not self.capabilities:
            raise ValueError("Agent must have at least one capability")


@dataclass
class CommandResult:
    """Result of a command execution."""
    command_id: str
    status: ExecutionStatus
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0
    agent_responses: List[AgentResponse] = field(default_factory=list)
    
    def is_success(self) -> bool:
        """Check if command execution was successful."""
        return self.status == ExecutionStatus.SUCCESS and self.error is None
    
    def get_agent_response(self, agent_id: str) -> Optional[AgentResponse]:
        """Get response from a specific agent."""
        for response in self.agent_responses:
            if response.agent_id == agent_id:
                return response
        return None


@dataclass
class AgentRegistry:
    """Registry of all available agents."""
    agents: Dict[str, AgentConfiguration] = field(default_factory=dict)
    capabilities: Dict[str, List[str]] = field(default_factory=dict)  # capability -> agent_ids
    command_mappings: Dict[CommandType, List[str]] = field(default_factory=dict)  # command -> agent_ids
    
    def add_agent(self, config: AgentConfiguration):
        """Add an agent to the registry."""
        self.agents[config.agent_id] = config
        
        # Update capability mappings
        for capability in config.capabilities:
            if capability.name not in self.capabilities:
                self.capabilities[capability.name] = []
            self.capabilities[capability.name].append(config.agent_id)
            
            # Update command mappings
            for command_type in capability.command_types:
                if command_type not in self.command_mappings:
                    self.command_mappings[command_type] = []
                if config.agent_id not in self.command_mappings[command_type]:
                    self.command_mappings[command_type].append(config.agent_id)
    
    def get_agents_for_command(self, command_type: CommandType) -> List[str]:
        """Get agent IDs that can handle a specific command type."""
        return self.command_mappings.get(command_type, [])
    
    def get_agents_for_capability(self, capability_name: str) -> List[str]:
        """Get agent IDs that provide a specific capability."""
        return self.capabilities.get(capability_name, [])
    
    def get_agent_config(self, agent_id: str) -> Optional[AgentConfiguration]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_id)


# Type aliases for better readability
AgentID = str
CapabilityName = str
RequestID = str
ResponseID = str
MessageID = str