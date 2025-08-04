"""
Monitor Command Agent for CloudWAN MCP CLI.

This agent provides real-time monitoring and alerting capabilities for CloudWAN
environments, including CloudWatch metrics collection, network performance
monitoring, and proactive alerting.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime

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

# Import existing monitoring tools
from ..tools.monitoring.cloudwatch_metrics_synthesizer import CloudWatchMetricsSynthesizer
from ..tools.monitoring.dashboard_automator import DashboardAutomator
from ..tools.monitoring.realtime_alerting import RealtimeAlertingEngine
from ..tools.monitoring.anomaly_detection_engine import AnomalyDetectionEngine
from ..tools.monitoring.multi_region_monitor import MultiRegionMonitor
from ..tools.monitoring.monitoring_tools import MonitoringTools

logger = logging.getLogger(__name__)


class MonitorCommandAgent(AbstractAgent):
    """
    Advanced monitoring command agent for real-time network monitoring.
    
    This agent orchestrates sophisticated monitoring operations including:
    - Real-time CloudWatch metrics collection and analysis
    - Network performance monitoring and SLA tracking
    - Proactive alerting and anomaly detection
    - Multi-region monitoring coordination
    - Dashboard automation and visualization
    """
    
    def __init__(self, agent_id: str = "monitor_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, AgentType.MONITORING, config)
        
        # Monitoring tools
        self.metrics_synthesizer: Optional[CloudWatchMetricsSynthesizer] = None
        self.dashboard_automator: Optional[DashboardAutomator] = None
        self.alerting_engine: Optional[RealtimeAlertingEngine] = None
        self.anomaly_detector: Optional[AnomalyDetectionEngine] = None
        self.multi_region_monitor: Optional[MultiRegionMonitor] = None
        self.monitoring_tools: Optional[MonitoringTools] = None
        
        # Monitoring state
        self.active_monitors: Dict[str, Dict[str, Any]] = {}
        self.alert_subscriptions: Dict[str, List[str]] = {}
        self.metric_streams: Dict[str, AsyncGenerator] = {}
        self.dashboard_cache: Dict[str, Any] = {}
        self.monitoring_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.max_concurrent_monitors = self.config.get('max_concurrent_monitors', 10)
        self.metric_collection_interval = self.config.get('metric_collection_interval', 60)
        self.alert_threshold_defaults = self.config.get('alert_thresholds', {})
        self.dashboard_refresh_interval = self.config.get('dashboard_refresh_interval', 300)
        
        # Real-time monitoring
        self.websocket_enabled = self.config.get('websocket_enabled', False)
        self.websocket_server = None
        self.websocket_notifier = None
        
    async def initialize(self) -> None:
        """Initialize the monitor agent with all required tools."""
        try:
            self.logger.info(f"Initializing monitor agent {self.agent_id}")
            
            # Initialize monitoring tools
            self.metrics_synthesizer = CloudWatchMetricsSynthesizer(
                config=self.config.get('metrics_synthesizer', {})
            )
            self.dashboard_automator = DashboardAutomator(
                config=self.config.get('dashboard_automator', {})
            )
            self.alerting_engine = RealtimeAlertingEngine(
                config=self.config.get('alerting_engine', {})
            )
            self.anomaly_detector = AnomalyDetectionEngine(
                config=self.config.get('anomaly_detector', {})
            )
            self.multi_region_monitor = MultiRegionMonitor(
                config=self.config.get('multi_region_monitor', {})
            )
            self.monitoring_tools = MonitoringTools(
                config=self.config.get('monitoring_tools', {})
            )
            
            # Initialize capabilities
            self.capabilities = self.get_capabilities()
            
            # Start background monitoring tasks
            await self._start_background_monitoring()
            
            # Set status to ready
            self.status = AgentStatus.READY
            self.logger.info(f"Monitor agent {self.agent_id} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitor agent: {str(e)}")
            raise AgentInitializationError(f"Monitor agent initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown the monitor agent gracefully."""
        self.logger.info(f"Shutting down monitor agent {self.agent_id}")
        
        # Stop all active monitors
        for monitor_id, monitor in self.active_monitors.items():
            if 'task' in monitor and not monitor['task'].done():
                monitor['task'].cancel()
                self.logger.info(f"Cancelled monitor {monitor_id}")
        
        # Close metric streams
        for stream_id, stream in self.metric_streams.items():
            try:
                await stream.aclose()
            except Exception as e:
                self.logger.error(f"Error closing metric stream {stream_id}: {str(e)}")
        
        # Wait for tasks to complete
        if self.active_monitors:
            tasks = [monitor['task'] for monitor in self.active_monitors.values() 
                    if 'task' in monitor and not monitor['task'].done()]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clear state
        self.active_monitors.clear()
        self.alert_subscriptions.clear()
        self.metric_streams.clear()
        self.dashboard_cache.clear()
        
        self.status = AgentStatus.STOPPED
        self.logger.info(f"Monitor agent {self.agent_id} shutdown complete")
    
    async def execute_capability(
        self, 
        capability_name: str, 
        context: CommandContext, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a specific monitoring capability."""
        self.logger.debug(f"Executing capability {capability_name}")
        
        # Create monitor ID for tracking
        monitor_id = f"{capability_name}_{context.command_id}"
        
        try:
            # Execute capability based on name
            if capability_name == "realtime_monitoring":
                result = await self._execute_realtime_monitoring(context, parameters, monitor_id)
            elif capability_name == "metric_collection":
                result = await self._execute_metric_collection(context, parameters, monitor_id)
            elif capability_name == "alerting_setup":
                result = await self._execute_alerting_setup(context, parameters, monitor_id)
            elif capability_name == "dashboard_creation":
                result = await self._execute_dashboard_creation(context, parameters, monitor_id)
            elif capability_name == "anomaly_monitoring":
                result = await self._execute_anomaly_monitoring(context, parameters, monitor_id)
            elif capability_name == "performance_tracking":
                result = await self._execute_performance_tracking(context, parameters, monitor_id)
            elif capability_name == "multi_region_monitoring":
                result = await self._execute_multi_region_monitoring(context, parameters, monitor_id)
            elif capability_name == "sla_monitoring":
                result = await self._execute_sla_monitoring(context, parameters, monitor_id)
            elif capability_name == "custom_metrics":
                result = await self._execute_custom_metrics(context, parameters, monitor_id)
            elif capability_name == "monitoring_analytics":
                result = await self._execute_monitoring_analytics(context, parameters, monitor_id)
            else:
                raise AgentExecutionError(f"Unknown capability: {capability_name}")
            
            # Update monitoring history
            self._update_monitoring_history(capability_name, context, parameters, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing capability {capability_name}: {str(e)}")
            raise AgentExecutionError(f"Monitor capability {capability_name} failed: {str(e)}")
        
        finally:
            # Clean up active monitor if it's a one-time operation
            if monitor_id in self.active_monitors and not self._is_long_running_capability(capability_name):
                del self.active_monitors[monitor_id]
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get the list of capabilities this agent provides."""
        return [
            AgentCapability(
                name="realtime_monitoring",
                command_types=[CommandType.MONITOR],
                description="Real-time network monitoring with live metrics streaming",
                priority=10,
                dependencies=[],
                supports_async=True,
                timeout_seconds=3600  # Long-running
            ),
            AgentCapability(
                name="metric_collection",
                command_types=[CommandType.MONITOR],
                description="CloudWatch metrics collection and synthesis",
                priority=9,
                dependencies=[],
                supports_async=True,
                timeout_seconds=300
            ),
            AgentCapability(
                name="alerting_setup",
                command_types=[CommandType.MONITOR],
                description="Setup and manage real-time alerting rules",
                priority=8,
                dependencies=[],
                supports_async=True,
                timeout_seconds=180
            ),
            AgentCapability(
                name="dashboard_creation",
                command_types=[CommandType.MONITOR],
                description="Automated dashboard creation and management",
                priority=7,
                dependencies=[],
                supports_async=True,
                timeout_seconds=240
            ),
            AgentCapability(
                name="anomaly_monitoring",
                command_types=[CommandType.MONITOR],
                description="Anomaly detection and monitoring",
                priority=6,
                dependencies=[],
                supports_async=True,
                timeout_seconds=1800  # Long-running
            ),
            AgentCapability(
                name="performance_tracking",
                command_types=[CommandType.MONITOR],
                description="Network performance monitoring and SLA tracking",
                priority=5,
                dependencies=[],
                supports_async=True,
                timeout_seconds=900
            ),
            AgentCapability(
                name="multi_region_monitoring",
                command_types=[CommandType.MONITOR],
                description="Multi-region network monitoring coordination",
                priority=4,
                dependencies=[],
                supports_async=True,
                timeout_seconds=1200
            ),
            AgentCapability(
                name="sla_monitoring",
                command_types=[CommandType.MONITOR],
                description="SLA monitoring and compliance tracking",
                priority=3,
                dependencies=[],
                supports_async=True,
                timeout_seconds=600
            ),
            AgentCapability(
                name="custom_metrics",
                command_types=[CommandType.MONITOR],
                description="Custom metrics creation and monitoring",
                priority=2,
                dependencies=[],
                supports_async=True,
                timeout_seconds=300
            ),
            AgentCapability(
                name="monitoring_analytics",
                command_types=[CommandType.MONITOR],
                description="Monitoring data analytics and insights",
                priority=1,
                dependencies=[],
                supports_async=True,
                timeout_seconds=480
            )
        ]
    
    async def _execute_realtime_monitoring(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute real-time monitoring with live metrics streaming."""
        self.logger.info(f"Starting real-time monitoring {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'realtime_monitoring',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'parameters': parameters
        }
        
        # Start real-time metric collection
        if self.metrics_synthesizer:
            metric_stream = self.metrics_synthesizer.start_realtime_collection(
                resources=parameters.get('resources', []),
                metrics=parameters.get('metrics', []),
                interval=parameters.get('interval', self.metric_collection_interval)
            )
            self.metric_streams[monitor_id] = metric_stream
        
        # Setup alerting if requested
        if parameters.get('enable_alerting', True) and self.alerting_engine:
            await self.alerting_engine.setup_realtime_alerts(
                monitor_id=monitor_id,
                thresholds=parameters.get('alert_thresholds', self.alert_threshold_defaults)
            )
        
        # Create monitoring task
        monitor_task = asyncio.create_task(
            self._realtime_monitoring_loop(monitor_id, parameters)
        )
        self.active_monitors[monitor_id]['task'] = monitor_task
        
        return {
            'monitor_id': monitor_id,
            'status': 'started',
            'started_at': datetime.utcnow().isoformat(),
            'monitoring_type': 'realtime',
            'parameters': parameters
        }
    
    async def _execute_metric_collection(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute CloudWatch metrics collection."""
        self.logger.info(f"Starting metric collection {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'metric_collection',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Collect metrics using synthesizer
        if self.metrics_synthesizer:
            metrics = await self.metrics_synthesizer.collect_metrics(
                namespace=parameters.get('namespace', 'AWS/CloudWAN'),
                metrics=parameters.get('metrics', []),
                start_time=parameters.get('start_time'),
                end_time=parameters.get('end_time'),
                period=parameters.get('period', 300)
            )
            results['metrics'] = metrics
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed metric collection {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'metric_collection',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_alerting_setup(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute alerting setup and configuration."""
        self.logger.info(f"Setting up alerting {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'alerting_setup',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Setup alerting rules
        if self.alerting_engine:
            alert_rules = await self.alerting_engine.setup_alert_rules(
                rules=parameters.get('rules', []),
                targets=parameters.get('targets', []),
                escalation_policy=parameters.get('escalation_policy', {})
            )
            results['alert_rules'] = alert_rules
            self.active_monitors[monitor_id]['progress'] = 50
            
            # Enable real-time alerting
            await self.alerting_engine.enable_realtime_alerting(
                monitor_id=monitor_id,
                websocket_enabled=self.websocket_enabled
            )
            results['realtime_alerting'] = True
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed alerting setup {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'alerting_setup',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_dashboard_creation(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute dashboard creation and automation."""
        self.logger.info(f"Creating dashboard {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'dashboard_creation',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Create dashboard
        if self.dashboard_automator:
            dashboard = await self.dashboard_automator.create_dashboard(
                name=parameters.get('name', f'CloudWAN-{monitor_id}'),
                widgets=parameters.get('widgets', []),
                layout=parameters.get('layout', 'grid'),
                refresh_interval=parameters.get('refresh_interval', self.dashboard_refresh_interval)
            )
            results['dashboard'] = dashboard
            self.active_monitors[monitor_id]['progress'] = 80
            
            # Cache dashboard
            self.dashboard_cache[monitor_id] = dashboard
            
            # Setup auto-refresh if requested
            if parameters.get('auto_refresh', True):
                await self.dashboard_automator.setup_auto_refresh(
                    dashboard_id=dashboard['id'],
                    interval=parameters.get('refresh_interval', self.dashboard_refresh_interval)
                )
                results['auto_refresh'] = True
            
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed dashboard creation {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'dashboard_creation',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_anomaly_monitoring(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute anomaly detection monitoring."""
        self.logger.info(f"Starting anomaly monitoring {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'anomaly_monitoring',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'parameters': parameters
        }
        
        # Start anomaly detection
        if self.anomaly_detector:
            anomaly_task = asyncio.create_task(
                self._anomaly_monitoring_loop(monitor_id, parameters)
            )
            self.active_monitors[monitor_id]['task'] = anomaly_task
        
        return {
            'monitor_id': monitor_id,
            'status': 'started',
            'started_at': datetime.utcnow().isoformat(),
            'monitoring_type': 'anomaly_monitoring',
            'parameters': parameters
        }
    
    async def _execute_performance_tracking(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute performance tracking and SLA monitoring."""
        self.logger.info(f"Starting performance tracking {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'performance_tracking',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Collect performance metrics
        if self.monitoring_tools:
            perf_metrics = await self.monitoring_tools.collect_performance_metrics(
                resources=parameters.get('resources', []),
                timeframe=parameters.get('timeframe', '1h')
            )
            results['performance_metrics'] = perf_metrics
            self.active_monitors[monitor_id]['progress'] = 50
            
            # Calculate SLA compliance
            sla_compliance = await self.monitoring_tools.calculate_sla_compliance(
                metrics=perf_metrics,
                sla_targets=parameters.get('sla_targets', {})
            )
            results['sla_compliance'] = sla_compliance
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed performance tracking {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'performance_tracking',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_multi_region_monitoring(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute multi-region monitoring coordination."""
        self.logger.info(f"Starting multi-region monitoring {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'multi_region_monitoring',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        regions = parameters.get('regions', [])
        
        # Monitor each region
        if self.multi_region_monitor:
            for i, region in enumerate(regions):
                region_metrics = await self.multi_region_monitor.monitor_region(
                    region=region,
                    resources=parameters.get('resources', []),
                    metrics=parameters.get('metrics', [])
                )
                results[region] = region_metrics
                
                progress = int(((i + 1) / len(regions)) * 100)
                self.active_monitors[monitor_id]['progress'] = progress
            
            # Cross-region correlation
            correlation = await self.multi_region_monitor.correlate_metrics(
                region_metrics=results
            )
            results['cross_region_correlation'] = correlation
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed multi-region monitoring {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'multi_region_monitoring',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_sla_monitoring(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute SLA monitoring and compliance tracking."""
        self.logger.info(f"Starting SLA monitoring {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'sla_monitoring',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Monitor SLA compliance
        if self.monitoring_tools:
            sla_status = await self.monitoring_tools.monitor_sla_compliance(
                sla_definitions=parameters.get('sla_definitions', []),
                monitoring_period=parameters.get('monitoring_period', '24h')
            )
            results['sla_status'] = sla_status
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed SLA monitoring {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'sla_monitoring',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_custom_metrics(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute custom metrics creation and monitoring."""
        self.logger.info(f"Starting custom metrics {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'custom_metrics',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Create custom metrics
        if self.metrics_synthesizer:
            custom_metrics = await self.metrics_synthesizer.create_custom_metrics(
                metric_definitions=parameters.get('metric_definitions', []),
                namespace=parameters.get('namespace', 'Custom/CloudWAN')
            )
            results['custom_metrics'] = custom_metrics
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed custom metrics {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'custom_metrics',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    async def _execute_monitoring_analytics(
        self, context: CommandContext, parameters: Dict[str, Any], monitor_id: str
    ) -> Dict[str, Any]:
        """Execute monitoring data analytics and insights."""
        self.logger.info(f"Starting monitoring analytics {monitor_id}")
        
        # Register monitor
        self.active_monitors[monitor_id] = {
            'type': 'monitoring_analytics',
            'started_at': datetime.utcnow(),
            'status': 'running',
            'progress': 0
        }
        
        results = {}
        
        # Analyze monitoring data
        if self.monitoring_tools:
            analytics = await self.monitoring_tools.analyze_monitoring_data(
                timeframe=parameters.get('timeframe', '7d'),
                metrics=parameters.get('metrics', []),
                analysis_type=parameters.get('analysis_type', 'trend')
            )
            results['analytics'] = analytics
            self.active_monitors[monitor_id]['progress'] = 100
        
        self.active_monitors[monitor_id]['status'] = 'completed'
        self.logger.info(f"Completed monitoring analytics {monitor_id}")
        
        return {
            'monitor_id': monitor_id,
            'monitoring_type': 'monitoring_analytics',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results
        }
    
    # Background monitoring loops
    
    async def _realtime_monitoring_loop(self, monitor_id: str, parameters: Dict[str, Any]) -> None:
        """Background loop for real-time monitoring."""
        try:
            while monitor_id in self.active_monitors:
                # Collect real-time metrics
                if self.metrics_synthesizer:
                    metrics = await self.metrics_synthesizer.collect_realtime_metrics(
                        resources=parameters.get('resources', [])
                    )
                    
                    # Process metrics and check thresholds
                    await self._process_realtime_metrics(monitor_id, metrics)
                
                # Wait for next collection interval
                await asyncio.sleep(parameters.get('interval', self.metric_collection_interval))
                
        except asyncio.CancelledError:
            self.logger.info(f"Real-time monitoring loop {monitor_id} cancelled")
        except Exception as e:
            self.logger.error(f"Error in real-time monitoring loop {monitor_id}: {str(e)}")
    
    async def _anomaly_monitoring_loop(self, monitor_id: str, parameters: Dict[str, Any]) -> None:
        """Background loop for anomaly monitoring."""
        try:
            while monitor_id in self.active_monitors:
                # Check for anomalies
                if self.anomaly_detector:
                    anomalies = await self.anomaly_detector.detect_anomalies(
                        timeframe=parameters.get('timeframe', '1h'),
                        sensitivity=parameters.get('sensitivity', 'medium')
                    )
                    
                    # Process anomalies
                    await self._process_anomalies(monitor_id, anomalies)
                
                # Wait for next check
                await asyncio.sleep(parameters.get('check_interval', 300))
                
        except asyncio.CancelledError:
            self.logger.info(f"Anomaly monitoring loop {monitor_id} cancelled")
        except Exception as e:
            self.logger.error(f"Error in anomaly monitoring loop {monitor_id}: {str(e)}")
    
    # Helper methods
    
    async def _start_background_monitoring(self) -> None:
        """Start background monitoring tasks."""
        # Start metric collection background task
        if self.config.get('enable_background_monitoring', True):
            asyncio.create_task(self._background_metric_collection())
        
        # Start health check background task
        if self.config.get('enable_health_checks', True):
            asyncio.create_task(self._background_health_checks())
    
    async def _background_metric_collection(self) -> None:
        """Background metric collection task."""
        while self.status != AgentStatus.STOPPED:
            try:
                # Collect system metrics
                if self.metrics_synthesizer:
                    await self.metrics_synthesizer.collect_system_metrics()
                
                await asyncio.sleep(self.metric_collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background metric collection: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _background_health_checks(self) -> None:
        """Background health check task."""
        while self.status != AgentStatus.STOPPED:
            try:
                # Check health of monitoring tools
                await self._check_monitoring_tool_health()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background health checks: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _process_realtime_metrics(self, monitor_id: str, metrics: Dict[str, Any]) -> None:
        """Process real-time metrics and trigger alerts if necessary."""
        # Check thresholds and trigger alerts
        if self.alerting_engine:
            await self.alerting_engine.process_metrics(monitor_id, metrics)
    
    async def _process_anomalies(self, monitor_id: str, anomalies: List[Dict[str, Any]]) -> None:
        """Process detected anomalies."""
        if anomalies and self.alerting_engine:
            await self.alerting_engine.process_anomalies(monitor_id, anomalies)
    
    async def _check_monitoring_tool_health(self) -> None:
        """Check health of monitoring tools."""
        tools = [
            self.metrics_synthesizer,
            self.dashboard_automator,
            self.alerting_engine,
            self.anomaly_detector,
            self.multi_region_monitor,
            self.monitoring_tools
        ]
        
        for tool in tools:
            if tool and hasattr(tool, 'health_check'):
                try:
                    await tool.health_check()
                except Exception as e:
                    self.logger.error(f"Health check failed for {tool.__class__.__name__}: {str(e)}")
    
    def _is_long_running_capability(self, capability_name: str) -> bool:
        """Check if capability is long-running."""
        long_running_capabilities = {
            'realtime_monitoring',
            'anomaly_monitoring'
        }
        return capability_name in long_running_capabilities
    
    def _update_monitoring_history(
        self, capability_name: str, context: CommandContext, 
        parameters: Dict[str, Any], result: Any
    ) -> None:
        """Update monitoring history."""
        self.monitoring_history.append({
            'timestamp': datetime.utcnow(),
            'capability': capability_name,
            'command_id': context.command_id,
            'parameters': parameters,
            'success': True,
            'result_summary': self._summarize_result(result)
        })
        
        # Limit history size
        if len(self.monitoring_history) > 1000:
            self.monitoring_history = self.monitoring_history[-1000:]
    
    def _summarize_result(self, result: Any) -> str:
        """Generate a summary of monitoring result."""
        if isinstance(result, dict):
            if 'monitor_id' in result:
                return f"Monitor {result['monitor_id']} - {result.get('status', 'unknown')}"
            return f"Monitoring completed with {len(result)} components"
        return "Monitoring completed"
    
    async def handle_message(self, message: InterAgentMessage) -> Optional[InterAgentMessage]:
        """Handle inter-agent messages."""
        response = await super().handle_message(message)
        if response:
            return response
        
        # Handle monitoring-specific messages
        if message.topic == "monitoring_request":
            # Handle monitoring requests from other agents
            return await self._handle_monitoring_request(message)
        elif message.topic == "alert_subscription":
            # Handle alert subscription requests
            return await self._handle_alert_subscription(message)
        
        return None
    
    async def _handle_monitoring_request(self, message: InterAgentMessage) -> InterAgentMessage:
        """Handle monitoring requests from other agents."""
        # Process monitoring request
        response_payload = {'status': 'accepted'}
        
        return InterAgentMessage(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            topic="monitoring_response",
            payload=response_payload,
            correlation_id=message.message_id
        )
    
    async def _handle_alert_subscription(self, message: InterAgentMessage) -> InterAgentMessage:
        """Handle alert subscription requests."""
        # Process alert subscription
        agent_id = message.sender_id
        alert_types = message.payload.get('alert_types', [])
        
        if agent_id not in self.alert_subscriptions:
            self.alert_subscriptions[agent_id] = []
        
        self.alert_subscriptions[agent_id].extend(alert_types)
        
        return InterAgentMessage(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            topic="alert_subscription_response",
            payload={'status': 'subscribed', 'alert_types': alert_types},
            correlation_id=message.message_id
        )
    
    def get_active_monitors(self) -> Dict[str, Any]:
        """Get information about active monitors."""
        return {
            monitor_id: {
                'type': monitor['type'],
                'status': monitor['status'],
                'started_at': monitor['started_at'].isoformat(),
                'progress': monitor.get('progress', 0)
            }
            for monitor_id, monitor in self.active_monitors.items()
        }
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'active_monitors': len(self.active_monitors),
            'metric_streams': len(self.metric_streams),
            'alert_subscriptions': len(self.alert_subscriptions),
            'dashboard_cache_size': len(self.dashboard_cache),
            'monitoring_history_size': len(self.monitoring_history)
        }