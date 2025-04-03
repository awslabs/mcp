"""Implementation for terraform_aws_modules_listing resource."""

import asyncio
import requests
import time
from datetime import datetime
from loguru import logger

# Reuse functions from search_terraform_aws_modules
from terraform_mcp_server.impl.tools.search_terraform_aws_modules import clean_description
from typing import Any, Dict, List


async def terraform_aws_modules_listing_impl() -> str:
    """Generate a comprehensive listing of terraform-aws-modules.

    Returns:
        A markdown formatted string with module information
    """
    logger.info('Generating terraform-aws-modules listing')

    start_time = time.time()

    # Get modules from Terraform Registry
    try:
        modules = await fetch_all_terraform_aws_modules()
        if not modules:
            return '# Terraform AWS Modules Listing\n\nNo modules found or error accessing the Terraform Registry.'

        logger.info(
            f'Found {len(modules)} terraform-aws-modules in {time.time() - start_time:.2f} seconds'
        )

        # Sort modules by download count (descending) to show most popular first
        modules.sort(key=lambda m: int(m.get('downloads', 0)), reverse=True)

        # Generate markdown
        markdown = []
        markdown.append('# Terraform AWS Modules Listing')
        markdown.append(f'\nLast updated: {datetime.now().strftime("%B %d, %Y %H:%M:%S")}')
        markdown.append(
            f'\n{len(modules)} modules found in the terraform-aws-modules namespace.\n'
        )

        generation_time = time.time() - start_time
        markdown.append(f'Listing generated in {generation_time:.2f} seconds.\n')
    except Exception as e:
        logger.error(f'Error generating terraform-aws-modules listing: {e}')
        return f'# Terraform AWS Modules Listing\n\nError generating listing: {str(e)}'

    # Add module information
    markdown.append('## Available Modules\n')

    for module in modules:
        name = module.get('name', 'Unknown')
        namespace = module.get('namespace', 'terraform-aws-modules')
        provider = module.get('provider', 'aws')

        # Clean description of any emoji characters
        description = module.get('description', 'No description available')
        clean_desc = clean_description(description)

        # Module link
        module_link = f'https://registry.terraform.io/modules/{namespace}/{name}/{provider}'

        # Format downloads more nicely
        downloads = module.get('downloads', 0)
        if downloads > 1000000:
            formatted_downloads = f'{downloads / 1000000:.1f}M+'
        elif downloads > 1000:
            formatted_downloads = f'{downloads / 1000:.1f}k+'
        else:
            formatted_downloads = str(downloads)

        # Format published date
        published_at = module.get('published_at', '')
        try:
            if published_at:
                # Try to parse the datetime and format it more nicely
                parsed_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                published_date = parsed_date.strftime('%B %d, %Y')
            else:
                published_date = 'Unknown'
        except Exception:
            published_date = published_at or 'Unknown'

        # Build the module entry
        markdown.append(f'### {name}')
        markdown.append(f'- **Description**: {clean_desc}')
        markdown.append(f'- **Downloads**: {formatted_downloads}')
        markdown.append(f'- **Last Published**: {published_date}')

        # Add verified badge if applicable
        if module.get('verified', False):
            markdown.append('- **Status**: ✓ Verified')

        # Add link to registry
        markdown.append(f'- [View in Registry]({module_link})')
        markdown.append('')  # Empty line for spacing

    markdown.append('\n---')
    markdown.append('This listing is dynamically generated from the Terraform Registry API.')

    return '\n'.join(markdown)


async def fetch_all_terraform_aws_modules() -> List[Dict[str, Any]]:
    """Fetch all terraform-aws-modules from the Terraform Registry API.

    Returns:
        List of module dictionaries
    """
    all_modules = []
    offset = 0
    limit = 100  # Maximum allowed by API

    try:
        while True:
            url = f'https://registry.terraform.io/v1/modules?namespace=terraform-aws-modules&offset={offset}&limit={limit}'
            logger.debug(f'Fetching modules from {url}')

            start_time = time.time()
            response = requests.get(url, timeout=5.0)  # Add timeout
            logger.debug(
                f'Terraform Registry API request took {time.time() - start_time:.2f} seconds'
            )

            response.raise_for_status()
            data = response.json()

            modules = data.get('modules', [])
            if not modules:
                break  # No more modules

            all_modules.extend(modules)
            logger.debug(f'Retrieved {len(modules)} modules (total: {len(all_modules)})')

            # If we got fewer modules than the limit, we've reached the end
            if len(modules) < limit:
                break

            offset += limit

            # Add a small delay between requests to avoid hitting rate limits
            await asyncio.sleep(0.2)

    except requests.exceptions.Timeout:
        logger.error('Timeout error fetching modules from Terraform Registry')
        # Return what we have so far rather than failing completely
        if all_modules:
            logger.info(f'Returning {len(all_modules)} modules fetched before timeout')
            return all_modules
        return []
    except Exception as e:
        logger.error(f'Error fetching modules: {e}')
        return []

    return all_modules
