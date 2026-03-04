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
"""Response formatting utilities for the AWS Trusted Advisor MCP Server."""

from typing import Any, Dict, List, Optional


def _status_icon(status: str) -> str:
    """Return a text indicator for a recommendation status."""
    return {
        'ok': '[OK]',
        'warning': '[WARNING]',
        'error': '[ERROR]',
    }.get(status.lower(), f'[{status.upper()}]')


def _format_pillar(pillar: Optional[str]) -> str:
    """Format a pillar name for display."""
    if not pillar:
        return 'N/A'
    return pillar.replace('_', ' ').title()


def _extract_savings(recommendation: Dict[str, Any]) -> float:
    """Extract estimated monthly savings from a recommendation.

    Args:
        recommendation: A recommendation summary dict from the API.

    Returns:
        The estimated monthly savings as a float, or 0.0 if not available.
    """
    aggregates = recommendation.get('pillarSpecificAggregates', {})
    if not aggregates:
        return 0.0
    cost_optimizing = aggregates.get('costOptimizing', {})
    if not cost_optimizing:
        return 0.0
    return float(cost_optimizing.get('estimatedMonthlySavings', 0.0))


def _extract_savings_currency(recommendation: Dict[str, Any]) -> str:
    """Extract the savings currency from a recommendation."""
    aggregates = recommendation.get('pillarSpecificAggregates', {})
    if not aggregates:
        return 'USD'
    cost_optimizing = aggregates.get('costOptimizing', {})
    if not cost_optimizing:
        return 'USD'
    return cost_optimizing.get('estimatedMonthlySavingsCurrency', 'USD')


def format_checks_list(checks: List[Dict[str, Any]]) -> str:
    """Format a list of Trusted Advisor checks as markdown.

    Args:
        checks: List of check summaries from the API.

    Returns:
        A markdown-formatted string.
    """
    if not checks:
        return 'No Trusted Advisor checks found matching the specified filters.'

    lines = [f'# Trusted Advisor Checks ({len(checks)} found)\n']

    # Group by pillar
    by_pillar: Dict[str, List[Dict[str, Any]]] = {}
    for check in checks:
        pillar = check.get('pillar', 'other')
        by_pillar.setdefault(pillar, []).append(check)

    for pillar in sorted(by_pillar.keys()):
        pillar_checks = by_pillar[pillar]
        lines.append(f'## {_format_pillar(pillar)} ({len(pillar_checks)} checks)\n')
        for check in sorted(pillar_checks, key=lambda c: c.get('name', '')):
            name = check.get('name', 'Unknown')
            description = check.get('description', '')
            service = check.get('awsService', 'N/A')
            lines.append(f'- **{name}**')
            if service and service != 'N/A':
                lines.append(f'  - Service: `{service}`')
            if description:
                # Truncate long descriptions
                desc = description[:200] + '...' if len(description) > 200 else description
                lines.append(f'  - {desc}')
            lines.append('')

    return '\n'.join(lines)


def format_recommendations_list(recommendations: List[Dict[str, Any]]) -> str:
    """Format a list of recommendations as markdown.

    Args:
        recommendations: List of recommendation summaries from the API.

    Returns:
        A markdown-formatted string.
    """
    if not recommendations:
        return 'No Trusted Advisor recommendations found matching the specified filters.'

    lines = [f'# Trusted Advisor Recommendations ({len(recommendations)} found)\n']

    for rec in recommendations:
        status = rec.get('status', 'unknown')
        name = rec.get('name', 'Unknown')
        pillar = _format_pillar(rec.get('pillar'))
        icon = _status_icon(status)

        lines.append(f'### {icon} {name}')
        lines.append(f'- **Pillar**: {pillar}')
        lines.append(f'- **Status**: {status}')

        if rec.get('awsService'):
            lines.append(f'- **Service**: `{rec["awsService"]}`')

        aggregates = rec.get('resourcesAggregates', {})
        if aggregates:
            ok = aggregates.get('okCount', 0)
            warn = aggregates.get('warningCount', 0)
            err = aggregates.get('errorCount', 0)
            lines.append(f'- **Resources**: {ok} OK, {warn} Warning, {err} Error')

        savings = _extract_savings(rec)
        if savings > 0:
            currency = _extract_savings_currency(rec)
            lines.append(f'- **Estimated Monthly Savings**: {currency} ${savings:,.2f}')

        if rec.get('lastUpdatedAt'):
            lines.append(f'- **Last Updated**: {rec["lastUpdatedAt"]}')

        lines.append(f'- **ARN**: `{rec.get("arn", "N/A")}`')
        lines.append('')

    return '\n'.join(lines)


