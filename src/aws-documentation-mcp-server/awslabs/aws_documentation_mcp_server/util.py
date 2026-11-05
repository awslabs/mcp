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
"""Utility functions for AWS Documentation MCP Server."""

import httpx
import markdownify
import re
from awslabs.aws_documentation_mcp_server.models import RecommendationResult
from dataclasses import dataclass, field
from mcp.server.mcpserver.exceptions import ToolError
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote_plus, urljoin, urlsplit, urlunsplit


# An unresolved cross-reference leaves an href with no filename, e.g. './.html#anchor'.
_EMPTY_TARGET_FILENAMES = frozenset({'.html', '.htm'})


def has_empty_link_target(href: str) -> bool:
    """Report whether an href points at a path with no filename."""
    path = href.split('#', 1)[0].split('?', 1)[0].strip()
    if not path:
        return False  # fragment-only link; resolves to the current page
    return path.rsplit('/', 1)[-1].casefold() in _EMPTY_TARGET_FILENAMES


def _unwrap_broken_links(root) -> None:
    """Replace links whose target has no filename with their own text."""
    for anchor in root.find_all('a'):
        href = anchor.get('href')
        if isinstance(href, str) and has_empty_link_target(href):
            anchor.unwrap()


class DocumentationToolError(ToolError, ValueError):
    """An anticipated failure whose message is meant for the caller.

    The MCP SDK forwards a ``ToolError``'s message to the client and withholds the text of any
    other exception, keeping crash details off the wire (python-sdk#3314). Every failure the read
    path raises deliberately already builds a message for the caller, so those messages have to
    travel as a ``ToolError`` to arrive at all.

    ``ValueError`` stays in the bases because that is what these paths raised before, and callers
    and tests catch it.
    """


class UnreadablePageError(DocumentationToolError):
    """Raised when a page carries no extractable content, only markup."""


def has_readable_text(soup) -> bool:
    """Report whether a parsed document has body text outside scripts and styles."""
    from bs4 import Comment

    body = soup.body or soup
    return any(
        text.strip()
        for text in body.find_all(string=True)
        # comments are markup; <noscript> prose can be nested several levels down
        if not isinstance(text, Comment)
        and text.find_parent(['script', 'style', 'noscript']) is None
    )


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content

    Raises:
        UnreadablePageError: the page carries no extractable content
    """
    if not html:
        raise UnreadablePageError('Empty HTML content.')

    try:
        # First use BeautifulSoup to clean up the HTML
        from bs4 import BeautifulSoup

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Try to find the main content area
        main_content = None

        # Common content container selectors for AWS documentation
        content_selectors = [
            'main',
            'article',
            '#main-content',
            '.main-content',
            '#content',
            '.content',
            "div[role='main']",
            '#awsdocs-content',
            '.awsui-article',
        ]

        # Try to find the main content using common selectors
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                main_content = content
                break

        # If no main content found, use the body
        if not main_content:
            main_content = soup.body if soup.body else soup

        # Remove navigation elements that might be in the main content
        nav_selectors = [
            'noscript',
            '.prev-next',
            '#main-col-footer',
            '.awsdocs-page-utilities',
            '#quick-feedback-yes',
            '#quick-feedback-no',
            '.page-loading-indicator',
            '#tools-panel',
            '.doc-cookie-banner',
            'awsdocs-copyright',
            'awsdocs-thumb-feedback',
        ]

        for selector in nav_selectors:
            for element in main_content.select(selector):
                element.decompose()

        # strip= keeps a tag's text, so remove these outright
        for selector in ('script', 'style'):
            for element in main_content.select(selector):
                element.decompose()

        _unwrap_broken_links(main_content)

        # Define tags to strip - these are elements we don't want in the output
        tags_to_strip = [
            'script',
            'style',
            'noscript',
            'meta',
            'link',
            'footer',
            'nav',
            'aside',
            'header',
            # AWS documentation specific elements
            'awsdocs-cookie-consent-container',
            'awsdocs-feedback-container',
            'awsdocs-page-header',
            'awsdocs-page-header-container',
            'awsdocs-filter-selector',
            'awsdocs-breadcrumb-container',
            'awsdocs-page-footer',
            'awsdocs-page-footer-container',
            'awsdocs-footer',
            'awsdocs-cookie-banner',
            # Common unnecessary elements
            'js-show-more-buttons',
            'js-show-more-text',
            'feedback-container',
            'feedback-section',
            'doc-feedback-container',
            'doc-feedback-section',
            'warning-container',
            'warning-section',
            'cookie-banner',
            'cookie-notice',
            'copyright-section',
            'legal-section',
            'terms-section',
        ]

        # Use markdownify on the cleaned HTML content
        content = markdownify.markdownify(
            str(main_content),
            heading_style=markdownify.ATX,
            autolinks=False,  # markdownify gates this on default_title; keep [url](url)
            default_title=False,  # would repeat the href as the title: [text](url "url")
            escape_asterisks=True,
            escape_underscores=True,
            newline_style='SPACES',
            strip=tags_to_strip,
        )

        if not content.strip():
            raise UnreadablePageError('Page failed to be simplified from HTML.')

        return content
    except UnreadablePageError:
        raise
    except Exception as e:
        raise UnreadablePageError(f'Error converting HTML to Markdown: {str(e)}.') from e


def is_html_content(page_raw: str, content_type: str) -> bool:
    """Determine if content is HTML.

    Args:
        page_raw: Raw page content
        content_type: Content-Type header

    Returns:
        True if content is HTML, False otherwise
    """
    return '<html' in page_raw[:100] or 'text/html' in content_type or not content_type


def url_matches_allowlist(url: str, allowed_domain_regexes: Sequence[str]) -> bool:
    """Return True if the URL's host matches an allowed domain regex (extension not checked)."""
    return any(re.match(pattern, url) for pattern in allowed_domain_regexes)


