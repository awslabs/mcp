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

"""Runner for DynamoDB Cost & Performance Calculator workflow."""

from awslabs.dynamodb_mcp_server.cost_performance_calculator.cost_calculator import calculate_cost
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import DataModel
from awslabs.dynamodb_mcp_server.cost_performance_calculator.report_generator import (
    REPORT_END_MARKER,
    REPORT_START_MARKER,
    generate_report,
)
from pathlib import Path


_REPORT_FILENAME = 'dynamodb_data_model.md'


def run_cost_calculator(data_model: DataModel, workspace_dir: str) -> str:
    """Execute cost calculator workflow: calculate costs and generate report.

    Args:
        data_model: Validated DataModel instance.
        workspace_dir: Pre-validated path to append report to dynamodb_data_model.md.

    Returns:
        Summary message describing what was analyzed.
    """
    cost_model = calculate_cost(data_model)
    report = generate_report(data_model, cost_model)
    _replace_or_append_report(report, workspace_dir)

    pattern_count = len(data_model.access_pattern_list)
    table_count = len(data_model.table_list)
    return (
        f'Cost analysis complete. Analyzed {pattern_count} access patterns '
        f'across {table_count} tables. Report written to {_REPORT_FILENAME}'
    )


def _replace_or_append_report(report: str, workspace_dir: str) -> None:
    """Replace existing cost report section or append if not found.

    Looks for content between REPORT_START_MARKER and REPORT_END_MARKER.
    If found, replaces that section. Otherwise appends the report.

    Note:
        This reads the entire file into memory for the replace path.
        If the target file grows very large, consider a streaming
        approach with a temporary file instead.

    Args:
        report: Markdown report content (must include start/end markers).
        workspace_dir: Validated workspace directory path (must be pre-validated).
    """
    file_path = Path(workspace_dir) / _REPORT_FILENAME

    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        start_idx = content.find(REPORT_START_MARKER)
        end_idx = content.find(REPORT_END_MARKER)

        if start_idx != -1 and end_idx != -1:
            end_idx += len(REPORT_END_MARKER)
            new_content = content[:start_idx] + report + content[end_idx:]
            file_path.write_text(new_content, encoding='utf-8')
            return

    with file_path.open('a', encoding='utf-8') as f:
        f.write('\n\n')
        f.write(report)
