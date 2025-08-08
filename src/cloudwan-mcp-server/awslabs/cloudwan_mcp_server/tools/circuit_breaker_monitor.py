# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Circuit breaker monitoring and management tools."""

from typing import Dict, Any
from ..server import mcp
from ..utils.circuit_breaker import get_circuit_breaker_stats
from ..utils.metrics import metrics
from ..utils.response_formatter import format_response
from ..utils.logger import get_logger

logger = get_logger(__name__)


@mcp.tool(name="get_circuit_breaker_status")
def get_circuit_breaker_status() -> str:
    """Get status of all circuit breakers in the system.

    Returns:
        JSON string with circuit breaker statistics and health status
    """
    try:
        # Get all circuit breaker statistics
        breaker_stats = get_circuit_breaker_stats()

        # Calculate overall system health
        total_breakers = len(breaker_stats)
        open_breakers = sum(1 for stats in breaker_stats.values() if stats["state"] == "open")
        half_open_breakers = sum(1 for stats in breaker_stats.values() if stats["state"] == "half_open")

        # Determine overall health status
        if open_breakers == 0:
            health_status = "HEALTHY"
        elif open_breakers < total_breakers * 0.3:  # Less than 30% open
            health_status = "DEGRADED"
        else:
            health_status = "UNHEALTHY"

        # Calculate failure rates
        recent_failure_rates = {}
        for name, stats in breaker_stats.items():
            failure_rate = stats.get("failure_rate", 0.0)
            recent_failure_rates[name] = {
                "failure_rate": failure_rate,
                "status": "HIGH" if failure_rate > 0.5 else "MODERATE" if failure_rate > 0.1 else "LOW",
            }

        # Identify problematic breakers
        problematic_breakers = [
            name
            for name, stats in breaker_stats.items()
            if stats["state"] in ["open", "half_open"] or stats.get("failure_rate", 0) > 0.3
        ]

        result = {
            "system_health": {
                "status": health_status,
                "total_breakers": total_breakers,
                "open_breakers": open_breakers,
                "half_open_breakers": half_open_breakers,
                "closed_breakers": total_breakers - open_breakers - half_open_breakers,
            },
            "individual_breakers": breaker_stats,
            "failure_analysis": recent_failure_rates,
            "alerts": {
                "problematic_breakers": problematic_breakers,
                "recommendation": _generate_health_recommendations(breaker_stats, health_status),
            },
        }

        # Record monitoring metrics
        metrics.record_gauge("circuit_breaker.total_count", total_breakers)
        metrics.record_gauge("circuit_breaker.open_count", open_breakers)
        metrics.record_gauge("circuit_breaker.half_open_count", half_open_breakers)

        return format_response(success=True, data=result)

    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {str(e)}")
        return format_response(success=False, error=f"Circuit breaker monitoring failed: {str(e)}")


def _generate_health_recommendations(breaker_stats: Dict[str, Any], health_status: str) -> list:
    """Generate recommendations based on circuit breaker health."""
    recommendations = []

    if health_status == "UNHEALTHY":
        recommendations.append(
            {
                "priority": "CRITICAL",
                "message": "Multiple circuit breakers are open - system experiencing widespread issues",
                "action": "Investigate underlying AWS service health and network connectivity",
            }
        )

    for name, stats in breaker_stats.items():
        if stats["state"] == "open":
            recommendations.append(
                {
                    "priority": "HIGH",
                    "message": f"Circuit breaker '{name}' is open",
                    "action": f"Check AWS service health for {name.split('_')[1] if '_' in name else 'service'}",
                }
            )

        if stats.get("failure_rate", 0) > 0.5:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "message": f"High failure rate detected for '{name}' ({stats['failure_rate']:.2%})",
                    "action": "Review recent error logs and consider increasing timeout or retry configuration",
                }
            )

    if not recommendations:
        recommendations.append(
            {
                "priority": "INFO",
                "message": "All circuit breakers are healthy",
                "action": "Continue monitoring for any changes in failure patterns",
            }
        )

    return recommendations


@mcp.tool(name="get_system_resilience_metrics")
def get_system_resilience_metrics() -> str:
    """Get comprehensive resilience metrics for the system.

    Returns:
        JSON string with resilience metrics and analysis
    """
    try:
        # Get circuit breaker stats
        breaker_stats = get_circuit_breaker_stats()

        # Get metrics summary
        metrics_summary = metrics.get_metrics_summary()

        # Calculate resilience indicators
        resilience_metrics = {
            "circuit_breaker_effectiveness": _calculate_breaker_effectiveness(breaker_stats),
            "error_recovery_rate": _calculate_recovery_rate(breaker_stats),
            "system_availability": _estimate_availability(breaker_stats),
            "performance_impact": _analyze_performance_impact(metrics_summary),
        }

        # Generate resilience score (0-100)
        resilience_score = _calculate_resilience_score(resilience_metrics)

        result = {
            "resilience_score": resilience_score,
            "score_breakdown": resilience_metrics,
            "circuit_breaker_summary": {
                "total_protected_operations": len(breaker_stats),
                "average_failure_rate": sum(stats.get("failure_rate", 0) for stats in breaker_stats.values())
                / max(len(breaker_stats), 1),
                "recovery_success_rate": sum(1 for stats in breaker_stats.values() if stats["state"] == "closed")
                / max(len(breaker_stats), 1),
            },
            "recommendations": _generate_resilience_recommendations(resilience_score, resilience_metrics),
        }

        return format_response(success=True, data=result)

    except Exception as e:
        logger.error(f"Failed to get resilience metrics: {str(e)}")
        return format_response(success=False, error=f"Resilience metrics calculation failed: {str(e)}")


