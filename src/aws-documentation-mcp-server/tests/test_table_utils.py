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
"""Tests for large table handling in the AWS Documentation MCP Server."""

import json
from awslabs.aws_documentation_mcp_server.table_utils import (
    filter_table_rows,
    format_search_table_response,
    parse_html_tables,
)
from awslabs.aws_documentation_mcp_server.util import truncate_large_tables


class TestTruncateLargeTables:
    """Tests for truncate_large_tables function."""

    def test_small_table_unchanged(self):
        """Tables with fewer rows than max_rows are not truncated."""
        md = '| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |'
        result = truncate_large_tables(md, max_rows=20)
        assert result == md

    def test_large_table_truncated(self):
        """Tables exceeding max_rows get truncated with a hint."""
        header = '| Name | Value |'
        sep = '|---|---|'
        rows = [f'| row{i} | val{i} |' for i in range(30)]
        md = '\n'.join([header, sep] + rows)

        result = truncate_large_tables(
            md, url='https://example.com/page.html', max_rows=10, preview_rows=3
        )

        assert '| row0 | val0 |' in result
        assert '| row2 | val2 |' in result
        assert '| row3 | val3 |' not in result
        assert 'Table truncated (showing 3 of 30 rows)' in result
        assert 'search_table' in result
        assert 'https://example.com/page.html' in result

    def test_no_table_unchanged(self):
        """Content without tables passes through unchanged."""
        md = '# Hello\n\nSome text here.\n\n- item 1\n- item 2'
        result = truncate_large_tables(md)
        assert result == md

    def test_multiple_tables_only_large_truncated(self):
        """Only tables exceeding the threshold are truncated."""
        small_table = '| A |\n|---|\n| 1 |\n| 2 |'
        large_rows = [f'| row{i} |' for i in range(25)]
        large_table = '\n'.join(['| B |', '|---|'] + large_rows)
        md = small_table + '\n\nSome text\n\n' + large_table

        result = truncate_large_tables(md, max_rows=10, preview_rows=3)

        # Small table intact
        assert '| 1 |' in result
        assert '| 2 |' in result
        # Large table truncated
        assert 'Table truncated (showing 3 of 25 rows)' in result

    def test_empty_input(self):
        """Empty string returns empty string."""
        assert truncate_large_tables('') == ''
        assert truncate_large_tables(None) is None

    def test_large_table_truncated_no_url(self):
        """Truncated table hint works without a URL (no Example line)."""
        header = '| Name | Value |'
        sep = '|---|---|'
        rows = [f'| row{i} | val{i} |' for i in range(30)]
        md = '\n'.join([header, sep] + rows)

        result = truncate_large_tables(md, url='', max_rows=10, preview_rows=3)

        assert 'Table truncated (showing 3 of 30 rows)' in result
        assert 'search_table' in result
        assert 'Example:' not in result

    def test_incomplete_table_fewer_than_3_lines(self):
        """Table-like lines with fewer than 3 rows pass through unchanged."""
        md = '| just a pipe line |\n| another pipe line |'
        result = truncate_large_tables(md)
        assert result == md

    def test_single_pipe_line(self):
        """A single pipe-delimited line passes through unchanged."""
        md = 'Some text\n| solo pipe line |\nMore text'
        result = truncate_large_tables(md)
        assert result == md


