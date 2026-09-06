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

import re
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from typing import Optional


def _safe_span(cell: Tag, attr: str) -> int:
    """Safely parse a colspan/rowspan attribute, returning at least 1."""
    try:
        val = int(str(cell.get(attr, '1')).strip() or '1')
    except (ValueError, TypeError):
        return 1
    return max(1, val)


def parse_html_tables(html: str, section_title: Optional[str] = None) -> Optional[dict]:
    """Extract tables from an HTML section as structured data.

    Matches section_title against h1/h2/h3 headings (case-insensitive).
    Collects all tables until the next heading at the same or higher level,
    including tables under deeper nested headings (e.g., h4 under an h3).

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

    # Find ALL tables until the next heading at the same or higher level
    if not isinstance(section_element, Tag):
        return None
    heading_level = int(section_element.name[1])
    # Collect tables paired with the last sub-heading seen before them (within section)
    tables: list[tuple[Tag, Optional[Tag]]] = []
    last_sub_heading: Optional[Tag] = None
    for sibling in section_element.find_next_siblings():
        if isinstance(sibling, Tag):
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if int(sibling.name[1]) <= heading_level:
                    break
                last_sub_heading = sibling
            if sibling.name == 'table':
                tables.append((sibling, last_sub_heading))
            else:
                for found in sibling.find_all('table'):
                    if isinstance(found, Tag):
                        tables.append((found, last_sub_heading))

    if not tables:
        return {
            'error': f'No table found in section "{section_title}"',
            'available_sections': available_sections,
        }

    # Parse all tables and merge rows
    parsed_tables = []
    for table, sub_heading in tables:
        table_data = _extract_table_data(table)
        if table_data and 'rows' in table_data:
            table_data['table_heading'] = sub_heading.get_text(strip=True) if sub_heading else None
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
    tables = [t for t in soup.find_all('table') if isinstance(t, Tag)]
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


def _parse_multi_row_thead(header_rows: list[Tag]) -> list[str]:
    """Parse a multi-row thead into a flat list of column headers.

    Handles rowspan (cells that span from an earlier row into the last row)
    and colspan (cells that span multiple columns).
    Uses the last row as the primary source, filling in rowspan cells from above.
    Dynamically expands the grid to accommodate rowspan reservations.
    """
    num_rows = len(header_rows)
    # Build grid dynamically — expand as cells are placed
    grid: list[list[str]] = [[] for _ in range(num_rows)]

    for row_idx, tr in enumerate(header_rows):
        col_idx = 0
        for cell in tr.find_all(['th', 'td']):
            if not isinstance(cell, Tag):
                continue
            # Skip columns already filled by rowspan from above
            while col_idx < len(grid[row_idx]) and grid[row_idx][col_idx]:
                col_idx += 1
            text = cell.get_text(strip=True)
            colspan = _safe_span(cell, 'colspan')
            rowspan = _safe_span(cell, 'rowspan')
            for r in range(rowspan):
                for c in range(colspan):
                    target_row = row_idx + r
                    target_col = col_idx + c
                    if target_row < num_rows:
                        while len(grid[target_row]) <= target_col:
                            grid[target_row].append('')
                        grid[target_row][target_col] = text
            col_idx += colspan

    num_cols = max((len(row) for row in grid), default=0)

    # Flatten: join parent and child names with " - " for each column
    headers: list[str] = []
    for col in range(num_cols):
        parts: list[str] = []
        seen: set[str] = set()
        for row in range(num_rows):
            val = grid[row][col] if col < len(grid[row]) else ''
            if val and val not in seen:
                parts.append(val)
                seen.add(val)
        headers.append(' - '.join(parts))
    return _deduplicate_headers(headers)


def _deduplicate_headers(headers: list[str]) -> list[str]:
    """De-duplicate header names by appending numeric suffixes to collisions."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            result.append(f'{h}_{seen[h]}')
        else:
            seen[h] = 1
            result.append(h)
    return result


