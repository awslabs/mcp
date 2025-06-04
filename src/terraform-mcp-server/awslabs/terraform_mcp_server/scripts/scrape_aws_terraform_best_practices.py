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

"""Script to download and extract content from AWS Terraform best practices PDF and save it as markdown."""

import io
import os
import PyPDF2
import re
import requests
from pathlib import Path


# URL to the PDF
PDF_URL = 'https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/terraform-aws-provider-best-practices/terraform-aws-provider-best-practices.pdf'

# Output file path
OUTPUT_DIR = Path(__file__).parent.parent / 'static'
OUTPUT_FILE = 'AWS_TERRAFORM_BEST_PRACTICES.md'


def download_pdf(url):
    """Download PDF from URL and return as bytes."""
    print(f'Downloading PDF from {url}...')
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.content


def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes."""
    print('Extracting text from PDF...')
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PyPDF2.PdfReader(pdf_file)

    text = ''
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text() + '\n\n'

    return text


def convert_to_markdown(text):
    """Convert extracted text to markdown format."""
    print('Converting text to markdown...')

    # Add title
    markdown = '# AWS Terraform Provider Best Practices\n\n'
    markdown += (
        '_This document was automatically extracted from the AWS Prescriptive Guidance PDF._\n\n'
    )
    markdown += f'_Source: [{PDF_URL}]({PDF_URL})_\n\n'

    # Process the text
    lines = text.split('\n')
    current_section = ''

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Try to identify headers
        if re.match(r'^[A-Z][A-Za-z\s]{2,}$', line.strip()) and len(line.strip()) < 80:
            # Looks like a header
            current_section = line.strip()

            # Stop before Document history section
            if current_section.lower() == 'document history':
                break

            markdown += f'## {current_section}\n\n'
            continue

        # Process content
        if re.match(r'^\d+\.\s+[A-Z]', line.strip()):
            # Numbered section
            markdown += f'### {line.strip()}\n\n'
        else:
            # Regular text
            # Check if it's a bullet point
            if line.strip().startswith('•') or line.strip().startswith('-'):
                markdown += f'{line.strip()}\n\n'
            else:
                markdown += f'{line.strip()}\n\n'

    # Clean up the markdown
    # Remove page numbers and headers/footers
    markdown = re.sub(r'\n\d+\n', '\n', markdown)

    # Fix bullet points
    markdown = markdown.replace('•', '*')

    # Remove excessive newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    return markdown


def main():
    """Execute the main workflow to download, extract, and convert AWS Terraform best practices to markdown.

    Downloads the PDF from the specified URL, extracts the text content, converts it to markdown format,
    and saves it to the output file. Creates the output directory if it doesn't exist.
    """
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # Download the PDF
        pdf_bytes = download_pdf(PDF_URL)

        # Extract text from PDF
        text = extract_text_from_pdf(pdf_bytes)

        # Convert to markdown
        markdown = convert_to_markdown(text)

        # Write to file
        output_path = OUTPUT_DIR / OUTPUT_FILE
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f'Successfully saved to {output_path}')

    except Exception as e:
        print(f'Error: {e}')


if __name__ == '__main__':
    main()
