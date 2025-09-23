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

import re
from .doc_fetcher import Page


_WHITESPACE = re.compile(r'\s+')
_CODE_FENCE = re.compile(r'```.*?```', re.S)


def normalize(s: str) -> str:
    """Normalize whitespace in a string.

    Args:
        s: Input string to normalize

    Returns:
        String with collapsed whitespace and trimmed edges
    """
    return _WHITESPACE.sub(' ', s).strip()


def title_from_url(url: str) -> str:
    """Generate a human-readable title from a URL path.

    Args:
        url: URL to extract title from

    Returns:
        Formatted title derived from the URL path

    Note:
        Removes 'index.*' files, converts hyphens/underscores to spaces,
        and applies title case. Falls back to 'Documentation' if no path.
    """
    path = url.split('://', 1)[-1]
    parts = [p for p in path.split('/') if p]
    # remove trailing index.*
    if parts and parts[-1].startswith('index.'):
        parts = parts[:-1]
    slug = parts[-1] if parts else path
    slug = slug.replace('-', ' ').replace('_', ' ').strip()
    return slug.title() or 'Documentation'


def format_display_title(url: str, extracted: str | None, url_titles: dict[str, str]) -> str:
    """Determine the best display title for a document.

    Args:
        url: Document URL
        extracted: Title extracted from document content (if any)
        url_titles: Mapping of URLs to curated titles from llms.txt

    Returns:
        The best available title for display purposes

    Priority:
        1. Curated title from llms.txt (highest priority)
        2. URL-derived title if extracted title is missing/generic
        3. Normalized extracted title otherwise

    """
    # Fast path: check curated first (most common case)
    curated = url_titles.get(url)
    if curated:
        return normalize(curated)

    # No extracted title or it's generic - use URL slug
    if not extracted:
        return title_from_url(url)

    t = extracted.strip()
    if not t or t.lower() in {'index', 'index.md'} or t.endswith('.md'):
        return title_from_url(url)
    return normalize(t)


def index_title_variants(display_title: str, url: str) -> str:
    """Generate searchable title variants for indexing.

    Args:
        display_title: The main display title
        url: Document URL for additional context

    Returns:
        Space-separated string of title variants for search indexing

    """
    base = display_title
    # hyphen/underscore variants from URL slug
    slug = title_from_url(url)

    # numeric-to-word '2' -> 'to' for cases like Agent2Agent
    variant = re.sub(r'(?i)(\w)2(\w)', r'\1 to \2', base)
    # collapse whitespace
    base = normalize(base)
    slug = normalize(slug)
    variant = normalize(variant)

    # Build a minimal distinct set: avoid obvious duplicates like "Agent Loop" twice
    variants = []
    for v in (base, variant, slug):
        if v and v.lower() not in {x.lower() for x in variants}:
            variants.append(v)

    return ' '.join(variants)


def normalize_for_comparison(string: str) -> str:
    """Normalize string for case-insensitive comparison.

    Args:
        string: Input string to normalize

    Returns:
        Lowercase string with only alphanumeric characters and spaces

    Note:
        Removes punctuation and normalizes whitespace for reliable comparison.
    """
    string_lower = string.lower()
    processed_string = re.sub(r'[^a-z0-9 ]+', ' ', string_lower)
    return _WHITESPACE.sub(' ', processed_string).strip()


def make_snippet(page: Page | None, display_title: str, max_chars: int = 300) -> str:
    """Create a contextual snippet from page content.

    Args:
        page: Page object with content attribute (or None)
        display_title: Title to use as fallback
        max_chars: Maximum length of the snippet

    Returns:
        Contextual snippet text, truncated with ellipsis if needed

    """
    if not page or not page.content:
        return display_title

    text = page.content.strip()
    # Remove fenced code blocks
    text = _CODE_FENCE.sub('', text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Drop a first line that looks like a title or a Markdown heading
    if lines:
        first = lines[0]
        if first.startswith('#'):
            lines = lines[1:]
        else:
            if normalize_for_comparison(first) == normalize_for_comparison(
                display_title
            ) or normalize_for_comparison(first).startswith(
                normalize_for_comparison(display_title)
            ):
                lines = lines[1:]

    # Collect first meaningful paragraph: skip headings/TOC bullets
    paras: list[str] = []
    buf: list[str] = []

    def is_heading_or_toc(line: str) -> bool:
        """Check if a line is a heading or table of contents entry.

        Args:
            line: Text line to check

        Returns:
            True if line appears to be a heading or TOC entry
        """
        no_leading_space_line = line.lstrip()
        return (
            no_leading_space_line.startswith('#')  # Markdown headers
            or no_leading_space_line.startswith(('-', '*'))  # Bullet points
            # Numbered lists
            or re.match(r'^\d+\.', no_leading_space_line) is not None
        )

    for line in lines:
        if is_heading_or_toc(line):
            if buf:
                break
            continue
        buf.append(line)
        # stop when we have a decent paragraph
        if len(' '.join(buf)) >= 120 or line.endswith('.'):
            paras.append(' '.join(buf))
            buf = []
            break

    if not paras and buf:
        paras.append(' '.join(buf))

    snippet = paras[0] if paras else display_title
    snippet = ' '.join(snippet.split())
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 1].rstrip() + '…'
    return snippet
