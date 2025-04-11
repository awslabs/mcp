"""Script to generate AWS provider resources markdown for the Terraform Expert MCP server.

This script scrapes the Terraform AWS provider documentation using Playwright
and generates a comprehensive markdown file listing all AWS service categories,
resources, and data sources.

The generated markdown is saved to the static directory for use by the MCP server.

Usage:
  python generate_aws_provider_resources.py [--max-categories N] [--output PATH]

Options:
  --max-categories N    Limit to N categories (default: all)
  --output PATH         Output file path (default: terraform_mcp_server/static/AWS_PROVIDER_RESOURCES.md)
  --no-fallback         Don't use fallback data if scraping fails
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path


# Add the parent directory to sys.path so we can import from terraform_mcp_server
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Now import modules after modifying sys.path
from awslabs.terraform_mcp_server.impl.resources.terraform_aws_provider_resources_listing import (  # noqa: E402
    fetch_aws_provider_page,
)


# Default output path
DEFAULT_OUTPUT_PATH = (
    repo_root / 'awslabs' / 'terraform_mcp_server' / 'static' / 'AWS_PROVIDER_RESOURCES.md'
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate AWS provider resources markdown for the Terraform Expert MCP server.'
    )
    parser.add_argument(
        '--max-categories',
        type=int,
        default=999,
        help='Limit to N categories (default: all)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f'Output file path (default: {DEFAULT_OUTPUT_PATH})',
    )
    parser.add_argument(
        '--no-fallback',
        action='store_true',
        help="Don't use fallback data if scraping fails",
    )
    return parser.parse_args()


async def main():
    """Main entry point for the script."""
    start_time = datetime.now()

    # Parse command line arguments
    args = parse_arguments()

    print('Generating AWS provider resources markdown...')
    print(f'Output path: {args.output}')
    print(f'Max categories: {args.max_categories if args.max_categories < 999 else "all"}')

    # Set environment variable for max categories
    os.environ['MAX_CATEGORIES'] = str(args.max_categories)

    # Set environment variable for fallback behavior
    if args.no_fallback:
        os.environ['USE_PLAYWRIGHT'] = '1'
        print('Using live scraping without fallback')

    try:
        # Fetch AWS provider data using the existing implementation
        result = await fetch_aws_provider_page()

        # Extract categories and version
        if isinstance(result, dict) and 'categories' in result and 'version' in result:
            categories = result['categories']
            provider_version = result.get('version', 'unknown')
        else:
            # Handle backward compatibility with older API
            categories = result
            provider_version = 'unknown'

        # Sort categories alphabetically
        sorted_categories = sorted(categories.keys())

        # Count totals
        total_resources = sum(len(cat['resources']) for cat in categories.values())
        total_data_sources = sum(len(cat['data_sources']) for cat in categories.values())

        print(
            f'Found {len(categories)} categories, {total_resources} resources, and {total_data_sources} data sources'
        )

        # Generate markdown
        markdown = []
        markdown.append('# AWS Provider Resources Listing')
        markdown.append(f'\nAWS Provider Version: {provider_version}')
        markdown.append(f'\nLast updated: {datetime.now().strftime("%B %d, %Y %H:%M:%S")}')
        markdown.append(
            f'\nFound {total_resources} resources and {total_data_sources} data sources across {len(categories)} AWS service categories.\n'
        )

        # Generate table of contents
        markdown.append('## Table of Contents')
        for category in sorted_categories:
            sanitized_category = (
                category.replace(' ', '-').replace('(', '').replace(')', '').lower()
            )
            markdown.append(f'- [{category}](#{sanitized_category})')
        markdown.append('')

        # Generate content for each category
        for category in sorted_categories:
            cat_data = categories[category]
            sanitized_heading = category.replace('(', '').replace(')', '')

            markdown.append(f'## {sanitized_heading}')

            resource_count = len(cat_data['resources'])
            data_source_count = len(cat_data['data_sources'])

            # Add category summary
            markdown.append(
                f'\n*{resource_count} resources and {data_source_count} data sources*\n'
            )

            # Add resources section if available
            if cat_data['resources']:
                markdown.append('### Resources')
                for resource in sorted(cat_data['resources'], key=lambda x: x['name']):
                    markdown.append(f'- [{resource["name"]}]({resource["url"]})')

            # Add data sources section if available
            if cat_data['data_sources']:
                markdown.append('\n### Data Sources')
                for data_source in sorted(cat_data['data_sources'], key=lambda x: x['name']):
                    markdown.append(f'- [{data_source["name"]}]({data_source["url"]})')

            markdown.append('')  # Add blank line between categories

        # Add generation metadata at the end
        duration = datetime.now() - start_time
        markdown.append('---')
        markdown.append(
            '*This document was generated automatically by the AWS Provider Resources Generator script.*'
        )
        markdown.append(f'*Generation time: {duration.total_seconds():.2f} seconds*')

        # Ensure directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        # Write markdown to output file
        with open(args.output, 'w') as f:
            f.write('\n'.join(markdown))

        print(f'Successfully generated markdown file at: {args.output}')
        print(f'Generation completed in {duration.total_seconds():.2f} seconds')
        return 0

    except Exception as e:
        print(f'Error generating AWS provider resources: {str(e)}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
