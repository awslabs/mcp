"""
Diagram Command Agent for CloudWAN MCP CLI.

This agent provides network topology visualization and diagram generation
capabilities for CloudWAN environments, including interactive web interfaces,
static diagram generation, and real-time topology updates.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
import json

from .base import AbstractAgent, AgentExecutionError, AgentInitializationError
from .models import (
    AgentType,
    AgentCapability,
    CommandType,
    CommandContext,
    AgentStatus,
    InterAgentMessage,
    MessageType
)

# Import existing visualization tools
from ..tools.visualization.network_topology_visualizer import NetworkTopologyVisualizationTool
from ..tools.visualization.topology_discovery import NetworkTopologyDiscovery
from ..tools.visualization.topology_renderer import NetworkTopologyRenderer
from ..tools.visualization.export_manager import ExportManager

logger = logging.getLogger(__name__)


class DiagramCommandAgent(AbstractAgent):
    """
    Advanced diagram command agent for network topology visualization.
    
    This agent orchestrates sophisticated diagram generation operations including:
    - Interactive network topology visualization
    - Multi-format diagram export (SVG, PNG, PDF, JSON)
    - Real-time topology updates and monitoring
    - Custom diagram themes and layouts
    - Integration with monitoring and analysis agents
    """
    
    def __init__(self, agent_id: str = "diagram_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, AgentType.VISUALIZATION, config)
        
        # Visualization tools
        self.topology_visualizer: Optional[NetworkTopologyVisualizationTool] = None
        self.topology_discovery: Optional[NetworkTopologyDiscovery] = None
        self.topology_renderer: Optional[NetworkTopologyRenderer] = None
        self.export_manager: Optional[ExportManager] = None
        
        # Diagram state
        self.active_diagrams: Dict[str, Dict[str, Any]] = {}
        self.diagram_cache: Dict[str, Any] = {}
        self.topology_cache: Dict[str, Any] = {}
        self.diagram_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.max_concurrent_diagrams = self.config.get('max_concurrent_diagrams', 5)
        self.diagram_timeout = self.config.get('diagram_timeout', 180)  # 3 minutes
        self.cache_ttl = self.config.get('cache_ttl', 1800)  # 30 minutes
        self.supported_formats = self.config.get('supported_formats', ['svg', 'png', 'pdf', 'json'])
        
        # Rendering options
        self.default_theme = self.config.get('default_theme', 'aws_standard')
        self.default_layout = self.config.get('default_layout', 'hierarchical')
        self.enable_animations = self.config.get('enable_animations', True)
        self.enable_interactions = self.config.get('enable_interactions', True)
        
        # Real-time updates
        self.enable_realtime_updates = self.config.get('enable_realtime_updates', False)
        self.update_interval = self.config.get('update_interval', 30)  # seconds
        self.realtime_connections: Set[str] = set()
        
    async def initialize(self) -> None:
        """Initialize the diagram agent with all required tools."""
        try:
            self.logger.info(f"Initializing diagram agent {self.agent_id}")
            
            # Initialize visualization tools
            self.topology_visualizer = NetworkTopologyVisualizationTool(
                config=self.config.get('topology_visualizer', {})
            )
            self.topology_discovery = NetworkTopologyDiscovery(
                config=self.config.get('topology_discovery', {})
            )
            self.topology_renderer = NetworkTopologyRenderer(
                config=self.config.get('topology_renderer', {})
            )
            self.export_manager = ExportManager(
                config=self.config.get('export_manager', {})
            )
            
            # Initialize capabilities
            self.capabilities = self.get_capabilities()
            
            # Start background tasks if real-time updates are enabled
            if self.enable_realtime_updates:
                await self._start_realtime_monitoring()
            
            # Set status to ready
            self.status = AgentStatus.READY
            self.logger.info(f"Diagram agent {self.agent_id} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize diagram agent: {str(e)}")
            raise AgentInitializationError(f"Diagram agent initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown the diagram agent gracefully."""
        self.logger.info(f"Shutting down diagram agent {self.agent_id}")
        
        # Stop all active diagram generation tasks
        for diagram_id, diagram in self.active_diagrams.items():
            if 'task' in diagram and not diagram['task'].done():
                diagram['task'].cancel()
                self.logger.info(f"Cancelled diagram generation {diagram_id}")
        
        # Wait for tasks to complete
        if self.active_diagrams:
            tasks = [diagram['task'] for diagram in self.active_diagrams.values() 
                    if 'task' in diagram and not diagram['task'].done()]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clear state
        self.active_diagrams.clear()
        self.diagram_cache.clear()
        self.topology_cache.clear()
        self.realtime_connections.clear()
        
        self.status = AgentStatus.STOPPED
        self.logger.info(f"Diagram agent {self.agent_id} shutdown complete")
    
    async def execute_capability(
        self, 
        capability_name: str, 
        context: CommandContext, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a specific diagram capability."""
        self.logger.debug(f"Executing capability {capability_name}")
        
        # Create diagram ID for tracking
        diagram_id = f"{capability_name}_{context.command_id}"
        
        try:
            # Check if diagram is already being generated
            if diagram_id in self.active_diagrams:
                return await self._get_diagram_status(diagram_id)
            
            # Check cache first
            cache_key = self._get_cache_key(capability_name, parameters)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.debug(f"Returning cached result for {capability_name}")
                return cached_result
            
            # Execute capability based on name
            if capability_name == "topology_visualization":
                result = await self._execute_topology_visualization(context, parameters, diagram_id)
            elif capability_name == "interactive_diagram":
                result = await self._execute_interactive_diagram(context, parameters, diagram_id)
            elif capability_name == "static_diagram_export":
                result = await self._execute_static_diagram_export(context, parameters, diagram_id)
            elif capability_name == "realtime_topology_updates":
                result = await self._execute_realtime_topology_updates(context, parameters, diagram_id)
            elif capability_name == "multi_format_export":
                result = await self._execute_multi_format_export(context, parameters, diagram_id)
            elif capability_name == "custom_diagram_themes":
                result = await self._execute_custom_diagram_themes(context, parameters, diagram_id)
            elif capability_name == "topology_comparison":
                result = await self._execute_topology_comparison(context, parameters, diagram_id)
            elif capability_name == "diagram_annotations":
                result = await self._execute_diagram_annotations(context, parameters, diagram_id)
            elif capability_name == "network_layer_visualization":
                result = await self._execute_network_layer_visualization(context, parameters, diagram_id)
            elif capability_name == "diagram_automation":
                result = await self._execute_diagram_automation(context, parameters, diagram_id)
            else:
                raise AgentExecutionError(f"Unknown capability: {capability_name}")
            
            # Cache result
            self._cache_result(cache_key, result)
            
            # Update diagram history
            self._update_diagram_history(capability_name, context, parameters, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing capability {capability_name}: {str(e)}")
            raise AgentExecutionError(f"Diagram capability {capability_name} failed: {str(e)}")
        
        finally:
            # Clean up active diagram if it's not a long-running operation
            if diagram_id in self.active_diagrams and not self._is_long_running_capability(capability_name):
                del self.active_diagrams[diagram_id]
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get the list of capabilities this agent provides."""
        return [
            AgentCapability(
                name="topology_visualization",
                command_types=[CommandType.VISUALIZATION],
                description="Generate network topology visualizations with discovery and analysis",
                priority=10,
                dependencies=[],
                supports_async=True,
                timeout_seconds=180
            ),
            AgentCapability(
                name="interactive_diagram",
                command_types=[CommandType.VISUALIZATION],
                description="Create interactive network diagrams with web interface",
                priority=9,
                dependencies=[],
                supports_async=True,
                timeout_seconds=120
            ),
            AgentCapability(
                name="static_diagram_export",
                command_types=[CommandType.VISUALIZATION],
                description="Export static network diagrams in multiple formats",
                priority=8,
                dependencies=[],
                supports_async=True,
                timeout_seconds=90
            ),
            AgentCapability(
                name="realtime_topology_updates",
                command_types=[CommandType.VISUALIZATION],
                description="Enable real-time topology updates and monitoring",
                priority=7,
                dependencies=[],
                supports_async=True,
                timeout_seconds=3600  # Long-running
            ),
            AgentCapability(
                name="multi_format_export",
                command_types=[CommandType.VISUALIZATION],
                description="Export diagrams in multiple formats (SVG, PNG, PDF, JSON)",
                priority=6,
                dependencies=[],
                supports_async=True,
                timeout_seconds=150
            ),
            AgentCapability(
                name="custom_diagram_themes",
                command_types=[CommandType.VISUALIZATION],
                description="Apply custom themes and styling to network diagrams",
                priority=5,
                dependencies=[],
                supports_async=True,
                timeout_seconds=60
            ),
            AgentCapability(
                name="topology_comparison",
                command_types=[CommandType.VISUALIZATION],
                description="Compare network topologies across time or regions",
                priority=4,
                dependencies=[],
                supports_async=True,
                timeout_seconds=240
            ),
            AgentCapability(
                name="diagram_annotations",
                command_types=[CommandType.VISUALIZATION],
                description="Add annotations and labels to network diagrams",
                priority=3,
                dependencies=[],
                supports_async=True,
                timeout_seconds=90
            ),
            AgentCapability(
                name="network_layer_visualization",
                command_types=[CommandType.VISUALIZATION],
                description="Visualize different network layers (physical, logical, security)",
                priority=2,
                dependencies=[],
                supports_async=True,
                timeout_seconds=180
            ),
            AgentCapability(
                name="diagram_automation",
                command_types=[CommandType.VISUALIZATION],
                description="Automate diagram generation and updates",
                priority=1,
                dependencies=[],
                supports_async=True,
                timeout_seconds=300
            )
        ]
    
    async def _execute_topology_visualization(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute topology visualization with discovery and analysis."""
        self.logger.info(f"Starting topology visualization {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'topology_visualization',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Discover topology
        if self.topology_discovery:
            topology = await self._run_with_timeout(
                self.topology_discovery.discover_topology(
                    region=parameters.get('region'),
                    core_network_id=parameters.get('core_network_id'),
                    include_vpc=parameters.get('include_vpc', True),
                    include_tgw=parameters.get('include_tgw', True)
                ),
                timeout=120
            )
            results['topology'] = topology
            self.active_diagrams[diagram_id]['progress'] = 40
        
        # Generate visualization
        if self.topology_visualizer:
            visualization = await self._run_with_timeout(
                self.topology_visualizer.create_visualization(
                    topology_data=results.get('topology', {}),
                    layout=parameters.get('layout', self.default_layout),
                    theme=parameters.get('theme', self.default_theme),
                    include_labels=parameters.get('include_labels', True)
                ),
                timeout=120
            )
            results['visualization'] = visualization
            self.active_diagrams[diagram_id]['progress'] = 80
        
        # Render diagram
        if self.topology_renderer:
            rendered_diagram = await self._run_with_timeout(
                self.topology_renderer.render_diagram(
                    visualization_data=results.get('visualization', {}),
                    output_format=parameters.get('format', 'svg'),
                    width=parameters.get('width', 1200),
                    height=parameters.get('height', 800)
                ),
                timeout=60
            )
            results['rendered_diagram'] = rendered_diagram
            self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed topology visualization {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'topology_visualization',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_topology_summary(results)
        }
    
    async def _execute_interactive_diagram(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute interactive diagram creation with web interface."""
        self.logger.info(f"Starting interactive diagram {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'interactive_diagram',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Create interactive visualization
        if self.topology_visualizer:
            interactive_viz = await self._run_with_timeout(
                self.topology_visualizer.create_interactive_visualization(
                    topology_data=parameters.get('topology_data', {}),
                    enable_zoom=parameters.get('enable_zoom', True),
                    enable_pan=parameters.get('enable_pan', True),
                    enable_select=parameters.get('enable_select', True),
                    enable_hover=parameters.get('enable_hover', True)
                ),
                timeout=90
            )
            results['interactive_visualization'] = interactive_viz
            self.active_diagrams[diagram_id]['progress'] = 60
        
        # Generate web interface
        web_interface = await self._generate_web_interface(
            interactive_viz=results.get('interactive_visualization', {}),
            parameters=parameters
        )
        results['web_interface'] = web_interface
        self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed interactive diagram {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'interactive_diagram',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_interactive_summary(results)
        }
    
    async def _execute_static_diagram_export(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute static diagram export in specified format."""
        self.logger.info(f"Starting static diagram export {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'static_diagram_export',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        export_format = parameters.get('format', 'svg')
        
        # Export diagram
        if self.export_manager:
            exported_diagram = await self._run_with_timeout(
                self.export_manager.export_diagram(
                    diagram_data=parameters.get('diagram_data', {}),
                    format=export_format,
                    quality=parameters.get('quality', 'high'),
                    compression=parameters.get('compression', False)
                ),
                timeout=90
            )
            results['exported_diagram'] = exported_diagram
            self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed static diagram export {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'static_diagram_export',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_export_summary(results, export_format)
        }
    
    async def _execute_realtime_topology_updates(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute real-time topology updates and monitoring."""
        self.logger.info(f"Starting real-time topology updates {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'realtime_topology_updates',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'parameters': parameters
        }
        
        # Add to real-time connections
        self.realtime_connections.add(diagram_id)
        
        # Start real-time monitoring task
        monitor_task = asyncio.create_task(
            self._realtime_topology_loop(diagram_id, parameters)
        )
        self.active_diagrams[diagram_id]['task'] = monitor_task
        
        return {
            'diagram_id': diagram_id,
            'status': 'started',
            'started_at': datetime.utcnow().isoformat(),
            'diagram_type': 'realtime_topology_updates',
            'parameters': parameters
        }
    
    async def _execute_multi_format_export(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute multi-format diagram export."""
        self.logger.info(f"Starting multi-format export {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'multi_format_export',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        formats = parameters.get('formats', ['svg', 'png', 'pdf'])
        
        # Export in each format
        if self.export_manager:
            for i, format_type in enumerate(formats):
                exported = await self._run_with_timeout(
                    self.export_manager.export_diagram(
                        diagram_data=parameters.get('diagram_data', {}),
                        format=format_type,
                        quality=parameters.get('quality', 'high')
                    ),
                    timeout=60
                )
                results[format_type] = exported
                
                progress = int(((i + 1) / len(formats)) * 100)
                self.active_diagrams[diagram_id]['progress'] = progress
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed multi-format export {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'multi_format_export',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_multi_format_summary(results)
        }
    
    async def _execute_custom_diagram_themes(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute custom diagram theming."""
        self.logger.info(f"Starting custom diagram themes {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'custom_diagram_themes',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Apply custom theme
        if self.topology_renderer:
            themed_diagram = await self._run_with_timeout(
                self.topology_renderer.apply_theme(
                    diagram_data=parameters.get('diagram_data', {}),
                    theme_config=parameters.get('theme_config', {}),
                    custom_styles=parameters.get('custom_styles', {})
                ),
                timeout=60
            )
            results['themed_diagram'] = themed_diagram
            self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed custom diagram themes {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'custom_diagram_themes',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_theme_summary(results)
        }
    
    async def _execute_topology_comparison(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute topology comparison between different states."""
        self.logger.info(f"Starting topology comparison {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'topology_comparison',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Compare topologies
        if self.topology_discovery:
            comparison = await self._run_with_timeout(
                self.topology_discovery.compare_topologies(
                    topology_a=parameters.get('topology_a', {}),
                    topology_b=parameters.get('topology_b', {}),
                    comparison_type=parameters.get('comparison_type', 'structural')
                ),
                timeout=120
            )
            results['comparison'] = comparison
            self.active_diagrams[diagram_id]['progress'] = 60
        
        # Generate comparison visualization
        if self.topology_visualizer:
            comparison_viz = await self._run_with_timeout(
                self.topology_visualizer.create_comparison_visualization(
                    comparison_data=results.get('comparison', {}),
                    highlight_changes=parameters.get('highlight_changes', True)
                ),
                timeout=90
            )
            results['comparison_visualization'] = comparison_viz
            self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed topology comparison {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'topology_comparison',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_comparison_summary(results)
        }
    
    async def _execute_diagram_annotations(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute diagram annotations and labeling."""
        self.logger.info(f"Starting diagram annotations {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'diagram_annotations',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Add annotations
        if self.topology_renderer:
            annotated_diagram = await self._run_with_timeout(
                self.topology_renderer.add_annotations(
                    diagram_data=parameters.get('diagram_data', {}),
                    annotations=parameters.get('annotations', []),
                    annotation_style=parameters.get('annotation_style', 'default')
                ),
                timeout=60
            )
            results['annotated_diagram'] = annotated_diagram
            self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed diagram annotations {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'diagram_annotations',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_annotation_summary(results)
        }
    
    async def _execute_network_layer_visualization(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute network layer visualization."""
        self.logger.info(f"Starting network layer visualization {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'network_layer_visualization',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        layers = parameters.get('layers', ['physical', 'logical', 'security'])
        
        # Visualize each layer
        if self.topology_visualizer:
            for i, layer in enumerate(layers):
                layer_viz = await self._run_with_timeout(
                    self.topology_visualizer.create_layer_visualization(
                        topology_data=parameters.get('topology_data', {}),
                        layer_type=layer,
                        show_connections=parameters.get('show_connections', True)
                    ),
                    timeout=90
                )
                results[f'{layer}_layer'] = layer_viz
                
                progress = int(((i + 1) / len(layers)) * 100)
                self.active_diagrams[diagram_id]['progress'] = progress
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed network layer visualization {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'network_layer_visualization',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_layer_summary(results)
        }
    
    async def _execute_diagram_automation(
        self, context: CommandContext, parameters: Dict[str, Any], diagram_id: str
    ) -> Dict[str, Any]:
        """Execute diagram automation and scheduling."""
        self.logger.info(f"Starting diagram automation {diagram_id}")
        
        # Register diagram
        self.active_diagrams[diagram_id] = {
            'type': 'diagram_automation',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Setup automation
        automation_config = await self._setup_diagram_automation(parameters)
        results['automation_config'] = automation_config
        self.active_diagrams[diagram_id]['progress'] = 50
        
        # Schedule automated tasks
        scheduled_tasks = await self._schedule_automated_diagrams(automation_config)
        results['scheduled_tasks'] = scheduled_tasks
        self.active_diagrams[diagram_id]['progress'] = 100
        
        self.active_diagrams[diagram_id]['status'] = 'completed'
        self.logger.info(f"Completed diagram automation {diagram_id}")
        
        return {
            'diagram_id': diagram_id,
            'diagram_type': 'diagram_automation',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_automation_summary(results)
        }
    
    # Background monitoring loops
    
    async def _realtime_topology_loop(self, diagram_id: str, parameters: Dict[str, Any]) -> None:
        """Background loop for real-time topology monitoring."""
        try:
            while diagram_id in self.realtime_connections:
                # Update topology
                if self.topology_discovery:
                    updated_topology = await self.topology_discovery.discover_topology(
                        region=parameters.get('region'),
                        core_network_id=parameters.get('core_network_id')
                    )
                    
                    # Check for changes
                    await self._process_topology_changes(diagram_id, updated_topology)
                
                # Wait for next update
                await asyncio.sleep(parameters.get('update_interval', self.update_interval))
                
        except asyncio.CancelledError:
            self.logger.info(f"Real-time topology loop {diagram_id} cancelled")
        except Exception as e:
            self.logger.error(f"Error in real-time topology loop {diagram_id}: {str(e)}")
    
    async def _start_realtime_monitoring(self) -> None:
        """Start real-time monitoring background task."""
        if self.enable_realtime_updates:
            asyncio.create_task(self._realtime_monitoring_background())
    
    async def _realtime_monitoring_background(self) -> None:
        """Background task for real-time monitoring coordination."""
        while self.status != AgentStatus.STOPPED:
            try:
                # Process real-time updates
                for diagram_id in list(self.realtime_connections):
                    if diagram_id in self.active_diagrams:
                        await self._refresh_realtime_diagram(diagram_id)
                
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in real-time monitoring background: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry
    
    # Helper methods
    
    async def _run_with_timeout(self, coroutine, timeout: int):
        """Run a coroutine with timeout."""
        try:
            return await asyncio.wait_for(coroutine, timeout=timeout)
        except asyncio.TimeoutError:
            raise AgentExecutionError(f"Operation timed out after {timeout} seconds")
    
    async def _get_diagram_status(self, diagram_id: str) -> Dict[str, Any]:
        """Get the status of a diagram generation."""
        if diagram_id not in self.active_diagrams:
            return {'status': 'not_found'}
        
        diagram = self.active_diagrams[diagram_id]
        return {
            'diagram_id': diagram_id,
            'status': diagram['status'],
            'progress': diagram.get('progress', 0),
            'started_at': diagram['started_at'].isoformat(),
            'elapsed_time': (datetime.utcnow() - diagram['started_at']).total_seconds()
        }
    
    def _get_cache_key(self, capability_name: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for diagram results."""
        import hashlib
        
        # Create a deterministic string from parameters
        param_str = json.dumps(parameters, sort_keys=True)
        cache_key = f"{capability_name}:{hashlib.md5(param_str.encode()).hexdigest()}"
        return cache_key
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached diagram result if valid."""
        if cache_key not in self.diagram_cache:
            return None
        
        cached_item = self.diagram_cache[cache_key]
        if datetime.utcnow() - cached_item['timestamp'] > timedelta(seconds=self.cache_ttl):
            del self.diagram_cache[cache_key]
            return None
        
        return cached_item['result']
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache diagram result."""
        self.diagram_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.utcnow()
        }
        
        # Limit cache size
        if len(self.diagram_cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self.diagram_cache.keys(),
                key=lambda k: self.diagram_cache[k]['timestamp']
            )[:10]
            for key in oldest_keys:
                del self.diagram_cache[key]
    
    def _is_long_running_capability(self, capability_name: str) -> bool:
        """Check if capability is long-running."""
        long_running_capabilities = {
            'realtime_topology_updates',
            'diagram_automation'
        }
        return capability_name in long_running_capabilities
    
    def _update_diagram_history(
        self, capability_name: str, context: CommandContext, 
        parameters: Dict[str, Any], result: Any
    ) -> None:
        """Update diagram history."""
        self.diagram_history.append({
            'timestamp': datetime.utcnow(),
            'capability': capability_name,
            'command_id': context.command_id,
            'parameters': parameters,
            'success': True,
            'result_summary': self._summarize_result(result)
        })
        
        # Limit history size
        if len(self.diagram_history) > 1000:
            self.diagram_history = self.diagram_history[-1000:]
    
    def _summarize_result(self, result: Any) -> str:
        """Generate a summary of diagram result."""
        if isinstance(result, dict):
            if 'diagram_id' in result:
                return f"Diagram {result['diagram_id']} - {result.get('diagram_type', 'unknown')}"
            return f"Diagram completed with {len(result)} components"
        return "Diagram completed"
    
    # Diagram-specific helper methods
    
    def _generate_topology_summary(self, results: Dict[str, Any]) -> str:
        """Generate topology visualization summary."""
        topology_nodes = len(results.get('topology', {}).get('nodes', []))
        return f"Topology visualization completed with {topology_nodes} nodes"
    
    def _generate_interactive_summary(self, results: Dict[str, Any]) -> str:
        """Generate interactive diagram summary."""
        has_web_interface = 'web_interface' in results
        return f"Interactive diagram created with web interface: {has_web_interface}"
    
    def _generate_export_summary(self, results: Dict[str, Any], export_format: str) -> str:
        """Generate export summary."""
        return f"Static diagram exported in {export_format.upper()} format"
    
    def _generate_multi_format_summary(self, results: Dict[str, Any]) -> str:
        """Generate multi-format export summary."""
        formats = list(results.keys())
        return f"Diagram exported in {len(formats)} formats: {', '.join(formats)}"
    
    def _generate_theme_summary(self, results: Dict[str, Any]) -> str:
        """Generate theme summary."""
        return "Custom theme applied to diagram"
    
    def _generate_comparison_summary(self, results: Dict[str, Any]) -> str:
        """Generate comparison summary."""
        changes = len(results.get('comparison', {}).get('changes', []))
        return f"Topology comparison completed with {changes} changes detected"
    
    def _generate_annotation_summary(self, results: Dict[str, Any]) -> str:
        """Generate annotation summary."""
        return "Diagram annotations added successfully"
    
    def _generate_layer_summary(self, results: Dict[str, Any]) -> str:
        """Generate layer visualization summary."""
        layers = len([k for k in results.keys() if k.endswith('_layer')])
        return f"Network layer visualization completed for {layers} layers"
    
    def _generate_automation_summary(self, results: Dict[str, Any]) -> str:
        """Generate automation summary."""
        tasks = len(results.get('scheduled_tasks', []))
        return f"Diagram automation configured with {tasks} scheduled tasks"
    
    # Placeholder methods for complex operations
    
    async def _generate_web_interface(
        self, interactive_viz: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate web interface for interactive diagram."""
        return {
            'interface_type': 'web',
            'url': f"/diagram/{parameters.get('diagram_id', 'unknown')}",
            'features': ['zoom', 'pan', 'select', 'hover']
        }
    
    async def _process_topology_changes(self, diagram_id: str, updated_topology: Dict[str, Any]) -> None:
        """Process topology changes for real-time updates."""
        # Compare with cached topology and trigger updates if needed
        pass
    
    async def _refresh_realtime_diagram(self, diagram_id: str) -> None:
        """Refresh real-time diagram."""
        # Update diagram with latest topology data
        pass
    
    async def _setup_diagram_automation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Setup diagram automation configuration."""
        return {
            'schedule': parameters.get('schedule', 'daily'),
            'formats': parameters.get('formats', ['svg']),
            'notifications': parameters.get('notifications', True)
        }
    
    async def _schedule_automated_diagrams(self, automation_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Schedule automated diagram generation tasks."""
        return [
            {
                'task_id': 'auto_diagram_1',
                'schedule': automation_config.get('schedule', 'daily'),
                'next_run': datetime.utcnow() + timedelta(days=1)
            }
        ]
    
    async def handle_message(self, message: InterAgentMessage) -> Optional[InterAgentMessage]:
        """Handle inter-agent messages."""
        response = await super().handle_message(message)
        if response:
            return response
        
        # Handle diagram-specific messages
        if message.topic == "diagram_request":
            # Handle diagram requests from other agents
            return await self._handle_diagram_request(message)
        elif message.topic == "topology_update":
            # Handle topology update notifications
            return await self._handle_topology_update(message)
        
        return None
    
    async def _handle_diagram_request(self, message: InterAgentMessage) -> InterAgentMessage:
        """Handle diagram requests from other agents."""
        # Process diagram request
        response_payload = {'status': 'accepted'}
        
        return InterAgentMessage(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            topic="diagram_response",
            payload=response_payload,
            correlation_id=message.message_id
        )
    
    async def _handle_topology_update(self, message: InterAgentMessage) -> InterAgentMessage:
        """Handle topology update notifications."""
        # Process topology update
        topology_data = message.payload.get('topology_data', {})
        
        # Update cached topology
        self.topology_cache[message.sender_id] = {
            'topology': topology_data,
            'timestamp': datetime.utcnow()
        }
        
        return InterAgentMessage(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            topic="topology_update_response",
            payload={'status': 'updated'},
            correlation_id=message.message_id
        )
    
    def get_active_diagrams(self) -> Dict[str, Any]:
        """Get information about active diagrams."""
        return {
            diagram_id: {
                'type': diagram['type'],
                'status': diagram['status'],
                'started_at': diagram['started_at'].isoformat(),
                'progress': diagram.get('progress', 0)
            }
            for diagram_id, diagram in self.active_diagrams.items()
        }
    
    def get_diagram_statistics(self) -> Dict[str, Any]:
        """Get diagram statistics."""
        return {
            'active_diagrams': len(self.active_diagrams),
            'diagram_cache_size': len(self.diagram_cache),
            'topology_cache_size': len(self.topology_cache),
            'realtime_connections': len(self.realtime_connections),
            'diagram_history_size': len(self.diagram_history)
        }