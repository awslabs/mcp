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

from typing import Any, Dict, List


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



def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def generate_html_report(
    recommendations: List[Dict[str, Any]],
    generated_at: str = '',
) -> str:
    """Generate a self-contained HTML report from Trusted Advisor recommendations.

    Args:
        recommendations: List of all recommendation summaries from the API.
        generated_at: Timestamp string for when the report was generated.

    Returns:
        A complete self-contained HTML file as a string.
    """
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

    # Pillar summary data
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
                    min-width:160px;flex:1;">
            <div style="font-weight:600;margin-bottom:8px;">{_escape_html(_pillar_label(pillar))}</div>
            <div style="font-size:28px;font-weight:700;color:{score_color};">{p_score}</div>
            <div style="font-size:12px;color:#757575;margin-top:4px;">
                {p_ok} OK &middot; {p_warn} Warn &middot; {p_err} Error
            </div>
        </div>'''

    # Security issues section
    security_recs = [
        r for r in recommendations
        if _get_primary_pillar(r) == 'security' and r.get('status') in ('warning', 'error')
    ]
    security_recs.sort(key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', '')))

    security_html = ''
    if security_recs:
        rows = ''
        for rec in security_recs:
            status = rec.get('status', 'unknown')
            color = _status_color(status)
            agg = rec.get('resourcesAggregates', {})
            affected = int(agg.get('warningCount', 0)) + int(agg.get('errorCount', 0))
            rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">
                    <span style="color:{color};font-weight:600;">[{_escape_html(_status_label(status))}]</span>
                    {_escape_html(rec.get('name', 'Unknown'))}
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:center;">
                    {affected}
                </td>
            </tr>'''
        security_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;">Security Issues ({len(security_recs)})</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:8px;">
            <tr style="background:#f5f5f5;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e0e0e0;">Issue</th>
                <th style="padding:8px 12px;text-align:center;border-bottom:2px solid #e0e0e0;">Affected Resources</th>
            </tr>
            {rows}
        </table>'''

    # Cost optimization section
    cost_recs = [
        r for r in recommendations
        if _get_primary_pillar(r) == 'cost_optimizing' and r.get('status') in ('warning', 'error')
    ]
    cost_recs.sort(key=lambda r: _extract_savings(r), reverse=True)

    cost_html = ''
    if cost_recs:
        rows = ''
        for rec in cost_recs:
            status = rec.get('status', 'unknown')
            color = _status_color(status)
            savings = _extract_savings(rec)
            savings_str = f'${savings:,.2f}/mo' if savings > 0 else 'N/A'
            rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">
                    <span style="color:{color};font-weight:600;">[{_escape_html(_status_label(status))}]</span>
                    {_escape_html(rec.get('name', 'Unknown'))}
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:right;">
                    {savings_str}
                </td>
            </tr>'''
        cost_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;">Cost Optimization Opportunities ({len(cost_recs)})</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:8px;">
            <tr style="background:#f5f5f5;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e0e0e0;">Recommendation</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:2px solid #e0e0e0;">Est. Monthly Savings</th>
            </tr>
            {rows}
        </table>'''

    # Service limits section
    limits_recs = [
        r for r in recommendations
        if _get_primary_pillar(r) == 'service_limits' and r.get('status') in ('warning', 'error')
    ]
    limits_recs.sort(key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', '')))

    limits_html = ''
    if limits_recs:
        rows = ''
        for rec in limits_recs:
            status = rec.get('status', 'unknown')
            color = _status_color(status)
            agg = rec.get('resourcesAggregates', {})
            affected = int(agg.get('warningCount', 0)) + int(agg.get('errorCount', 0))
            rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">
                    <span style="color:{color};font-weight:600;">[{_escape_html(_status_label(status))}]</span>
                    {_escape_html(rec.get('name', 'Unknown'))}
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:center;">
                    {affected}
                </td>
            </tr>'''
        limits_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;">Service Limits ({len(limits_recs)})</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:8px;">
            <tr style="background:#f5f5f5;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e0e0e0;">Service Limit</th>
                <th style="padding:8px 12px;text-align:center;border-bottom:2px solid #e0e0e0;">Affected Resources</th>
            </tr>
            {rows}
        </table>'''

    # Other issues section (pillars not covered above)
    other_pillars = {'performance', 'fault_tolerance', 'operational_excellence'}
    other_recs = [
        r for r in recommendations
        if _get_primary_pillar(r) in other_pillars and r.get('status') in ('warning', 'error')
    ]
    other_recs.sort(key=lambda r: (0 if r.get('status') == 'error' else 1, r.get('name', '')))

    other_html = ''
    if other_recs:
        rows = ''
        for rec in other_recs:
            status = rec.get('status', 'unknown')
            color = _status_color(status)
            pillar = _get_primary_pillar(rec)
            agg = rec.get('resourcesAggregates', {})
            affected = int(agg.get('warningCount', 0)) + int(agg.get('errorCount', 0))
            rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">
                    <span style="color:{color};font-weight:600;">[{_escape_html(_status_label(status))}]</span>
                    {_escape_html(rec.get('name', 'Unknown'))}
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">
                    {_escape_html(_pillar_label(pillar))}
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:center;">
                    {affected}
                </td>
            </tr>'''
        other_html = f'''
        <h2 style="color:#1a237e;margin-top:32px;">Other Issues ({len(other_recs)})</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:8px;">
            <tr style="background:#f5f5f5;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e0e0e0;">Issue</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e0e0e0;">Pillar</th>
                <th style="padding:8px 12px;text-align:center;border-bottom:2px solid #e0e0e0;">Affected Resources</th>
            </tr>
            {rows}
        </table>'''

    # Savings callout
    savings_callout = ''
    if total_savings > 0:
        savings_callout = f'''
        <div style="background:#e8f5e9;border-left:4px solid #2e7d32;padding:16px;margin-top:16px;
                    border-radius:4px;">
            <div style="font-weight:600;color:#2e7d32;font-size:16px;">Potential Savings</div>
            <div style="font-size:24px;font-weight:700;color:#1b5e20;margin-top:4px;">
                ${total_savings:,.2f}/month &middot; ${total_savings * 12:,.2f}/year
            </div>
        </div>'''

    # Score bar
    score_color = '#2e7d32' if overall_score >= 75 else '#e65100' if overall_score >= 50 else '#b71c1c'

    account_title = ''
    date_line = f'<div style="color:#757575;margin-top:4px;">Generated: {_escape_html(generated_at)}</div>' if generated_at else ''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Trusted Advisor Report{account_title}</title>
