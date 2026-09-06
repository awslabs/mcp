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

from awslabs.aws_documentation_mcp_server.table_utils import (
    filter_table_rows,
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
        assert truncate_large_tables(None) is None  # type: ignore[arg-type]

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

    def test_rowspan_with_flat_row_first(self):
        """Rowspan detection works when a flat row precedes the rowspan row."""
        html = """<html><body><h2>Actions</h2><table>
        <thead><tr><th>Action</th><th>Level</th><th>Resource</th></tr></thead>
        <tbody>
            <tr><td>DescribeInstances</td><td>Read</td><td>instance*</td></tr>
            <tr><td rowspan="2">RunInstances</td><td rowspan="2">Write</td><td>image*</td></tr>
            <tr><td>subnet*</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Actions')
        assert result is not None
        assert 'parent_columns' in result
        assert 'Action' in result['parent_columns']
        # Should have 2 groups: DescribeInstances and RunInstances
        assert len(result['rows']) == 2
        run_group = next(r for r in result['rows'] if r.get('Action') == 'RunInstances')
        assert len(run_group['rows']) == 2

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

    def test_no_partial_token_match(self):
        """'1' does not match inside '100' — requires whole token match."""
        rows = [
            {'Name': 'Quota A', 'Value': '100'},
            {'Name': 'Quota B', 'Value': '1'},
        ]
        matches = filter_table_rows(rows, '1')
        assert len(matches) == 1
        assert matches[0]['Value'] == '1'

    def test_hyphenated_term_matches_whole_and_parts(self):
        """'east' matches within 'us-east-1', and 'us-east-1' matches exactly."""
        rows = [
            {'Name': 'Region us-east-1', 'Value': '500'},
            {'Name': 'Region eu-west-1', 'Value': '100'},
        ]
        matches = filter_table_rows(rows, 'us-east-1')
        assert len(matches) == 1
        assert 'us-east-1' in matches[0]['Name']

        matches = filter_table_rows(rows, 'east')
        assert len(matches) == 1
        assert 'us-east-1' in matches[0]['Name']

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

    def test_relevance_sorting_ranks_by_first_column(self):
        """Row with more query words in Name column ranks higher."""
        rows = [
            {'Name': 'General quota', 'Description': 'Titan requests per minute limit'},
            {'Name': 'Titan requests per minute', 'Description': 'General quota limit'},
        ]
        matches = filter_table_rows(rows, 'Titan requests')
        assert len(matches) == 2
        # Second row has both query words in Name, first row has them in Description
        assert matches[0]['Name'] == 'Titan requests per minute'
        assert matches[1]['Name'] == 'General quota'

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

    def test_prefix_match_on_compound_identifiers(self):
        """A long query (4+ chars) matches as prefix of compound tokens."""
        rows = [
            {
                'Name': '(Automated Reasoning) DeleteAutomatedReasoningPolicy requests per second',
                'Default': 'Each supported Region: 5',
            },
            {
                'Name': '(Automated Reasoning) DeleteAutomatedReasoningPolicyBuildWorkflow requests per second',
                'Default': 'Each supported Region: 5',
            },
            {
                'Name': '(Automated Reasoning) DeleteAutomatedReasoningPolicyTestCase requests per second',
                'Default': 'Each supported Region: 5',
            },
            {
                'Name': '(Automated Reasoning) CreateAutomatedReasoningPolicy requests per second',
                'Default': 'Each supported Region: 5',
            },
        ]
        matches = filter_table_rows(rows, 'DeleteAutomatedReasoningPolicy')
        assert len(matches) == 3
        assert all('Delete' in m['Name'] for m in matches)

    def test_short_words_no_prefix_match(self):
        """Short words (< 4 chars) require exact token match, no prefix."""
        rows = [
            {'Name': 'Quota A', 'Value': '100'},
            {'Name': 'Quota B', 'Value': '10'},
            {'Name': 'Quota C', 'Value': '1'},
        ]
        matches = filter_table_rows(rows, '10')
        assert len(matches) == 1
        assert matches[0]['Value'] == '10'

    def test_thousands_separator_matching(self):
        """Numbers with thousands separators match plain integers and vice versa."""
        rows = [
            {'Name': 'Titan requests', 'Value': '6,000'},
            {'Name': 'Claude requests', 'Value': '500'},
            {'Name': 'Large quota', 'Value': '300,000'},
        ]
        # Plain integer matches comma-formatted value
        matches = filter_table_rows(rows, '6000')
        assert len(matches) == 1
        assert matches[0]['Name'] == 'Titan requests'

        # Comma-formatted query also matches
        matches = filter_table_rows(rows, '6,000')
        assert len(matches) == 1
        assert matches[0]['Name'] == 'Titan requests'

        matches = filter_table_rows(rows, '300000')
        assert len(matches) == 1
        assert matches[0]['Name'] == 'Large quota'

    def test_query_with_punctuation(self):
        """Query containing punctuation like colons and slashes is tokenized correctly."""
        rows = [
            {'Name': 'ec2:RunInstances', 'Description': 'Launch instances'},
            {'Name': 'ec2:StopInstances', 'Description': 'Stop instances'},
            {'Name': 's3:GetObject', 'Description': 'Get object'},
        ]
        matches = filter_table_rows(rows, 'ec2')
        assert len(matches) == 2

    def test_query_with_parentheses(self):
        """Query with parentheses still matches (parens stripped during tokenization)."""
        rows = [
            {
                'Name': '(Automated Reasoning) Policies per account',
                'Default': 'Each supported Region: 100',
            },
            {
                'Name': '(Data Automation) Max blueprints per account',
                'Default': 'Each supported Region: 350',
            },
        ]
        matches = filter_table_rows(rows, 'Automated Reasoning')
        assert len(matches) == 1
        assert 'Automated Reasoning' in matches[0]['Name']


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
        assert result is not None
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
        assert result is not None
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
        assert result is not None
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
        assert result is not None
        assert result['rows'][0]['Name'] == 'plain link'

    def test_nested_tag_with_link(self):
        """A nested tag (span/p) containing a link preserves the link as markdown."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><span><a href="/docs/foo">Foo Link</a></span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['rows'][0]['Name'] == '[Foo Link](/docs/foo)'

    def test_nested_tag_with_link_no_href(self):
        """A nested tag containing a link with no href renders as plain text."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><span><a>Just Text</a></span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['rows'][0]['Name'] == 'Just Text'

    def test_nested_tag_without_link(self):
        """A nested tag without any link renders as plain text."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th>Info</th></tr></thead>
        <tbody><tr><td><a href="/x">link</a></td><td><span>some info</span></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['rows'][0]['Info'] == 'some info'

    def test_mixed_text_and_link(self):
        """Cell with raw text nodes alongside a link preserves both."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>See <a href="/doc">docs</a> for details</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
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
        assert result is not None
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
        assert result is not None
        cell_val = result['rows'][0]['Name']
        assert cell_val == '[Link](/x)'

    def test_link_with_href_but_no_text(self):
        """A link tag with href but empty text is skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/x">visible</a><a href="/y"></a></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        cell_val = result['rows'][0]['Name']
        assert cell_val == '[visible](/x)'
        assert '/y' not in cell_val

    def test_nested_tag_link_with_href_but_no_text(self):
        """A nested tag containing a link with href but no text is skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/x">visible</a><div><a href="/empty"></a></div></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        cell_val = result['rows'][0]['Name']
        assert cell_val == '[visible](/x)'
        assert '/empty' not in cell_val

    def test_empty_text_node_between_links(self):
        """Empty whitespace-only text nodes between elements are skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>  <a href="/x">Link</a>  </td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        cell_val = result['rows'][0]['Name']
        assert cell_val == '[Link](/x)'


class TestTwoTierHeaders:
    """Tests for multi-row thead handling."""

    def test_two_tier_header_flattens(self):
        """Multi-row thead flattens parent and child into column names."""
        html = """<html><body><h2>Sec</h2><table>
        <thead>
            <tr><th rowspan="2">Name</th><th colspan="2">Limits</th></tr>
            <tr><th>Requests/min</th><th>Tokens/min</th></tr>
        </thead>
        <tbody>
            <tr><td>Titan</td><td>6000</td><td>300000</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert 'error' not in result
        assert result['columns'] == ['Name', 'Limits - Requests/min', 'Limits - Tokens/min']
        assert len(result['rows']) == 1
        assert result['rows'][0]['Name'] == 'Titan'
        assert result['rows'][0]['Limits - Requests/min'] == '6000'
        assert result['rows'][0]['Limits - Tokens/min'] == '300000'

    def test_single_row_thead_unchanged(self):
        """Single-row thead still works normally."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th></tr></thead>
        <tbody><tr><td>1</td><td>2</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['columns'] == ['A', 'B']
        assert result['rows'][0] == {'A': '1', 'B': '2'}


class TestMultipleTbody:
    """Tests for tables with multiple tbody elements."""

    def test_multiple_tbody_all_rows_parsed(self):
        """Rows from all tbody sections are included."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody>
            <tr><td>A</td><td>1</td></tr>
            <tr><td>B</td><td>2</td></tr>
        </tbody>
        <tbody>
            <tr><td>C</td><td>3</td></tr>
            <tr><td>D</td><td>4</td></tr>
        </tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 4
        assert result['rows'][0]['Name'] == 'A'
        assert result['rows'][2]['Name'] == 'C'
        assert result['rows'][3]['Name'] == 'D'

    def test_single_tbody_unchanged(self):
        """Single tbody still works normally."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>X</th></tr></thead>
        <tbody><tr><td>val</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 1


class TestColspanHandling:
    """Tests for colspan support in table parsing."""

    def test_colspan_in_data_row(self):
        """A data cell with colspan fills multiple columns."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th>Region 1</th><th>Region 2</th></tr></thead>
        <tbody>
            <tr><td>Normal</td><td>100</td><td>200</td></tr>
            <tr><td>Spanned</td><td colspan="2">All regions: 50</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 2
        assert result['rows'][0] == {'Name': 'Normal', 'Region 1': '100', 'Region 2': '200'}
        assert result['rows'][1] == {
            'Name': 'Spanned',
            'Region 1': 'All regions: 50',
            'Region 2': 'All regions: 50',
        }

    def test_colspan_in_header(self):
        """A header cell with colspan expands into multiple columns."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th colspan="2">Values</th></tr></thead>
        <tbody>
            <tr><td>Foo</td><td>10</td><td>20</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['columns'] == ['Name', 'Values', 'Values_2']
        assert result['rows'][0] == {'Name': 'Foo', 'Values': '10', 'Values_2': '20'}

    def test_colspan_with_rowspan(self):
        """Colspan and rowspan can coexist in the same table."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Action</th><th>Col A</th><th>Col B</th></tr></thead>
        <tbody>
            <tr><td rowspan="2">Run</td><td colspan="2">Shared value</td></tr>
            <tr><td>a</td><td>b</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        # rowspan=2 with colspan=1 on "Action" makes it a parent column
        assert 'parent_columns' in result
        assert 'Action' in result['parent_columns']
        assert len(result['rows']) == 1
        assert result['rows'][0]['Action'] == 'Run'
        assert len(result['rows'][0]['rows']) == 2

    def test_colspan_row_not_dropped(self):
        """Rows with colspan cells are not dropped due to cell count mismatch."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th><th>C</th><th>D</th></tr></thead>
        <tbody>
            <tr><td>1</td><td>2</td><td>3</td><td>4</td></tr>
            <tr><td colspan="4">This spans all columns</td></tr>
            <tr><td>5</td><td>6</td><td>7</td><td>8</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 3
        assert result['rows'][1]['A'] == 'This spans all columns'


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
        assert result is not None
        assert 'error' in result
        assert 'No parseable table data' in result['error']

    def test_table_with_empty_rows(self):
        """Rows with no cells are skipped."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody><tr></tr><tr><td>valid</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 1
        assert result['rows'][0]['Name'] == 'valid'

    def test_table_with_no_data_rows(self):
        """Table with headers but no data rows returns None."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th></tr></thead>
        <tbody></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
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
        assert result is not None
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
        assert result is not None
        assert result['detected_section'] == 'Big Section'

    def test_detected_section_no_heading(self):
        """detected_section falls back to '(all tables)' when no heading exists."""
        html = """<html><body>
        <table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, None)
        assert result is not None
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
        assert result is not None
        assert result['tables'][0]['table_heading'] == 'Sub A'
        assert result['tables'][1]['table_heading'] == 'Sub B'


class TestSectionBoundary:
    """Tests for section boundary detection in parse_html_tables."""

    def test_section_heading_with_no_siblings(self):
        """Section heading that is the last element has no siblings to iterate."""
        html = """<html><body>
        <h2>Lonely Section</h2>
        </body></html>"""
        result = parse_html_tables(html, 'Lonely Section')
        assert result is not None
        assert 'error' in result
        assert 'No table found' in result['error']

    def test_section_heading_only_non_tag_siblings(self):
        """Section heading followed only by text (non-Tag) siblings."""
        html = """<html><body>
        <h2>Text Only</h2>
        Just some text, no elements.
        </body></html>"""
        result = parse_html_tables(html, 'Text Only')
        assert result is not None
        assert 'error' in result
        assert 'No table found' in result['error']

    def test_stops_at_next_h2(self):
        """Table search stops at the next h2 heading."""
        html = """<html><body>
        <h2>First</h2>
        <table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
        <h2>Second</h2>
        <table><thead><tr><th>B</th></tr></thead><tbody><tr><td>2</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'First')
        assert result is not None
        assert 'tables' not in result
        assert result['columns'] == ['A']
        assert result['rows'][0] == {'A': '1'}

    def test_h3_stops_at_next_h3(self):
        """When targeting an h3, stops at the next h3 sibling."""
        html = """<html><body>
        <h2>Service quotas</h2>
        <h3>Amazon EC2</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>Instances</td></tr></tbody></table>
        <h3>VM Import/Export</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>ImportImage</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Amazon EC2')
        assert result is not None
        assert 'tables' not in result
        assert result['rows'][0] == {'Name': 'Instances'}

    def test_h3_includes_nested_h4(self):
        """When targeting an h3, includes tables under nested h4 headings."""
        html = """<html><body>
        <h2>Service quotas</h2>
        <h3>Amazon EC2</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>Main</td></tr></tbody></table>
        <h4>On-Demand limits</h4>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>OnDemand</td></tr></tbody></table>
        <h4>Spot limits</h4>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>Spot</td></tr></tbody></table>
        <h3>VM Import/Export</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>ImportImage</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Amazon EC2')
        assert result is not None
        assert 'tables' in result
        assert len(result['tables']) == 3

    def test_h2_includes_all_nested_h3_tables(self):
        """When targeting an h2, includes all h3 and h4 tables beneath it."""
        html = """<html><body>
        <h2>Service quotas</h2>
        <h3>Amazon EC2</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>EC2</td></tr></tbody></table>
        <h3>VM Import</h3>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>VM</td></tr></tbody></table>
        <h2>Endpoints</h2>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>endpoint</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Service quotas')
        assert result is not None
        assert 'tables' in result
        assert len(result['tables']) == 2

    def test_finds_table_nested_in_div(self):
        """Table nested in a div after the heading is still found."""
        html = """<html><body>
        <h2>My Section</h2>
        <div class="wrapper">
            <table><thead><tr><th>X</th></tr></thead><tbody><tr><td>val</td></tr></tbody></table>
        </div>
        </body></html>"""
        result = parse_html_tables(html, 'My Section')
        assert result is not None
        assert result['columns'] == ['X']
        assert result['rows'][0] == {'X': 'val'}

    def test_table_heading_does_not_cross_section_boundary(self):
        """A table with no sub-heading in its section gets None, not a heading from before."""
        html = """<html><body>
        <h3>Unrelated Earlier Subsection</h3>
        <table><thead><tr><th>Z</th></tr></thead><tbody><tr><td>old</td></tr></tbody></table>
        <h2>Service quotas</h2>
        <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>quota1</td></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Service quotas')
        assert result is not None
        # table_heading should be None (not "Unrelated Earlier Subsection")
        assert result.get('table_heading') is None

    def test_unparseable_table_in_section(self):
        """Section with a table that has no usable data returns error."""
        html = """<html><body>
        <h2>Bad Tables</h2>
        <table><tbody><tr></tr><tr></tr></tbody></table>
        </body></html>"""
        result = parse_html_tables(html, 'Bad Tables')
        assert result is not None
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


