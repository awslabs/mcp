"""
Memory Monitoring Dashboard for CloudWAN MCP System.

This module provides a comprehensive real-time memory monitoring dashboard
with web interface, metrics collection, and visualization capabilities.
Designed for enterprise-scale network topology processing with memory optimization.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import tracemalloc
import psutil
import gc
from collections import deque
from contextlib import asynccontextmanager

# Web dashboard dependencies
try:
    from flask import Flask, render_template_string, jsonify, request
    from flask_socketio import SocketIO, emit

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Memory optimization integration
from .memory_optimization import (
    get_memory_usage,
)

# Streaming topology integration
from .streaming_topology_manager import StreamingTopologyManager

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    """Comprehensive memory metrics snapshot."""

    __slots__ = (
        "timestamp",
        "total_memory_mb",
        "used_memory_mb",
        "available_memory_mb",
        "memory_percent",
        "python_memory_mb",
        "gc_stats",
        "topology_memory_mb",
        "agent_memory_mb",
        "cache_memory_mb",
        "thread_count",
        "process_count",
    )

    timestamp: datetime
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_percent: float
    python_memory_mb: float
    gc_stats: Dict[str, Any]
    topology_memory_mb: float
    agent_memory_mb: float
    cache_memory_mb: float
    thread_count: int
    process_count: int


@dataclass
class MemoryAlert:
    """Memory alert information."""

    __slots__ = (
        "timestamp",
        "level",
        "message",
        "metric_name",
        "current_value",
        "threshold_value",
        "component",
        "action_taken",
    )

    timestamp: datetime
    level: str  # 'info', 'warning', 'error', 'critical'
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    component: str
    action_taken: Optional[str] = None


class MemoryMetricsCollector:
    """Collects comprehensive memory metrics for monitoring."""

    def __init__(
        self, collection_interval: float = 1.0, max_history_size: int = 3600
    ):  # 1 hour at 1s intervals
        self.collection_interval = collection_interval
        self.max_history_size = max_history_size
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.component_memory: Dict[str, float] = {}
        self.process = psutil.Process()
        self.logger = logging.getLogger(__name__)

        # Enable tracemalloc for Python memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        # Collection state
        self._collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_thread: Optional[threading.Thread] = None

    def register_component(self, name: str, memory_tracker: Callable[[], float]):
        """Register a component for memory tracking."""
        self.component_memory[name] = memory_tracker
        self.logger.debug(f"Registered component for memory tracking: {name}")

    def collect_metrics(self) -> MemoryMetrics:
        """Collect current memory metrics."""
        try:
            # System memory metrics
            memory_info = psutil.virtual_memory()

            # Python process memory
            process_memory = self.process.memory_info()

            # GC statistics
            gc_stats = {
                "collections": gc.get_stats(),
                "objects": len(gc.get_objects()),
                "garbage": len(gc.garbage) if hasattr(gc, "garbage") else 0,
            }

            # Component-specific memory
            topology_memory = self._get_component_memory("topology")
            agent_memory = self._get_component_memory("agents")
            cache_memory = self._get_component_memory("cache")

            # System resources
            thread_count = self.process.num_threads()
            process_count = len(psutil.pids())

            metrics = MemoryMetrics(
                timestamp=datetime.now(),
                total_memory_mb=memory_info.total / (1024 * 1024),
                used_memory_mb=memory_info.used / (1024 * 1024),
                available_memory_mb=memory_info.available / (1024 * 1024),
                memory_percent=memory_info.percent,
                python_memory_mb=process_memory.rss / (1024 * 1024),
                gc_stats=gc_stats,
                topology_memory_mb=topology_memory,
                agent_memory_mb=agent_memory,
                cache_memory_mb=cache_memory,
                thread_count=thread_count,
                process_count=process_count,
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting memory metrics: {e}")
            # Return minimal metrics on error
            return MemoryMetrics(
                timestamp=datetime.now(),
                total_memory_mb=0.0,
                used_memory_mb=0.0,
                available_memory_mb=0.0,
                memory_percent=0.0,
                python_memory_mb=0.0,
                gc_stats={},
                topology_memory_mb=0.0,
                agent_memory_mb=0.0,
                cache_memory_mb=0.0,
                thread_count=0,
                process_count=0,
            )

    def _get_component_memory(self, component: str) -> float:
        """Get memory usage for a specific component."""
        if component in self.component_memory:
            try:
                return self.component_memory[component]()
            except Exception as e:
                self.logger.warning(f"Error getting memory for component {component}: {e}")
        return 0.0

    async def start_collection(self):
        """Start continuous metrics collection."""
        if self._collecting:
            return

        self._collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self.logger.info("Started memory metrics collection")

    async def stop_collection(self):
        """Stop metrics collection."""
        if not self._collecting:
            return

        self._collecting = False

        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped memory metrics collection")

    async def _collection_loop(self):
        """Main collection loop."""
        while self._collecting:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)

                # Log metrics periodically
                if len(self.metrics_history) % 60 == 0:  # Every minute
                    self.logger.info(
                        f"Memory metrics: {metrics.memory_percent:.1f}% used, "
                        f"Python: {metrics.python_memory_mb:.1f}MB, "
                        f"Topology: {metrics.topology_memory_mb:.1f}MB"
                    )

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self.collection_interval)

    def get_recent_metrics(self, duration_seconds: int = 300) -> List[MemoryMetrics]:
        """Get metrics from the last N seconds."""
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current memory metrics."""
        if not self.metrics_history:
            return {}

        latest = self.metrics_history[-1]
        recent_metrics = self.get_recent_metrics(300)  # Last 5 minutes

        if not recent_metrics:
            return {}

        # Calculate trends
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        min_memory = min(m.memory_percent for m in recent_metrics)

        return {
            "current": {
                "memory_percent": latest.memory_percent,
                "python_memory_mb": latest.python_memory_mb,
                "topology_memory_mb": latest.topology_memory_mb,
                "agent_memory_mb": latest.agent_memory_mb,
                "cache_memory_mb": latest.cache_memory_mb,
                "thread_count": latest.thread_count,
            },
            "trends": {
                "avg_memory_percent": avg_memory,
                "max_memory_percent": max_memory,
                "min_memory_percent": min_memory,
                "samples": len(recent_metrics),
            },
            "system": {
                "total_memory_mb": latest.total_memory_mb,
                "available_memory_mb": latest.available_memory_mb,
                "process_count": latest.process_count,
            },
        }


