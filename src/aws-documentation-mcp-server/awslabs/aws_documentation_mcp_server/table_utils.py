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
"""Table parsing and filtering utilities for AWS Documentation MCP Server."""

import json
from bs4 import BeautifulSoup, Tag
from typing import Optional


def parse_html_tables(html: str, section_title: Optional[str] = None) -> Optional[dict]:
    """Extract a table from an HTML section as structured data.

    Args:
        html: Raw HTML content of the page
        section_title: The section heading containing the target table.
            If None, searches all tables on the page.

    Returns:
        Dict with 'columns' and 'rows' keys on success.
        Dict with 'error' and 'available_sections' keys if section not found.
        None if no table exists at all.
    """
    soup = BeautifulSoup(html, 'html.parser')

    if section_title is None:
        return _find_all_tables(soup)

    normalized_target = ' '.join(section_title.strip().lower().split())
    section_element = None
    available_sections = []

    for heading in soup.find_all(['h1', 'h2', 'h3']):
        heading_text = heading.get_text(strip=True)
        normalized = ' '.join(heading_text.lower().split())
        available_sections.append(heading_text)
        if normalized == normalized_target:
            section_element = heading

    if not section_element:
        return {
            'error': f'Section "{section_title}" not found',
            'available_sections': available_sections,
        }

    # Find ALL tables after this heading until the next same-level heading
    tables = []
    for sibling in section_element.find_next_siblings():
        if isinstance(sibling, Tag):
            if sibling.name in ['h1', 'h2'] and sibling != section_element:
                break
            if sibling.name == 'table':
                tables.append(sibling)
            else:
                for found in sibling.find_all('table'):
                    tables.append(found)

    if not tables:
        return {
            'error': f'No table found in section "{section_title}"',
            'available_sections': available_sections,
        }

    # Parse all tables and merge rows
    parsed_tables = []
    for table in tables:
        table_data = _extract_table_data(table)
        if table_data and 'rows' in table_data:
            # Find the nearest sub-heading for this table
            heading = table.find_previous(['h3', 'h4', 'h5', 'h6'])
            table_data['table_heading'] = heading.get_text(strip=True) if heading else None
            parsed_tables.append(table_data)

    if not parsed_tables:
        return {
            'error': f'No parseable table data in section "{section_title}"',
            'available_sections': available_sections,
        }

    # If only one table, return it directly (flat response)
    if len(parsed_tables) == 1:
        return parsed_tables[0]

    # Multiple tables — return them grouped
    return {'tables': parsed_tables}


def _find_all_tables(soup: BeautifulSoup) -> Optional[dict]:
    """Parse all tables on the page and return them separately."""
    tables = soup.find_all('table')
    if not tables:
        return None

    parsed_tables = []
    for table in tables:
        table_data = _extract_table_data(table)
        if table_data and 'rows' in table_data:
            # Find the nearest heading for this table
            heading = table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            table_data['table_heading'] = heading.get_text(strip=True) if heading else None
            parsed_tables.append(table_data)

    if not parsed_tables:
        return None

    # Use heading above the primary table for detected_section
    primary_table = max(tables, key=lambda t: len(t.find_all('tr')))
    heading = primary_table.find_previous(['h1', 'h2', 'h3'])

    return {
        'tables': parsed_tables,
        'detected_section': heading.get_text(strip=True) if heading else '(all tables)',
    }


