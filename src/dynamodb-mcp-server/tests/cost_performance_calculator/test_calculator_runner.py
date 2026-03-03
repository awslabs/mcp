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

"""Unit tests for calculator_runner module."""

import os
import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner import (
    run_cost_calculator,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_ITEM_SIZE_BYTES,
    DataModel,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.report_generator import (
    REPORT_END_MARKER,
    REPORT_START_MARKER,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch


@pytest.fixture
def valid_data_model():
    """Create a valid DataModel for testing."""
    return DataModel(
        access_pattern_list=[
            {
                'operation': 'GetItem',
                'pattern': 'get-user',
                'description': 'Get user by ID',
                'table': 'users',
                'rps': 100,
                'item_size_bytes': 1024,
            }
        ],
        table_list=[{'name': 'users', 'item_count': 10000, 'item_size_bytes': 2048}],
    )


@pytest.fixture
def mock_cost_model():
    """Create a mock CostModel."""
    return MagicMock()


class TestRunCostCalculator:
    """Tests for run_cost_calculator function."""

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_valid_input_returns_report(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test valid input returns summary message."""
        mock_calculate_cost.return_value = mock_cost_model
        mock_generate_report.return_value = '# Cost and Performance Report\n\nMocked content'

        result = run_cost_calculator(valid_data_model, workspace_dir=str(tmp_path))

        assert isinstance(result, str)
        assert 'Cost analysis complete' in result
        assert '1 access patterns' in result
        assert '1 tables' in result
        mock_calculate_cost.assert_called_once_with(valid_data_model)
        mock_generate_report.assert_called_once_with(valid_data_model, mock_cost_model)

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_report_written_to_file(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test report content is written to file."""
        mock_calculate_cost.return_value = mock_cost_model
        expected_report = '# Cost and Performance Report\n\n## Access Patterns\n\nMocked'
        mock_generate_report.return_value = expected_report

        run_cost_calculator(valid_data_model, workspace_dir=str(tmp_path))

        file_path = tmp_path / 'dynamodb_data_model.md'
        content = file_path.read_text()
        assert expected_report in content

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_file_created_when_workspace_dir_provided(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test file is created when workspace_dir provided."""
        mock_calculate_cost.return_value = mock_cost_model
        mock_generate_report.return_value = '# Report'

        workspace_dir = str(tmp_path)
        run_cost_calculator(valid_data_model, workspace_dir=workspace_dir)

        file_path = os.path.join(workspace_dir, 'dynamodb_data_model.md')
        assert os.path.exists(file_path)

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_file_append_preserves_existing_content(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test file append preserves existing content."""
        mock_calculate_cost.return_value = mock_cost_model
        mock_generate_report.return_value = '# Cost and Performance Report'

        workspace_dir = str(tmp_path)
        file_path = os.path.join(workspace_dir, 'dynamodb_data_model.md')

        existing_content = '# Existing Content\n\nSome existing data.'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(existing_content)

        run_cost_calculator(valid_data_model, workspace_dir=workspace_dir)

        with open(file_path, encoding='utf-8') as f:
            content = f.read()
        assert existing_content in content
        assert '# Cost and Performance Report' in content

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_multiple_access_patterns_count(
        self,
        mock_calculate_cost,
        mock_generate_report,
        mock_cost_model,
        tmp_path,
    ):
        """Test summary correctly counts multiple access patterns."""
        mock_calculate_cost.return_value = mock_cost_model
        mock_generate_report.return_value = '# Report'

        data_model = DataModel(
            access_pattern_list=[
                {
                    'operation': 'GetItem',
                    'pattern': 'get-user',
                    'description': 'Get user',
                    'table': 'users',
                    'rps': 100,
                    'item_size_bytes': 1024,
                },
                {
                    'operation': 'PutItem',
                    'pattern': 'put-user',
                    'description': 'Put user',
                    'table': 'users',
                    'rps': 50,
                    'item_size_bytes': 1024,
                },
            ],
            table_list=[{'name': 'users', 'item_count': 10000, 'item_size_bytes': 2048}],
        )

        result = run_cost_calculator(data_model, workspace_dir=str(tmp_path))

        assert '2 access patterns' in result
        assert '1 tables' in result

    @given(
        item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        item_count=st.integers(min_value=1, max_value=10000),
        rps=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=100)
    def test_run_cost_calculator_returns_report_property(self, item_size, item_count, rps):
        """Property 8: run_cost_calculator Returns Report.

        For any valid DataModel input, run_cost_calculator SHALL return
        a non-empty string starting with '#' (markdown heading).

        **Validates: Requirements 3.2**
        """
        import tempfile

        data_model = DataModel(
            access_pattern_list=[
                {
                    'operation': 'GetItem',
                    'pattern': 'test-pattern',
                    'description': 'Test description',
                    'table': 'test-table',
                    'rps': rps,
                    'item_size_bytes': item_size,
                }
            ],
            table_list=[
                {
                    'name': 'test-table',
                    'item_count': item_count,
                    'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                }
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_cost_calculator(data_model, workspace_dir=tmp_dir)

        assert isinstance(result, str)
        assert len(result) > 0
        assert 'Cost analysis complete' in result


class TestReplaceOrAppendReport:
    """Tests for the replace-or-append report behavior."""

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_replaces_existing_report_between_markers(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test that an existing report section is replaced when markers are present."""
        mock_calculate_cost.return_value = mock_cost_model
        new_report = f'{REPORT_START_MARKER}\n\nNew content\n\n{REPORT_END_MARKER}'
        mock_generate_report.return_value = new_report

        workspace_dir = str(tmp_path)
        file_path = tmp_path / 'dynamodb_data_model.md'

        old_report = f'{REPORT_START_MARKER}\n\nOld content\n\n{REPORT_END_MARKER}'
        existing = f'# Header\n\nPreamble\n\n{old_report}\n\n# Footer\n\nPostamble'
        file_path.write_text(existing, encoding='utf-8')

        run_cost_calculator(valid_data_model, workspace_dir=workspace_dir)

        content = file_path.read_text(encoding='utf-8')
        assert 'New content' in content
        assert 'Old content' not in content
        assert '# Header' in content
        assert 'Preamble' in content
        assert '# Footer' in content
        assert 'Postamble' in content

    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.generate_report'
    )
    @patch(
        'awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner.calculate_cost'
    )
    def test_appends_when_only_start_marker_present(
        self,
        mock_calculate_cost,
        mock_generate_report,
        valid_data_model,
        mock_cost_model,
        tmp_path,
    ):
        """Test append fallback when only start marker exists (no end marker)."""
        mock_calculate_cost.return_value = mock_cost_model
        new_report = f'{REPORT_START_MARKER}\n\nNew content\n\n{REPORT_END_MARKER}'
        mock_generate_report.return_value = new_report

        workspace_dir = str(tmp_path)
        file_path = tmp_path / 'dynamodb_data_model.md'

        existing = f'# Header\n\n{REPORT_START_MARKER}\n\nOrphan start'
        file_path.write_text(existing, encoding='utf-8')

        run_cost_calculator(valid_data_model, workspace_dir=workspace_dir)

        content = file_path.read_text(encoding='utf-8')
        # Original content preserved, new report appended
        assert 'Orphan start' in content
        assert 'New content' in content