class MemoryAlertManager:
    """Manages memory alerts and notifications."""

    def __init__(
        self,
        warning_threshold: float = 75.0,
        critical_threshold: float = 85.0,
        max_alert_history: int = 1000,
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.max_alert_history = max_alert_history
        self.alert_history: deque = deque(maxlen=max_alert_history)
        self.active_alerts: Dict[str, MemoryAlert] = {}
        self.alert_callbacks: List[Callable[[MemoryAlert], None]] = []
        self.logger = logging.getLogger(__name__)

    def add_alert_callback(self, callback: Callable[[MemoryAlert], None]):
        """Add callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def check_metrics(self, metrics: MemoryMetrics):
        """Check metrics against thresholds and generate alerts."""
        alerts = []

        # Check memory percentage
        if metrics.memory_percent >= self.critical_threshold:
            alert = self._create_alert(
                "critical",
                f"Critical memory usage: {metrics.memory_percent:.1f}%",
                "memory_percent",
                metrics.memory_percent,
                self.critical_threshold,
                "system",
            )
            alerts.append(alert)
        elif metrics.memory_percent >= self.warning_threshold:
            alert = self._create_alert(
                "warning",
                f"High memory usage: {metrics.memory_percent:.1f}%",
                "memory_percent",
                metrics.memory_percent,
                self.warning_threshold,
                "system",
            )
            alerts.append(alert)

        # Check Python memory growth
        if metrics.python_memory_mb > 1000:  # 1GB threshold
            alert = self._create_alert(
                "warning",
                f"High Python memory usage: {metrics.python_memory_mb:.1f}MB",
                "python_memory_mb",
                metrics.python_memory_mb,
                1000,
                "python",
            )
            alerts.append(alert)

        # Check topology memory
        if metrics.topology_memory_mb > 500:  # 500MB threshold
            alert = self._create_alert(
                "warning",
                f"High topology memory usage: {metrics.topology_memory_mb:.1f}MB",
                "topology_memory_mb",
                metrics.topology_memory_mb,
                500,
                "topology",
            )
            alerts.append(alert)

        # Process alerts
        for alert in alerts:
            self._process_alert(alert)

    def _create_alert(
        self,
        level: str,
        message: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        component: str,
    ) -> MemoryAlert:
        """Create a memory alert."""
        return MemoryAlert(
            timestamp=datetime.now(),
            level=level,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            component=component,
        )

    def _process_alert(self, alert: MemoryAlert):
        """Process and manage an alert."""
        alert_key = f"{alert.component}_{alert.metric_name}"

        # Check if this is a new alert or update
        if alert_key not in self.active_alerts:
            # New alert
            self.active_alerts[alert_key] = alert
            self.alert_history.append(alert)

            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")

            self.logger.warning(f"Memory alert: {alert.message}")
        else:
            # Update existing alert
            existing_alert = self.active_alerts[alert_key]
            if existing_alert.level != alert.level:
                # Level changed, treat as new alert
                self.active_alerts[alert_key] = alert
                self.alert_history.append(alert)
                self.logger.warning(f"Memory alert level changed: {alert.message}")

    def clear_alert(self, component: str, metric_name: str):
        """Clear an active alert."""
        alert_key = f"{component}_{metric_name}"
        if alert_key in self.active_alerts:
            del self.active_alerts[alert_key]
            self.logger.info(f"Cleared alert for {component}_{metric_name}")

    def get_active_alerts(self) -> List[MemoryAlert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[MemoryAlert]:
        """Get alert history for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp >= cutoff_time]