class TestParseHtmlTables:
    """Tests for parse_html_tables function."""

    def _make_html(self, section_title, headers, rows):
        """Helper to build HTML with a section and table."""
        ths = ''.join(f'<th>{h}</th>' for h in headers)
        trs = ''
        for row in rows:
            tds = ''.join(f'<td>{c}</td>' for c in row)
            trs += f'<tr>{tds}</tr>'
        return f'<html><body><h2>{section_title}</h2><table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></body></html>'

    def test_basic_table_extraction(self):
        """Extracts a table from a section correctly."""
        html = self._make_html(
            'My Section',
            ['Name', 'Value'],
            [['foo', '100'], ['bar', '200']],
        )
        result = parse_html_tables(html, 'My Section')
        assert result is not None
        assert result['columns'] == ['Name', 'Value']
        assert len(result['rows']) == 2
        assert result['rows'][0] == {'Name': 'foo', 'Value': '100'}

    def test_section_not_found(self):
        """Returns error dict with available sections when section title doesn't match."""
        html = self._make_html('Other Section', ['A'], [['1']])
        result = parse_html_tables(html, 'Nonexistent Section')
        assert result is not None
        assert 'error' in result
        assert 'available_sections' in result
        assert 'Other Section' in result['available_sections']

    def test_no_table_in_section(self):
        """Returns error dict when section has no table."""
        html = '<html><body><h2>Empty Section</h2><p>No table here</p></body></html>'
        result = parse_html_tables(html, 'Empty Section')
        assert result is not None
        assert 'error' in result
        assert 'No table found' in result['error']

    def test_case_insensitive_section_match(self):
        """Section title matching is case-insensitive."""
        html = self._make_html('Amazon Bedrock Service Quotas', ['Q'], [['val']])
        result = parse_html_tables(html, 'amazon bedrock service quotas')
        assert result is not None
        assert len(result['rows']) == 1

    def test_rowspan_nesting(self):
        """Tables with rowspan produce nested output."""
        html = """<html><body><h2>Actions</h2><table>
        <thead><tr><th>Action</th><th>Level</th><th>Resource</th></tr></thead>
        <tbody>
            <tr><td rowspan="3">RunInstances</td><td rowspan="3">Write</td><td>image*</td></tr>
            <tr><td>instance*</td></tr>
            <tr><td>subnet*</td></tr>
            <tr><td>StopInstances</td><td>Write</td><td>instance*</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Actions')
        assert result is not None
        assert 'error' not in result
        assert 'parent_columns' in result
        assert 'Action' in result['parent_columns']
        assert 'Resource' in result['child_columns']
        # RunInstances should be one group with 3 child rows
        run_group = next(r for r in result['rows'] if r.get('Action') == 'RunInstances')
        assert len(run_group['rows']) == 3
        assert run_group['rows'][0]['Resource'] == 'image*'
        assert run_group['rows'][2]['Resource'] == 'subnet*'

    def test_link_preservation(self):
        """Links in cells are preserved as markdown."""
        html = """<html><body><h2>Quotas</h2><table>
        <thead><tr><th>Name</th><th>Adjustable</th></tr></thead>
        <tbody>
            <tr><td>Some quota</td><td><a href="https://console.aws.amazon.com/sq">Yes</a></td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Quotas')
        assert result is not None
        assert 'error' not in result
        assert '[Yes](https://console.aws.amazon.com/sq)' in result['rows'][0]['Adjustable']

    def test_no_section_title_searches_all_tables(self):
        """When section_title is None, returns all tables separately."""
        html = """<html><body>
        <h2>Section A</h2>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>foo</td></tr></tbody></table>
        <h2>Section B</h2>
        <table><thead><tr><th>Value</th></tr></thead><tbody><tr><td>bar</td></tr><tr><td>baz</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result is not None
        assert 'tables' in result
        assert len(result['tables']) == 2
        assert result['tables'][0]['columns'] == ['Name']
        assert result['tables'][1]['columns'] == ['Value']


class TestFilterTableRows:
    """Tests for filter_table_rows function."""

    def test_substring_match(self):
        """Matches rows containing all query words."""
        rows = [
            {'Name': 'Titan Text Embeddings V2 requests', 'Value': '6000'},
            {'Name': 'Claude 3 requests', 'Value': '1000'},
            {'Name': 'Titan Text Embeddings V2 tokens', 'Value': '300000'},
        ]
        matches = filter_table_rows(rows, 'Titan Text Embeddings V2')
        assert len(matches) == 2

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        rows = [{'Name': 'TITAN TEXT', 'Value': '100'}]
        matches = filter_table_rows(rows, 'titan text')
        assert len(matches) == 1

    def test_no_matches(self):
        """Returns empty list when nothing matches."""
        rows = [{'Name': 'foo', 'Value': 'bar'}]
        matches = filter_table_rows(rows, 'nonexistent')
        assert matches == []

    def test_matches_any_column(self):
        """Query can match in any column, not just Name."""
        rows = [{'Name': 'Some quota', 'Value': '6000', 'Region': 'us-east-1'}]
        matches = filter_table_rows(rows, 'us-east-1')
        assert len(matches) == 1

    def test_multi_word_and_logic(self):
        """All words must be present (AND logic), but can be in different columns."""
        rows = [
            {'Name': 'On-demand requests per minute for Claude 3 Sonnet', 'Value': '500'},
            {'Name': 'On-demand tokens per minute for Claude 3 Sonnet', 'Value': '1000000'},
            {'Name': 'On-demand requests per minute for Titan', 'Value': '6000'},
        ]
        matches = filter_table_rows(rows, 'Claude Sonnet requests')
        assert len(matches) == 1
        assert 'requests' in matches[0]['Name']

    def test_empty_query(self):
        """Empty query returns no matches."""
        rows = [{'Name': 'foo'}]
        assert filter_table_rows(rows, '') == []

    def test_nested_row_filtering(self):
        """Filtering works on nested rows (searches parent + child fields)."""
        rows = [
            {
                'Action': 'RunInstances',
                'Level': 'Write',
                'rows': [{'Resource': 'image*'}, {'Resource': 'instance*'}],
            },
            {'Action': 'StopInstances', 'Level': 'Write', 'rows': [{'Resource': 'instance*'}]},
        ]
        matches = filter_table_rows(rows, 'RunInstances')
        assert len(matches) == 1
        assert matches[0]['Action'] == 'RunInstances'

    def test_nested_row_filtering_child_value(self):
        """Filtering can match on child row values."""
        rows = [
            {
                'Action': 'RunInstances',
                'Level': 'Write',
                'rows': [{'Resource': 'image*'}, {'Resource': 'subnet*'}],
            },
            {'Action': 'StopInstances', 'Level': 'Write', 'rows': [{'Resource': 'instance*'}]},
        ]
        matches = filter_table_rows(rows, 'subnet')
        assert len(matches) == 1
        assert matches[0]['Action'] == 'RunInstances'

    def test_relevance_sorting(self):
        """Results are sorted by how many query words appear in the first column."""
        rows = [
            {'Name': 'Cross-region requests per minute for Claude 3 Sonnet', 'Value': '1000'},
            {'Name': 'On-demand requests per minute for Claude 3 Sonnet', 'Value': '500'},
            {'Name': 'Batch inference for Claude 3 Sonnet requests', 'Value': '100'},
        ]
        # "on-demand" differentiates - row with on-demand in Name should rank first
        matches = filter_table_rows(rows, 'on-demand Claude 3 Sonnet requests')
        assert len(matches) == 1  # only on-demand row has all words
        assert 'On-demand' in matches[0]['Name']

    def test_relevance_sorting_tiebreaker(self):
        """When scores tie, document order is preserved."""
        rows = [
            {'Name': 'Alpha requests per minute', 'Value': '100'},
            {'Name': 'Beta requests per minute', 'Value': '200'},
        ]
        matches = filter_table_rows(rows, 'requests per minute')
        assert len(matches) == 2
        # Both score equally, so document order preserved
        assert matches[0]['Name'] == 'Alpha requests per minute'
        assert matches[1]['Name'] == 'Beta requests per minute'


class TestFormatSearchTableResponse:
    """Tests for format_search_table_response function."""

    def test_valid_json_output(self):
        """Output is valid JSON with expected fields."""
        result = format_search_table_response(
            url='https://docs.aws.amazon.com/test.html',
            section_title='Test Section',
            query='foo',
            columns=['A', 'B'],
            matches=[{'A': '1', 'B': '2'}],
            total_rows=100,
            max_rows=20,
        )
        data = json.loads(result)
        assert data['url'] == 'https://docs.aws.amazon.com/test.html'
        assert data['query'] == 'foo'
        assert data['total_rows'] == 100
        assert data['matched_rows'] == 1
        assert data['showing'] == 1
        assert data['columns'] == ['A', 'B']
        assert len(data['rows']) == 1

    def test_respects_max_rows(self):
        """Output is capped at max_rows."""
        matches = [{'A': str(i)} for i in range(50)]
        result = format_search_table_response(
            url='u',
            section_title='s',
            query='q',
            columns=['A'],
            matches=matches,
            total_rows=100,
            max_rows=5,
        )
        data = json.loads(result)
        assert data['showing'] == 5
        assert len(data['rows']) == 5
        assert data['matched_rows'] == 50

    def test_zero_match_includes_hint(self):
        """Zero matches includes a hint field."""
        result = format_search_table_response(
            url='u',
            section_title='s',
            query='nothing',
            columns=['A'],
            matches=[],
            total_rows=100,
            max_rows=20,
        )
        data = json.loads(result)
        assert data['matched_rows'] == 0
        assert data['rows'] == []
        assert 'hint' in data


class TestMultiTableParsing:
    """Tests for multi-table behavior in parse_html_tables."""

    def test_section_with_multiple_tables(self):
        """Multiple tables in one section are returned separately."""
        html = """<html><body>
        <h2>Service quotas</h2>
        <h6>Amazon EC2</h6>
        <table><thead><tr><th>Name</th><th>Default</th></tr></thead>
        <tbody><tr><td>Instances</td><td>100</td></tr></tbody></table>
        <h6>VM Import/Export</h6>
        <table><thead><tr><th>Name</th><th>Limit</th></tr></thead>
        <tbody><tr><td>ImportImage tasks</td><td>20</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Service quotas')
        assert 'tables' in result
        assert len(result['tables']) == 2
        assert result['tables'][0]['columns'] == ['Name', 'Default']
        assert result['tables'][1]['columns'] == ['Name', 'Limit']

    def test_section_with_one_table_returns_flat(self):
        """Single table in section returns flat format (no 'tables' key)."""
        html = """<html><body>
        <h2>Quotas</h2>
        <table><thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>foo</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Quotas')
        assert 'tables' not in result
        assert 'rows' in result
        assert result['rows'][0] == {'Name': 'foo'}

    def test_multi_table_filter_finds_across_tables(self):
        """filter_table_rows works on rows from any table."""
        table1_rows = [{'Name': 'Instances', 'Default': '100'}]
        table2_rows = [{'Name': 'ImportImage tasks', 'Limit': '20'}]
        matches1 = filter_table_rows(table1_rows, 'ImportImage')
        matches2 = filter_table_rows(table2_rows, 'ImportImage')
        assert len(matches1) == 0
        assert len(matches2) == 1

    def test_no_section_returns_all_tables_separately(self):
        """When section_title is None, all page tables returned separately."""
        html = """<html><body>
        <h2>Section A</h2>
        <table><thead><tr><th>Col1</th></tr></thead><tbody><tr><td>a</td></tr></tbody></table>
        <h2>Section B</h2>
        <table><thead><tr><th>Col2</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert 'tables' in result
        assert len(result['tables']) == 2
        assert result['tables'][0]['columns'] == ['Col1']
        assert result['tables'][1]['columns'] == ['Col2']


