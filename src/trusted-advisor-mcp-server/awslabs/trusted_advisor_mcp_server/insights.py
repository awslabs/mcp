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
"""Insight generation utilities for the AWS Trusted Advisor MCP Server."""

from typing import Any, Dict, List


REMEDIATION_HINTS: Dict[str, str] = {
    'deprecated runtime': (
        'Update Lambda functions to a supported runtime (python3.12, nodejs20.x, java21). '
        'Use: aws lambda update-function-configuration --function-name NAME --runtime python3.12'
    ),
    'access analyzer': (
        'Enable IAM Access Analyzer in each region: '
        'aws accessanalyzer create-analyzer --analyzer-name default --type ACCOUNT'
    ),
    'security group': (
        'Review and restrict inbound rules. Remove 0.0.0.0/0 for sensitive ports '
        '(22, 3389, 3306, 5432).'
    ),
    'access key rotation': (
        'Rotate IAM access keys older than 90 days. Create new key, update applications, '
        'then deactivate old key.'
    ),
    'mfa': 'Enable MFA on the root account via IAM console > Security credentials.',
    'ec2 instance': (
        'Right-size or stop underutilized EC2 instances. '
        'Use AWS Compute Optimizer recommendations.'
    ),
    'ebs': (
        'Delete unattached EBS volumes or change to cheaper gp3 type. '
        'aws ec2 describe-volumes --filters Name=status,Values=available'
    ),
    'nat gateway': (
        'Delete idle NAT Gateways not forwarding traffic. '
        'Check CloudWatch NatGatewayActiveConnectionCount metric.'
    ),
    'vpc endpoint': (
        'Delete VPC interface endpoints with no traffic. '
        'Check CloudWatch metrics for usage.'
    ),
    'load balancer': 'Delete idle load balancers with no active targets or traffic.',
    's3': (
        'Configure S3 lifecycle rules to abort incomplete multipart uploads: '
        'aws s3api put-bucket-lifecycle-configuration'
    ),
    'fargate': (
        'Right-size Fargate task CPU/memory based on CloudWatch Container Insights metrics.'
    ),
    'well-architected': (
        'Schedule a Well-Architected Review with your AWS team to address high-risk issues.'
    ),
    'service limit': (
        'Request a service quota increase via Service Quotas console before hitting the limit.'
    ),
    'cloudfront': (
        'Update CloudFront origin to use HTTPS with a valid SSL certificate.'
    ),
}

EFFORT_BY_PILLAR: Dict[str, str] = {
    'security': 'Medium',
    'cost_optimizing': 'Low',
    'service_limits': 'Low',
    'performance': 'Medium',
    'fault_tolerance': 'High',
    'operational_excellence': 'Medium',
}

PILLAR_LABELS: Dict[str, str] = {
    'security': 'Security',
    'cost_optimizing': 'Cost Optimization',
    'performance': 'Performance',
    'fault_tolerance': 'Fault Tolerance',
    'service_limits': 'Service Limits',
    'operational_excellence': 'Operational Excellence',
}


def _get_remediation_hint(name: str) -> str:
    """Return a remediation hint based on keyword matching on the recommendation name."""
    name_lower = name.lower()
    for keyword, hint in REMEDIATION_HINTS.items():
        if keyword in name_lower:
            return hint
    return 'Review the Trusted Advisor recommendation details and follow AWS documentation guidance.'


def _extract_savings(recommendation: Dict[str, Any]) -> float:
    """Extract estimated monthly savings from a recommendation."""
    aggregates = recommendation.get('pillarSpecificAggregates', {})
    if not aggregates:
        return 0.0
    cost_optimizing = aggregates.get('costOptimizing', {})
    if not cost_optimizing:
        return 0.0
    return float(cost_optimizing.get('estimatedMonthlySavings', 0.0))


def _extract_affected(recommendation: Dict[str, Any]) -> int:
    """Extract the count of warning + error resources from a recommendation."""
    aggregates = recommendation.get('resourcesAggregates', {})
    if not aggregates:
        return 0
    return int(aggregates.get('warningCount', 0)) + int(aggregates.get('errorCount', 0))


