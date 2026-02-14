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

    disclaimer = """\
> **Disclaimer:** This report provides cost estimates based on DynamoDB on-demand pricing for the
> **US East (N. Virginia) / us-east-1** region. Prices were last verified in **January 2025**.
> Actual costs may vary based on your AWS region, pricing model (on-demand vs. provisioned),
> reserved capacity, and real-world traffic patterns. This report assumes constant RPS average
> item sizes, and may not cover all cost scenarios. For the most current pricing, refer to the
> [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/) page."""

    sections = [
        REPORT_START_MARKER,
        disclaimer,
        _generate_access_pattern_costs_section(data_model, cost_model),
        _generate_storage_section(cost_model),
    ]

    report = '\n\n'.join(sections)

    if '¹' in report:
        report += (
            '\n\n¹ **GSI write amplification** — When a table write changes attributes '
            'projected into a GSI, DynamoDB performs an additional write to that index, '
            'incurring extra WRUs. '
            '[Learn more](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/'
            'GSI.html#GSI.ThroughputConsiderations.Writes)'
        )

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
    """Collect GSI write amplification rows."""
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


def _generate_gsi_section(
    table_name: str,
    gsi_name: str,
    cost_model: CostModel,
    ap_map: dict[str, AccessPattern],
    headers: list[str],
) -> tuple[list[str], float]:
    """Generate report lines for a single GSI under a table."""
    lines = ['', f'##### {gsi_name}', '']

    read_rows, read_cost = _collect_gsi_read_rows(table_name, gsi_name, cost_model, ap_map)
    amp_rows, amp_cost = _collect_gsi_write_amp_rows(table_name, gsi_name, cost_model, ap_map)

    gsi_total = read_cost + amp_cost
    lines.append(_generate_padded_table(headers, read_rows + amp_rows))
    lines.append('')
    lines.append(f'**{gsi_name} Cost:** {_format_cost(gsi_total)}')

    return lines, gsi_total


def _generate_access_pattern_costs_section(data_model: DataModel, cost_model: CostModel) -> str:
    """Generate hierarchical access pattern costs by table and GSI."""
    ap_map = {ap.pattern: ap for ap in data_model.access_pattern_list}
    table_gsis = {
        table.name: [gsi.name for gsi in table.gsi_list] for table in data_model.table_list
    }

    lines = ['### Access Pattern Costs', '']
    headers = ['Pattern', 'Operation', 'RPS', 'RRU / WRU', 'Monthly Cost']
    grand_total = 0.0

    for table in data_model.table_list:
        lines.append(f'#### {table.name}')
        lines.append('')

        rows, table_cost = _collect_base_table_rows(table.name, cost_model, ap_map)
        lines.append(_generate_padded_table(headers, rows))
        lines.append('')
        lines.append(f'**{table.name} Table Cost:** {_format_cost(table_cost)}')

        table_total = table_cost
        for gsi_name in table_gsis.get(table.name, []):
            gsi_lines, gsi_cost = _generate_gsi_section(
                table.name, gsi_name, cost_model, ap_map, headers
            )
            lines.extend(gsi_lines)
            table_total += gsi_cost

        lines.append('')
        lines.append(f'**{table.name} Total Cost:** {_format_cost(table_total)}')
        lines.append('')
        grand_total += table_total

    lines.append(f'**Total Access Pattern Cost:** {_format_cost(grand_total)}')

    return '\n'.join(lines)


def _build_storage_rows(cost_model: CostModel) -> tuple[list[list[str]], float]:
    """Build storage table rows for all tables and their GSIs."""
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

    return rows, total_cost


def _generate_storage_section(cost_model: CostModel) -> str:
    """Generate hierarchical storage table with tables and their GSIs."""
    headers = ['Resource', 'Type', 'Storage (GB)', 'Monthly Cost']
    rows, total_cost = _build_storage_rows(cost_model)

    lines = [
        '### Storage Costs',
        '',
        _generate_padded_table(headers, rows),
        '',
        f'**Total Storage Cost:** {_format_cost(total_cost)}',
    ]

    return '\n'.join(lines)