class TestCellToText:
    """Tests for _cell_to_text edge cases via parse_html_tables."""

    def test_link_without_href(self):
        """A link tag with text but no href renders as plain text."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><a>plain link</a></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result['rows'][0]['Name'] == 'plain link'

    def test_nested_tag_with_link(self):
        """A nested tag (span/p) containing a link preserves the link as markdown."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><span><a href="/docs/foo">Foo Link</a></span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result['rows'][0]['Name'] == '[Foo Link](/docs/foo)'

    def test_nested_tag_with_link_no_href(self):
        """A nested tag containing a link with no href renders as plain text."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><span><a>Just Text</a></span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result['rows'][0]['Name'] == 'Just Text'

    def test_nested_tag_without_link(self):
        """A nested tag without any link renders as plain text."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th>Info</th></tr></thead>
        <tbody><tr><td><a href="/x">link</a></td><td><span>some info</span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result['rows'][0]['Info'] == 'some info'

    def test_mixed_text_and_link(self):
        """Cell with raw text nodes alongside a link preserves both."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>See <a href="/doc">docs</a> for details</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        cell_val = result['rows'][0]['Name']
        assert '[docs](/doc)' in cell_val
        assert 'See' in cell_val
        assert 'for details' in cell_val

    def test_sibling_tag_without_link_in_cell_with_link(self):
        """A cell with a link AND a sibling tag without links preserves both."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/x">Link</a><span>extra info</span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        cell_val = result['rows'][0]['Name']
        assert '[Link](/x)' in cell_val
        assert 'extra info' in cell_val

    def test_sibling_tag_without_link_empty_text(self):
        """A sibling tag with no text in a cell with a link is skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/x">Link</a><span></span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        cell_val = result['rows'][0]['Name']
        assert cell_val == '[Link](/x)'


class TestExtractTableDataEdgeCases:
    """Tests for _extract_table_data edge cases."""

    def test_table_without_thead(self):
        """Table without thead uses first row as headers."""
        html = """<html><body><h2>Sec</h2><table>
        <tbody>
        <tr><th>Name</th><th>Value</th></tr>
        <tr><td>foo</td><td>100</td></tr>
        <tr><td>bar</td><td>200</td></tr>
        </tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['columns'] == ['Name', 'Value']
        # First row is headers re-parsed as data (no thead/tbody split)
        assert result['rows'][0] == {'Name': 'Name', 'Value': 'Value'}
        assert result['rows'][1] == {'Name': 'foo', 'Value': '100'}
        assert result['rows'][2] == {'Name': 'bar', 'Value': '200'}

    def test_table_with_no_headers(self):
        """Table with no parseable headers returns error."""
        html = """<html><body><h2>Sec</h2><table>
        <tbody></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert 'error' in result
        assert 'No parseable table data' in result['error']

    def test_table_with_empty_rows(self):
        """Rows with no cells are skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr></tr><tr><td>valid</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert len(result['rows']) == 1
        assert result['rows'][0]['Name'] == 'valid'

    def test_table_with_no_data_rows(self):
        """Table with headers but no data rows returns None."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert 'error' in result

    def test_row_with_fewer_cells_than_headers(self):
        """Rows with fewer cells than headers are skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th><th>C</th></tr></thead>
        <tbody>
            <tr><td>1</td><td>2</td><td>3</td></tr>
            <tr><td>x</td></tr>
        </tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert len(result['rows']) == 1
        assert result['rows'][0] == {'A': '1', 'B': '2', 'C': '3'}


