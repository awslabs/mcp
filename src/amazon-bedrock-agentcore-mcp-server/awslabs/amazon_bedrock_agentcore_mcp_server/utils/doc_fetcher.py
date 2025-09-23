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

import html
import re
import urllib.request
from ..config import doc_config
from dataclasses import dataclass


# Example: "[Quickstart](https://strandsagents.com/.../index.md)"
_MD_LINK = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
_HTML_BLOCK = re.compile(r'(?is)<(script|style|noscript).*?>.*?</\1>')
_TAG = re.compile(r'(?s)<[^>]+>')
_TITLE_TAG = re.compile(r'(?is)<title[^>]*>(.*?)</title>')
_H1_TAG = re.compile(r'(?is)<h1[^>]*>(.*?)</h1>')
_META_OG = re.compile(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']')


@dataclass
class Page:
    """Represents a fetched and cleaned documentation page.

    Attributes:
        url: The source URL of the page
        title: Extracted or derived title of the page
        content: Cleaned text content of the page
    """

    url: str  # Source URL of the page
    title: str  # Page title (extracted or derived)
    content: str  # Cleaned text content


def _get(url: str) -> str:
    """Fetch content from a URL with proper headers and timeout.

    Args:
        url: The URL to fetch

    Returns:
        The decoded text content of the response

    Raises:
        urllib.error.URLError: If the request fails
    """
    req = urllib.request.Request(url, headers={'User-Agent': doc_config.user_agent})
    with urllib.request.urlopen(req, timeout=doc_config.timeout) as r:
        return r.read().decode('utf-8', errors='ignore')


def parse_llms_txt(url: str) -> list[tuple[str, str]]:
    """Parse an llms.txt file and extract document links.

    Args:
        url: URL of the llms.txt file to parse

    Returns:
        List of (title, url) tuples extracted from markdown links

    """
    txt = _get(url)
    return [
        (match.group(1).strip() or match.group(2).strip(), match.group(2).strip())
        for match in _MD_LINK.finditer(txt)
    ]


def _html_to_text(raw_html: str) -> str:
    """Convert HTML to plain text using stdlib only.

    Args:
        raw_html: Raw HTML content to convert

    Returns:
        Plain text with HTML tags removed and entities unescaped

    """
    stripped = _HTML_BLOCK.sub('', raw_html)  # remove script/style
    stripped = _TAG.sub(' ', stripped)  # drop tags
    stripped = html.unescape(stripped)
    # normalize whitespace, remove empty lines
    lines = [ln.strip() for ln in stripped.splitlines()]
    return '\n'.join(ln for ln in lines if ln)


def _extract_html_title(raw_html: str) -> str | None:
    """Extract title from HTML content using multiple strategies.

    Args:
        raw_html: Raw HTML content to extract title from

    Returns:
        Extracted title string, or None if no title found

    """
    match = _TITLE_TAG.search(raw_html)
    if match:
        return html.unescape(match.group(1)).strip()
    match = _META_OG.search(raw_html)
    if match:
        return html.unescape(match.group(1)).strip()
    match = _H1_TAG.search(raw_html)
    if match:
        inner = _TAG.sub(' ', match.group(1))
        return html.unescape(inner).strip()
    return None


def fetch_and_clean(page_url: str) -> Page:
    """Fetch a web page and return cleaned content.

    Args:
        page_url: URL of the page to fetch

    Returns:
        Page object with URL, title, and cleaned content

    """
    raw = _get(page_url)
    lower = raw.lower()
    if '<html' in lower or '<head' in lower or '<body' in lower:
        extracted_title = _extract_html_title(raw)
        content = _html_to_text(raw)
        title = extracted_title or page_url.rsplit('/', 1)[-1] or page_url
        return Page(url=page_url, title=title, content=content)
    else:
        title = page_url.rsplit('/', 1)[-1] or page_url
        return Page(url=page_url, title=title, content=raw)
