# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""File utility functions for the frontend MCP server."""

from pathlib import Path


def load_markdown_file(filename: str) -> str:
    """Load a markdown file from the static/react directory.

    Args:
        filename (str): The name of the markdown file to load (e.g. 'basic-ui-setup.md')

    Returns:
        str: The content of the markdown file, or empty string if file not found
    """
    base_dir = Path(__file__).parent.parent
    react_dir = base_dir / 'static' / 'react'
    file_path = react_dir / filename

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print(f'Warning: File not found: {file_path}')
        return ''