class MemoryMonitoringDashboard:
    """Web-based memory monitoring dashboard."""

    def __init__(self, host: str = "localhost", port: int = 5000, debug: bool = False):
        self.host = host
        self.port = port
        self.debug = debug

        self.metrics_collector = MemoryMetricsCollector()
        self.alert_manager = MemoryAlertManager()
        self.streaming_manager = StreamingTopologyManager()

        # Web app setup
        self.app = None
        self.socketio = None
        self.web_thread = None
        self.running = False

        # Add alert callback for web notifications
        self.alert_manager.add_alert_callback(self._handle_web_alert)

        self.logger = logging.getLogger(__name__)

        if not FLASK_AVAILABLE:
            self.logger.warning("Flask not available - web dashboard disabled")

    def _handle_web_alert(self, alert: MemoryAlert):
        """Handle alert for web dashboard."""
        if self.socketio:
            self.socketio.emit(
                "memory_alert",
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "level": alert.level,
                    "message": alert.message,
                    "component": alert.component,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                },
            )

    def _create_web_app(self):
        """Create Flask web application."""
        if not FLASK_AVAILABLE:
            raise RuntimeError("Flask not available for web dashboard")

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "cloudwan-memory-dashboard"
        socketio = SocketIO(app, cors_allowed_origins="*")

        @app.route("/")
        def dashboard():
            return render_template_string(self._get_dashboard_template())

        @app.route("/api/metrics")
        def get_metrics():
            return jsonify(self.metrics_collector.get_metrics_summary())

        @app.route("/api/metrics/history")
        def get_metrics_history():
            duration = request.args.get("duration", 300, type=int)
            metrics = self.metrics_collector.get_recent_metrics(duration)

            return jsonify(
                [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "memory_percent": m.memory_percent,
                        "python_memory_mb": m.python_memory_mb,
                        "topology_memory_mb": m.topology_memory_mb,
                        "agent_memory_mb": m.agent_memory_mb,
                        "cache_memory_mb": m.cache_memory_mb,
                        "thread_count": m.thread_count,
                    }
                    for m in metrics
                ]
            )

        @app.route("/api/alerts")
        def get_alerts():
            return jsonify(
                [
                    {
                        "timestamp": a.timestamp.isoformat(),
                        "level": a.level,
                        "message": a.message,
                        "component": a.component,
                        "current_value": a.current_value,
                        "threshold_value": a.threshold_value,
                    }
                    for a in self.alert_manager.get_active_alerts()
                ]
            )

        @app.route("/api/alerts/history")
        def get_alert_history():
            hours = request.args.get("hours", 24, type=int)
            alerts = self.alert_manager.get_alert_history(hours)

            return jsonify(
                [
                    {
                        "timestamp": a.timestamp.isoformat(),
                        "level": a.level,
                        "message": a.message,
                        "component": a.component,
                        "current_value": a.current_value,
                        "threshold_value": a.threshold_value,
                    }
                    for a in alerts
                ]
            )

        @socketio.on("connect")
        def handle_connect():
            emit("connected", {"data": "Connected to memory dashboard"})

        @socketio.on("request_metrics")
        def handle_metrics_request():
            metrics = self.metrics_collector.get_metrics_summary()
            emit("metrics_update", metrics)

        return app, socketio

    def _get_dashboard_template(self) -> str:
        """Get HTML template for dashboard."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>CloudWAN Memory Monitoring Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .metric-label { color: #7f8c8d; margin-bottom: 10px; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .alerts-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .alert-warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .alert-critical { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }
        .status-good { background: #27ae60; }
        .status-warning { background: #f39c12; }
        .status-critical { background: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CloudWAN Memory Monitoring Dashboard</h1>
            <p>Real-time memory usage monitoring for large-scale network topology processing</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">System Memory Usage</div>
                <div class="metric-value" id="memory-percent">--</div>
                <div><span class="status-indicator" id="memory-status"></span>Available: <span id="available-memory">--</span> MB</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Python Process Memory</div>
                <div class="metric-value" id="python-memory">--</div>
                <div>MB</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Topology Memory</div>
                <div class="metric-value" id="topology-memory">--</div>
                <div>MB</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Agent Memory</div>
                <div class="metric-value" id="agent-memory">--</div>
                <div>MB</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Cache Memory</div>
                <div class="metric-value" id="cache-memory">--</div>
                <div>MB</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Active Threads</div>
                <div class="metric-value" id="thread-count">--</div>
                <div>Threads</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>Memory Usage History</h3>
            <canvas id="memory-chart" width="400" height="200"></canvas>
        </div>
        
        <div class="alerts-container">
            <h3>Active Alerts</h3>
            <div id="alerts-list">No active alerts</div>
        </div>
    </div>
    
    <script>
        const socket = io();
        
        // Chart setup
        const ctx = document.getElementById('memory-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory %',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.1
                }, {
                    label: 'Python MB',
                    data: [],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.1,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: 'Memory %' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Python MB' }
                    }
                }
            }
        });
        
        // Update metrics
        function updateMetrics(data) {
            if (data.current) {
                document.getElementById('memory-percent').textContent = data.current.memory_percent.toFixed(1) + '%';
                document.getElementById('python-memory').textContent = data.current.python_memory_mb.toFixed(1);
                document.getElementById('topology-memory').textContent = data.current.topology_memory_mb.toFixed(1);
                document.getElementById('agent-memory').textContent = data.current.agent_memory_mb.toFixed(1);
                document.getElementById('cache-memory').textContent = data.current.cache_memory_mb.toFixed(1);
                document.getElementById('thread-count').textContent = data.current.thread_count;
                
                // Update status indicator
                const statusElement = document.getElementById('memory-status');
                const memoryPercent = data.current.memory_percent;
                if (memoryPercent < 75) {
                    statusElement.className = 'status-indicator status-good';
                } else if (memoryPercent < 85) {
                    statusElement.className = 'status-indicator status-warning';
                } else {
                    statusElement.className = 'status-indicator status-critical';
                }
            }
            
            if (data.system) {
                document.getElementById('available-memory').textContent = data.system.available_memory_mb.toFixed(1);
            }
        }
        
        // Update chart
        function updateChart(historyData) {
            if (historyData.length === 0) return;
            
            chart.data.labels = historyData.map(d => new Date(d.timestamp).toLocaleTimeString());
            chart.data.datasets[0].data = historyData.map(d => d.memory_percent);
            chart.data.datasets[1].data = historyData.map(d => d.python_memory_mb);
            chart.update();
        }
        
        // Update alerts
        function updateAlerts(alerts) {
            const alertsList = document.getElementById('alerts-list');
            if (alerts.length === 0) {
                alertsList.innerHTML = 'No active alerts';
                return;
            }
            
            alertsList.innerHTML = alerts.map(alert => `
                <div class="alert alert-${alert.level}">
                    <strong>${alert.component}:</strong> ${alert.message}
                    <small>(${new Date(alert.timestamp).toLocaleTimeString()})</small>
                </div>
            `).join('');
        }
        
        // Socket event handlers
        socket.on('connect', function() {
            console.log('Connected to dashboard');
            socket.emit('request_metrics');
        });
        
        socket.on('metrics_update', updateMetrics);
        socket.on('memory_alert', function(alert) {
            console.log('Alert received:', alert);
        });
        
        // Periodic updates
        setInterval(function() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(updateMetrics);
            
            fetch('/api/metrics/history?duration=300')
                .then(response => response.json())
                .then(updateChart);
            
            fetch('/api/alerts')
                .then(response => response.json())
                .then(updateAlerts);
        }, 2000);
    </script>
</body>
</html>
        """

    async def start(self):
        """Start the memory monitoring dashboard."""
        if self.running:
            return

        self.running = True

        # Start metrics collection
        await self.metrics_collector.start_collection()

        # Register component memory trackers
        self._register_component_trackers()

        # Start web dashboard if available
        if FLASK_AVAILABLE:
            self._start_web_dashboard()

        # Start periodic alert checking
        asyncio.create_task(self._alert_check_loop())

        self.logger.info(f"Memory monitoring dashboard started on http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the memory monitoring dashboard."""
        if not self.running:
            return

        self.running = False

        # Stop metrics collection
        await self.metrics_collector.stop_collection()

        # Stop web dashboard
        if self.web_thread and self.web_thread.is_alive():
            # Flask doesn't have a clean shutdown mechanism in this context
            pass

        self.logger.info("Memory monitoring dashboard stopped")

    def _register_component_trackers(self):
        """Register component memory trackers."""
        # These would be connected to actual component memory tracking
        self.metrics_collector.register_component("topology", lambda: self._get_topology_memory())

        self.metrics_collector.register_component("agents", lambda: self._get_agent_memory())

        self.metrics_collector.register_component("cache", lambda: self._get_cache_memory())

    def _get_topology_memory(self) -> float:
        """Get topology component memory usage."""
        try:
            # This would integrate with actual topology memory tracking
            return get_memory_usage() * 0.3  # Placeholder
        except Exception:
            return 0.0

    def _get_agent_memory(self) -> float:
        """Get agent component memory usage."""
        try:
            # This would integrate with actual agent memory tracking
            return get_memory_usage() * 0.2  # Placeholder
        except Exception:
            return 0.0

    def _get_cache_memory(self) -> float:
        """Get cache component memory usage."""
        try:
            # This would integrate with actual cache memory tracking
            return get_memory_usage() * 0.1  # Placeholder
        except Exception:
            return 0.0

    def _start_web_dashboard(self):
        """Start web dashboard in background thread."""
        if not FLASK_AVAILABLE:
            return

        self.app, self.socketio = self._create_web_app()

        def run_web_app():
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,
            )

        self.web_thread = threading.Thread(target=run_web_app, daemon=True)
        self.web_thread.start()

    async def _alert_check_loop(self):
        """Periodic alert checking loop."""
        while self.running:
            try:
                if self.metrics_collector.metrics_history:
                    latest_metrics = self.metrics_collector.metrics_history[-1]
                    self.alert_manager.check_metrics(latest_metrics)

                await asyncio.sleep(5)  # Check every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(5)

    def get_dashboard_url(self) -> str:
        """Get the dashboard URL."""
        return f"http://{self.host}:{self.port}"

    @asynccontextmanager
    async def monitoring_context(self):
        """Context manager for monitoring sessions."""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()


# Factory function for easy dashboard creation
def create_memory_dashboard(
    host: str = "localhost", port: int = 5000, debug: bool = False, **kwargs
) -> MemoryMonitoringDashboard:
    """
    Create a memory monitoring dashboard instance.

    Args:
        host: Host to bind dashboard to
        port: Port to bind dashboard to
        debug: Enable debug mode
        **kwargs: Additional configuration options

    Returns:
        Configured MemoryMonitoringDashboard instance
    """
    return MemoryMonitoringDashboard(host=host, port=port, debug=debug)


# Example usage
if __name__ == "__main__":

    async def main():
        dashboard = create_memory_dashboard(debug=True)

        async with dashboard.monitoring_context():
            print(f"Dashboard available at: {dashboard.get_dashboard_url()}")

            # Simulate some memory usage
            await asyncio.sleep(60)

    asyncio.run(main())
