"""
MCP Heartbeat Mechanism for Tool Health Monitoring.

This module provides heartbeat functionality to ensure MCP tools remain
responsive and healthy throughout the session, as required by MCP-SPEC-101.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status for tools and services."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check definition."""

    name: str
    check_function: Callable[[], bool]
    interval_seconds: int = 30
    timeout_seconds: int = 10
    max_failures: int = 3
    description: str = ""

    # Runtime state
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    total_failures: int = 0
    total_checks: int = 0
    status: HealthStatus = HealthStatus.UNKNOWN
    last_error: Optional[str] = None


@dataclass
class HeartbeatMessage:
    """Heartbeat message sent to client."""

    timestamp: str
    server_id: str
    status: HealthStatus
    uptime_seconds: float
    active_tools: int
    health_checks: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None


class ToolHealthTracker:
    """Tracks health status of individual MCP tools."""

    def __init__(self):
        self.tool_stats: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()

    def record_tool_execution(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None,
    ) -> None:
        """Record tool execution results."""
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "last_execution": None,
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "recent_errors": [],
            }

        stats = self.tool_stats[tool_name]
        now = datetime.now(timezone.utc).isoformat()

        # Update counters
        stats["total_executions"] += 1
        stats["total_execution_time"] += execution_time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
        stats["last_execution"] = now

        if success:
            stats["successful_executions"] += 1
            stats["last_success"] = now
            stats["consecutive_failures"] = 0
        else:
            stats["failed_executions"] += 1
            stats["last_failure"] = now
            stats["consecutive_failures"] += 1

            # Track recent errors (keep last 5)
            if error:
                stats["recent_errors"].append({"timestamp": now, "error": error})
                if len(stats["recent_errors"]) > 5:
                    stats["recent_errors"] = stats["recent_errors"][-5:]

    def get_tool_health(self, tool_name: str) -> HealthStatus:
        """Get health status for a specific tool."""
        if tool_name not in self.tool_stats:
            return HealthStatus.UNKNOWN

        stats = self.tool_stats[tool_name]

        # No executions yet
        if stats["total_executions"] == 0:
            return HealthStatus.UNKNOWN

        # Calculate success rate
        success_rate = stats["successful_executions"] / stats["total_executions"]

        # Check consecutive failures
        consecutive_failures = stats["consecutive_failures"]

        # Determine health status
        if consecutive_failures >= 5:
            return HealthStatus.UNHEALTHY
        elif consecutive_failures >= 3 or success_rate < 0.8:
            return HealthStatus.DEGRADED
        elif success_rate >= 0.95:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.DEGRADED

    def get_overall_health(self) -> HealthStatus:
        """Get overall health status across all tools."""
        if not self.tool_stats:
            return HealthStatus.UNKNOWN

        tool_healths = [self.get_tool_health(tool) for tool in self.tool_stats.keys()]

        # Count health statuses
        unhealthy_count = tool_healths.count(HealthStatus.UNHEALTHY)
        degraded_count = tool_healths.count(HealthStatus.DEGRADED)
        healthy_count = tool_healths.count(HealthStatus.HEALTHY)

        # Determine overall health
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > healthy_count:
            return HealthStatus.DEGRADED
        elif healthy_count > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tool statistics."""
        return self.tool_stats.copy()

    def reset_tool_stats(self, tool_name: Optional[str] = None) -> None:
        """Reset statistics for a tool or all tools."""
        if tool_name:
            if tool_name in self.tool_stats:
                del self.tool_stats[tool_name]
        else:
            self.tool_stats.clear()


class HeartbeatManager:
    """Manages heartbeat functionality for MCP server."""

    def __init__(
        self,
        server_name: str,
        heartbeat_interval: int = 30,
        health_check_interval: int = 60,
    ):
        self.server_name = server_name
        self.server_id = str(uuid4())
        self.heartbeat_interval = heartbeat_interval
        self.health_check_interval = health_check_interval

        # Runtime state
        self.start_time = time.time()
        self.is_running = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None

        # Health tracking
        self.tool_tracker = ToolHealthTracker()
        self.health_checks: Dict[str, HealthCheck] = {}
        self.heartbeat_callbacks: List[Callable[[HeartbeatMessage], None]] = []

        # Metrics
        self.metrics = {
            "heartbeats_sent": 0,
            "health_checks_performed": 0,
            "last_heartbeat": None,
            "last_health_check": None,
        }

    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a health check to the monitoring system."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")

    def remove_health_check(self, name: str) -> None:
        """Remove a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Removed health check: {name}")

    def add_heartbeat_callback(self, callback: Callable[[HeartbeatMessage], None]) -> None:
        """Add callback to be called on each heartbeat."""
        self.heartbeat_callbacks.append(callback)

    def record_tool_execution(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None,
    ) -> None:
        """Record tool execution for health tracking."""
        self.tool_tracker.record_tool_execution(tool_name, success, execution_time, error)

    async def start(self) -> None:
        """Start heartbeat and health check tasks."""
        if self.is_running:
            logger.warning("Heartbeat manager already running")
            return

        self.is_running = True

        # Start heartbeat task
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start health check task
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info(
            f"Heartbeat manager started - interval: {self.heartbeat_interval}s, "
            f"health checks: {self.health_check_interval}s"
        )

    async def stop(self) -> None:
        """Stop heartbeat and health check tasks."""
        self.is_running = False

        # Cancel tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("Heartbeat manager stopped")

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self.is_running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(min(self.heartbeat_interval, 5))

    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while self.is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(min(self.health_check_interval, 10))

    async def _send_heartbeat(self) -> None:
        """Send heartbeat message."""
        try:
            # Calculate uptime
            uptime = time.time() - self.start_time

            # Get health status
            overall_health = self.tool_tracker.get_overall_health()

            # Build health check summary
            health_check_summary = {}
            for name, check in self.health_checks.items():
                health_check_summary[name] = {
                    "status": check.status.value,
                    "last_check": (check.last_check.isoformat() if check.last_check else None),
                    "consecutive_failures": check.consecutive_failures,
                    "total_failures": check.total_failures,
                    "total_checks": check.total_checks,
                }

            # Get tool statistics
            tool_stats = self.tool_tracker.get_tool_statistics()

            # Build metrics
            metrics = {
                **self.metrics,
                "uptime_seconds": uptime,
                "tool_count": len(tool_stats),
                "total_tool_executions": sum(
                    stats["total_executions"] for stats in tool_stats.values()
                ),
                "successful_tool_executions": sum(
                    stats["successful_executions"] for stats in tool_stats.values()
                ),
                "failed_tool_executions": sum(
                    stats["failed_executions"] for stats in tool_stats.values()
                ),
                "average_execution_time": (
                    sum(stats["average_execution_time"] for stats in tool_stats.values())
                    / len(tool_stats)
                    if tool_stats
                    else 0.0
                ),
            }

            # Create heartbeat message
            heartbeat = HeartbeatMessage(
                timestamp=datetime.now(timezone.utc).isoformat(),
                server_id=self.server_id,
                status=overall_health,
                uptime_seconds=uptime,
                active_tools=len(tool_stats),
                health_checks=health_check_summary,
                metrics=metrics,
                message=self._get_status_message(overall_health),
            )

            # Update metrics
            self.metrics["heartbeats_sent"] += 1
            self.metrics["last_heartbeat"] = heartbeat.timestamp

            # Call callbacks
            for callback in self.heartbeat_callbacks:
                try:
                    callback(heartbeat)
                except Exception as e:
                    logger.warning(f"Heartbeat callback error: {e}")

            logger.debug(f"Heartbeat sent - status: {overall_health.value}, uptime: {uptime:.1f}s")

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

    async def _perform_health_checks(self) -> None:
        """Perform all registered health checks."""
        if not self.health_checks:
            return

        check_results = []

        for name, check in self.health_checks.items():
            # Skip if check interval hasn't elapsed
            if (
                check.last_check
                and (datetime.now(timezone.utc) - check.last_check).total_seconds()
                < check.interval_seconds
            ):
                continue

            check_result = await self._perform_single_health_check(check)
            check_results.append((name, check_result))

        # Update metrics
        if check_results:
            self.metrics["health_checks_performed"] += len(check_results)
            self.metrics["last_health_check"] = datetime.now(timezone.utc).isoformat()

        logger.debug(f"Performed {len(check_results)} health checks")

    async def _perform_single_health_check(self, check: HealthCheck) -> bool:
        """Perform a single health check."""
        check.total_checks += 1
        check.last_check = datetime.now(timezone.utc)

        try:
            # Run health check with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(check.check_function), timeout=check.timeout_seconds
            )

            if result:
                check.consecutive_failures = 0
                check.last_success = datetime.now(timezone.utc)
                check.status = HealthStatus.HEALTHY
                check.last_error = None
            else:
                check.consecutive_failures += 1
                check.total_failures += 1
                check.last_error = "Health check returned False"
                check.status = self._determine_health_status(check)

            return result

        except asyncio.TimeoutError:
            check.consecutive_failures += 1
            check.total_failures += 1
            check.last_error = f"Health check timeout ({check.timeout_seconds}s)"
            check.status = self._determine_health_status(check)
            logger.warning(f"Health check '{check.name}' timed out")
            return False

        except Exception as e:
            check.consecutive_failures += 1
            check.total_failures += 1
            check.last_error = str(e)
            check.status = self._determine_health_status(check)
            logger.warning(f"Health check '{check.name}' failed: {e}")
            return False

    def _determine_health_status(self, check: HealthCheck) -> HealthStatus:
        """Determine health status based on failure count."""
        if check.consecutive_failures >= check.max_failures:
            return HealthStatus.UNHEALTHY
        elif check.consecutive_failures > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _get_status_message(self, status: HealthStatus) -> str:
        """Get status message for heartbeat."""
        messages = {
            HealthStatus.HEALTHY: "All systems operational",
            HealthStatus.DEGRADED: "Some tools experiencing issues",
            HealthStatus.UNHEALTHY: "Critical issues detected",
            HealthStatus.UNKNOWN: "Health status unknown",
        }
        return messages.get(status, "Status unknown")

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        overall_health = self.tool_tracker.get_overall_health()
        tool_stats = self.tool_tracker.get_tool_statistics()

        # Health check summary
        health_check_summary = {}
        for name, check in self.health_checks.items():
            health_check_summary[name] = {
                "status": check.status.value,
                "description": check.description,
                "interval_seconds": check.interval_seconds,
                "last_check": (check.last_check.isoformat() if check.last_check else None),
                "last_success": (check.last_success.isoformat() if check.last_success else None),
                "consecutive_failures": check.consecutive_failures,
                "total_failures": check.total_failures,
                "total_checks": check.total_checks,
                "last_error": check.last_error,
            }

        # Tool health summary
        tool_health = {}
        for tool_name in tool_stats.keys():
            tool_health[tool_name] = self.tool_tracker.get_tool_health(tool_name).value

        return {
            "overall_health": overall_health.value,
            "uptime_seconds": time.time() - self.start_time,
            "server_id": self.server_id,
            "is_running": self.is_running,
            "metrics": self.metrics,
            "health_checks": health_check_summary,
            "tool_health": tool_health,
            "tool_statistics": tool_stats,
        }


