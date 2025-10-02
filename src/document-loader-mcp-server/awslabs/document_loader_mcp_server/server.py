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
"""Document Loader MCP Server."""

import pdfplumber
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from markitdown import MarkItDown
from pathlib import Path


# Initialize FastMCP server
mcp = FastMCP('Document Loader')


def _convert_with_markitdown(file_path: str, file_type: str) -> str:
    """Helper function to convert documents to markdown using MarkItDown.

    Args:
        file_path (str): Path to the file to convert
        file_type (str): Type of file for error messages (e.g., "Word document", "Excel file")

    Returns:
        str: Extracted content as markdown or error message
    """
    try:
        # Initialize MarkItDown
        md = MarkItDown()

        # Convert the document to markdown
        result = md.convert(file_path)

        return result.text_content

    except FileNotFoundError:
        return f'Error: Could not find {file_type} at {file_path}'
    except Exception as e:
        return f'Error reading {file_type} {file_path}: {str(e)}'


@mcp.tool()
def read_pdf(file_path: str) -> str:
    """Extract text content from a PDF file (*.pdf).

    Args:
        file_path (str): Path to the PDF file to read

    Returns:
        str: Extracted text content from the PDF or error message
    """
    try:
        text_content = ''

        # Open the PDF file with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text_content += f'\n--- Page {page_num} ---\n'
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text

        return text_content.strip()

    except FileNotFoundError:
        return f'Error: Could not find PDF file at {file_path}'
    except Exception as e:
        return f'Error reading PDF file {file_path}: {str(e)}'


@mcp.tool()
def read_docx(file_path: str) -> str:
    """Extract markdown content from a Microsoft Word document (*.docx, *.doc).

    Args:
        file_path (str): Path to the Word document file (*.docx, *.doc)

    Returns:
        str: Extracted content as markdown or error message
    """
    return _convert_with_markitdown(file_path, 'Word document')


@mcp.tool()
def read_xlsx(file_path: str) -> str:
    """Extract markdown content from an Excel spreadsheet (*.xlsx, *.xls).

    Args:
        file_path (str): Path to the Excel file (*.xlsx, *.xls)

    Returns:
        str: Extracted content as markdown or error message
    """
    return _convert_with_markitdown(file_path, 'Excel file')


@mcp.tool()
def read_pptx(file_path: str) -> str:
    """Extract markdown content from a PowerPoint presentation (*.pptx, *.ppt).

    Args:
        file_path (str): Path to the PowerPoint file (*.pptx, *.ppt)

    Returns:
        str: Extracted content as markdown or error message
    """
    return _convert_with_markitdown(file_path, 'PowerPoint file')


@mcp.tool()
def read_image(file_path: str) -> Image:
    """Load an image file and return it to the LLM for viewing and analysis.

    Args:
        file_path (str): Absolute path to the image file (supports PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)

    Returns:
        Image: Image object that can be displayed in the LLM interface
    """
    try:
        # Convert to Path object for easier handling
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f'Image file not found at {file_path}')

        # Check if it's a supported image format
        supported_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
        if path.suffix.lower() not in supported_extensions:
            raise ValueError(
                f'Unsupported image format: {path.suffix}. Supported formats: {", ".join(supported_extensions)}'
            )

        # Create and return Image object using FastMCP's Image helper
        return Image(path=file_path)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f'Error loading image {file_path}: {str(e)}') from e


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