def _compute_impact_score(recommendation: Dict[str, Any]) -> float:
    """Compute an impact score for prioritization."""
    savings = _extract_savings(recommendation)
    affected = _extract_affected(recommendation)
    status = recommendation.get('status', '').lower()
    severity_weight = 3 if status == 'error' else 1 if status == 'warning' else 0
    return (savings * 0.5) + (affected * severity_weight * 2)


def _status_icon(status: str) -> str:
    """Return a text indicator for a recommendation status."""
    return {
        'ok': '[OK]',
        'warning': '[WARNING]',
        'error': '[ERROR]',
    }.get(status.lower(), f'[{status.upper()}]')


def _format_pillar(pillar: str) -> str:
    """Format a pillar name for display."""
    return PILLAR_LABELS.get(pillar, pillar.replace('_', ' ').title() if pillar else 'N/A')


def format_prioritized_actions(recommendations: List[Dict[str, Any]]) -> str:
    """Generate a prioritized action plan from Trusted Advisor recommendations.

    Args:
        recommendations: List of recommendation summaries from the API.

    Returns:
        A markdown-formatted string with categorized, prioritized actions.
    """
    if not recommendations:
        return (
            '# Prioritized Actions\n\n'
            'No recommendations found. Your account appears to be in good shape!'
        )

    scored: List[Dict[str, Any]] = []
    for rec in recommendations:
        status = rec.get('status', 'unknown').lower()
        if status == 'ok':
            continue

        pillars = rec.get('pillars') or []
        pillar = pillars[0] if pillars else rec.get('pillar', '')
        impact_score = _compute_impact_score(rec)
        effort = EFFORT_BY_PILLAR.get(pillar, 'Medium')

        if impact_score >= 50 and effort in ('Low', 'Medium'):
            category = 'Quick Win'
        elif impact_score >= 20:
            category = 'High Impact'
        else:
            category = 'Review When Possible'

        scored.append({
            'name': rec.get('name', 'Unknown'),
            'status': status,
            'pillar': pillar,
            'savings': _extract_savings(rec),
            'affected': _extract_affected(rec),
            'effort': effort,
            'impact_score': impact_score,
            'category': category,
            'hint': _get_remediation_hint(rec.get('name', '')),
        })

    if not scored:
        return (
            '# Prioritized Actions\n\n'
            'No actionable recommendations found. All checks are passing!'
        )

    # Sort within each category by impact_score desc
    scored.sort(key=lambda r: r['impact_score'], reverse=True)

    categories = ['Quick Win', 'High Impact', 'Review When Possible']
    by_category: Dict[str, List[Dict[str, Any]]] = {c: [] for c in categories}
    for item in scored:
        by_category[item['category']].append(item)

    lines = ['# Prioritized Actions\n']
    count = 0
    max_items = 15

    for category in categories:
        items = by_category[category]
        if not items or count >= max_items:
            continue

        lines.append(f'## {category}\n')
        for item in items:
            if count >= max_items:
                break

            icon = _status_icon(item['status'])
            lines.append(f'### {icon} {item["name"]}')
            lines.append(f'- **Pillar**: {_format_pillar(item["pillar"])}')
            lines.append(f'- **Effort**: {item["effort"]}')
            if item['savings'] > 0:
                lines.append(f'- **Estimated Monthly Savings**: ${item["savings"]:,.2f}')
            lines.append(f'- **Affected Resources**: {item["affected"]}')
            lines.append(f'- **Remediation**: {item["hint"]}')
            lines.append('')
            count += 1

    return '\n'.join(lines)


