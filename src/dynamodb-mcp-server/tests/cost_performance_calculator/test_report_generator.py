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

"""Unit tests for report_generator module."""

import pytest
import re
from awslabs.dynamodb_mcp_server.cost_performance_calculator.cost_model import (
    AccessPatternResult,
    CostModel,
    GSIResult,
    GSIWriteAmplification,
    TableResult,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    DataModel,
    GetItemAccessPattern,
    PutItemAccessPattern,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.report_generator import (
    _format_cost,
    _generate_padded_table,
    generate_report,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock


@pytest.fixture
def data_model():
    """Mock data model with a table and GSI."""
    data_model = MagicMock(spec=DataModel)
    ap = MagicMock(spec=PutItemAccessPattern)
    ap.pattern = 'create-order'
    ap.operation = 'PutItem'
    ap.table = 'orders'
    ap.rps = 50
    ap.gsi = None
    data_model.access_pattern_list = [ap]

    gsi = MagicMock()
    gsi.name = 'status-index'
    table = MagicMock()
    table.name = 'orders'
    table.gsi_list = [gsi]
    data_model.table_list = [table]
    return data_model


@pytest.fixture
def cost_model():
    """Cost model with table and GSI storage."""
    return CostModel(
        access_patterns=[
            AccessPatternResult(
                pattern='create-order',
                rcus=0.0,
                wcus=1.0,
                cost=82.35,
                gsi_write_amplification=[],
            )
        ],
        tables=[TableResult(table_name='orders', storage_gb=0.01, storage_cost=0.0025)],
        gsis=[
            GSIResult(
                gsi_name='status-index',
                table_name='orders',
                storage_gb=0.003,
                storage_cost=0.00075,
            )
        ],
    )


class TestGenerateReport:
    """Tests for generate_report function."""

    class TestReportStructure:
        """Tests for report structure."""

        def test_report_starts_with_header(self, data_model, cost_model):
            """Report starts with markdown header followed by disclaimer."""
            report = generate_report(data_model, cost_model)
            assert report.startswith('## Cost Report')
            assert '> **Disclaimer:**' in report

        def test_report_contains_access_patterns_section(self, data_model, cost_model):
            """Report contains read and write request costs section."""
            report = generate_report(data_model, cost_model)
            assert '### Read and Write Request Costs' in report

        def test_report_contains_storage_section(self, data_model, cost_model):
            """Report contains storage section."""
            report = generate_report(data_model, cost_model)
            assert '### Storage Costs' in report

        def test_report_contains_gsi_section_when_gsis_exist(self, data_model, cost_model):
            """Report contains GSI in storage section when GSIs exist."""
            report = generate_report(data_model, cost_model)
            assert re.search(r'\|\s*GSI\s*\|', report)

        def test_report_no_gsi_section_when_no_gsis(self):
            """Report does not contain GSI rows when no GSIs."""
            dm = MagicMock(spec=DataModel)
            ap = MagicMock(spec=GetItemAccessPattern)
            ap.pattern = 'get-user'
            ap.operation = 'GetItem'
            ap.table = 'users'
            ap.rps = 100
            ap.gsi = None
            dm.access_pattern_list = [ap]
            table = MagicMock()
            table.name = 'users'
            table.gsi_list = []
            dm.table_list = [table]

            cm = CostModel(
                access_patterns=[
                    AccessPatternResult(
                        pattern='get-user',
                        rcus=0.5,
                        wcus=0.0,
                        cost=16.47,
                        gsi_write_amplification=[],
                    )
                ],
                tables=[TableResult(table_name='users', storage_gb=0.002, storage_cost=0.0005)],
                gsis=[],
            )
            report = generate_report(dm, cm)
            storage_section = (
                report.split('### Storage Costs')[1] if '### Storage Costs' in report else ''
            )
            assert not re.search(r'\|\s*GSI\s*\|', storage_section)

        def test_report_costs_have_dollar_sign(self, data_model, cost_model):
            """All costs in report have dollar sign."""
            report = generate_report(data_model, cost_model)
            matches = re.findall(r'\$\d+\.\d{2}', report)
            assert len(matches) >= 2

    class TestAccessPatternsTable:
        """Tests for access patterns table."""

        def test_access_patterns_table_has_correct_columns(self, data_model, cost_model):
            """Access patterns table has Pattern, Operation, RPS, RRU / WRU, Monthly Cost columns."""
            report = generate_report(data_model, cost_model)
            assert re.search(
                r'\|\s*Pattern\s*\|\s*Operation\s*\|\s*RPS\s*\|\s*RRU / WRU\s*\|\s*Monthly Cost\s*\|',
                report,
            )

        def test_access_patterns_table_contains_pattern_name(self, data_model, cost_model):
            """Access patterns table contains pattern name."""
            report = generate_report(data_model, cost_model)
            assert 'create-order' in report

        def test_access_patterns_table_contains_operation(self, data_model, cost_model):
            """Access patterns table contains operation type."""
            report = generate_report(data_model, cost_model)
            assert 'PutItem' in report

    class TestStorageTable:
        """Tests for storage table (base tables and GSIs)."""

        def test_storage_table_has_correct_columns(self, data_model, cost_model):
            """Storage table has Resource, Type, Storage (GB), Monthly Cost columns."""
            report = generate_report(data_model, cost_model)
            assert re.search(
                r'\|\s*Resource\s*\|\s*Type\s*\|\s*Storage \(GB\)\s*\|\s*Monthly Cost\s*\|', report
            )

        def test_storage_table_contains_table_name(self, data_model, cost_model):
            """Storage table contains table name."""
            report = generate_report(data_model, cost_model)
            storage_section = report.split('### Storage')[1]
            assert 'orders' in storage_section

        def test_storage_table_contains_type_column(self, data_model, cost_model):
            """Storage table contains Type column with Table value."""
            report = generate_report(data_model, cost_model)
            storage_section = report.split('### Storage Costs')[1]
            assert re.search(r'\|\s*Table\s*\|', storage_section)

        def test_gsi_storage_has_correct_columns(self, data_model, cost_model):
            """GSI storage appears in the unified storage table with correct columns."""
            report = generate_report(data_model, cost_model)
            assert re.search(
                r'\|\s*Resource\s*\|\s*Type\s*\|\s*Storage \(GB\)\s*\|\s*Monthly Cost\s*\|', report
            )

        def test_gsi_storage_contains_gsi_name(self, data_model, cost_model):
            """Storage table contains GSI name with Type=GSI."""
            report = generate_report(data_model, cost_model)
            storage_section = report.split('### Storage Costs')[1]
            assert 'status-index' in storage_section
            assert re.search(r'\|\s*GSI\s*\|', storage_section)

    class TestMonetaryFormat:
        """Tests for _format_cost."""

        def test_format_cost_basic(self):
            """_format_cost formats as $X.XX."""
            assert _format_cost(10.5) == '$10.50'
            assert _format_cost(0) == '$0.00'
            assert _format_cost(123.456) == '$123.46'


class TestReportGeneratorProperties:
    """Property-based tests for report_generator."""

    @staticmethod
    def _make_data_model(num_patterns, num_tables):
        """Build a mock DataModel with N access patterns across M tables."""
        data_model = MagicMock(spec=DataModel)
        data_model.access_pattern_list = []
        for i in range(num_patterns):
            ap = MagicMock(spec=GetItemAccessPattern)
            ap.pattern = f'pattern-{i}'
            ap.operation = 'GetItem'
            ap.table = 'table-0'
            ap.rps = 100
            ap.gsi = None
            data_model.access_pattern_list.append(ap)

        data_model.table_list = []
        for i in range(num_tables):
            table = MagicMock()
            table.name = f'table-{i}'
            table.gsi_list = []
            data_model.table_list.append(table)
        return data_model

    @staticmethod
    def _make_cost_model(num_patterns, num_tables):
        """Build a CostModel matching _make_data_model."""
        return CostModel(
            access_patterns=[
                AccessPatternResult(
                    pattern=f'pattern-{i}',
                    rcus=0.5,
                    wcus=0.0,
                    cost=10.0,
                    gsi_write_amplification=[],
                )
                for i in range(num_patterns)
            ],
            tables=[
                TableResult(table_name=f'table-{i}', storage_gb=0.01, storage_cost=0.0025)
                for i in range(num_tables)
            ],
            gsis=[],
        )

    @given(
        num_patterns=st.integers(min_value=1, max_value=5),
        num_tables=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100)
    def test_report_contains_all_access_patterns(self, num_patterns, num_tables):
        """Property 5: Report Contains All Access Patterns.

        For any CostModel with N access patterns, the generated report SHALL
        contain exactly N rows in the access patterns table, one for each pattern.

        **Validates: Requirements 2.2**
        """
        dm = self._make_data_model(num_patterns, num_tables)
        cm = self._make_cost_model(num_patterns, num_tables)
        report = generate_report(dm, cm)

        for i in range(num_patterns):
            assert f'pattern-{i}' in report

        rw_section = report.split('### Read and Write Request Costs')[1]
        # Skip the summary table; only count detail rows after #### headers
        detail_parts = rw_section.split('#### ')[1:]
        data_rows = []
        for part in detail_parts:
            for line in part.split('\n'):
                if (
                    line.startswith('|')
                    and 'Pattern' not in line
                    and '---' not in line
                    and line.count('|') > 2
                ):
                    data_rows.append(line)
        assert len(data_rows) == num_patterns

    @given(num_tables=st.integers(min_value=1, max_value=5))
    @settings(max_examples=100)
    def test_report_contains_all_tables(self, num_tables):
        """Property 6: Report Contains All Tables.

        For any CostModel with M tables, the generated report SHALL contain
        exactly M rows in the storage table, one for each table.

        **Validates: Requirements 2.3**
        """
        dm = self._make_data_model(1, num_tables)
        cm = self._make_cost_model(1, num_tables)
        report = generate_report(dm, cm)
        storage_section = report.split('### Storage Costs')[1].split('### ')[0]

        for i in range(num_tables):
            assert f'table-{i}' in storage_section

        data_rows = [
            line for line in storage_section.split('\n') if re.search(r'\|\s*Table\s*\|', line)
        ]
        assert len(data_rows) == num_tables

    @given(
        cost=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_monetary_format_property(self, cost):
        """Property 7: Monetary Format.

        For any generated report, all monetary values SHALL match the pattern
        $X.XX (dollar sign, digits, decimal point, exactly 2 decimal digits).

        **Validates: Requirements 2.6**
        """
        formatted = _format_cost(cost)
        pattern = r'^\$\d+\.\d{2}$'
        assert re.match(pattern, formatted), f'Invalid format: {formatted}'


class TestReportGeneratorValidation:
    """Tests for input validation in report_generator."""

    def test_generate_report_with_none_data_model_raises_error(self):
        """Test generate_report raises ValueError when data_model is None."""
        cost_model = CostModel(access_patterns=[], tables=[], gsis=[])
        with pytest.raises(ValueError, match='data_model cannot be None'):
            generate_report(None, cost_model)

    def test_generate_report_with_none_cost_model_raises_error(self, data_model):
        """Test generate_report raises ValueError when cost_model is None."""
        with pytest.raises(ValueError, match='cost_model cannot be None'):
            generate_report(data_model, None)

    def test_generate_report_with_empty_access_patterns_raises_error(self):
        """Test generate_report raises ValueError when access_pattern_list is empty."""
        data_model = MagicMock(spec=DataModel)
        data_model.access_pattern_list = []
        cost_model = CostModel(access_patterns=[], tables=[], gsis=[])

        with pytest.raises(ValueError, match='access_pattern_list cannot be empty'):
            generate_report(data_model, cost_model)


class TestGSIWriteAmplification:
    """Tests for GSI write amplification coverage.

    Covers: _collect_gsi_write_amp_rows, _generate_gsi_section with write amp,
    the footnote in generate_report, and the empty-headers branch in
    _generate_padded_table.
    """

    @staticmethod
    def _make_write_amp_scenario():
        """Build a data model and cost model with GSI write amplification."""
        dm = MagicMock(spec=DataModel)

        # A PutItem that triggers write amplification on the GSI
        ap_write = MagicMock(spec=PutItemAccessPattern)
        ap_write.pattern = 'create-order'
        ap_write.operation = 'PutItem'
        ap_write.table = 'orders'
        ap_write.rps = 50
        ap_write.gsi = None

        # A GetItem that reads through the GSI
        ap_read = MagicMock(spec=GetItemAccessPattern)
        ap_read.pattern = 'query-by-status'
        ap_read.operation = 'Query'
        ap_read.table = 'orders'
        ap_read.rps = 200
        ap_read.gsi = 'status-index'

        dm.access_pattern_list = [ap_write, ap_read]

        gsi = MagicMock()
        gsi.name = 'status-index'
        table = MagicMock()
        table.name = 'orders'
        table.gsi_list = [gsi]
        dm.table_list = [table]

        cm = CostModel(
            access_patterns=[
                AccessPatternResult(
                    pattern='create-order',
                    rcus=0.0,
                    wcus=1.0,
                    cost=82.35,
                    gsi_write_amplification=[
                        GSIWriteAmplification(
                            gsi_name='status-index',
                            wcus=1.0,
                            cost=41.18,
                        ),
                    ],
                ),
                AccessPatternResult(
                    pattern='query-by-status',
                    rcus=0.5,
                    wcus=0.0,
                    cost=16.47,
                    gsi_write_amplification=[],
                ),
            ],
            tables=[TableResult(table_name='orders', storage_gb=0.01, storage_cost=0.0025)],
            gsis=[
                GSIResult(
                    gsi_name='status-index',
                    table_name='orders',
                    storage_gb=0.003,
                    storage_cost=0.00075,
                )
            ],
        )
        return dm, cm

    def test_write_amp_row_appears_in_report(self):
        """Write amplification row shows pattern with footnote marker."""
        dm, cm = self._make_write_amp_scenario()
        report = generate_report(dm, cm)
        assert 'create-order¹' in report

    def test_write_amp_footnote_present(self):
        """Report includes the GSI additional writes footnote."""
        dm, cm = self._make_write_amp_scenario()
        report = generate_report(dm, cm)
        assert '¹ **GSI additional writes** -' in report
        assert 'estimate assumes single writes only.' in report

    def test_write_amp_cost_in_gsi_section(self):
        """GSI section includes the write amplification cost."""
        dm, cm = self._make_write_amp_scenario()
        report = generate_report(dm, cm)
        assert '$41.18' in report

    def test_gsi_section_header_present(self):
        """GSI subsection header appears for the index."""
        dm, cm = self._make_write_amp_scenario()
        report = generate_report(dm, cm)
        assert '#### orders Table / status-index GSI' in report

    def test_gsi_total_cost_includes_reads_and_write_amp(self):
        """GSI cost line sums read cost + write amplification cost."""
        dm, cm = self._make_write_amp_scenario()
        report = generate_report(dm, cm)
        # GSI section: read cost 16.47 + write amp cost 41.18 = 57.65
        gsi_section = report.split('#### orders Table / status-index GSI')[1].split('####')[0]
        assert '**Monthly Cost:** $57.65' in gsi_section

    def test_generate_padded_table_empty_headers(self):
        """_generate_padded_table returns empty string for empty headers."""
        assert _generate_padded_table([], []) == ''
        assert _generate_padded_table([], [['a', 'b']]) == ''

    def test_write_amp_skips_unrelated_table_patterns(self):
        """Write amp collection skips patterns belonging to a different table."""
        dm = MagicMock(spec=DataModel)

        ap1 = MagicMock(spec=PutItemAccessPattern)
        ap1.pattern = 'write-orders'
        ap1.operation = 'PutItem'
        ap1.table = 'orders'
        ap1.rps = 10
        ap1.gsi = None

        ap2 = MagicMock(spec=PutItemAccessPattern)
        ap2.pattern = 'write-users'
        ap2.operation = 'PutItem'
        ap2.table = 'users'
        ap2.rps = 20
        ap2.gsi = None

        dm.access_pattern_list = [ap1, ap2]

        gsi = MagicMock()
        gsi.name = 'order-gsi'
        table_orders = MagicMock()
        table_orders.name = 'orders'
        table_orders.gsi_list = [gsi]
        table_users = MagicMock()
        table_users.name = 'users'
        table_users.gsi_list = []
        dm.table_list = [table_orders, table_users]

        cm = CostModel(
            access_patterns=[
                AccessPatternResult(
                    pattern='write-orders',
                    rcus=0.0,
                    wcus=1.0,
                    cost=10.0,
                    gsi_write_amplification=[
                        GSIWriteAmplification(gsi_name='order-gsi', wcus=1.0, cost=5.0),
                    ],
                ),
                AccessPatternResult(
                    pattern='write-users',
                    rcus=0.0,
                    wcus=1.0,
                    cost=20.0,
                    gsi_write_amplification=[],
                ),
            ],
            tables=[
                TableResult(table_name='orders', storage_gb=0.01, storage_cost=0.0025),
                TableResult(table_name='users', storage_gb=0.01, storage_cost=0.0025),
            ],
            gsis=[
                GSIResult(
                    gsi_name='order-gsi',
                    table_name='orders',
                    storage_gb=0.003,
                    storage_cost=0.00075,
                ),
            ],
        )

        report = generate_report(dm, cm)
        # write-users pattern should NOT appear with ¹ marker
        assert 'write-users¹' not in report
        # write-orders write amp should still be present
        assert 'write-orders¹' in report

    def test_padded_table_row_longer_than_headers(self):
        """_generate_padded_table handles rows with more cells than headers."""
        result = _generate_padded_table(['A'], [['x', 'extra']])
        # Extra cell is silently ignored; table still renders
        assert '| x |' in result
        assert 'extra' not in result

    def test_write_amp_non_matching_gsi_name_skipped(self):
        """Write amp entries for a different GSI are skipped."""
        dm = MagicMock(spec=DataModel)

        ap = MagicMock(spec=PutItemAccessPattern)
        ap.pattern = 'write-item'
        ap.operation = 'PutItem'
        ap.table = 'tbl'
        ap.rps = 10
        ap.gsi = None
        dm.access_pattern_list = [ap]

        gsi = MagicMock()
        gsi.name = 'my-gsi'
        table = MagicMock()
        table.name = 'tbl'
        table.gsi_list = [gsi]
        dm.table_list = [table]

        cm = CostModel(
            access_patterns=[
                AccessPatternResult(
                    pattern='write-item',
                    rcus=0.0,
                    wcus=1.0,
                    cost=10.0,
                    gsi_write_amplification=[
                        GSIWriteAmplification(gsi_name='other-gsi', wcus=0.5, cost=3.0),
                    ],
                ),
            ],
            tables=[TableResult(table_name='tbl', storage_gb=0.01, storage_cost=0.0025)],
            gsis=[
                GSIResult(
                    gsi_name='my-gsi', table_name='tbl', storage_gb=0.001, storage_cost=0.0003
                ),
            ],
        )

        report = generate_report(dm, cm)
        # The write amp for 'other-gsi' should not appear under 'my-gsi'
        assert '$3.00' not in report
        # No footnote since no matching write amp rendered
        assert '¹' not in report