def format_recommendation_detail(
    recommendation: Dict[str, Any], resources: List[Dict[str, Any]]
) -> str:
    """Format a detailed recommendation view with affected resources.

    Args:
        recommendation: Detailed recommendation data from get_recommendation.
        resources: List of affected resources from list_recommendation_resources.

    Returns:
        A markdown-formatted string.
    """
    name = recommendation.get('name', 'Unknown')
    status = recommendation.get('status', 'unknown')
    icon = _status_icon(status)

    lines = [f'# {icon} {name}\n']

    if recommendation.get('description'):
        lines.append(f'{recommendation["description"]}\n')

    lines.append('## Details\n')
    lines.append(f'- **Status**: {status}')
    lines.append(f'- **Pillar**: {_format_pillar(recommendation.get("pillar"))}')

    if recommendation.get('awsService'):
        lines.append(f'- **Service**: `{recommendation["awsService"]}`')
    if recommendation.get('source'):
        lines.append(f'- **Source**: {recommendation["source"]}')
    if recommendation.get('lifecycleStage'):
        lines.append(f'- **Lifecycle Stage**: {recommendation["lifecycleStage"]}')
    if recommendation.get('createdAt'):
        lines.append(f'- **Created**: {recommendation["createdAt"]}')
    if recommendation.get('lastUpdatedAt'):
        lines.append(f'- **Last Updated**: {recommendation["lastUpdatedAt"]}')
    if recommendation.get('resolvedAt'):
        lines.append(f'- **Resolved**: {recommendation["resolvedAt"]}')
    if recommendation.get('updateReason'):
        lines.append(f'- **Update Reason**: {recommendation["updateReason"]}')

    lines.append(f'- **ARN**: `{recommendation.get("arn", "N/A")}`')

    aggregates = recommendation.get('resourcesAggregates', {})
    if aggregates:
        ok = aggregates.get('okCount', 0)
        warn = aggregates.get('warningCount', 0)
        err = aggregates.get('errorCount', 0)
        lines.append(f'\n## Resource Summary\n')
        lines.append(f'- OK: {ok}')
        lines.append(f'- Warning: {warn}')
        lines.append(f'- Error: {err}')
        lines.append(f'- **Total**: {ok + warn + err}')

    savings = _extract_savings(recommendation)
    if savings > 0:
        currency = _extract_savings_currency(recommendation)
        lines.append(f'\n## Estimated Savings\n')
        lines.append(f'- **Monthly**: {currency} ${savings:,.2f}')
        lines.append(f'- **Annual**: {currency} ${savings * 12:,.2f}')

    if resources:
        lines.append(f'\n## Affected Resources ({len(resources)})\n')
        # Show up to 50 resources
        display_resources = resources[:50]
        for res in display_resources:
            res_status = _status_icon(res.get('status', 'unknown'))
            res_id = res.get('awsResourceId', 'Unknown')
            region = res.get('regionCode', 'N/A')
            lines.append(f'- {res_status} `{res_id}` (Region: {region})')

            metadata = res.get('metadata', {})
            if metadata:
                for key, value in metadata.items():
                    lines.append(f'  - {key}: {value}')

        if len(resources) > 50:
            lines.append(f'\n*... and {len(resources) - 50} more resources*')

    return '\n'.join(lines)