class TestFindAllTablesEdgeCases:
    """Tests for _find_all_tables edge cases."""

    def test_detected_section_uses_largest_table_heading(self):
        """detected_section is the heading above the largest table."""
        html = """<html><body>
        <h2>Small Section</h2>
        <table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        <h2>Big Section</h2>
        <table><thead><tr><th>B</th></tr></thead><tbody>
            <tr><td>x</td></tr><tr><td>y</td></tr><tr><td>z</td></tr>
        </tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result['detected_section'] == 'Big Section'

    def test_detected_section_no_heading(self):
        """detected_section falls back to '(all tables)' when no heading exists."""
        html = """<html><body>
        <table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result['detected_section'] == '(all tables)'

    def test_table_heading_uses_nearest_subheading(self):
        """Each table gets the nearest h3-h6 heading as table_heading."""
        html = """<html><body>
        <h2>Section</h2>
        <h3>Sub A</h3>
        <table><thead><tr><th>X</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        <h3>Sub B</h3>
        <table><thead><tr><th>Y</th></tr></thead><tbody><tr><td>2</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result['tables'][0]['table_heading'] == 'Sub A'
        assert result['tables'][1]['table_heading'] == 'Sub B'


class TestSectionBoundary:
    """Tests for section boundary detection in parse_html_tables."""

    def test_stops_at_next_h2(self):
        """Table search stops at the next h2 heading."""
        html = """<html><body>
        <h2>First</h2>
        <table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        <h2>Second</h2>
        <table><thead><tr><th>B</th></tr></thead><tbody><tr><td>2</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'First')
        assert 'tables' not in result
        assert result['columns'] == ['A']
        assert result['rows'][0] == {'A': '1'}

    def test_finds_table_nested_in_div(self):
        """Table nested in a div after the heading is still found."""
        html = """<html><body>
        <h2>My Section</h2>
        <div class="wrapper">
            <table><thead><tr><th>X</th></tr></thead><tbody><tr><td>val</td></tr></tbody></table>
        </div>
        </body></html>"""
        result = parse_html_tables(html, 'My Section')
        assert result['columns'] == ['X']
        assert result['rows'][0] == {'X': 'val'}

    def test_unparseable_table_in_section(self):
        """Section with a table that has no usable data returns error."""
        html = """<html><body>
        <h2>Bad Tables</h2>
        <table><tbody><tr></tr><tr></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Bad Tables')
        assert 'error' in result

    def test_no_tables_on_page_returns_none(self):
        """Page with no tables at all returns None when section is None."""
        html = """<html><body><h2>Just text</h2><p>No tables here</p></body></html>"""
        result = parse_html_tables(html, None)
        assert result is None

    def test_all_tables_unparseable_returns_none(self):
        """Page where all tables have no usable data returns None."""
        html = """<html><body>
        <h2>Section</h2>
        <table><tbody></tbody></table>
        <table><tbody><tr></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result is None