def format_executive_summary(
    recommendations: List[Dict[str, Any]], account_alias: str = ''
) -> str:
    """Generate an executive summary from Trusted Advisor recommendations.

    Args:
        recommendations: List of all recommendation summaries from the API.
        account_alias: Optional customer or account name.

    Returns:
        A markdown-formatted executive summary.
    """
    total = len(recommendations)
    ok_count = sum(1 for r in recommendations if r.get('status') == 'ok')
    warning_count = sum(1 for r in recommendations if r.get('status') == 'warning')
    error_count = sum(1 for r in recommendations if r.get('status') == 'error')

    # Calculate overall score (same formula as get_account_score)
    if total > 0:
        penalty = (error_count * 3) + warning_count
        max_penalty = total * 3
        overall_score = max(0, round(100 * (1 - penalty / max_penalty)))
    else:
        overall_score = 100

    grade = (
        'A' if overall_score >= 90 else
        'B' if overall_score >= 75 else
        'C' if overall_score >= 60 else
        'D' if overall_score >= 40 else 'F'
    )

    # Total savings
    total_savings = sum(_extract_savings(r) for r in recommendations)

    # Top security error (pillars is a list in the API response)
    security_errors = [
        r for r in recommendations
        if 'security' in (r.get('pillars') or [r.get('pillar')])
        and r.get('status') == 'error'
    ]
    top_security_error = security_errors[0].get('name', 'Unknown') if security_errors else None

    # Top savings recommendation
    savings_recs = sorted(recommendations, key=_extract_savings, reverse=True)
    top_savings_rec = None
    top_savings_amount = 0.0
    if savings_recs and _extract_savings(savings_recs[0]) > 0:
        top_savings_rec = savings_recs[0].get('name', 'Unknown')
        top_savings_amount = _extract_savings(savings_recs[0])

    # Build output
    account_label = f' for {account_alias}' if account_alias else ''
    lines = [f'## Executive Summary{account_label}\n']

    lines.append('### Key Metrics\n')
    lines.append(f'- **Account Health Score**: {overall_score}/100 (Grade: {grade})')
    lines.append(f'- **Total Checks**: {total}')
    lines.append(f'- **Passing**: {ok_count}  |  **Warnings**: {warning_count}  |  **Errors**: {error_count}')
    if total_savings > 0:
        lines.append(f'- **Total Estimated Monthly Savings**: ${total_savings:,.2f}')
        lines.append(f'- **Total Estimated Annual Savings**: ${total_savings * 12:,.2f}')
    if top_security_error:
        lines.append(f'- **Top Security Concern**: {top_security_error}')
    if top_savings_rec:
        lines.append(f'- **Top Savings Opportunity**: {top_savings_rec} (${top_savings_amount:,.2f}/mo)')

    lines.append('\n### Assessment\n')

    if overall_score >= 90:
        lines.append(
            f'The AWS account{account_label} is in excellent health with a score of '
            f'{overall_score}/100. The vast majority of Trusted Advisor checks are passing '
            f'with only {warning_count} warnings and {error_count} errors across {total} total checks.'
        )
    elif overall_score >= 75:
        lines.append(
            f'The AWS account{account_label} is in good overall health with a score of '
            f'{overall_score}/100, but there are areas that need attention. '
            f'Out of {total} total checks, {warning_count} returned warnings and '
            f'{error_count} returned errors.'
        )
    elif overall_score >= 60:
        lines.append(
            f'The AWS account{account_label} has a moderate health score of '
            f'{overall_score}/100, indicating several areas requiring attention. '
            f'There are {error_count} errors and {warning_count} warnings across '
            f'{total} checks that should be reviewed.'
        )
    else:
        lines.append(
            f'The AWS account{account_label} has a health score of {overall_score}/100, '
            f'indicating significant issues that require immediate attention. '
            f'With {error_count} errors and {warning_count} warnings across {total} checks, '
            f'a focused remediation effort is recommended.'
        )

    if total_savings > 0:
        lines.append(
            f' There is an estimated ${total_savings:,.2f} in potential monthly savings '
            f'(${total_savings * 12:,.2f} annually) available through cost optimization.'
        )

    if top_security_error:
        lines.append(
            f' Security should be prioritized, starting with the "{top_security_error}" finding.'
        )

    return '\n'.join(lines)