def enforce_redirect_allowlist(allowed_domain_regexes: Sequence[str]):
    """Build an httpx response event hook that rejects redirects to off-allowlist hosts.

    Without this, ``follow_redirects=True`` follows a 3xx from an allow-listed page to any
    host, including link-local metadata. The hook resolves each ``Location`` (including
    relative redirects) against the request URL and raises if the target is not allow-listed.
    """

    async def _hook(response: httpx.Response) -> None:
        if not response.is_redirect:
            return
        location = response.headers.get('location')
        if not location:
            return
        target = urljoin(str(response.request.url), location)
        if not url_matches_allowlist(target, allowed_domain_regexes):
            raise httpx.RequestError(
                f'Refusing to follow redirect to non-allowlisted URL: {target}',
                request=response.request,
            )

    return _hook


def format_documentation_result(url: str, content: str, start_index: int, max_length: int) -> str:
    """Format documentation result with pagination information.

    Args:
        url: Documentation URL
        content: Content to format
        start_index: Start index for pagination
        max_length: Maximum content length

    Returns:
        Formatted documentation result
    """
    original_length = len(content)

    if start_index >= original_length:
        return f'AWS Documentation from {url}:\n\n<e>No more content available.</e>'

    # Calculate the end index, ensuring we don't go beyond the content length
    end_index = min(start_index + max_length, original_length)
    truncated_content = content[start_index:end_index]

    if not truncated_content:
        return f'AWS Documentation from {url}:\n\n<e>No more content available.</e>'

    actual_content_length = len(truncated_content)
    remaining_content = original_length - (start_index + actual_content_length)

    result = f'AWS Documentation from {url}:\n\n{truncated_content}'

    # Only add the prompt to continue fetching if there is still remaining content
    if remaining_content > 0:
        next_start = start_index + actual_content_length
        result += f'\n\n<e>Content truncated. Call the read_documentation tool with start_index={next_start} to get more content.</e>'

    return result


# ATX headings; four or more leading spaces make an indented code block instead.
_MARKDOWN_HEADING = re.compile(r'^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$')


def _heading_text(title: str) -> str:
    """Reduce a Markdown heading title to the text a reader sees."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', title)  # links keep their text
    return ' '.join(re.sub(r'[*`\\\u00b6]', '', text).split())  # markers, escapes, pilcrow


@dataclass(frozen=True)
class _Heading:
    line: int
    level: int
    text: str


@dataclass(frozen=True)
class SectionSelection:
    """What read_sections returns for a page: the matched sections, or the page itself."""

    markdown: str
    whole_page: bool  # every title that matched named only the page's level-1 heading
    missing: List[str]
    page_titles: List[str] = field(default_factory=list)  # set only alongside sections

    @property
    def notes(self) -> str:
        """Notes on requested titles that matched no heading or were not returned as sections."""
        notes = ''
        if self.missing:
            missing_list = ', '.join(f'"{title}"' for title in self.missing)
            notes += (
                f'\n\n> **Note**: The following requested sections were not found: {missing_list}'
            )
        if self.page_titles:
            page_list = ', '.join(f'"{title}"' for title in self.page_titles)
            verb = 'names' if len(self.page_titles) == 1 else 'name'
            notes += (
                f'\n\n> **Note**: {page_list} also {verb} the whole page. Use the'
                ' read_documentation tool to read all of it.'
            )
        return notes


def _markdown_headings(lines: List[str]) -> List[_Heading]:
    """List the page's headings. Only the first level-1 heading counts as the page title."""
    headings = []
    in_code_block = False
    seen_title = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Track fenced code blocks — '#' lines inside them are not headings
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code_block = not in_code_block
        heading = None if in_code_block else _MARKDOWN_HEADING.match(line)
        if not heading:
            continue
        level = len(heading.group(1))
        # Converted HTML leaves a paragraph such as '# of hosts' unescaped, so a later
        # level-1 line is text
        if level == 1:
            if seen_title:
                continue
            seen_title = True
        headings.append(_Heading(i, level, _heading_text(heading.group(2))))
    return headings