</head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f5f5f5;color:#212121;">
    <div style="max-width:900px;margin:0 auto;padding:24px;">

        <!-- Header -->
        <div style="background:#1a237e;color:#fff;padding:24px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:24px;">AWS Trusted Advisor Report{account_title}</h1>
            {date_line}
        </div>

        <!-- Score -->
        <div style="background:#fff;padding:24px;border:1px solid #e0e0e0;border-top:none;">
            <div style="display:flex;align-items:center;gap:16px;">
                <div>
                    <div style="font-size:48px;font-weight:700;color:{score_color};">{overall_score}</div>
                    <div style="font-size:14px;color:#757575;">out of 100 (Grade: {grade})</div>
                </div>
                <div style="flex:1;">
                    <div style="background:#e0e0e0;border-radius:8px;height:24px;overflow:hidden;">
                        <div style="background:{score_color};height:100%;width:{overall_score}%;
                                    border-radius:8px;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:8px;
                                font-size:13px;color:#616161;">
                        <span style="color:#2e7d32;">{ok_count} OK</span>
                        <span style="color:#e65100;">{warning_count} Warnings</span>
                        <span style="color:#b71c1c;">{error_count} Errors</span>
                    </div>
                </div>
            </div>
            {savings_callout}
        </div>

        <!-- Pillar Summary -->
        <div style="background:#fff;padding:24px;border:1px solid #e0e0e0;border-top:none;">
            <h2 style="color:#1a237e;margin-top:0;">Pillar Summary</h2>
            <div style="display:flex;gap:12px;flex-wrap:wrap;">
                {pillar_cards_html}
            </div>
        </div>

        <!-- Sections -->
        <div style="background:#fff;padding:24px;border:1px solid #e0e0e0;border-top:none;
                    border-radius:0 0 8px 8px;">
            {security_html}
            {cost_html}
            {limits_html}
            {other_html}
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:16px;color:#9e9e9e;font-size:12px;">
            Generated by AWS Trusted Advisor MCP Server
        </div>

    </div>
</body>
</html>'''

    return html
