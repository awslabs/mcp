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

"""Report generation for DynamoDB Cost & Performance Calculator."""

from __future__ import annotations

from awslabs.dynamodb_mcp_server.cost_performance_calculator.cost_model import (
    AccessPatternResult,
    CostModel,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    AccessPattern,
    DataModel,
)


REPORT_START_MARKER = '## Cost Report'
REPORT_END_MARKER = '<!-- end-cost-report -->'

DISCLAIMER = """\
> **Disclaimer:** This estimate covers **read/write request costs** and **storage costs** only,
> based on DynamoDB Standard table class on-demand pricing for the **US East (N. Virginia) /
> us-east-1** region. Prices were last verified in **January 2026**. Additional features such as
> Point-in-Time Recovery (PITR), backups, streams, and data transfer may incur additional costs.
> Actual costs may also vary based on your AWS region, pricing model (on-demand vs. provisioned),
> reserved capacity, and real-world traffic patterns. This report assumes constant RPS and average
> item sizes. For the most current pricing, refer to the
> [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/) page."""

GSI_FOOTNOTE = """\
¹ **GSI additional writes** - When a table write changes attributes projected into a GSI,
DynamoDB performs an additional write to that index, incurring extra WRUs. If the GSI partition
key value changes, the cost doubles (delete + insert) - this estimate assumes single writes only.
[Learn more](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html#GSI.ThroughputConsiderations.Writes)"""


def _format_cost(cost: float) -> str:
    """Format cost as $X.XX."""
    return f'${cost:.2f}'