def select_sections(markdown: str, section_titles: List[str]) -> SectionSelection:
    """Select the requested sections of a page, matching headings at any level.

    A title selects every heading below level 1 that carries it. A section runs until the next
    heading at the same or a higher level. When the titles that match name only the page's
    level-1 heading, the whole page is selected; otherwise a title that also names the page is
    reported in a note.

    Args:
        markdown: Markdown content of the whole page
        section_titles: List of section titles to extract

    Returns:
        The selected sections in page order, or the page when whole_page is set
    """
    if not markdown.strip():
        raise UnreadablePageError('The page carries no readable content.')

    if not section_titles:
        return SectionSelection('No content or section titles provided', False, [])

    lines = markdown.split('\n')
    headings = _markdown_headings(lines)

    # Normalize like page headings, so a title copied with its markup still matches
    requested = [(title.strip(), _heading_text(title).lower()) for title in section_titles]
    sections_for: Dict[str, List[_Heading]] = {}
    names_page: Dict[str, bool] = {}
    for _, key in requested:
        if key in sections_for:
            continue
        matches = [h for h in headings if key and h.text.lower() == key]
        sections_for[key] = [h for h in matches if h.level > 1]
        names_page[key] = any(h.level == 1 for h in matches)

    selected = {h.line for matched in sections_for.values() for h in matched}

    if not selected and not any(names_page.values()):
        section_list = ', '.join(f'"{title}"' for title in section_titles)
        # Level-6 headings are callout titles such as "Note" in converted HTML, not sections
        offered = [h for h in headings if 1 < h.level < 6 and h.text]
        top_level = min((h.level for h in offered), default=None)
        if top_level == 2:  # repeated h2 titles stay listed, as they always have
            available = [h.text for h in offered if h.level == 2]
        else:
            available = list(dict.fromkeys(h.text for h in offered if h.level == top_level))
        if available:
            available_list = ', '.join(f'"{section}"' for section in available)
            error_msg = f'No matching sections were found: {section_list}. Available sections: {available_list}. Please retry with one or more of these sections or use the read_documentation tool instead to get the full document content.'
            raise DocumentationToolError(error_msg)
        else:
            error_msg = 'This document does not contain subsections. Please use the read_documentation tool instead to get the full document content.'
            raise DocumentationToolError(error_msg)

    # One note entry per normalized title, spelled as first requested
    unmatched: Dict[str, str] = {}
    page_named: Dict[str, str] = {}
    for title, key in requested:
        if not sections_for[key] and not names_page[key]:
            unmatched.setdefault(key, title)
        elif names_page[key]:
            page_named.setdefault(key, title)
    missing = list(unmatched.values())

    if not selected:
        return SectionSelection(markdown, True, missing)

    page_titles = list(page_named.values())

    sections = []
    open_section = None  # (first line, level) of the section being collected
    for heading in headings:
        if heading.level == 1:
            continue
        if open_section is not None and heading.level <= open_section[1]:
            sections.append('\n'.join(lines[open_section[0] : heading.line]).strip())
            open_section = None
        # A selected heading nested in an open section is already part of it
        if open_section is None and heading.line in selected:
            open_section = (heading.line, heading.level)
    if open_section is not None:
        sections.append('\n'.join(lines[open_section[0] :]).strip())

    return SectionSelection('\n\n'.join(sections), False, missing, page_titles)