def format_cost_optimization_summary(
    recommendations: List[Dict[str, Any]],
) -> str:
    """Format a cost optimization summary as markdown.

    Args:
        recommendations: List of cost optimization recommendations.

    Returns:
        A markdown-formatted string with total savings and top recommendations.
    """
    if not recommendations:
        return (
            '# Cost Optimization Summary\n\n'
            'No active cost optimization recommendations found. '
            'Your account appears to be well-optimized!'
        )

    # Calculate totals
    total_savings = 0.0
    currency = 'USD'
    rec_with_savings = []

    for rec in recommendations:
        savings = _extract_savings(rec)
        if savings > 0:
            currency = _extract_savings_currency(rec)
        total_savings += savings
        rec_with_savings.append({
            'name': rec.get('name', 'Unknown'),
            'status': rec.get('status', 'unknown'),
            'savings': savings,
            'resources': rec.get('resourcesAggregates', {}),
            'arn': rec.get('arn', 'N/A'),
        })

    # Sort by savings descending
    rec_with_savings.sort(key=lambda r: r['savings'], reverse=True)

    lines = ['# Cost Optimization Summary\n']
    lines.append(f'**Total Estimated Monthly Savings: {currency} ${total_savings:,.2f}**')
    lines.append(f'**Total Estimated Annual Savings: {currency} ${total_savings * 12:,.2f}**')
    lines.append(f'\nActive Recommendations: {len(recommendations)}\n')

    lines.append('## Recommendations by Savings\n')
    for rec in rec_with_savings:
        icon = _status_icon(rec['status'])
        savings_str = f'{currency} ${rec["savings"]:,.2f}/mo' if rec['savings'] > 0 else 'N/A'
        lines.append(f'### {icon} {rec["name"]}')
        lines.append(f'- **Estimated Savings**: {savings_str}')

        resources = rec.get('resources', {})
        if resources:
            warn = resources.get('warningCount', 0)
            err = resources.get('errorCount', 0)
            lines.append(f'- **Affected Resources**: {warn} warning, {err} error')

        lines.append(f'- **ARN**: `{rec["arn"]}`')
        lines.append('')

    return '\n'.join(lines)