def _extract_table_data(table: Tag) -> Optional[dict]:
    """Extract headers and rows from an HTML table element.

    Handles rowspan by detecting which columns are "parent" (have rowspan > 1)
    and nesting the non-rowspan columns as a 'rows' array under the parent fields.

    Preserves links as markdown: text with <a href> becomes [text](url).
    """
    headers: list[str] = []
    thead = table.find('thead')
    if thead and isinstance(thead, Tag):
        header_rows = [tr for tr in thead.find_all('tr') if isinstance(tr, Tag)]
        if len(header_rows) > 1:
            headers = _parse_multi_row_thead(header_rows)
        elif header_rows:
            for th in header_rows[0].find_all(['th', 'td']):
                if not isinstance(th, Tag):
                    continue
                colspan = _safe_span(th, 'colspan')
                text = th.get_text(strip=True)
                for i in range(colspan):
                    headers.append(text if i == 0 else f'{text}_{i + 1}')
            headers = _deduplicate_headers(headers)
    else:
        first_row = table.find('tr')
        if first_row and isinstance(first_row, Tag):
            for cell in first_row.find_all(['th', 'td']):
                if not isinstance(cell, Tag):
                    continue
                colspan = _safe_span(cell, 'colspan')
                text = cell.get_text(strip=True)
                for i in range(colspan):
                    headers.append(text if i == 0 else f'{text}_{i + 1}')
            headers = _deduplicate_headers(headers)

    if not headers:
        return None

    # Parse all rows, tracking rowspan state
    # Each active_rowspan entry: (value, remaining_rows, is_parent_eligible)
    # is_parent_eligible is True only when the original cell had colspan==1
    active_rowspans: dict[int, tuple[str, int, bool]] = {}
    parsed_rows = []

    tbody_elements = [tb for tb in table.find_all('tbody') if isinstance(tb, Tag)]
    if not tbody_elements:
        tbody_elements = [table]
    all_trs: list[Tag] = []
    for tbody in tbody_elements:
        all_trs.extend(tr for tr in tbody.find_all('tr') if isinstance(tr, Tag))

    for tr in all_trs:
        cells = [c for c in tr.find_all(['td', 'th']) if isinstance(c, Tag)]
        if not cells:
            continue

        row: dict[str, object] = {}
        rowspan_cols: set[int] = set()
        # Track whether this row physically starts a new rowspan block
        has_fresh_rowspan = False
        cell_idx = 0

        col_idx = 0
        while col_idx < len(headers):
            if col_idx in active_rowspans:
                value, remaining, is_parent = active_rowspans[col_idx]
                row[headers[col_idx]] = value
                if is_parent:
                    rowspan_cols.add(col_idx)
                if remaining <= 1:
                    del active_rowspans[col_idx]
                else:
                    active_rowspans[col_idx] = (value, remaining - 1, is_parent)
                col_idx += 1
            elif cell_idx < len(cells):
                cell = cells[cell_idx]
                value = _cell_to_text(cell)
                colspan = _safe_span(cell, 'colspan')
                rowspan = _safe_span(cell, 'rowspan')
                is_parent_eligible = rowspan > 1 and colspan == 1
                for span in range(colspan):
                    if col_idx + span < len(headers):
                        row[headers[col_idx + span]] = value
                        if rowspan > 1:
                            active_rowspans[col_idx + span] = (
                                value,
                                rowspan - 1,
                                is_parent_eligible,
                            )
                        if is_parent_eligible:
                            rowspan_cols.add(col_idx + span)
                            has_fresh_rowspan = True
                col_idx += colspan
                cell_idx += 1
            else:
                col_idx += 1

        if len(row) == len(headers):
            row['_rowspan_cols'] = rowspan_cols
            row['_starts_new_group'] = has_fresh_rowspan
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
            row.pop('_starts_new_group', None)
        return {'columns': headers, 'rows': parsed_rows}

    # Nested table — group by parent columns
    # Parent columns = union of rowspan columns across all group-starting rows
    parent_cols: set[int] = set()
    for row in parsed_rows:
        if row.get('_starts_new_group'):
            rowspan_set = row.get('_rowspan_cols')
            if rowspan_set and isinstance(rowspan_set, set):
                parent_cols.update(rowspan_set)

    parent_headers = [h for i, h in enumerate(headers) if i in parent_cols]
    child_headers = [h for i, h in enumerate(headers) if i not in parent_cols]

    # Group rows: a new group starts when a row physically begins a fresh rowspan block,
    # or when a row has no rowspan at all (a standalone flat row in a rowspan table).
    groups: list[dict[str, object]] = []
    current_group: dict[str, object] | None = None

    for row in parsed_rows:
        rowspan_set = row.get('_rowspan_cols')
        has_any_rowspan = bool(rowspan_set)
        starts_new = row.get('_starts_new_group') or not has_any_rowspan

        if starts_new or current_group is None:
            current_group = {h: row[h] for h in parent_headers}
            current_group['rows'] = []
            groups.append(current_group)

        child_row = {h: row[h] for h in child_headers if row.get(h)}
        if child_row:
            rows_list = current_group['rows']
            if isinstance(rows_list, list):
                rows_list.append(child_row)

    # Clean parsed_rows metadata
    for row in parsed_rows:
        row.pop('_rowspan_cols', None)
        row.pop('_starts_new_group', None)

    return {
        'columns': headers,
        'parent_columns': parent_headers,
        'child_columns': child_headers,
        'rows': groups,
    }