def truncate_large_tables(
    markdown: str, url: str = '', max_rows: int = 20, preview_rows: int = 5
) -> str:
    """Detect large markdown tables and truncate them with a search_table hint.

    Args:
        markdown: Markdown content that may contain large tables
        url: The source URL (used in the hint message)
        max_rows: Tables with more data rows than this get truncated
        preview_rows: Number of sample rows to keep

    Returns:
        Markdown with large tables truncated and a tool usage hint appended
    """
    if not markdown:
        return markdown

    lines = markdown.split('\n')
    result = []
    i = 0
    in_code_block = False

    while i < len(lines):
        stripped = lines[i].strip()
        # Track fenced code blocks — never truncate inside them
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code_block = not in_code_block
            result.append(lines[i])
            i += 1
            continue

        if in_code_block:
            result.append(lines[i])
            i += 1
            continue

        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1

            # Validate: must have >=3 lines and line[1] must be a GFM separator
            is_table = (
                len(table_lines) >= 3
                and re.fullmatch(r'\s*\|?[\s|:-]+\|?\s*', table_lines[1])
                and '-' in table_lines[1]
            )

            if is_table:
                header = table_lines[0]
                separator = table_lines[1]
                data_rows = table_lines[2:]

                if len(data_rows) > max_rows:
                    result.append(header)
                    result.append(separator)
                    for row in data_rows[:preview_rows]:
                        result.append(row)
                    hint = f'\n\nTable truncated (showing {preview_rows} of {len(data_rows)} rows). Use the `search_table` tool to find specific rows.'
                    if url:
                        hint += f'\n  Example: search_table(url="{url}", section_title="<section>", query="your search term")'
                    result.append(hint)
                else:
                    result.extend(table_lines)
            else:
                result.extend(table_lines)
        else:
            result.append(lines[i])
            i += 1

    return '\n'.join(result)


def to_html_page_url(url: str) -> Optional[str]:
    """Return the '.html' page URL for a documentation page given as '.html' or '.md'.

    Published Markdown links its sibling pages as relative '.md' files, often with a section
    fragment. Accepting those URLs lets agents follow links as published, without the read tools
    expanding every link to an absolute URL. Fetches still target the bare '.html' page: it
    negotiates Markdown or HTML, which search_table needs, and search results key their query
    IDs by the '.html' URL.

    Args:
        url: Documentation page URL, optionally with a query or fragment

    Returns:
        The '.html' page URL without query or fragment, or None when the path ends with
        neither '.html' nor '.md'
    """
    parts = urlsplit(url)._replace(query='', fragment='')
    path = parts.path.casefold()
    if path.endswith('.html'):
        return urlunsplit(parts)
    if path.endswith('.md'):
        return urlunsplit(parts._replace(path=parts.path[: -len('.md')] + '.html'))
    return None


def parse_recommendation_results(data: Dict[str, Any]) -> List[RecommendationResult]:
    """Parse recommendation API response into RecommendationResult objects.

    Args:
        data: Raw API response data

    Returns:
        List of recommendation results
    """
    results = []

    # Process journey recommendations (organized by intent)
    if 'journey' in data and 'items' in data['journey']:
        for intent_group in data['journey']['items']:
            intent = intent_group.get('intent', '')
            if 'urls' in intent_group:
                for url_item in intent_group['urls']:
                    # Add intent as part of the context
                    context = f'Intent: {intent}' if intent else None

                    results.append(
                        RecommendationResult(
                            url=url_item.get('url', ''),
                            title=url_item.get('assetTitle', ''),
                            context=context,
                        )
                    )

    # Process new content recommendations
    if 'new' in data and 'items' in data['new']:
        for item in data['new']['items']:
            # Add "New content" label to context
            date_created = item.get('dateCreated', '')
            context = f'New content added on {date_created}' if date_created else 'New content'

            results.append(
                RecommendationResult(
                    url=item.get('url', ''), title=item.get('assetTitle', ''), context=context
                )
            )

    # Process similar recommendations
    if 'similar' in data and 'items' in data['similar']:
        for item in data['similar']['items']:
            context = item.get('abstract') if 'abstract' in item else 'Similar content'

            results.append(
                RecommendationResult(
                    url=item.get('url', ''), title=item.get('assetTitle', ''), context=context
                )
            )

    return results


def add_search_intent_to_search_request(search_url: str, search_intent: str) -> str:
    """Adds the search_intent query parameter to the search_url if search_intent is a string.

    :param search_url: URL to be used for search_documentation tool call
    :type search_url: str
    :param search_intent: Intent derived and provided by LLM to MCP Server for user's search intent
    :type search_intent: str
    :return: search_url with search_intent query parameter added
    :rtype: str
    """
    if search_intent and search_intent != '':
        # Remove all whitespaces, including tabs and returns
        search_intent = ' '.join(f'{search_intent}'.split())
        if search_intent:
            encoded_search_intent = quote_plus(search_intent)
            search_url = f'{search_url}&search_intent={encoded_search_intent}'

    return search_url
