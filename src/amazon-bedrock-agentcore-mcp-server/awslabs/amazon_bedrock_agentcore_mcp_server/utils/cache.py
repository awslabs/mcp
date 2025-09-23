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

from ..config import doc_config
from . import doc_fetcher, indexer, text_processor
from typing import Dict


# Global state
_INDEX: indexer.IndexSearch | None = None
# url -> Page (None if not fetched yet)
_URL_CACHE: Dict[str, doc_fetcher.Page | None] = {}
_URL_TITLES: Dict[str, str] = {}  # url -> curated title from llms.txt
_LINKS_LOADED = False

SNIPPET_HYDRATE_MAX = 5  # how many top results to hydrate with content


def load_links_only() -> None:
    """Parse llms.txt files and index curated titles without fetching content.

    This function initializes the search index with document titles and URLs from
    configured llms.txt files. Content is not fetched during initialization for
    faster startup times.

    Side Effects:
        - Updates global _INDEX with document entries
        - Populates _URL_TITLES with curated titles
        - Sets placeholder entries in _URL_CACHE
        - Sets _LINKS_LOADED to True
    """
    global _INDEX, _LINKS_LOADED, _URL_TITLES, _URL_CACHE
    if _INDEX is None:
        _INDEX = indexer.IndexSearch()

    for src in doc_config.llm_texts_url:
        for title, url in doc_fetcher.parse_llms_txt(src):
            # Record curated display title and placeholder cache
            _URL_TITLES[url] = title
            _URL_CACHE.setdefault(url, None)

            # For curated titles from llms.txt, we already have the title
            display_title = text_processor.normalize(title)
            index_title = text_processor.index_title_variants(display_title, url)

            # Index now with clean display title + hidden index variants; empty content for now
            _INDEX.add(
                indexer.Doc(
                    uri=url, display_title=display_title, content='', index_title=index_title
                )
            )

    _LINKS_LOADED = True


def ensure_ready() -> None:
    """Ensure the search index is initialized and ready for use.

    Calls load_links_only() if the index hasn't been loaded yet.
    This is the main entry point for index initialization.
    """
    if not _LINKS_LOADED:
        load_links_only()


def ensure_page(url: str) -> doc_fetcher.Page | None:
    """Ensure a page is cached, fetching it if necessary.

    Args:
        url: The URL of the page to ensure is cached

    Returns:
        The cached or newly fetched Page object, or None if fetch failed

    """
    page = _URL_CACHE.get(url)
    if page is not None:
        return page
    try:
        raw = doc_fetcher.fetch_and_clean(url)
        display_title = text_processor.format_display_title(url, raw.title, _URL_TITLES)
        page = doc_fetcher.Page(url=url, title=display_title, content=raw.content)
        _URL_CACHE[url] = page
        return page
    except Exception:
        return None


def get_index() -> indexer.IndexSearch | None:
    """Get the current search index instance.

    Returns:
        The initialized IndexSearch instance, or None if not yet loaded
    """
    return _INDEX


def get_url_cache() -> Dict[str, doc_fetcher.Page | None]:
    """Get the URL cache dictionary.

    Returns:
        Dictionary mapping URLs to cached Page objects (or None if not fetched)
    """
    return _URL_CACHE


def get_url_titles() -> Dict[str, str]:
    """Get the curated URL titles mapping.

    Returns:
        Dictionary mapping URLs to their curated display titles from llms.txt
    """
    return _URL_TITLES