class TestDuplicateHeaders:
    """Tests for finding #1: duplicate column-header names."""

    def test_duplicate_headers_deduplicated(self):
        """Two columns sharing the same name get deduplicated with suffix."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Name</th><th>Value</th><th>Value</th></tr></thead>
        <tbody>
            <tr><td>A</td><td>10</td><td>20</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert 'error' not in result
        assert result['columns'] == ['Name', 'Value', 'Value_2']
        assert len(result['rows']) == 1
        assert result['rows'][0]['Name'] == 'A'
        assert result['rows'][0]['Value'] == '10'
        assert result['rows'][0]['Value_2'] == '20'

    def test_triple_duplicate_headers(self):
        """Three columns with the same name are all deduplicated."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Limit</th><th>Limit</th><th>Limit</th></tr></thead>
        <tbody>
            <tr><td>A</td><td>B</td><td>C</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert result['columns'] == ['Limit', 'Limit_2', 'Limit_3']
        assert result['rows'][0] == {'Limit': 'A', 'Limit_2': 'B', 'Limit_3': 'C'}


class TestSafeSpan:
    """Tests for finding #7: unguarded int() on colspan/rowspan."""

    def test_empty_colspan_treated_as_1(self):
        """colspan='' is treated as 1, not a crash."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th></tr></thead>
        <tbody><tr><td colspan="">val</td><td>other</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 1

    def test_invalid_colspan_treated_as_1(self):
        """colspan='auto' is treated as 1, not a crash."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th></tr></thead>
        <tbody><tr><td colspan="auto">val</td><td>other</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['rows']) == 1

    def test_zero_colspan_treated_as_1(self):
        """colspan='0' is clamped to 1, not causing column drop."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th colspan="0">Name</th><th>Value</th></tr></thead>
        <tbody><tr><td>A</td><td>100</td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        # colspan=0 clamped to 1, so 2 columns
        assert len(result['columns']) == 2


class TestCellToTextProsePreservation:
    """Tests for finding #4: descriptive prose around nested links is preserved."""

    def test_prose_around_nested_link_preserved(self):
        """Text surrounding a link inside a child tag is kept."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Description</th></tr></thead>
        <tbody><tr><td><p>Grants permission to <a href="/api">RunInstances</a> on the account</p></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        cell_val = result['rows'][0]['Description']
        assert 'Grants permission to' in cell_val
        assert '[RunInstances](/api)' in cell_val
        assert 'on the account' in cell_val

    def test_multiple_links_in_nested_tag(self):
        """Multiple links inside a <p> with surrounding prose all preserved."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>Info</th></tr></thead>
        <tbody><tr><td><p>See <a href="/a">doc A</a> and <a href="/b">doc B</a> for details</p></td></tr></tbody>
        </table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        cell_val = result['rows'][0]['Info']
        assert 'See' in cell_val
        assert '[doc A](/a)' in cell_val
        assert 'and' in cell_val
        assert '[doc B](/b)' in cell_val
        assert 'for details' in cell_val


