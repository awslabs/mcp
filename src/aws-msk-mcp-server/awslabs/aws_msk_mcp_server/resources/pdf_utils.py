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

"""PDF Utilities for MSK Documentation.

This module provides utilities for processing PDF documentation directly from URLs.
"""

import httpx
import io
import PyPDF2
from typing import Any, Dict, List, Optional, Union


# Define PDF resources
PDF_RESOURCES = {
    'developer-guide': {
        'title': 'Amazon MSK Developer Guide',
        'url': 'https://docs.aws.amazon.com/pdfs/msk/latest/developerguide/MSKDevGuide.pdf',
    }
}

# Default user agent for HTTP requests
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'


async def get_pdf_content(pdf_id: str) -> bytes:
    """Get the content of a PDF file directly from the URL without downloading.

    Args:
        pdf_id: ID of the PDF resource

    Returns:
        PDF content as bytes
    """
    # Check if the PDF ID is valid
    if pdf_id not in PDF_RESOURCES:
        raise ValueError(f'Unknown PDF resource: {pdf_id}')

    # Get the resource information
    resource = PDF_RESOURCES[pdf_id]

    # Download the PDF content
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                resource['url'],
                follow_redirects=True,
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
            response.raise_for_status()

            return response.content
        except Exception:
            raise


def extract_pdf_content(
    pdf_content: bytes, start_page: int = 1, end_page: Optional[int] = None
) -> Dict[str, Any]:
    """Extract content from PDF bytes.

    Args:
        pdf_content: PDF content as bytes
        start_page: First page to extract (1-based index)
        end_page: Last page to extract (or None for all remaining pages)

    Returns:
        Dictionary containing the extracted content and pagination information
    """
    # Create a PDF reader from the bytes
    try:
        pdf_bytes = io.BytesIO(pdf_content)
    except Exception as e:
        return {'error': f'Failed to extract PDF content: {str(e)}', 'content': None}

    try:
        reader = PyPDF2.PdfReader(pdf_bytes)
    except Exception as e:
        return {'error': f'Failed to extract PDF content: {str(e)}', 'content': None}

    try:
        # Get total pages
        total_pages = len(reader.pages)

        # Validate page range
        if start_page < 1:
            start_page = 1
        if end_page is None or end_page > total_pages:
            end_page = total_pages

        # Extract content from specified pages
        content = []
        for page_num in range(start_page - 1, end_page):
            try:
                page = reader.pages[page_num]
                content.append(page.extract_text())
            except Exception as e:
                return {'error': f'Failed to extract PDF content: {str(e)}', 'content': None}

        # Join content with page breaks
        full_content = '\n\n--- Page Break ---\n\n'.join(content)

        return {
            'content': full_content,
            'pagination': {
                'start_page': start_page,
                'end_page': end_page,
                'total_pages': total_pages,
                'has_more': end_page < total_pages,
            },
        }
    except Exception as e:
        return {'error': f'Failed to extract PDF content: {str(e)}', 'content': None}


def extract_pdf_toc(pdf_content: bytes) -> List[Dict[str, Union[str, int]]]:
    """Extract table of contents from PDF bytes.

    Args:
        pdf_content: PDF content as bytes

    Returns:
        List of TOC entries, each containing title and page number
    """
    try:
        # Create a PDF reader from the bytes
        pdf_bytes = io.BytesIO(pdf_content)
        reader = PyPDF2.PdfReader(pdf_bytes)

        # Try to get the outline (TOC)
        toc = []

        # PyPDF2 doesn't have great TOC extraction, so we'll use a simple approach
        # Extract first line of each page as a potential heading
        for i in range(len(reader.pages)):
            try:
                page = reader.pages[i]
                text = page.extract_text(0, 200)  # Get first 200 chars

                # Skip empty pages
                if not text:
                    continue

                # Get the first line
                first_line = text.split('\n')[0].strip()

                # Skip very short lines or page numbers
                if len(first_line) < 3 or first_line.isdigit():
                    continue

                toc.append({'title': first_line, 'page': i + 1})
            except Exception:
                # Skip pages that cause errors
                continue

        return toc
    except Exception:
        return []