def _cell_to_text(cell: Tag) -> str:
    """Convert a table cell to text, preserving links as markdown.

    A cell like <td><a href="url">text</a></td> becomes "[text](url)".
    A cell with mixed content preserves links inline with surrounding prose.
    """
    # Check if cell contains any links
    links = cell.find_all('a')
    if not links:
        return cell.get_text(strip=True)

    # Build text with markdown links
    parts: list[str] = []
    _extract_with_links(cell, parts)
    return ' '.join(parts).strip()


def _extract_with_links(element: Tag, parts: list[str]) -> None:
    """Recursively extract text from an element, preserving links as markdown."""
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            if child.name == 'a':
                href = str(child.get('href', ''))
                text = child.get_text(strip=True)
                if href and text:
                    parts.append(f'[{text}]({href})')
                elif text:
                    parts.append(text)
            else:
                _extract_with_links(child, parts)


def filter_table_rows(rows: list[dict], query: str) -> list[dict]:
    """Filter table rows by matching ALL query words (case-insensitive) across cell values.

    Handles both flat rows (dict of column→value) and nested rows (dict with a 'rows' sub-array).
    For nested rows, searches across parent fields AND all child rows.

    Each query word must match a whole token in the row (exact match), or for words
    with 4+ characters, match as a prefix of a row token. This prevents '1' from
    matching inside '100', while allowing prefix searches on long compound identifiers
    (e.g., 'DeleteAutomatedReasoningPolicy' matches 'DeleteAutomatedReasoningPolicyBuildWorkflow').

    Results are sorted by relevance: rows with more query words in the first column
    (typically the Name field) rank higher.

    Args:
        rows: List of row dicts (flat or nested)
        query: Search term (multiple words are ANDed together)

    Returns:
        List of matching rows, sorted by relevance
    """
    words = _tokenize(query.lower())
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

        row_tokens = set(_tokenize(row_text))
        if all(_word_matches(word, row_tokens) for word in words):
            matches.append(row)

    # Sort by relevance: count query words in the first column value
    def relevance(row):
        first_val = str(list(row.values())[0]).lower()
        first_tokens = set(_tokenize(first_val))
        return sum(1 for w in words if _word_matches(w, first_tokens))

    return sorted(matches, key=relevance, reverse=True)


def _word_matches(word: str, row_tokens: set[str]) -> bool:
    """Check if a query word matches any token in the row.

    Exact match is always checked. For words with 4+ characters, also checks
    if the word is a prefix of any row token (enabling compound-identifier matching
    like 'DeleteAutomatedReasoningPolicy' matching 'DeleteAutomatedReasoningPolicyBuildWorkflow').
    """
    if word in row_tokens:
        return True
    if len(word) >= 4:
        return any(token.startswith(word) for token in row_tokens)
    return False


def _tokenize(text: str) -> list[str]:
    """Split text into searchable tokens.

    Splits on whitespace and punctuation boundaries, preserving hyphenated
    terms (e.g., 'us-east-1') and version numbers (e.g., 'v2') as single tokens.
    Also generates sub-tokens from hyphenated/dotted terms so that 'east' matches 'us-east-1'.
    Normalizes thousands separators so '6,000' and '6000' both match.
    """
    # Normalize thousands separators (e.g., '6,000' -> '6000')
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    tokens = re.findall(r'[a-z0-9]+(?:[-_.][a-z0-9]+)*', text)
    result = list(tokens)
    for token in tokens:
        if '-' in token or '.' in token or '_' in token:
            result.extend(re.split(r'[-_.]', token))
    return result
