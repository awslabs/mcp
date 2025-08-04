"""
Command delegation engine for multi-agent CLI architecture.

This module provides the command delegation system that routes commands to the
appropriate agents based on their capabilities and current load. It serves as
the unified entry point for all CLI commands and manages the command execution
workflow.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from .base import AbstractAgent, AgentError
from .registry import AgentRegistrySystem, get_registry
from .models import (
    CommandType,
    CommandContext,
    CommandResult,
    AgentRequest,
    AgentResponse,
    ExecutionStatus,
    AgentCapability,
    InterAgentMessage
)

logger = logging.getLogger(__name__)


class DelegationError(AgentError):
    """Error raised by the command delegation engine."""
    pass


class NoAgentAvailableError(DelegationError):
    """Error raised when no agent is available for a command."""
    pass


class CommandTimeoutError(DelegationError):
    """Error raised when command execution times out."""
    pass


class CommandDelegationEngine:
    """
    Command delegation engine for routing commands to appropriate agents.
    
    This class provides:
    - Command routing based on agent capabilities
    - Load balancing across multiple agents
    - Fault tolerance and retry logic
    - Parallel execution support
    - Command execution monitoring
    """
    
    def __init__(self, registry: Optional[AgentRegistrySystem] = None):
        """
        Initialize the command delegation engine.
        
        Args:
            registry: Optional agent registry system. If None, uses global registry.
        """
        self.registry = registry or get_registry()
        self.logger = logging.getLogger(__name__)
        
        # Execution tracking
        self.active_commands: Dict[str, CommandContext] = {}
        self.command_history: List[CommandResult] = []
        self.execution_stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'average_execution_time': 0.0,
            'command_types': {}
        }
        
        # Configuration
        self.config = {
            'max_concurrent_commands': 10,
            'default_timeout_seconds': 60,
            'retry_attempts': 3,
            'retry_delay_seconds': 1,
            'load_balancing_strategy': 'least_loaded',  # 'round_robin', 'least_loaded', 'random'
            'parallel_execution_enabled': True,
            'command_queue_size': 100
        }
        
        # Command queue for rate limiting
        self.command_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config['command_queue_size'])
        self.queue_processor_task: Optional[asyncio.Task] = None
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
    
    async def start(self) -> None:
        """Start the delegation engine."""
        self.logger.info("Starting command delegation engine")
        
        # Start queue processor
        self.queue_processor_task = asyncio.create_task(self._process_command_queue())
        
        self.logger.info("Command delegation engine started")
    
    async def stop(self) -> None:
        """Stop the delegation engine."""
        self.logger.info("Stopping command delegation engine")
        
        # Stop queue processor
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Command delegation engine stopped")
    
    async def execute_command(
        self, 
        command_type: CommandType,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> CommandResult:
        """
        Execute a command by delegating to appropriate agents.
        
        Args:
            command_type: Type of command to execute
            context: Command execution context
            parameters: Command parameters
            
        Returns:
            Command execution result
            
        Raises:
            NoAgentAvailableError: If no agent is available for the command
            CommandTimeoutError: If command execution times out
            DelegationError: If delegation fails
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing command {command_type.value} (ID: {context.command_id})")
            
            # Update statistics
            self.execution_stats['total_commands'] += 1
            self.execution_stats['command_types'][command_type.value] = \
                self.execution_stats['command_types'].get(command_type.value, 0) + 1
            
            # Track active command
            self.active_commands[context.command_id] = context
            
            # Get capable agents for this command
            agents = self.registry.get_agents_for_command(command_type)
            if not agents:
                raise NoAgentAvailableError(f"No agents available for command type {command_type.value}")
            
            # Select best agent(s) for execution
            selected_agents = self._select_agents_for_command(command_type, agents, context)
            
            # Execute command
            if len(selected_agents) == 1:
                result = await self._execute_single_agent_command(
                    selected_agents[0], command_type, context, parameters
                )
            else:
                result = await self._execute_multi_agent_command(
                    selected_agents, command_type, context, parameters
                )
            
            # Update execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            result.execution_time_ms = int(execution_time)
            
            # Update statistics
            if result.is_success():
                self.execution_stats['successful_commands'] += 1
            else:
                self.execution_stats['failed_commands'] += 1
            
            # Update average execution time
            total_time = self.execution_stats['average_execution_time'] * (self.execution_stats['total_commands'] - 1)
            self.execution_stats['average_execution_time'] = (total_time + execution_time) / self.execution_stats['total_commands']
            
            # Store in history
            self.command_history.append(result)
            if len(self.command_history) > 1000:  # Keep last 1000 commands
                self.command_history = self.command_history[-1000:]
            
            self.logger.info(f"Command {context.command_id} completed with status {result.status.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing command {context.command_id}: {str(e)}")
            
            # Create error result
            execution_time = (time.time() - start_time) * 1000
            result = CommandResult(
                command_id=context.command_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                execution_time_ms=int(execution_time)
            )
            
            self.execution_stats['failed_commands'] += 1
            self.command_history.append(result)
            
            if isinstance(e, (NoAgentAvailableError, CommandTimeoutError)):
                raise
            else:
                raise DelegationError(f"Command execution failed: {str(e)}")
                
        finally:
            # Remove from active commands
            self.active_commands.pop(context.command_id, None)
    
    def _select_agents_for_command(
        self, 
        command_type: CommandType, 
        agents: List[AbstractAgent], 
        context: CommandContext
    ) -> List[AbstractAgent]:
        """Select the best agent(s) for executing a command."""
        # Filter healthy agents
        healthy_agents = [agent for agent in agents if agent.is_healthy()]
        
        if not healthy_agents:
            raise NoAgentAvailableError(f"No healthy agents available for command type {command_type.value}")
        
        # Check if command supports parallel execution
        supports_parallel = any(
            cap.supports_async for agent in healthy_agents 
            for cap in agent.capabilities 
            if command_type in cap.command_types
        )
        
        # Select agents based on strategy
        strategy = self.config['load_balancing_strategy']
        
        if strategy == 'least_loaded':
            # Sort by current load (ascending)
            healthy_agents.sort(key=lambda a: len(a.active_requests))
        elif strategy == 'round_robin':
            # Use simple round-robin (simplified implementation)
            pass
        elif strategy == 'random':
            import random
            random.shuffle(healthy_agents)
        
        # For now, return single agent unless parallel execution is specifically requested
        if supports_parallel and context.command_args.get('parallel', False):
            # Return up to 3 agents for parallel execution
            return healthy_agents[:3]
        else:
            return [healthy_agents[0]]
    
    async def _execute_single_agent_command(
        self,
        agent: AbstractAgent,
        command_type: CommandType,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> CommandResult:
        """Execute a command on a single agent."""
        try:
            # Find appropriate capability
            capability = self._find_capability_for_command(agent, command_type)
            if not capability:
                raise DelegationError(f"Agent {agent.agent_id} does not support command type {command_type.value}")
            
            # Create agent request
            request = AgentRequest(
                agent_id=agent.agent_id,
                capability_name=capability.name,
                context=context,
                parameters=parameters
            )
            
            # Execute with timeout
            timeout = context.timeout_seconds or self.config['default_timeout_seconds']
            
            try:
                response = await asyncio.wait_for(
                    agent.handle_request(request),
                    timeout=timeout
                )
                
                # Create command result
                result = CommandResult(
                    command_id=context.command_id,
                    status=ExecutionStatus.SUCCESS if response.is_success() else ExecutionStatus.FAILED,
                    data=response.data,
                    error=response.error,
                    metadata={'agent_id': agent.agent_id, 'capability': capability.name},
                    agent_responses=[response]
                )
                
                return result
                
            except asyncio.TimeoutError:
                raise CommandTimeoutError(f"Command {context.command_id} timed out after {timeout} seconds")
                
        except Exception as e:
            self.logger.error(f"Error executing command on agent {agent.agent_id}: {str(e)}")
            raise
    
    async def _execute_multi_agent_command(
        self,
        agents: List[AbstractAgent],
        command_type: CommandType,
        context: CommandContext,
        parameters: Dict[str, Any]
    ) -> CommandResult:
        """Execute a command on multiple agents in parallel."""
        tasks = []
        
        for agent in agents:
            task = asyncio.create_task(
                self._execute_single_agent_command(agent, command_type, context, parameters)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        agent_responses = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append(f"Agent {agents[i].agent_id}: {str(result)}")
            else:
                if result.is_success():
                    successful_results.append(result)
                else:
                    failed_results.append(f"Agent {agents[i].agent_id}: {result.error}")
                
                agent_responses.extend(result.agent_responses)
        
        # Determine overall result
        if successful_results:
            # At least one agent succeeded
            combined_data = {
                'results': [r.data for r in successful_results],
                'agent_count': len(successful_results),
                'success_rate': len(successful_results) / len(agents)
            }
            
            status = ExecutionStatus.SUCCESS
            error = None
            
            if failed_results:
                # Partial success
                combined_data['warnings'] = failed_results
        else:
            # All agents failed
            combined_data = None
            status = ExecutionStatus.FAILED
            error = f"All agents failed: {'; '.join(failed_results)}"
        
        return CommandResult(
            command_id=context.command_id,
            status=status,
            data=combined_data,
            error=error,
            metadata={'parallel_execution': True, 'agent_count': len(agents)},
            agent_responses=agent_responses
        )
    
    def _find_capability_for_command(self, agent: AbstractAgent, command_type: CommandType) -> Optional[AgentCapability]:
        """Find the appropriate capability for a command type."""
        for capability in agent.capabilities:
            if command_type in capability.command_types:
                return capability
        return None
    
    async def _process_command_queue(self) -> None:
        """Process commands from the command queue."""
        while True:
            try:
                # Get command from queue
                command_data = await self.command_queue.get()
                
                # Process command
                try:
                    result = await self.execute_command(**command_data)
                    command_data.get('callback', lambda r: None)(result)
                except Exception as e:
                    self.logger.error(f"Error processing queued command: {str(e)}")
                    if 'callback' in command_data:
                        error_result = CommandResult(
                            command_id=command_data['context'].command_id,
                            status=ExecutionStatus.FAILED,
                            error=str(e)
                        )
                        command_data['callback'](error_result)
                
                # Mark task as done
                self.command_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in command queue processor: {str(e)}")
    
    async def queue_command(
        self,
        command_type: CommandType,
        context: CommandContext,
        parameters: Dict[str, Any],
        callback: Optional[callable] = None
    ) -> None:
        """
        Queue a command for execution.
        
        Args:
            command_type: Type of command to execute
            context: Command execution context
            parameters: Command parameters
            callback: Optional callback function for result
        """
        command_data = {
            'command_type': command_type,
            'context': context,
            'parameters': parameters,
            'callback': callback
        }
        
        await self.command_queue.put(command_data)
    
    def get_agent_for_capability(self, capability_name: str) -> Optional[AbstractAgent]:
        """Get the best agent for a specific capability."""
        agents = self.registry.get_agents_for_capability(capability_name)
        if not agents:
            return None
        
        # Return the least loaded healthy agent
        healthy_agents = [agent for agent in agents if agent.is_healthy()]
        if not healthy_agents:
            return None
        
        return min(healthy_agents, key=lambda a: len(a.active_requests))
    
    def get_available_commands(self) -> Dict[CommandType, List[str]]:
        """Get available commands and their supporting agents."""
        result = {}
        
        for command_type in CommandType:
            agents = self.registry.get_agents_for_command(command_type)
            if agents:
                result[command_type] = [agent.agent_id for agent in agents]
        
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            **self.execution_stats,
            'active_commands': len(self.active_commands),
            'queue_size': self.command_queue.qsize(),
            'registry_status': self.registry.get_registry_status()
        }
    
    def get_command_history(self, limit: int = 100) -> List[CommandResult]:
        """Get recent command execution history."""
        return self.command_history[-limit:]
    
    def cancel_command(self, command_id: str) -> bool:
        """Cancel an active command."""
        if command_id in self.active_commands:
            context = self.active_commands[command_id]
            
            # Create cancellation result
            result = CommandResult(
                command_id=command_id,
                status=ExecutionStatus.CANCELLED,
                error="Command cancelled by user"
            )
            
            self.command_history.append(result)
            del self.active_commands[command_id]
            
            self.logger.info(f"Command {command_id} cancelled")
            return True
        
        return False
    
    async def broadcast_message(self, message: InterAgentMessage) -> List[AgentResponse]:
        """Broadcast a message to all agents."""
        agents = list(self.registry.agents.values())
        responses = []
        
        for agent in agents:
            try:
                response = await agent.handle_message(message)
                if response:
                    responses.append(response)
            except Exception as e:
                self.logger.error(f"Error broadcasting message to agent {agent.agent_id}: {str(e)}")
        
        return responses
    
    def __str__(self) -> str:
        """String representation of the delegation engine."""
        return f"CommandDelegationEngine(active_commands={len(self.active_commands)}, registry_agents={len(self.registry.agents)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the delegation engine."""
        return (f"CommandDelegationEngine(active_commands={len(self.active_commands)}, "
                f"registry_agents={len(self.registry.agents)}, "
                f"total_commands={self.execution_stats['total_commands']}, "
                f"success_rate={self.execution_stats['successful_commands'] / max(1, self.execution_stats['total_commands']) * 100:.1f}%)")


# Global delegation engine instance
_delegation_engine: Optional[CommandDelegationEngine] = None


def get_delegation_engine() -> CommandDelegationEngine:
    """Get the global delegation engine instance."""
    global _delegation_engine
    if _delegation_engine is None:
        _delegation_engine = CommandDelegationEngine()
    return _delegation_engine


async def initialize_delegation_engine(registry: Optional[AgentRegistrySystem] = None) -> CommandDelegationEngine:
    """Initialize the global delegation engine."""
    global _delegation_engine
    _delegation_engine = CommandDelegationEngine(registry)
    await _delegation_engine.start()
    return _delegation_engine


async def shutdown_delegation_engine() -> None:
    """Shutdown the global delegation engine."""
    global _delegation_engine
    if _delegation_engine:
        await _delegation_engine.stop()
        _delegation_engine = None


# Convenience functions for common operations
async def execute_command(
    command_type: CommandType,
    context: CommandContext,
    parameters: Dict[str, Any]
) -> CommandResult:
    """Execute a command using the global delegation engine."""
    engine = get_delegation_engine()
    return await engine.execute_command(command_type, context, parameters)


async def execute_show_command(
    resource_type: str,
    regions: List[str] = None,
    **kwargs
) -> CommandResult:
    """Execute a show command with simplified parameters."""
    context = CommandContext(
        command_type=CommandType.SHOW,
        command_args={'resource_type': resource_type, 'regions': regions or [], **kwargs}
    )
    
    return await execute_command(CommandType.SHOW, context, kwargs)


async def execute_trace_command(
    trace_type: str,
    source: str,
    destination: str,
    **kwargs
) -> CommandResult:
    """Execute a trace command with simplified parameters."""
    context = CommandContext(
        command_type=CommandType.TRACE,
        command_args={'trace_type': trace_type, 'source': source, 'destination': destination, **kwargs}
    )
    
    parameters = {'trace_type': trace_type, 'source': source, 'destination': destination, **kwargs}
    return await execute_command(CommandType.TRACE, context, parameters)


async def execute_analysis_command(
    analysis_type: str,
    target: str,
    **kwargs
) -> CommandResult:
    """Execute an analysis command with simplified parameters."""
    context = CommandContext(
        command_type=CommandType.ANALYSIS,
        command_args={'analysis_type': analysis_type, 'target': target, **kwargs}
    )
    
    parameters = {'analysis_type': analysis_type, 'target': target, **kwargs}
    return await execute_command(CommandType.ANALYSIS, context, parameters)