class TestMultiRowTheadWidth:
    """Tests for finding #8: multi-row thead width from max across rows."""

    def test_wider_second_row(self):
        """When second thead row is wider than first, all columns are captured."""
        html = """<html><body><h2>Sec</h2><table>
        <thead>
            <tr><th rowspan="2">Name</th></tr>
            <tr><th>A</th><th>B</th></tr>
        </thead>
        <tbody>
            <tr><td>Foo</td><td>1</td><td>2</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        assert len(result['columns']) == 3


class TestColspanRowspanParentDetection:
    """Tests for finding #11: colspan+rowspan not treated as parent columns."""

    def test_colspan_rowspan_not_parent(self):
        """A cell with both colspan and rowspan does not make those columns parents."""
        html = """<html><body><h2>Sec</h2><table>
        <thead><tr><th>A</th><th>B</th><th>C</th></tr></thead>
        <tbody>
            <tr><td>x</td><td colspan="2" rowspan="2">BLOCK</td></tr>
            <tr><td>y</td></tr>
            <tr><td>z</td><td>m</td><td>n</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Sec')
        assert result is not None
        # Should be flat (no parent detection from colspan+rowspan cells)
        assert 'parent_columns' not in result
        assert len(result['rows']) == 3


class TestTruncateCodeFenceProtection:
    """Tests for findings #9 and #17: code blocks and separator validation."""

    def test_pipe_lines_inside_code_fence_not_truncated(self):
        """Pipe-leading lines inside a fenced code block are never truncated."""
        code_lines = [f'| item{i} | val{i} |' for i in range(30)]
        md = '```\n' + '\n'.join(code_lines) + '\n```'
        result = truncate_large_tables(md, max_rows=5)
        # All lines should be preserved (no truncation inside fence)
        assert 'Table truncated' not in result
        assert '| item29 | val29 |' in result

    def test_non_separator_pipe_block_not_truncated(self):
        """A block of pipe lines where line[1] is not a GFM separator is not truncated."""
        lines = ['| grammar rule A |', '| grammar rule B |'] + [f'| rule {i} |' for i in range(25)]
        md = '\n'.join(lines)
        result = truncate_large_tables(md, max_rows=5)
        # Not a real table (no separator row), so not truncated
        assert 'Table truncated' not in result
        assert '| rule 24 |' in result