def _compute_col_widths(headers: list[str], rows: list[list[str]]) -> list[int]:
    """Compute the max width for each column across headers and rows."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
    return widths


def _build_padded_row(cells: list[str], col_widths: list[int]) -> str:
    """Build a single padded markdown table row."""
    padded = [cell.ljust(col_widths[i]) for i, cell in enumerate(cells) if i < len(col_widths)]
    return '| ' + ' | '.join(padded) + ' |'


def _generate_padded_table(headers: list[str], rows: list[list[str]]) -> str:
    """Generate a markdown table with padded columns for alignment."""
    if not headers:
        return ''

    col_widths = _compute_col_widths(headers, rows)
    header_line = _build_padded_row(headers, col_widths)
    separator_line = '| ' + ' | '.join('-' * w for w in col_widths) + ' |'
    data_lines = [_build_padded_row(row, col_widths) for row in rows]

    return '\n'.join([header_line, separator_line] + data_lines)


def generate_report(data_model: DataModel, cost_model: CostModel) -> str:
    """Generate concise markdown report.

    Args:
        data_model: Validated data model
        cost_model: Cost model with computed metrics

    Returns:
        Markdown-formatted report string

    Raises:
        ValueError: If data_model or cost_model is None or invalid
    """
    if data_model is None:
        raise ValueError('data_model cannot be None')
    if not data_model.access_pattern_list:
        raise ValueError('data_model.access_pattern_list cannot be empty')
    if cost_model is None:
        raise ValueError('cost_model cannot be None')

    rw_cost, rw_summary_rows = _compute_rw_summary(data_model, cost_model)
    storage_cost, storage_rows = _build_storage_rows(cost_model)
    total = rw_cost + storage_cost

    sections = [
        REPORT_START_MARKER,
        DISCLAIMER,
        _generate_total_summary(total, storage_cost, rw_cost),
        _generate_storage_section(storage_rows, storage_cost),
        _generate_rw_section(data_model, cost_model, rw_summary_rows, rw_cost),
    ]

    report = '\n\n'.join(sections)

    if '¹' in report:
        report += '\n\n' + GSI_FOOTNOTE

    report += '\n\n' + REPORT_END_MARKER

    return report


def _build_ap_row(result: AccessPatternResult, ap: AccessPattern) -> list[str]:
    """Build a single access pattern table row."""
    ru = result.wcus if result.wcus > 0 else result.rcus
    return [
        result.pattern,
        ap.operation,
        str(ap.rps),
        f'{ru:.2f}',
        _format_cost(result.cost),
    ]


def _find_ap_for_table(
    result: AccessPatternResult,
    table_name: str,
    ap_map: dict[str, AccessPattern],
) -> AccessPattern | None:
    """Look up the access pattern for a result, returning None if not found or wrong table."""
    ap = ap_map.get(result.pattern)
    if not ap or ap.table != table_name:
        return None
    return ap


def _collect_base_table_rows(
    table_name: str,
    cost_model: CostModel,
    ap_map: dict[str, AccessPattern],
) -> tuple[list[list[str]], float]:
    """Collect access pattern rows for a base table (reads without GSI + all writes)."""
    rows = []
    cost = 0.0
    for result in cost_model.access_patterns:
        ap = _find_ap_for_table(result, table_name, ap_map)
        if not ap:
            continue
        is_base_table_read = not getattr(ap, 'gsi', None)
        is_write = result.wcus > 0
        if is_base_table_read or is_write:
            rows.append(_build_ap_row(result, ap))
            cost += result.cost
    return rows, cost


def _collect_gsi_read_rows(
    table_name: str,
    gsi_name: str,
    cost_model: CostModel,
    ap_map: dict[str, AccessPattern],
) -> tuple[list[list[str]], float]:
    """Collect GSI read pattern rows."""
    rows = []
    cost = 0.0
    for result in cost_model.access_patterns:
        ap = _find_ap_for_table(result, table_name, ap_map)
        if ap and getattr(ap, 'gsi', None) == gsi_name:
            rows.append(
                [
                    result.pattern,
                    ap.operation,
                    str(ap.rps),
                    f'{result.rcus:.2f}',
                    _format_cost(result.cost),
                ]
            )
            cost += result.cost
    return rows, cost


def _collect_gsi_write_amp_rows(
    table_name: str,
    gsi_name: str,
    cost_model: CostModel,
    ap_map: dict[str, AccessPattern],
) -> tuple[list[list[str]], float]:
    """Collect GSI additional write rows."""
    rows = []
    cost = 0.0
    for result in cost_model.access_patterns:
        ap = _find_ap_for_table(result, table_name, ap_map)
        if not ap:
            continue
        for gsi_amp in result.gsi_write_amplification:
            if gsi_amp.gsi_name == gsi_name:
                rows.append(
                    [
                        f'{result.pattern}¹',
                        ap.operation,
                        str(ap.rps),
                        f'{gsi_amp.wcus:.2f}',
                        _format_cost(gsi_amp.cost),
                    ]
                )
                cost += gsi_amp.cost
    return rows, cost


def _generate_total_summary(total: float, storage_cost: float, rw_cost: float) -> str:
    """Generate the top-line total monthly cost summary."""
    headers = ['Source', 'Monthly Cost']
    rows = [
        ['Storage', _format_cost(storage_cost)],
        ['Read and write requests', _format_cost(rw_cost)],
    ]

    lines = [
        f'**Total Monthly Cost: {_format_cost(total)}**',
        '',
        _generate_padded_table(headers, rows),
    ]

    return '\n'.join(lines)


def _build_storage_rows(cost_model: CostModel) -> tuple[float, list[list[str]]]:
    """Build storage table rows for all tables and their GSIs.

    Returns:
        Tuple of (total_cost, rows) for the storage summary table.
    """
    gsi_by_table: dict[str, list] = {}
    for gsi in cost_model.gsis:
        gsi_by_table.setdefault(gsi.table_name, []).append(gsi)

    rows = []
    total_cost = 0.0

    for table in cost_model.tables:
        rows.append(
            [
                table.table_name,
                'Table',
                f'{table.storage_gb:.2f}',
                _format_cost(table.storage_cost),
            ]
        )
        total_cost += table.storage_cost

        for gsi in gsi_by_table.get(table.table_name, []):
            rows.append(
                [gsi.gsi_name, 'GSI', f'{gsi.storage_gb:.2f}', _format_cost(gsi.storage_cost)]
            )
            total_cost += gsi.storage_cost

    return total_cost, rows


def _generate_storage_section(rows: list[list[str]], total_cost: float) -> str:
    """Generate storage costs section."""
    headers = ['Resource', 'Type', 'Storage (GB)', 'Monthly Cost']

    lines = [
        '### Storage Costs',
        '',
        f'**Monthly Cost:** {_format_cost(total_cost)}',
        '',
        _generate_padded_table(headers, rows),
    ]

    return '\n'.join(lines)


def _compute_rw_summary(
    data_model: DataModel, cost_model: CostModel
) -> tuple[float, list[list[str]]]:
    """Compute per-resource R/W cost summary rows.

    Returns:
        Tuple of (grand_total, summary_rows) where each row is
        [resource_name, type, monthly_cost].
    """
    ap_map = {ap.pattern: ap for ap in data_model.access_pattern_list}
    table_gsis = {
        table.name: [gsi.name for gsi in table.gsi_list] for table in data_model.table_list
    }

    rows = []
    grand_total = 0.0

    for table in data_model.table_list:
        _, table_cost = _collect_base_table_rows(table.name, cost_model, ap_map)
        rows.append([table.name, 'Table', _format_cost(table_cost)])
        grand_total += table_cost

        for gsi_name in table_gsis.get(table.name, []):
            _, read_cost = _collect_gsi_read_rows(table.name, gsi_name, cost_model, ap_map)
            _, amp_cost = _collect_gsi_write_amp_rows(table.name, gsi_name, cost_model, ap_map)
            gsi_total = read_cost + amp_cost
            rows.append([gsi_name, 'GSI', _format_cost(gsi_total)])
            grand_total += gsi_total

    return grand_total, rows


def _generate_rw_section(
    data_model: DataModel,
    cost_model: CostModel,
    summary_rows: list[list[str]],
    rw_cost: float,
) -> str:
    """Generate the read and write request costs section with summary and detail tables."""
    ap_map = {ap.pattern: ap for ap in data_model.access_pattern_list}
    table_gsis = {
        table.name: [gsi.name for gsi in table.gsi_list] for table in data_model.table_list
    }

    summary_headers = ['Resource', 'Type', 'Monthly Cost']
    detail_headers = ['Pattern', 'Operation', 'RPS', 'RRU / WRU', 'Monthly Cost']

    lines = [
        '### Read and Write Request Costs',
        '',
        f'**Monthly Cost:** {_format_cost(rw_cost)}',
        '',
        _generate_padded_table(summary_headers, summary_rows),
    ]

    for table in data_model.table_list:
        rows, table_cost = _collect_base_table_rows(table.name, cost_model, ap_map)
        lines.append('')
        lines.append(f'#### {table.name} Table')
        lines.append('')
        lines.append(f'**Monthly Cost:** {_format_cost(table_cost)}')
        lines.append('')
        lines.append(_generate_padded_table(detail_headers, rows))

        for gsi_name in table_gsis.get(table.name, []):
            read_rows, read_cost = _collect_gsi_read_rows(table.name, gsi_name, cost_model, ap_map)
            amp_rows, amp_cost = _collect_gsi_write_amp_rows(
                table.name, gsi_name, cost_model, ap_map
            )
            gsi_total = read_cost + amp_cost
            lines.append('')
            lines.append(f'#### {table.name} Table / {gsi_name} GSI')
            lines.append('')
            lines.append(f'**Monthly Cost:** {_format_cost(gsi_total)}')
            lines.append('')
            lines.append(_generate_padded_table(detail_headers, read_rows + amp_rows))

    return '\n'.join(lines)