# Global heartbeat manager
_heartbeat_manager: Optional[HeartbeatManager] = None


def initialize_heartbeat(
    server_name: str, heartbeat_interval: int = 30, health_check_interval: int = 60
) -> HeartbeatManager:
    """Initialize global heartbeat manager."""
    global _heartbeat_manager

    _heartbeat_manager = HeartbeatManager(
        server_name=server_name,
        heartbeat_interval=heartbeat_interval,
        health_check_interval=health_check_interval,
    )

    logger.info(f"Heartbeat manager initialized for {server_name}")
    return _heartbeat_manager


def get_heartbeat_manager() -> Optional[HeartbeatManager]:
    """Get global heartbeat manager."""
    return _heartbeat_manager


def record_tool_execution(
    tool_name: str, success: bool, execution_time: float, error: Optional[str] = None
) -> None:
    """Record tool execution for health tracking."""
    if _heartbeat_manager:
        _heartbeat_manager.record_tool_execution(tool_name, success, execution_time, error)


def add_health_check(health_check: HealthCheck) -> None:
    """Add health check to global manager."""
    if _heartbeat_manager:
        _heartbeat_manager.add_health_check(health_check)


def get_health_report() -> Dict[str, Any]:
    """Get comprehensive health report."""
    if not _heartbeat_manager:
        return {"status": "not_initialized"}

    return _heartbeat_manager.get_health_report()


# Backward compatibility alias
MCPHeartbeatManager = HeartbeatManager
