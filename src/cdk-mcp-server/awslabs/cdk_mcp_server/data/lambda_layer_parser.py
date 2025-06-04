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

"""Lambda layer documentation parser module."""

import httpx
import logging
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import Any, Dict, List, Optional


# Set up logging
logger = logging.getLogger(__name__)


class LambdaLayerParser:
    """Parser for Lambda layer documentation from AWS docs."""

    # Documentation URLs
    GENERIC_LAYER_URL = (
        'https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda-readme.html#layers'
    )
    PYTHON_LAYER_URL = 'https://docs.aws.amazon.com/cdk/api/v2/docs/@aws-cdk_aws-lambda-python-alpha.PythonLayerVersion.html'

    # Search patterns to directly find sections when headers aren't working
    LAYER_SECTION_PATTERNS = ['layers', 'layer version', 'layerversion']

    @classmethod
    async def fetch_page(cls, url: str) -> Optional[str]:
        """Fetch a page from AWS documentation."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f'Failed to fetch {url}: HTTP {response.status_code}')
                    return None
        except Exception as e:
            logger.error(f'Error fetching {url}: {str(e)}')
            return None

    @classmethod
    def extract_code_examples(cls, html_section: Optional[str]) -> List[Dict[str, str]]:
        """Extract code examples from an HTML section."""
        if not html_section:
            return []

        soup = BeautifulSoup(html_section, 'html.parser')
        code_blocks = soup.find_all('pre')

        examples = []
        for block in code_blocks:
            # Make sure we're working with a Tag
            if not isinstance(block, Tag):
                continue

            # Try to determine the language
            language = 'typescript'  # Default
            classes = block.attrs.get('class', [])

            # Make sure classes is a list of strings
            if not isinstance(classes, list):
                classes = [str(classes)]

            class_str = ' '.join(classes)

            if 'python' in class_str.lower():
                language = 'python'
            elif 'javascript' in class_str.lower():
                language = 'javascript'

            # Get the code content
            code = block.get_text()
            examples.append({'language': language, 'code': code})

        return examples

    @classmethod
    def extract_directory_structure(cls, html_section: Optional[str]) -> Optional[str]:
        """Extract directory structure information from HTML section."""
        if not html_section:
            return None

        soup = BeautifulSoup(html_section, 'html.parser')

        # Look for pre blocks that might contain directory structure
        pre_blocks = soup.find_all('pre')
        for block in pre_blocks:
            text = block.get_text()
            if '/' in text and (
                'directory' in text.lower()
                or 'structure' in text.lower()
                or 'layer' in text.lower()
            ):
                return text

        # Look for paragraphs that might describe directory structure
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text()
            if (
                'directory' in text.lower() and 'structure' in text.lower()
            ) or 'layer' in text.lower():
                return text

        return None

    @classmethod
    def find_layer_content(cls, html: Optional[str]) -> Optional[str]:
        """Find Lambda layer content using multiple strategies."""
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Strategy 1: Find section by id
        section = soup.find(id='layers')
        if section and isinstance(section, Tag):
            # If we found an anchor, get its parent and look for the actual content
            if section.name == 'a':
                parent = section.parent
                if parent and isinstance(parent, Tag) and parent.name and parent.name[0] == 'h':
                    # We found a header, extract all content until the next header of same or higher level
                    content = []
                    content.append(str(parent))

                    header_level = int(parent.name[1])
                    sibling = parent.next_sibling

                    while sibling:
                        if (
                            isinstance(sibling, Tag)
                            and sibling.name
                            and sibling.name[0] == 'h'
                            and int(sibling.name[1]) <= header_level
                        ):
                            break
                        if isinstance(sibling, Tag) and sibling.name:
                            content.append(str(sibling))
                        sibling = sibling.next_sibling

                    return ''.join(content)

        # Strategy 2: Look for headers containing layer keywords
        for tag in ['h1', 'h2', 'h3', 'h4']:
            headers = soup.find_all(tag)
            for header in headers:
                if not isinstance(header, Tag):
                    continue

                text = header.get_text().lower()
                if any(pattern in text for pattern in cls.LAYER_SECTION_PATTERNS):
                    # Found a relevant header, extract all content until the next header of same or higher level
                    content = []
                    content.append(str(header))

                    if not header.name:
                        continue

                    header_level = int(header.name[1])
                    sibling = header.next_sibling

                    while sibling:
                        if (
                            isinstance(sibling, Tag)
                            and sibling.name
                            and sibling.name[0] == 'h'
                            and int(sibling.name[1]) <= header_level
                        ):
                            break
                        if isinstance(sibling, Tag) and sibling.name:
                            content.append(str(sibling))
                        sibling = sibling.next_sibling

                    return ''.join(content)

        # Strategy 3: Look for content div with class="api" or class="props"
        content_divs = soup.find_all('div', class_=['api', 'props'])
        if content_divs:
            return ''.join(str(div) for div in content_divs)

        # Strategy 4: Look for table with class containing 'cdk'
        tables = soup.find_all('table')
        for table in tables:
            if not isinstance(table, Tag):
                continue

            classes = table.attrs.get('class', [])
            if not isinstance(classes, list):
                classes = [str(classes)]

            if any('cdk' in str(cls_name) for cls_name in classes):
                return str(table)

        return None

    @classmethod
    async def fetch_lambda_layer_docs(cls) -> Dict[str, Any]:
        """Fetch Lambda layer documentation from AWS docs."""
        logger.info('Fetching Lambda layer documentation from AWS')

        # Fetch only the generic page
        generic_html = await cls.fetch_page(cls.GENERIC_LAYER_URL)

        # Extract relevant sections using our specialized finder
        generic_layers_section = cls.find_layer_content(generic_html)

        # Extract code examples and directory structure
        generic_examples = cls.extract_code_examples(generic_layers_section)
        generic_dir_structure = cls.extract_directory_structure(generic_layers_section)

        # Compile the results
        result = {
            'generic_layers': {
                'examples': generic_examples,
                'directory_structure': generic_dir_structure,
                'url': cls.GENERIC_LAYER_URL,
            }
        }

        return result
