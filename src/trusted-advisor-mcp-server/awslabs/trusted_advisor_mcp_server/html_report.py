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
"""HTML report generation for the AWS Trusted Advisor MCP Server."""

import re
from typing import Any, Dict, List, Optional

from awslabs.trusted_advisor_mcp_server.insights import (
    REMEDIATION_HINTS,
    _get_remediation_hint,
)


def _extract_savings(recommendation: Dict[str, Any]) -> float:
    """Extract estimated monthly savings from a recommendation."""
    aggregates = recommendation.get('pillarSpecificAggregates', {})
    if not aggregates:
        return 0.0
    cost_optimizing = aggregates.get('costOptimizing', {})
    if not cost_optimizing:
        return 0.0
    return float(cost_optimizing.get('estimatedMonthlySavings', 0.0))


def _status_color(status: str) -> str:
    """Return a CSS color for a recommendation status."""
    return {
        'ok': '#2e7d32',
        'warning': '#e65100',
        'error': '#b71c1c',
    }.get(status.lower(), '#616161')


def _status_label(status: str) -> str:
    """Return a display label for a recommendation status."""
    return {
        'ok': 'OK',
        'warning': 'Warning',
        'error': 'Error',
    }.get(status.lower(), status.title())


def _status_badge(status: str) -> str:
    """Return an inline HTML badge for a status."""
    color = _status_color(status)
    label = _status_label(status)
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{color};color:#fff;font-size:12px;font-weight:600;'
        f'vertical-align:middle;">{label}</span>'
    )


def _pillar_label(pillar: str) -> str:
    """Format a pillar name for display."""
    labels = {
        'security': 'Security',
        'cost_optimizing': 'Cost Optimization',
        'performance': 'Performance',
        'fault_tolerance': 'Fault Tolerance',
        'service_limits': 'Service Limits',
        'operational_excellence': 'Operational Excellence',
    }
    return labels.get(pillar, pillar.replace('_', ' ').title() if pillar else 'N/A')


def _get_primary_pillar(recommendation: Dict[str, Any]) -> str:
    """Extract the primary pillar from a recommendation (handles both list and string formats)."""
    pillars = recommendation.get('pillars')
    if pillars and isinstance(pillars, list) and pillars:
        return pillars[0]
    return recommendation.get('pillar', 'other') or 'other'


def _has_pillar(recommendation: Dict[str, Any], pillar: str) -> bool:
    """Check if a recommendation belongs to the given pillar (checks all pillars, not just primary)."""
    pillars = recommendation.get('pillars')
    if pillars and isinstance(pillars, list):
        return pillar in pillars
    return _get_primary_pillar(recommendation) == pillar


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


_RISK_BY_PILLAR = {
    'security': 'Unresolved security issues may expose resources to unauthorized access, data breaches, or compliance violations.',
    'cost_optimizing': 'Unused or underutilized resources continue to incur costs unnecessarily.',
    'fault_tolerance': 'Without resilience improvements, your workload may experience downtime during failures.',
    'performance': 'Performance issues can degrade user experience and application response times.',
    'service_limits': 'Approaching service limits may cause request failures or deployment errors.',
    'operational_excellence': 'Operational gaps can lead to increased maintenance burden and incident response time.',
}
_RISK_DEFAULT = 'Unresolved issues may impact reliability, security, or cost efficiency of your workload.'


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _get_risk_text(pillar: str) -> str:
    """Return risk text for a pillar."""
    return _RISK_BY_PILLAR.get(pillar, _RISK_DEFAULT)


