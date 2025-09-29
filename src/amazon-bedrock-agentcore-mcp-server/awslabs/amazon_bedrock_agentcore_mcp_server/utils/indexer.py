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

from __future__ import annotations

import math
import re
from pydantic import BaseModel, ConfigDict, Field


# Enhanced tokenization patterns
_TOKEN = re.compile(r'[A-Za-z0-9_]+')
_MD_HEADER = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_MD_CODE_BLOCK = re.compile(r'```[\w]*\n([\s\S]*?)```')
_MD_INLINE_CODE = re.compile(r'`([^`]+)`')
_MD_LINK_TEXT = re.compile(r'\[([^\]]+)\]\([^)]+\)')


class Doc(BaseModel):
    """A single indexed document with display and search metadata.

    Attributes:
        uri: Unique identifier/URL for the document
        display_title: Human-readable title shown to users
        content: Full text content (may be empty before fetching)
        index_title: Searchable title text including variants and synonyms
    """

    uri: str = Field(description='Unique identifier/URL for the document')
    display_title: str = Field(description='Human-readable title shown to users')
    content: str = Field(description='Full text content (may be empty before fetching)')
    index_title: str = Field(description='Searchable title text including variants')

    model_config = ConfigDict(extra='allow')


# Title boost constants
_TITLE_BOOST_EMPTY = 8  # boost for unfetched content
_TITLE_BOOST_SHORT = 5  # boost for short pages (<800 chars)
_TITLE_BOOST_LONG = 3  # boost for longer pages
_SHORT_PAGE_THRESHOLD = 800  # character threshold for short pages


class IndexSearch:
    """Lightweight inverted index with TF-IDF scoring and Markdown awareness.

    This class provides document indexing and search functionality optimized for
    technical documentation. It uses TF-IDF scoring with special handling for
    Markdown structure elements like headers, code blocks, and links.

    Features:
        - Indexes searchable titles (not display titles) for synonym support
        - Adaptive title boosting based on content length
        - Enhanced scoring for Markdown elements (headers, code, links)
        - Lightweight implementation without external dependencies

    Attributes:
        docs: List of indexed documents
        doc_frequency: Token document frequency for IDF calculation
        doc_indices: Inverted index mapping tokens to document indices
    """

    def __init__(self) -> None:
        """Initialize an empty search index."""
        self.docs: list[Doc] = []
        self.doc_frequency: dict[str, int] = {}  # document frequency
        self.doc_indices: dict[str, list[int]] = {}  # token -> doc indices

    def add(self, doc: Doc) -> None:
        """Add a document to the search index.

        Args:
            doc: Document to add to the index

        Note:
            Extracts and weights different content types:
            - Titles: Highest weight for search relevance
            - Headers: High weight for structural importance
            - Code blocks: Medium weight for technical content
            - Link text: Medium weight for navigation context
            - Body text: Base weight for general content
        """
        idx = len(self.docs)
        self.docs.append(doc)
        seen: set[str] = set()

        # Extract MD-specific content with different weights
        content = doc.content.lower()
        title_text = doc.index_title.lower()

        # Extract headers (high importance)
        headers = ' '.join(_MD_HEADER.findall(doc.content))

        # Extract code content (medium importance for tech docs)
        code_blocks = ' '.join(_MD_CODE_BLOCK.findall(doc.content))
        inline_code = ' '.join(_MD_INLINE_CODE.findall(doc.content))

        # Extract link text (medium importance)
        link_text = ' '.join(_MD_LINK_TEXT.findall(doc.content))

        # Build weighted haystack: title gets highest weight
        haystack_parts = [
            title_text,  # Will get title boost in search
            headers.lower(),
            link_text.lower(),
            code_blocks.lower(),
            inline_code.lower(),
            content,
        ]

        haystack = ' '.join(part for part in haystack_parts if part)

        for tok in _TOKEN.findall(haystack):
            self.doc_indices.setdefault(tok, []).append(idx)
            if tok not in seen:
                self.doc_frequency[tok] = self.doc_frequency.get(tok, 0) + 1
                seen.add(tok)

    def search(self, query: str, k: int = 8) -> list[tuple[float, Doc]]:
        """Search the index and return ranked results.

        Args:
            query: Search query string
            k: Maximum number of results to return

        Returns:
            List of (score, document) tuples sorted by relevance (highest first)

        Note:
            Uses TF-IDF scoring with Markdown-aware enhancements:
            - Title matches receive adaptive boosting
            - Header matches get 4x weight
            - Code and link matches get 2x weight
            - Empty content gets higher title boost for better ranking
        """

        def _title_boost_for(doc: Doc) -> int:
            """Calculate title boost factor based on document content length.

            Args:
                doc: Document to calculate boost for

            Returns:
                Boost multiplier for title matches
            """
            n = len(doc.content)
            if n == 0:  # not fetched yet
                return _TITLE_BOOST_EMPTY
            if n < _SHORT_PAGE_THRESHOLD:  # short page
                return _TITLE_BOOST_SHORT
            return _TITLE_BOOST_LONG

        def _calculate_md_score(doc: Doc, token: str) -> float:
            """Calculate enhanced relevance score for Markdown content.

            Args:
                doc: Document to score
                token: Search token to score against

            Returns:
                Weighted relevance score considering Markdown structure

            Note:
                Applies different weights to content types:
                - Title matches: Variable boost (8x/5x/3x based on content length)
                - Header matches: 4x weight
                - Code matches: 2x weight
                - Link text matches: 2x weight
                - Body text: 1x weight (base)
            """
            content_lower = doc.content.lower()
            title_lower = doc.index_title.lower()

            # Base content frequency
            content_tf = content_lower.count(token)

            # Title matches (highest weight)
            title_tf = title_lower.count(token) * _title_boost_for(doc)

            # Header matches (high weight)
            header_tf = 0
            for header in _MD_HEADER.findall(doc.content):
                header_tf += header.lower().count(token) * 4

            # Code block matches (medium weight for tech docs)
            code_tf = 0
            for code in _MD_CODE_BLOCK.findall(doc.content):
                code_tf += code.lower().count(token) * 2

            # Link text matches (medium weight)
            link_tf = 0
            for link in _MD_LINK_TEXT.findall(doc.content):
                link_tf += link.lower().count(token) * 2

            return float(content_tf + title_tf + header_tf + code_tf + link_tf)

        q_tokens = [t.lower() for t in _TOKEN.findall(query)]
        scores: dict[int, float] = {}
        N = max(len(self.docs), 1)

        for qt in q_tokens:
            for idx in self.doc_indices.get(qt, []):
                d = self.docs[idx]
                tf = _calculate_md_score(d, qt)
                idf = math.log((N + 1) / (1 + self.doc_frequency.get(qt, 0))) + 1.0
                scores[idx] = scores.get(idx, 0.0) + tf * idf

        ranked = sorted(
            ((score, self.docs[i]) for i, score in scores.items()),
            key=lambda x: x[0],
            reverse=True,
        )
        return ranked[:k]