def _calculate_breaker_effectiveness(breaker_stats: Dict[str, Any]) -> float:
    """Calculate how effective circuit breakers are at preventing cascading failures."""
    if not breaker_stats:
        return 0.0

    # Effectiveness based on proper state transitions and failure isolation
    total_score = 0
    for stats in breaker_stats.values():
        if stats["state"] == "closed" and stats["failure_count"] == 0:
            total_score += 1.0  # Perfect state
        elif stats["state"] == "half_open":
            total_score += 0.7  # Recovery in progress
        elif stats["state"] == "open":
            total_score += 0.3  # Protecting but service degraded

    return total_score / len(breaker_stats)


def _calculate_recovery_rate(breaker_stats: Dict[str, Any]) -> float:
    """Calculate how well the system recovers from failures."""
    if not breaker_stats:
        return 0.0

    # Recovery rate based on successful state transitions from open->closed
    recovering_breakers = sum(1 for stats in breaker_stats.values() if stats["state"] in ["closed", "half_open"])

    return recovering_breakers / len(breaker_stats)


def _estimate_availability(breaker_stats: Dict[str, Any]) -> float:
    """Estimate system availability based on circuit breaker states."""
    if not breaker_stats:
        return 1.0

    # Availability estimate based on closed circuit breakers
    available_services = sum(1 for stats in breaker_stats.values() if stats["state"] == "closed")

    return available_services / len(breaker_stats)


def _analyze_performance_impact(metrics_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze performance impact of circuit breaker protection."""
    counters = metrics_summary.get("counters", {})

    # Look for circuit breaker metrics
    breaker_successes = sum(count for metric, count in counters.items() if "circuit_breaker.success" in metric)
    breaker_failures = sum(count for metric, count in counters.items() if "circuit_breaker.failure" in metric)
    breaker_rejections = sum(count for metric, count in counters.items() if "circuit_breaker.rejected" in metric)

    total_requests = breaker_successes + breaker_failures + breaker_rejections

    if total_requests == 0:
        return {"impact_level": "NONE", "requests_protected": 0}

    protection_ratio = (breaker_rejections) / total_requests
    success_ratio = breaker_successes / total_requests

    return {
        "impact_level": "HIGH" if protection_ratio > 0.1 else "MODERATE" if protection_ratio > 0.01 else "LOW",
        "requests_protected": breaker_rejections,
        "success_rate": success_ratio,
        "protection_ratio": protection_ratio,
    }


def _calculate_resilience_score(metrics: Dict[str, Any]) -> int:
    """Calculate overall resilience score (0-100)."""
    effectiveness = metrics.get("circuit_breaker_effectiveness", 0) * 30  # 30 points max
    recovery = metrics.get("error_recovery_rate", 0) * 25  # 25 points max
    availability = metrics.get("system_availability", 0) * 35  # 35 points max

    # Performance impact reduces score if too high
    perf_impact = metrics.get("performance_impact", {})
    impact_penalty = 0
    if perf_impact.get("impact_level") == "HIGH":
        impact_penalty = 10
    elif perf_impact.get("impact_level") == "MODERATE":
        impact_penalty = 5

    base_score = effectiveness + recovery + availability
    final_score = max(0, min(100, base_score - impact_penalty))

    return int(final_score)


def _generate_resilience_recommendations(score: int, metrics: Dict[str, Any]) -> list:
    """Generate recommendations for improving system resilience."""
    recommendations = []

    if score < 60:
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "RESILIENCE",
                "message": "System resilience score is below acceptable threshold",
                "action": "Review and improve circuit breaker configurations and failure handling",
            }
        )

    if metrics.get("circuit_breaker_effectiveness", 0) < 0.7:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "CIRCUIT_BREAKERS",
                "message": "Circuit breaker effectiveness could be improved",
                "action": "Review failure thresholds and recovery timeout settings",
            }
        )

    if metrics.get("system_availability", 0) < 0.9:
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "AVAILABILITY",
                "message": "System availability is below target",
                "action": "Investigate root causes of service failures and improve redundancy",
            }
        )

    perf_impact = metrics.get("performance_impact", {})
    if perf_impact.get("impact_level") == "HIGH":
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "PERFORMANCE",
                "message": "Circuit breakers are rejecting high percentage of requests",
                "action": "Consider adjusting thresholds or improving underlying service reliability",
            }
        )

    return recommendations


# Add tools to registration list
CIRCUIT_BREAKER_TOOLS = [get_circuit_breaker_status, get_system_resilience_metrics]