def format_security_summary(recommendations: List[Dict[str, Any]]) -> str:
    """Format a security summary as markdown.

    Args:
        recommendations: List of security recommendations.

    Returns:
        A markdown-formatted string with security status overview.
    """
    if not recommendations:
        return (
            '# Security Summary\n\n'
            'No security recommendations found. Your account security posture looks good!'
        )

    ok_count = sum(1 for r in recommendations if r.get('status') == 'ok')
    warning_count = sum(1 for r in recommendations if r.get('status') == 'warning')
    error_count = sum(1 for r in recommendations if r.get('status') == 'error')

    lines = ['# Security Summary\n']
    lines.append(f'Total Checks: {len(recommendations)}\n')
    lines.append(f'- [OK] Passed: {ok_count}')
    lines.append(f'- [WARNING] Warnings: {warning_count}')
    lines.append(f'- [ERROR] Errors: {error_count}')

    # Show active issues (warnings + errors)
    active = [r for r in recommendations if r.get('status') in ('warning', 'error')]
    if active:
        # Sort errors first, then warnings
        active.sort(key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', '')))

        lines.append(f'\n## Active Security Issues ({len(active)})\n')
        for rec in active:
            icon = _status_icon(rec.get('status', 'unknown'))
            name = rec.get('name', 'Unknown')
            lines.append(f'### {icon} {name}')

            aggregates = rec.get('resourcesAggregates', {})
            if aggregates:
                warn = aggregates.get('warningCount', 0)
                err = aggregates.get('errorCount', 0)
                lines.append(f'- **Affected Resources**: {warn} warning, {err} error')

            if rec.get('lastUpdatedAt'):
                lines.append(f'- **Last Updated**: {rec["lastUpdatedAt"]}')
            lines.append(f'- **ARN**: `{rec.get("arn", "N/A")}`')
            lines.append('')
    else:
        lines.append('\n## No Active Security Issues\n')
        lines.append('All security checks are passing.')

    return '\n'.join(lines)


def format_service_limits_summary(recommendations: List[Dict[str, Any]]) -> str:
    """Format a service limits summary as markdown.

    Args:
        recommendations: List of service limits recommendations with warning/error status.

    Returns:
        A markdown-formatted string with service limits status.
    """
    if not recommendations:
        return (
            '# Service Limits Summary\n\n'
            'No service limit concerns found. All services are within their limits.'
        )

    lines = ['# Service Limits Summary\n']
    lines.append(f'**Services Approaching or Exceeding Limits: {len(recommendations)}**\n')

    # Sort errors first
    recommendations.sort(
        key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', ''))
    )

    for rec in recommendations:
        icon = _status_icon(rec.get('status', 'unknown'))
        name = rec.get('name', 'Unknown')
        lines.append(f'### {icon} {name}')

        if rec.get('awsService'):
            lines.append(f'- **Service**: `{rec["awsService"]}`')

        aggregates = rec.get('resourcesAggregates', {})
        if aggregates:
            warn = aggregates.get('warningCount', 0)
            err = aggregates.get('errorCount', 0)
            ok = aggregates.get('okCount', 0)
            lines.append(f'- **Resources**: {ok} OK, {warn} approaching limit, {err} at/over limit')

        if rec.get('lastUpdatedAt'):
            lines.append(f'- **Last Updated**: {rec["lastUpdatedAt"]}')
        lines.append(f'- **ARN**: `{rec.get("arn", "N/A")}`')
        lines.append('')

    return '\n'.join(lines)


def format_organization_recommendations(recommendations: List[Dict[str, Any]]) -> str:
    """Format organization-wide recommendations as markdown.

    Args:
        recommendations: List of organization recommendation summaries.

    Returns:
        A markdown-formatted string with org-wide recommendations.
    """
    if not recommendations:
        return (
            '# Organization Recommendations\n\n'
            'No organization-wide recommendations found matching the specified filters.'
        )

    lines = [f'# Organization Recommendations ({len(recommendations)} found)\n']

    # Count by status
    ok_count = sum(1 for r in recommendations if r.get('status') == 'ok')
    warning_count = sum(1 for r in recommendations if r.get('status') == 'warning')
    error_count = sum(1 for r in recommendations if r.get('status') == 'error')

    lines.append('## Summary\n')
    lines.append(f'- [OK] Passed: {ok_count}')
    lines.append(f'- [WARNING] Warnings: {warning_count}')
    lines.append(f'- [ERROR] Errors: {error_count}')
    lines.append('')

    for rec in recommendations:
        status = rec.get('status', 'unknown')
        name = rec.get('name', 'Unknown')
        icon = _status_icon(status)

        lines.append(f'### {icon} {name}')
        lines.append(f'- **Pillar**: {_format_pillar(rec.get("pillar"))}')
        lines.append(f'- **Status**: {status}')

        if rec.get('awsService'):
            lines.append(f'- **Service**: `{rec["awsService"]}`')

        aggregates = rec.get('resourcesAggregates', {})
        if aggregates:
            ok = aggregates.get('okCount', 0)
            warn = aggregates.get('warningCount', 0)
            err = aggregates.get('errorCount', 0)
            lines.append(f'- **Resources**: {ok} OK, {warn} Warning, {err} Error')

        savings = _extract_savings(rec)
        if savings > 0:
            currency = _extract_savings_currency(rec)
            lines.append(f'- **Estimated Monthly Savings**: {currency} ${savings:,.2f}')

        if rec.get('lifecycleStage'):
            lines.append(f'- **Lifecycle Stage**: {rec["lifecycleStage"]}')
        if rec.get('lastUpdatedAt'):
            lines.append(f'- **Last Updated**: {rec["lastUpdatedAt"]}')
        lines.append(f'- **ARN**: `{rec.get("arn", "N/A")}`')
        lines.append('')

    return '\n'.join(lines)


def format_lifecycle_update_result(
    recommendation_identifier: str, lifecycle_stage: str, update_reason: Optional[str] = None
) -> str:
    """Format the result of a lifecycle update.

    Args:
        recommendation_identifier: The recommendation ARN or ID.
        lifecycle_stage: The new lifecycle stage.
        update_reason: The reason for the update (optional).

    Returns:
        A markdown-formatted confirmation string.
    """
    lines = ['# Recommendation Lifecycle Updated\n']
    lines.append(f'- **Recommendation**: `{recommendation_identifier}`')
    lines.append(f'- **New Stage**: {lifecycle_stage}')
    if update_reason:
        lines.append(f'- **Reason**: {update_reason}')
    lines.append('\nThe recommendation lifecycle has been successfully updated.')

    return '\n'.join(lines)
