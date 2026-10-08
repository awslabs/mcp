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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, unquote, urljoin


# An unresolved cross-reference leaves an href with no filename, e.g. './.html#anchor'.
_EMPTY_TARGET_FILENAMES = frozenset({'.html', '.htm'})

# A URL fragment can only address a heading, so headings are what the anchor index records.
HEADING_TAGS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')


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


class UnreadablePageError(ValueError):
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


# Common content container selectors for AWS documentation
_CONTENT_SELECTORS = (
    'main',
    'article',
    '#main-content',
    '.main-content',
    '#content',
    '.content',
    "div[role='main']",
    '#awsdocs-content',
    '.awsui-article',
)

# Navigation elements that might be in the main content
_NAV_SELECTORS = (
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
)

# Tags to strip - these are elements we don't want in the output
_TAGS_TO_STRIP = [
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


def _clean_main_content(html: str):
    """Parse the page and return the cleaned element that markdownify will convert."""
    # First use BeautifulSoup to clean up the HTML
    from bs4 import BeautifulSoup

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Try to find the main content area using common selectors
    main_content = None
    for selector in _CONTENT_SELECTORS:
        content = soup.select_one(selector)
        if content:
            main_content = content
            break

    # If no main content found, use the body
    if not main_content:
        main_content = soup.body if soup.body else soup

    for selector in _NAV_SELECTORS:
        for element in main_content.select(selector):
            element.decompose()

    # strip= keeps a tag's text, so remove these outright
    for selector in ('script', 'style'):
        for element in main_content.select(selector):
            element.decompose()

    _unwrap_broken_links(main_content)

    return main_content


def _to_markdown(main_content) -> str:
    """Convert a cleaned content element to markdown.

    Raises:
        UnreadablePageError: the conversion produced nothing but whitespace
    """
    # Use markdownify on the cleaned HTML content
    content = markdownify.markdownify(
        str(main_content),
        heading_style=markdownify.ATX,
        autolinks=False,  # markdownify gates this on default_title; keep [url](url)
        default_title=False,  # would repeat the href as the title: [text](url "url")
        escape_asterisks=True,
        escape_underscores=True,
        newline_style='SPACES',
        strip=_TAGS_TO_STRIP,
    )

    if not content.strip():
        raise UnreadablePageError('Page failed to be simplified from HTML')

    return content


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
        raise UnreadablePageError('Empty HTML content')

    try:
        return _to_markdown(_clean_main_content(html))
    except UnreadablePageError:
        raise
    except Exception as e:
        raise UnreadablePageError(f'Error converting HTML to Markdown: {str(e)}') from e


def normalize_title(text: str) -> str:
    """Reduce heading text so a caller's wording matches the page's.

    Shared by both ways of naming a section: ``extract_sections_from_html`` compares the titles
    a caller passed against the page's headings, and ``heading_table`` records the same form so
    a title lookup and an anchor lookup agree on what a heading is called.
    """
    return ' '.join(text.strip().lower().split())


_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_MARKDOWN_EMPHASIS_RE = re.compile(r'[`*_\\]')


def heading_match_text(text: str) -> str:
    """Reduce heading text far enough that the HTML and the markdown forms agree.

    The conversion rewrites heading text in ways that are cosmetic but defeat equality:
    ``<code>`` becomes backticks, ``escape_asterisks`` adds backslashes, and the permalink
    ``<a>`` AWS puts inside CLI reference headings becomes a markdown link, so ``cp¶`` arrives
    as ``cp[¶](#cp "Permalink to this heading")``. Stripping link syntax and emphasis leaves a
    form both sides produce identically.
    """
    return normalize_title(_MARKDOWN_EMPHASIS_RE.sub('', _MARKDOWN_LINK_RE.sub(r'\1', text)))


# A heading inside one of these is not a section boundary, and the conversion does not render
# it as one either: markdownify indents it under the list or quote marker, or folds it into a
# table cell, so it never begins a line. Counting it would desynchronise the two sides.
NON_SECTION_ANCESTORS = frozenset({'blockquote', 'li', 'dd', 'dt', 'td', 'th', 'a'})


@dataclass(frozen=True)
class Heading:
    """One heading on a page, described for both ways of naming a section.

    Four views of one heading, all derived from the same source text:

    - ``text`` as the page writes it, which is what to show a caller who has to retype it.
    - ``title`` lowercased, for matching a title a caller supplied.
    - ``match_text`` stripped further, for finding this heading again after conversion.
    - ``anchors``, the ids and names that address it, for resolving a URL fragment.

    Holding them on one record is what keeps a title lookup and an anchor lookup resolving to
    the same heading, instead of each path discovering headings its own way.
    """

    level: int
    text: str
    title: str
    anchors: Tuple[str, ...]
    match_text: str

    @classmethod
    def of(cls, level: int, text: str, anchors: Tuple[str, ...] = ()) -> 'Heading':
        """Build from a heading's raw text, deriving every normalised form from it.

        The forms have to come from the same text or a heading becomes unfindable, so this is
        the only way one should be constructed.
        """
        return cls(
            level=level,
            text=' '.join(text.split()),
            title=normalize_title(text),
            anchors=anchors,
            match_text=heading_match_text(text),
        )


def heading_table(main_content) -> List[Heading]:
    """Describe every section heading on the page, in document order.

    One forward pass over the DOM. An anchor belongs to the first heading at or after it, which
    covers all three ways AWS pages carry one: on the heading itself, on a wrapper around the
    section, and on an empty ``<a name="...">`` just before the heading.

    Resolving each id on its own with ``find_next`` instead rescans the rest of the document
    per id, which is quadratic in the number of ids. On the Bedrock quotas page, whose table
    rows carry thousands of them, that measured 1.5s against 3ms here.

    Headings nested in a list, quote or table cell are skipped - see
    ``NON_SECTION_ANCESTORS``. Their anchors fall through to the next real section heading,
    which is where a reader following the link would land anyway.
    """
    headings: List[Heading] = []
    pending: List[str] = []

    for element in main_content.find_all(True):
        names = [
            value
            for value in (element.get('id'), element.get('name'))
            if isinstance(value, str) and value
        ]
        is_section_heading = element.name in HEADING_TAGS and not any(
            parent.name in NON_SECTION_ANCESTORS for parent in element.parents
        )
        if is_section_heading:
            # Anchors seen since the previous heading were waiting for this one.
            headings.append(
                Heading.of(int(element.name[1]), element.get_text(), (*pending, *names))
            )
            pending.clear()
        else:
            pending.extend(names)

    # Anchors left pending sit after the last heading and so address no section at all.
    return headings


@dataclass(frozen=True)
class SectionIndex:
    """The page's headings, and the lookups that turn a caller's name for one into its position.

    Position is the currency because markdownify drops the ``id`` off a heading, so by the time
    the page is markdown a fragment has nothing left to match against. Position survives the
    conversion: ``#automatically-created-buckets`` is heading 7 of 16, and heading 7 of the
    markdown is the same heading.

    Position also addresses a heading that a title cannot. Over 9 sampled pages carrying 267
    anchors, heading text repeated on 6 of the 9 - "Note", "Important" and "Warning" being the
    usual culprits - and markdown may render a heading differently from its source text, since
    a ``<code>`` element inside one comes back wrapped in backticks.
    """

    headings: Tuple[Heading, ...]

    @property
    def heading_count(self) -> int:
        """How many headings the page has, for checking the markdown still agrees."""
        return len(self.headings)

    def position_for_anchor(self, fragment: str) -> Optional[int]:
        """Return the heading position a URL fragment addresses, or None if it addresses none."""
        wanted = unquote(fragment).strip()
        for position, heading in enumerate(self.headings):
            if wanted in heading.anchors:
                return position
        return None

    def positions_for_title(self, title: str, levels: Optional[Sequence[int]] = None) -> List[int]:
        """Return every heading position matching a title, optionally limited to some levels.

        Returns a list because heading text is not unique on a page. ``levels`` exists because
        the level a title is allowed to match is a policy choice, not a property of the page:
        restricting to ``h2`` keeps a title like "Note" from matching a callout.
        """
        wanted = normalize_title(title)
        return [
            position
            for position, heading in enumerate(self.headings)
            if heading.title == wanted and (levels is None or heading.level in levels)
        ]


def extract_content_and_anchors(html: str) -> Tuple[str, SectionIndex]:
    """Convert HTML to markdown and record where each of its anchors points.

    One parse serves both, so honouring an anchor costs no extra pass over the page.

    Args:
        html: Raw HTML content to process

    Returns:
        The markdown, and the anchor index for resolving a fragment against it

    Raises:
        UnreadablePageError: the page carries no extractable content
    """
    if not html:
        raise UnreadablePageError('Empty HTML content')

    try:
        main_content = _clean_main_content(html)
        return _to_markdown(main_content), SectionIndex(tuple(heading_table(main_content)))
    except UnreadablePageError:
        raise
    except Exception as e:
        raise UnreadablePageError(f'Error converting HTML to Markdown: {str(e)}') from e


_ATX_HEADING_RE = re.compile(r'^(#{1,6})\s+(\S.*)$')

# How far ahead to look for the next expected heading. The conversion occasionally drops one
# outright, and without a little slack a single miss would strand every heading after it.
_ALIGNMENT_LOOKAHEAD = 4


def markdown_heading_candidates(markdown: str) -> List[Tuple[int, int]]:
    """List the (level, character offset) of every line that looks like an ATX heading.

    Candidates only. A '# ' inside a fenced code block is a comment in the sample rather than a
    heading, and this does not try to tell the difference - ``locate_headings`` does, by matching
    against the headings the page actually has.
    """
    offsets: List[Tuple[int, int]] = []
    position = 0

    for line in markdown.splitlines(keepends=True):
        if match := _ATX_HEADING_RE.match(line):
            offsets.append((len(match.group(1)), position))
        position += len(line)

    return offsets


def locate_headings(markdown: str, headings: Sequence[Heading]) -> List[Optional[int]]:
    """Locate each of the page's headings in the markdown, by character offset.

    Returns one entry per heading, in the same order, holding the offset of its heading line or
    None if it could not be found.

    Matching on level and text rather than counting is what makes this reliable. Counting
    assumes every candidate line is a heading and every heading becomes a candidate, and
    neither holds: a '# ' inside a code fence is not a heading, and the conversion sometimes
    drops one. Both break a count, and a broken count silently shifts every position after it.
    Text matching rejects a false candidate because it matches nothing the page has, and the
    lookahead steps over a heading the conversion dropped.
    """
    located: List[Optional[int]] = [None] * len(headings)
    cursor = 0

    for level, offset in markdown_heading_candidates(markdown):
        if cursor >= len(headings):
            break
        line_end = markdown.find('\n', offset)
        match = _ATX_HEADING_RE.match(
            markdown[offset : line_end if line_end != -1 else len(markdown)]
        )
        if match is None:
            continue
        candidate = heading_match_text(match.group(2))
        for ahead in range(min(_ALIGNMENT_LOOKAHEAD, len(headings) - cursor)):
            heading = headings[cursor + ahead]
            if heading.level == level and heading.match_text == candidate:
                located[cursor + ahead] = offset
                cursor += ahead + 1
                break

    return located


def section_markdown(markdown: str, index: SectionIndex, position: int) -> Optional[str]:
    """Return the markdown of one section, named by its heading's position.

    The position can come from either lookup on ``SectionIndex``, so an anchor and a title
    reach the same slicing. Returns None when the heading cannot be found in the markdown
    rather than raising, leaving the caller free to serve the whole page instead.

    Args:
        markdown: The page as markdown
        index: The section index built from the same page
        position: The heading's position in document order

    Returns:
        The section's markdown, or None if that heading could not be located
    """
    if not 0 <= position < index.heading_count:
        return None

    located = locate_headings(markdown, index.headings)
    start = located[position]
    if start is None:
        return None

    level = index.headings[position].level
    end = len(markdown)
    for later in range(position + 1, len(located)):
        # A sibling or an ancestor ends the section; a deeper heading belongs to it. AWS uses
        # h6 for both callouts and real subsections, so stopping at the next heading of any
        # level would cut a section off at its first "Note".
        if index.headings[later].level <= level and located[later] is not None:
            end = located[later]
            break

    return markdown[start:end].strip()


def anchor_section(markdown: str, index: SectionIndex, fragment: str) -> Optional[str]:
    """Return just the section a URL fragment addresses.

    Selecting the heading is all that is specific to anchors; the bounding is shared with any
    other way of naming a section. Returns None when the fragment resolves to nothing, so an
    anchor that misses is no worse for the agent than a read with no anchor at all.

    Args:
        markdown: The page as markdown
        index: The section index built from the same page
        fragment: The URL fragment, without its leading '#'

    Returns:
        The section's markdown, or None if the fragment addresses no heading
    """
    position = index.position_for_anchor(fragment)
    return None if position is None else section_markdown(markdown, index, position)


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


# A title names a section, and on these pages a section is an h2. Search returns the page's h2
# titles as its table of contents, so those are the titles a caller has to work with, and
# matching deeper levels would let a title like "Note" select a callout instead of a section.
TITLE_MATCH_LEVELS = (2,)


def extract_sections_from_html(html: str, section_titles: List[str]) -> str:
    """Extract the named sections from a page, as markdown.

    Resolves each title against the same heading table an anchor resolves against, so the two
    ways of naming a section cannot disagree about which heading a page has or where it ends.
    Titles are matched at the levels in ``TITLE_MATCH_LEVELS``.

    Args:
        html: Raw HTML content
        section_titles: Titles of the sections to return

    Returns:
        Markdown holding only the requested sections, in the order the page presents them

    Raises:
        UnreadablePageError: the page carries no readable content
        ValueError: none of the requested titles name a section on the page
    """
    if not html or not section_titles:
        return 'No content or section titles provided'

    from bs4 import BeautifulSoup

    if not has_readable_text(BeautifulSoup(html, 'html.parser')):
        raise UnreadablePageError('The page carries no readable content.')

    markdown, index = extract_content_and_anchors(html)

    # Page order, not the order the caller asked in, and deduplicated: one title can name
    # several headings, and two titles can name the same one.
    wanted_positions = sorted(
        {
            position
            for title in section_titles
            for position in index.positions_for_title(title, levels=TITLE_MATCH_LEVELS)
        }
    )
    found_titles = {
        title.strip()
        for title in section_titles
        if index.positions_for_title(title, levels=TITLE_MATCH_LEVELS)
    }

    if not found_titles:
        section_list = ', '.join(f'"{title}"' for title in section_titles)
        # As the page writes them, since the caller has to retype one of these to retry.
        available = [h.text for h in index.headings if h.level in TITLE_MATCH_LEVELS]
        if available:
            available_list = ', '.join(f'"{section}"' for section in available)
            error_msg = f'No matching sections were found: {section_list}. Available sections: {available_list}. Please retry with one or more of these sections or use the read_documentation tool instead to get the full document content.'
            raise ValueError(error_msg)
        else:
            error_msg = 'This document does not contain subsections. Please use the read_documentation tool instead to get the full document content.'
            raise ValueError(error_msg)

    sections = [section_markdown(markdown, index, position) for position in wanted_positions]
    result = '\n\n'.join(section for section in sections if section)

    if not result:
        # The titles named headings the page has, but none could be found again in the converted
        # markdown. That happens when malformed markup collapses the headings into one another,
        # so there is no section boundary left to cut on. Say so rather than return a header with
        # nothing under it.
        raise ValueError(
            'The requested sections could not be separated from the rest of the page. '
            'Please use the read_documentation tool instead to get the full document content.'
        )

    if len(found_titles) < len({title.strip() for title in section_titles}):
        missing_sections = [
            title.strip() for title in section_titles if title.strip() not in found_titles
        ]
        missing_list = ', '.join(f'"{title}"' for title in missing_sections)
        result += (
            f'\n\n> **Note**: The following requested sections were not found: {missing_list}'
        )

    return result


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