def _extract_table_data(table: Tag) -> Optional[dict]:
    """Extract headers and rows from an HTML table element.

    Handles rowspan by detecting which columns are "parent" (have rowspan > 1)
    and nesting the non-rowspan columns as a 'rows' array under the parent fields.

    Preserves links as markdown: text with <a href> becomes [text](url).
    """
    headers = []
    thead = table.find('thead')
    if thead:
        for th in thead.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True))
    else:
        first_row = table.find('tr')
        if first_row:
            for cell in first_row.find_all(['th', 'td']):
                headers.append(cell.get_text(strip=True))

    if not headers:
        return None

    # Parse all rows, tracking rowspan state
    active_rowspans = {}  # {col_index: (value, remaining_count)}
    parsed_rows = []

    tbody = table.find('tbody') or table
    for tr in tbody.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue

        row = {}
        rowspan_cols = set()
        cell_idx = 0

        for col_idx in range(len(headers)):
            if col_idx in active_rowspans:
                value, remaining = active_rowspans[col_idx]
                row[headers[col_idx]] = value
                rowspan_cols.add(col_idx)
                if remaining <= 1:
                    del active_rowspans[col_idx]
                else:
                    active_rowspans[col_idx] = (value, remaining - 1)
            elif cell_idx < len(cells):
                cell = cells[cell_idx]
                value = _cell_to_text(cell)
                row[headers[col_idx]] = value
                rowspan = int(cell.get('rowspan', 1))
                if rowspan > 1:
                    active_rowspans[col_idx] = (value, rowspan - 1)
                    rowspan_cols.add(col_idx)
                cell_idx += 1

        if len(row) == len(headers):
            row['_rowspan_cols'] = rowspan_cols
            parsed_rows.append(row)

    if not parsed_rows:
        return None

    # Determine if this table uses rowspan nesting
    # A column is a "parent" if it has rowspan in the majority of grouped rows
    has_rowspan = any(row.get('_rowspan_cols') for row in parsed_rows)

    if not has_rowspan:
        # Flat table — return simple rows
        for row in parsed_rows:
            row.pop('_rowspan_cols', None)
        return {'columns': headers, 'rows': parsed_rows}

    # Nested table — group by parent columns
    # Parent columns = columns that had rowspan on their first appearance in a group
    # Detect parent columns from the first row that starts a group
    parent_cols = set()
    for row in parsed_rows:
        if row.get('_rowspan_cols'):
            parent_cols.update(row['_rowspan_cols'])
            break

    parent_headers = [h for i, h in enumerate(headers) if i in parent_cols]
    child_headers = [h for i, h in enumerate(headers) if i not in parent_cols]

    # Group rows: a new group starts when a row has fresh rowspan values
    groups = []
    current_group = None

    for row in parsed_rows:
        # A new group starts when the parent column values change
        parent_values = tuple(row.get(h, '') for h in parent_headers)

        if current_group is None or current_group['_key'] != parent_values:
            current_group = {h: row[h] for h in parent_headers}
            current_group['_key'] = parent_values
            current_group['rows'] = []
            groups.append(current_group)

        child_row = {h: row[h] for h in child_headers if row.get(h)}
        if child_row:
            current_group['rows'].append(child_row)

    # Clean up internal keys
    for group in groups:
        group.pop('_key', None)

    # Clean parsed_rows metadata
    for row in parsed_rows:
        row.pop('_rowspan_cols', None)

    return {
        'columns': headers,
        'parent_columns': parent_headers,
        'child_columns': child_headers,
        'rows': groups,
    }


def _cell_to_text(cell: Tag) -> str:
    """Convert a table cell to text, preserving links as markdown.

    A cell like <td><a href="url">text</a></td> becomes "[text](url)".
    A cell with mixed content preserves links inline.
    """
    # Check if cell contains any links
    links = cell.find_all('a')
    if not links:
        return cell.get_text(strip=True)

    # Build text with markdown links
    parts = []
    for child in cell.children:
        if isinstance(child, Tag) and child.name == 'a':
            href = child.get('href', '')
            text = child.get_text(strip=True)
            if href and text:
                # Make relative URLs absolute-ish (keep fragment refs as-is)
                parts.append(f'[{text}]({href})')
            elif text:
                parts.append(text)
        elif isinstance(child, Tag):
            # Recurse for nested tags that might contain links
            inner_links = child.find_all('a')
            if inner_links:
                for a in inner_links:
                    href = a.get('href', '')
                    text = a.get_text(strip=True)
                    if href and text:
                        parts.append(f'[{text}]({href})')
                    elif text:
                        parts.append(text)
            else:
                text = child.get_text(strip=True)
                if text:
                    parts.append(text)
        else:
            text = str(child).strip()
            if text:
                parts.append(text)

    return ' '.join(parts).strip()


def filter_table_rows(rows: list[dict], query: str) -> list[dict]:
    """Filter table rows by matching ALL query words (case-insensitive) across cell values.

    Handles both flat rows (dict of column→value) and nested rows (dict with a 'rows' sub-array).
    For nested rows, searches across parent fields AND all child rows.

    Results are sorted by relevance: rows with more query words in the first column
    (typically the Name field) rank higher.

    Args:
        rows: List of row dicts (flat or nested)
        query: Search term (multiple words are ANDed together)

    Returns:
        List of matching rows, sorted by relevance
    """
    words = query.lower().split()
    if not words:
        return []

    matches = []
    for row in rows:
        # Build searchable text from all values in the row
        if 'rows' in row and isinstance(row['rows'], list):
            # Nested format: include parent fields + all child row values
            parts = [str(v) for k, v in row.items() if k != 'rows']
            for child in row['rows']:
                parts.extend(str(v) for v in child.values())
            row_text = ' '.join(parts).lower()
        else:
            # Flat format
            row_text = ' '.join(str(v) for v in row.values()).lower()

        if all(word in row_text for word in words):
            matches.append(row)

    # Sort by relevance: count query words in the first column value
    def relevance(row):
        first_val = str(list(row.values())[0]).lower()
        return sum(1 for w in words if w in first_val)

    return sorted(matches, key=relevance, reverse=True)


def format_search_table_response(
    url: str,
    section_title: str,
    query: str,
    columns: list[str],
    matches: list[dict],
    total_rows: int,
    max_rows: int,
) -> str:
    """Format filtered table results as a JSON string."""
    response = {
        'url': url,
        'section_title': section_title,
        'query': query,
        'total_rows': total_rows,
        'matched_rows': len(matches),
        'showing': min(len(matches), max_rows),
        'columns': columns,
        'rows': matches[:max_rows],
    }
    if not matches:
        response['hint'] = (
            'No rows matched all query words. Try fewer or broader terms, '
            'or check spelling. Each word must appear somewhere in the row.'
        )
    return json.dumps(response, indent=2)