def _render_accordion_item(
    rec: Dict[str, Any],
    extra_col_html: str = '',
    detail: Optional[Dict[str, Any]] = None,
    resource_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Render a single recommendation as a clickable <details> accordion item."""
    status = rec.get('status', 'unknown').lower()
    name = rec.get('name', 'Unknown')
    arn = rec.get('arn', '')
    pillar = _get_primary_pillar(rec)
    agg = rec.get('resourcesAggregates', {})
    ok_n = int(agg.get('okCount', 0))
    warn_n = int(agg.get('warningCount', 0))
    err_n = int(agg.get('errorCount', 0))
    affected = warn_n + err_n
    savings = _extract_savings(rec)
    raw_ts = rec.get('lastUpdatedAt', '')
    updated = str(raw_ts)[:10] if raw_ts else ''
    hint = _get_remediation_hint(name)
    border_color = _status_color(status)

    # Description section (from detail API)
    description_html = ''
    if detail:
        raw_desc = detail.get('description', '')
        if raw_desc:
            stripped = _strip_html(raw_desc)
            truncated = stripped[:300] + ('...' if len(stripped) > 300 else '')
            description_html = (
                f'<div style="margin-top:6px;padding:8px 10px;background:#e3f2fd;'
                f'border-radius:4px;border-left:3px solid #1565c0;">'
                f'<strong>What is this check?</strong><br>'
                f'<span style="font-size:12px;">{_escape_html(truncated)}</span></div>'
            )

    # Risk section
    risk_text = _get_risk_text(pillar)
    risk_html = (
        f'<div style="margin-top:8px;padding:8px 10px;background:#fce4ec;'
        f'border-radius:4px;border-left:3px solid #c62828;">'
        f'<strong>Risk:</strong> {_escape_html(risk_text)}</div>'
    )

    # Affected resources section
    resources_html = ''
    if resource_list:
        active_resources = [
            r for r in resource_list
            if r.get('status', '').lower() in ('warning', 'error')
        ]
        if active_resources:
            total_count = len(active_resources)
            display = active_resources[:10]
            items = ''
            for r in display:
                label = (
                    r.get('id')
                    or r.get('arn')
                    or next(iter(r.get('metadata', {}).values()), 'N/A')
                )
                res_status = r.get('status', '').lower()
                res_color = '#b71c1c' if res_status == 'error' else '#e65100'
                items += (
                    f'<li><span style="color:{res_color};">[{_status_label(res_status)}]</span> '
                    f'{_escape_html(str(label))}</li>'
                )
            more = ''
            if total_count > 10:
                more = f'<div style="font-size:12px;color:#757575;margin-top:4px;">(and {total_count - 10} more...)</div>'
            resources_html = (
                f'<div style="margin-top:10px;">'
                f'<strong>Affected Resources ({total_count} total):</strong>'
                f'<ul style="margin:6px 0;padding-left:20px;font-size:12px;font-family:monospace;">'
                f'{items}</ul>{more}</div>'
            )

    # Savings line (only if > 0)
    savings_line = ''
    if savings > 0:
        savings_line = (
            f'<div style="margin-top:6px;">'
            f'<strong>Estimated Savings:</strong> ${savings:,.2f}/month</div>'
        )

    # ARN line
    arn_line = (
        f'<div style="margin-top:6px;word-break:break-all;">'
        f'<strong>ARN:</strong> <code style="font-size:11px;">{_escape_html(arn)}</code></div>'
    ) if arn else ''

    # Updated line
    updated_line = (
        f'<div style="margin-top:6px;"><strong>Last Updated:</strong> {updated}</div>'
    ) if updated else ''

    detail_html = f'''
        <div style="padding:12px 16px;background:#fafafa;border-top:1px solid #e0e0e0;
                    font-size:13px;color:#424242;line-height:1.6;">
            {description_html}
            {risk_html}
            <div style="margin-top:8px;"><strong>Resources:</strong>
                <span style="color:#2e7d32;">{ok_n} OK</span> ·
                <span style="color:#e65100;">{warn_n} Warning</span> ·
                <span style="color:#b71c1c;">{err_n} Error</span>
                (affected: {affected})
            </div>
            {resources_html}
            {savings_line}
            {updated_line}
            {arn_line}
            <div style="margin-top:10px;padding:10px;background:#fff3e0;border-radius:4px;
                        border-left:3px solid #e65100;">
                <strong>Recommended Action:</strong><br>{_escape_html(hint)}
            </div>
        </div>'''

    return f'''
    <details style="border:1px solid #e0e0e0;border-left:4px solid {border_color};
                    border-radius:4px;margin-bottom:8px;overflow:hidden;">
        <summary style="padding:12px 16px;cursor:pointer;list-style:none;
                        display:flex;align-items:center;justify-content:space-between;
                        background:#fff;user-select:none;"
                 onmouseover="this.style.background='#f5f5f5'"
                 onmouseout="this.style.background='#fff'">
            <span style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">
                {_status_badge(status)}
                <span style="font-weight:500;overflow:hidden;text-overflow:ellipsis;">
                    {_escape_html(name)}
                </span>
            </span>
            <span style="display:flex;align-items:center;gap:12px;white-space:nowrap;
                         margin-left:12px;font-size:13px;color:#757575;">
                {extra_col_html}
                <span class="ta-arrow" style="display:inline-block;font-size:11px;transition:transform 0.2s;">&#9660;</span>
            </span>
        </summary>
        {detail_html}
    </details>'''


def generate_html_report(
    recommendations: List[Dict[str, Any]],
    generated_at: str = '',
    details: Optional[Dict[str, Any]] = None,
    resources: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> str:
    """Generate a self-contained HTML report from Trusted Advisor recommendations.

    Each recommendation is rendered as a clickable accordion item (HTML5 details/summary,
    no JavaScript required) that expands to show resource counts, savings, ARN,
    last updated date, and a recommended action.

    Args:
        recommendations: List of all recommendation summaries from the API.
        generated_at: Timestamp string for when the report was generated.
        details: Optional dict mapping ARN to recommendation detail from get_recommendation.
        resources: Optional dict mapping ARN to list of resource dicts from list_recommendation_resources.

    Returns:
        A complete self-contained HTML file as a string.
    """
    if details is None:
        details = {}
    if resources is None:
        resources = {}
    total = len(recommendations)
    ok_count = sum(1 for r in recommendations if r.get('status') == 'ok')
    warning_count = sum(1 for r in recommendations if r.get('status') == 'warning')
    error_count = sum(1 for r in recommendations if r.get('status') == 'error')

    # Calculate overall score
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

    total_savings = sum(_extract_savings(r) for r in recommendations)

    # Group by pillar
    by_pillar: Dict[str, List[Dict[str, Any]]] = {}
    for rec in recommendations:
        pillar = _get_primary_pillar(rec)
        by_pillar.setdefault(pillar, []).append(rec)

    # Pillar summary cards
    pillar_cards_html = ''
    for pillar in sorted(by_pillar.keys()):
        recs = by_pillar[pillar]
        p_ok = sum(1 for r in recs if r.get('status') == 'ok')
        p_warn = sum(1 for r in recs if r.get('status') == 'warning')
        p_err = sum(1 for r in recs if r.get('status') == 'error')
        p_total = len(recs)
        if p_total > 0:
            p_penalty = (p_err * 3) + p_warn
            p_max = p_total * 3
            p_score = max(0, round(100 * (1 - p_penalty / p_max)))
        else:
            p_score = 100
        score_color = '#2e7d32' if p_score >= 75 else '#e65100' if p_score >= 50 else '#b71c1c'
        pillar_cards_html += f'''
        <div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:16px;
                    min-width:140px;flex:1;text-align:center;">
            <div style="font-weight:600;font-size:13px;margin-bottom:8px;color:#424242;">
                {_escape_html(_pillar_label(pillar))}
            </div>
            <div style="font-size:32px;font-weight:700;color:{score_color};">{p_score}</div>
            <div style="font-size:11px;color:#757575;margin-top:4px;">
                {p_ok} OK &middot; {p_warn} Warn &middot; {p_err} Error
            </div>
        </div>'''

    # --- Security section ---
    security_recs = sorted(
        [r for r in recommendations
         if _has_pillar(r, 'security') and r.get('status') in ('warning', 'error')],
        key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', ''))
    )
    security_html = ''
    if security_recs:
        items = ''.join(
            _render_accordion_item(
                r,
                extra_col_html=(
                    f'<span style="color:#b71c1c;">{int(r.get("resourcesAggregates", {}).get("warningCount", 0)) + int(r.get("resourcesAggregates", {}).get("errorCount", 0))} affected</span>'
                ),
                detail=details.get(r.get('arn', '')),
                resource_list=resources.get(r.get('arn', '')),
            )
            for r in security_recs
        )
        security_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;margin-bottom:12px;">
            Security Issues <span style="font-size:16px;color:#757575;">({len(security_recs)})</span>
        </h2>
        {items}'''

    # --- Cost Optimization section ---
    cost_recs = sorted(
        [r for r in recommendations
         if _has_pillar(r, 'cost_optimizing') and r.get('status') in ('warning', 'error')],
        key=lambda r: _extract_savings(r), reverse=True
    )
    cost_html = ''
    if cost_recs:
        items = ''.join(
            _render_accordion_item(
                r,
                extra_col_html=(
                    f'<span style="color:#2e7d32;font-weight:600;">'
                    f'{"$" + f"{_extract_savings(r):,.2f}/mo" if _extract_savings(r) > 0 else "N/A"}'
                    f'</span>'
                ),
                detail=details.get(r.get('arn', '')),
                resource_list=resources.get(r.get('arn', '')),
            )
            for r in cost_recs
        )
        cost_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;margin-bottom:12px;">
            Cost Optimization <span style="font-size:16px;color:#757575;">({len(cost_recs)})</span>
        </h2>
        {items}'''

    # --- Service Limits section ---
    limits_recs = sorted(
        [r for r in recommendations
         if _has_pillar(r, 'service_limits') and r.get('status') in ('warning', 'error')],
        key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', ''))
    )
    limits_html = ''
    if limits_recs:
        items = ''.join(
            _render_accordion_item(
                r,
                detail=details.get(r.get('arn', '')),
                resource_list=resources.get(r.get('arn', '')),
            )
            for r in limits_recs
        )
        limits_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;margin-bottom:12px;">
            Service Limits <span style="font-size:16px;color:#757575;">({len(limits_recs)})</span>
        </h2>
        {items}'''

    # --- Other Issues section ---
    other_pillars = {'performance', 'fault_tolerance', 'operational_excellence'}
    other_recs = sorted(
        [r for r in recommendations
         if any(_has_pillar(r, p) for p in other_pillars) and r.get('status') in ('warning', 'error')],
        key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', ''))
    )
    other_html = ''
    if other_recs:
        items = ''.join(
            _render_accordion_item(
                r,
                extra_col_html=(
                    f'<span style="color:#616161;">{_escape_html(_pillar_label(_get_primary_pillar(r)))}</span>'
                ),
                detail=details.get(r.get('arn', '')),
                resource_list=resources.get(r.get('arn', '')),
            )
            for r in other_recs
        )
        other_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;margin-bottom:12px;">
            Other Issues <span style="font-size:16px;color:#757575;">({len(other_recs)})</span>
        </h2>
        {items}'''

    # --- Unclassified Issues section ---
    known_pillars = {'security', 'cost_optimizing', 'service_limits',
                     'performance', 'fault_tolerance', 'operational_excellence'}
    classified_ids = {id(r) for r in security_recs + cost_recs + limits_recs + other_recs}
    unclassified_recs = sorted(
        [r for r in recommendations
         if id(r) not in classified_ids and r.get('status') in ('warning', 'error')],
        key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', ''))
    )
    unclassified_html = ''
    if unclassified_recs:
        items = ''.join(
            _render_accordion_item(
                r,
                extra_col_html=(
                    f'<span style="color:#616161;">{_escape_html(_pillar_label(_get_primary_pillar(r)))}</span>'
                ),
                detail=details.get(r.get('arn', '')),
                resource_list=resources.get(r.get('arn', '')),
            )
            for r in unclassified_recs
        )
        unclassified_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;margin-bottom:12px;">
            Unclassified Issues <span style="font-size:16px;color:#757575;">({len(unclassified_recs)})</span>
        </h2>
        {items}'''

    # Savings callout
    savings_callout = ''
    if total_savings > 0:
        savings_callout = f'''
        <div style="background:#e8f5e9;border-left:4px solid #2e7d32;padding:16px;margin-top:16px;
                    border-radius:4px;">
            <div style="font-weight:600;color:#2e7d32;font-size:15px;">Potential Savings Available</div>
            <div style="font-size:26px;font-weight:700;color:#1b5e20;margin-top:4px;">
                ${total_savings:,.2f}/month &nbsp;&middot;&nbsp; ${total_savings * 12:,.2f}/year
            </div>
        </div>'''

    score_color = '#2e7d32' if overall_score >= 75 else '#e65100' if overall_score >= 50 else '#b71c1c'
    date_line = (
        f'<div style="color:#9fa8da;margin-top:4px;font-size:13px;">'
        f'Generated: {_escape_html(generated_at)}</div>'
    ) if generated_at else ''

    no_issues_msg = ''
    if not security_recs and not cost_recs and not limits_recs and not other_recs and not unclassified_recs:
        no_issues_msg = '''
        <div style="text-align:center;padding:32px;color:#2e7d32;">
            <div style="font-size:48px;">✅</div>
            <div style="font-size:18px;font-weight:600;margin-top:8px;">No active issues found</div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Trusted Advisor Report</title>
    <style>
        details > summary {{ list-style: none; }}
        details > summary::-webkit-details-marker {{ display: none; }}
        details[open] > summary .ta-arrow {{ transform: rotate(180deg); }}
    </style>
</head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f0f2f5;color:#212121;">
<div style="max-width:960px;margin:0 auto;padding:24px;">

    <!-- Header -->
    <div style="background:#1a237e;color:#fff;padding:24px 28px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:22px;font-weight:700;">AWS Trusted Advisor Report</h1>
        {date_line}
    </div>

    <!-- Score Card -->
    <div style="background:#fff;padding:24px 28px;border:1px solid #e0e0e0;border-top:none;">
        <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
            <div style="text-align:center;min-width:80px;">
                <div style="font-size:56px;font-weight:700;line-height:1;color:{score_color};">
                    {overall_score}
                </div>
                <div style="font-size:13px;color:#757575;margin-top:2px;">/ 100 &nbsp; Grade: <strong>{grade}</strong></div>
            </div>
            <div style="flex:1;min-width:200px;">
                <div style="background:#e0e0e0;border-radius:8px;height:20px;overflow:hidden;">
                    <div style="background:{score_color};height:100%;width:{overall_score}%;
                                border-radius:8px;transition:width 0.3s;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px;">
                    <span><span style="color:#2e7d32;font-weight:600;">{ok_count}</span> OK</span>
                    <span><span style="color:#e65100;font-weight:600;">{warning_count}</span> Warnings</span>
                    <span><span style="color:#b71c1c;font-weight:600;">{error_count}</span> Errors</span>
                    <span style="color:#757575;">{total} Total</span>
                </div>
            </div>
        </div>
        {savings_callout}
    </div>

    <!-- Pillar Summary -->
    <div style="background:#fff;padding:20px 28px;border:1px solid #e0e0e0;border-top:none;">
        <h2 style="color:#1a237e;margin:0 0 16px 0;font-size:16px;">Pillar Summary</h2>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
            {pillar_cards_html}
        </div>
    </div>

    <!-- Detail Sections -->
    <div style="background:#fff;padding:24px 28px;border:1px solid #e0e0e0;border-top:none;
                border-radius:0 0 8px 8px;">
        <p style="color:#757575;font-size:13px;margin-top:0;">
            Click any item to expand details, affected resources, and recommended actions.
        </p>
        {security_html}
        {cost_html}
        {limits_html}
        {other_html}
        {unclassified_html}
        {no_issues_msg}
    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#9e9e9e;font-size:12px;">
        Generated by AWS Trusted Advisor MCP Server
    </div>

</div>
</body>
</html>'''