class TestRowspanGroupBoundaries:
    """Tests for finding #3: rowspan group boundaries."""

    def test_same_parent_value_distinct_blocks(self):
        """Two adjacent rowspan blocks with same parent value are separate groups."""
        html = """<html><body><h2>Actions</h2><table>
        <thead><tr><th>Action</th><th>Level</th><th>Resource</th></tr></thead>
        <tbody>
            <tr><td rowspan="2">Write</td><td rowspan="2">Mutate</td><td>image</td></tr>
            <tr><td>instance</td></tr>
            <tr><td rowspan="2">Write</td><td rowspan="2">Mutate</td><td>subnet</td></tr>
            <tr><td>vpc</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Actions')
        assert result is not None
        assert 'parent_columns' in result
        # Should be 2 separate groups, not 1 merged group of 4
        write_groups = [g for g in result['rows'] if g.get('Action') == 'Write']
        assert len(write_groups) == 2
        assert len(write_groups[0]['rows']) == 2
        assert len(write_groups[1]['rows']) == 2
        assert write_groups[0]['rows'][0]['Resource'] == 'image'
        assert write_groups[1]['rows'][0]['Resource'] == 'subnet'

    def test_flat_row_between_rowspan_blocks(self):
        """A flat row in a rowspan table starts its own group."""
        html = """<html><body><h2>Actions</h2><table>
        <thead><tr><th>Action</th><th>Level</th><th>Resource</th></tr></thead>
        <tbody>
            <tr><td rowspan="2">RunInstances</td><td rowspan="2">Write</td><td>image*</td></tr>
            <tr><td>instance*</td></tr>
            <tr><td>DescribeInstances</td><td>Read</td><td>instance*</td></tr>
            <tr><td rowspan="2">StopInstances</td><td rowspan="2">Write</td><td>instance*</td></tr>
            <tr><td>network*</td></tr>
        </tbody></table></body></html>"""
        result = parse_html_tables(html, 'Actions')
        assert result is not None
        assert len(result['rows']) == 3
        assert result['rows'][0]['Action'] == 'RunInstances'
        assert len(result['rows'][0]['rows']) == 2
        assert result['rows'][1]['Action'] == 'DescribeInstances'
        assert len(result['rows'][1]['rows']) == 1
        assert result['rows'][2]['Action'] == 'StopInstances'
        assert len(result['rows'][2]['rows']) == 2


class TestMaxRowsCapping:
    """Tests for finding #15: max_rows capping is exercised."""

    def test_filter_returns_all_matches(self):
        """filter_table_rows returns all matching rows without capping."""
        rows = [{'Name': f'Quota {i}', 'Value': 'active'} for i in range(25)]
        matches = filter_table_rows(rows, 'active')
        assert len(matches) == 25

    def test_empty_rows_list(self):
        """Empty rows list returns empty matches."""
        assert filter_table_rows([], 'anything') == []

    def test_nested_group_with_empty_child_rows(self):
        """A nested group with empty child rows can still match on parent fields."""
        rows = [
            {'Action': 'RunInstances', 'Level': 'Write', 'rows': []},
            {'Action': 'StopInstances', 'Level': 'Write', 'rows': [{'Resource': 'instance*'}]},
        ]
        matches = filter_table_rows(rows, 'RunInstances')
        assert len(matches) == 1
        assert matches[0]['Action'] == 'RunInstances'
