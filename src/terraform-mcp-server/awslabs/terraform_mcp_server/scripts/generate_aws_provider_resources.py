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
import re
import sys
import tempfile
import time
from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement, ResultSet
from bs4.filter import SoupStrainer
from datetime import datetime
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, TypeVar, cast


## Playwright optional import
try:
    from playwright.async_api import async_playwright
except ImportError:
    # Playwright is optional, we'll use fallback data if it's not available
    async_playwright = None

# Add the parent directory to sys.path so we can import from terraform_mcp_server
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent.parent
sys.path.insert(0, str(repo_root))


# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {
            'sink': sys.stderr,
            'backtrace': True,
            'diagnose': True,
            'format': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        }
    ]
)

# Environment variable to control whether to use Playwright or go straight to fallback data
USE_PLAYWRIGHT = os.environ.get('USE_PLAYWRIGHT', '1').lower() in ('1', 'true', 'yes')
# Shorter timeout to fail faster if it's not going to work
NAVIGATION_TIMEOUT = 20000  # 20 seconds
# Default output path
DEFAULT_OUTPUT_PATH = (
    repo_root / 'awslabs' / 'terraform_mcp_server' / 'static' / 'AWS_PROVIDER_RESOURCES.md'
)
# AWS provider URL
AWS_PROVIDER_URL = 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs'


# Define TypedDict classes for the structures used in the script
class ResourceItem(TypedDict):
    """Type definition for a Terraform resource or data source item.

    Attributes:
        name: The name/identifier of the resource (e.g. 'aws_acm_certificate')
        url: The documentation URL for the resource
        type: The type of item - either 'resource' or 'data_source'
    """

    name: str
    url: str
    type: str


class CategoryData(TypedDict):
    """Type definition for a category of Terraform resources and data sources.

    Attributes:
        resources: List of ResourceItem objects representing Terraform resources in this category
        data_sources: List of ResourceItem objects representing Terraform data sources in this category
    """

    resources: List[ResourceItem]
    data_sources: List[ResourceItem]


class ProviderResult(TypedDict):
    """Type definition for the result of fetching AWS provider data.

    Attributes:
        categories: Dictionary mapping AWS service category names to their resources and data sources
        version: AWS provider version string (e.g. "5.91.0")
    """

    categories: Dict[str, CategoryData]
    version: str


# Type helpers for BeautifulSoup
T = TypeVar('T')


def ensure_tag(element: Optional[PageElement]) -> Optional[Tag]:
    """Ensure an element is a Tag or return None."""
    if isinstance(element, Tag):
        return element
    return None


def safe_find(element: Any, *args: Any, **kwargs: Any) -> Optional[Tag]:
    """Safely find an element in a Tag."""
    if not isinstance(element, Tag):
        return None
    result = element.find(*args, **kwargs)
    return ensure_tag(result)


def safe_find_all(element: Any, *args: Any, **kwargs: Any) -> ResultSet:
    """Safely find all elements in a Tag."""
    if not isinstance(element, Tag):
        return ResultSet(SoupStrainer(), [])
    return element.find_all(*args, **kwargs)


def safe_get_text(element: Any, strip: bool = False) -> str:
    """Safely get text from an element."""
    if hasattr(element, 'get_text'):
        return element.get_text(strip=strip)
    return str(element) if element is not None else ''


async def fetch_aws_provider_page() -> ProviderResult:
    """Fetch the AWS provider documentation page using Playwright.

    This function uses a headless browser to render the JavaScript-driven
    Terraform Registry website and extract the AWS provider resources.

    It will fall back to pre-defined data if:
    - The USE_PLAYWRIGHT environment variable is set to 0/false/no
    - There's any error during the scraping process

    Returns:
        A dictionary containing:
        - 'categories': Dictionary of AWS service categories with resources and data sources
        - 'version': AWS provider version string (e.g., "5.91.0")
    """
    # Check if we should skip Playwright and use fallback data directly
    if not USE_PLAYWRIGHT or async_playwright is None:
        logger.info(
            'Skipping Playwright and using pre-defined resource structure (USE_PLAYWRIGHT=0)'
        )
        return cast(
            ProviderResult, {'categories': get_fallback_resource_data(), 'version': 'unknown'}
        )
    else:
        logger.info('Playwright is available and will be used to scrape the AWS provider docs')
        logger.info('Starting browser to extract AWS provider resources structure')
        start_time = time.time()
        categories = {}

        try:
            async with async_playwright() as p:
                # Launch the browser with specific options for better performance
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox'],
                )
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                )
                page = await context.new_page()

                # Set a shorter timeout for navigation
                page.set_default_timeout(NAVIGATION_TIMEOUT)

                # Navigate to the AWS provider docs with reduced timeout
                logger.info(
                    f'Navigating to Terraform AWS provider documentation (timeout: {NAVIGATION_TIMEOUT}ms)'
                )
                try:
                    await page.goto(
                        AWS_PROVIDER_URL,
                        wait_until='domcontentloaded',
                    )  # Using 'domcontentloaded' instead of 'networkidle'
                    logger.info('Basic page loaded successfully')
                except Exception as nav_error:
                    logger.error(f'Error during navigation: {nav_error}')
                    await browser.close()
                    return cast(
                        ProviderResult,
                        {'categories': get_fallback_resource_data(), 'version': 'unknown'},
                    )

                # Wait for the content to be fully loaded
                logger.info('Waiting for page to render completely')

                # Add a small fixed delay to let JavaScript finish rendering
                await asyncio.sleep(2)

                # Extract AWS provider version
                provider_version = 'unknown'
                try:
                    # Try to extract version using the selector provided
                    logger.info('Attempting to extract AWS provider version')

                    # Try using the selector approach
                    version_element = await page.query_selector(
                        'body > div.provider-view > div.provider-nav > nav.bread-crumbs.is-light > div > div > ul > li:nth-child(4) > span'
                    )
                    if version_element:
                        # Try to extract text from the element
                        version_text = await version_element.inner_text()
                        logger.debug(f'Found version element with text: {version_text}')

                        # Extract just the version number using regex
                        version_match = re.search(r'Version\s+([0-9.]+)', version_text)
                        if version_match:
                            provider_version = version_match.group(1)  # e.g., "5.91.0"
                            logger.info(f'Extracted AWS provider version: {provider_version}')
                        else:
                            # If regex doesn't match, try JavaScript approach
                            logger.debug("Regex pattern didn't match, trying JavaScript approach")
                            provider_version = await page.evaluate("""
                                () => {
                                    const versionEl = document.querySelector('.version-dropdown button span');
                                    return versionEl ? versionEl.innerText.trim() : null;
                                }
                            """)
                            # Clean up the version string if needed
                            if provider_version:
                                provider_version = provider_version.strip()
                                version_match = re.search(r'([0-9.]+)', provider_version)
                                if version_match:
                                    provider_version = version_match.group(1)
                                logger.info(
                                    f'Extracted AWS provider version via JavaScript: {provider_version}'
                                )
                    else:
                        # If the specific selector doesn't work, try a more general approach
                        logger.debug(
                            'Specific version selector not found, trying alternative selectors'
                        )
                        provider_version = await page.evaluate("""
                                            () => {
                                                // Try different selectors that might contain the version
                                                const selectors = [
                                                    '.version-dropdown button span',
                                                    '.dropdown-trigger button span',
                                                    'span:contains("Version")'
                                                ];
                                                for (const selector of selectors) {
                                    try {
                                        const el = document.querySelector(selector);
                                        if (el && el.innerText.includes('Version')) {
                                            return el.innerText.trim();
                                        }
                                    } catch (e) {}
                                }
                                return null;
                            }
                        """)

                        # Extract version number from text if found
                        if provider_version:
                            version_match = re.search(r'([0-9.]+)', provider_version)
                            if version_match:
                                provider_version = version_match.group(1)
                                logger.info(
                                    f'Extracted AWS provider version via alternative selector: {provider_version}'
                                )
                except Exception as version_error:
                    logger.warning(f'Error extracting AWS provider version: {version_error}')

                # Check for and handle cookie consent banner
                logger.info('Checking for cookie consent banner')
                try:
                    # Check if the consent banner is present
                    consent_banner = await page.query_selector('#consent-banner')
                    if consent_banner:
                        logger.info('Cookie consent banner detected, attempting to dismiss')

                        # Target the specific dismiss button based on the HTML structure provided
                        dismiss_button_selectors = [
                            'button.hds-button:has-text("Dismiss")',
                            'button.hds-button .hds-button__text:has-text("Dismiss")',
                            'button.hds-button--color-primary',
                        ]

                        for selector in dismiss_button_selectors:
                            try:
                                # Check if the button exists with this selector
                                button = await page.query_selector(selector)
                                if button:
                                    logger.info(f'Found dismiss button with selector: {selector}')
                                    await button.click()
                                    logger.info('Clicked the dismiss button')

                                    # Wait a moment for the banner to disappear
                                    await asyncio.sleep(1)

                                    # Check if the banner is gone
                                    banner_still_visible = await page.query_selector(
                                        '#consent-banner'
                                    )
                                    if not banner_still_visible:
                                        logger.info('Banner successfully dismissed')
                                        break
                            except Exception as button_error:
                                logger.warning(
                                    f'Failed to click button {selector}: {button_error}'
                                )

                        # If button clicking didn't work, try JavaScript approach as a fallback
                        banner_still_visible = await page.query_selector('#consent-banner')
                        if banner_still_visible:
                            logger.info('Attempting to remove banner via JavaScript')
                            try:
                                # Try to remove the banner using JavaScript
                                await page.evaluate("""() => {
                                    const banner = document.getElementById('consent-banner');
                                    if (banner) banner.remove();
                                    return true;
                                }""")
                                logger.info('Removed banner using JavaScript')
                            except Exception as js_error:
                                logger.warning(
                                    f'Failed to remove banner via JavaScript: {js_error}'
                                )

                except Exception as banner_error:
                    logger.warning(f'Error handling consent banner: {banner_error}')

                # Progressive wait strategy - try multiple conditions in sequence
                # Define selectors to try in order of preference
                selectors = [
                    '.provider-docs-menu-content',
                    'nav',
                    '.docs-nav',
                    'aside',
                    'ul.nav',
                    'div[role="navigation"]',
                ]

                # Try each selector with a short timeout
                for selector in selectors:
                    try:
                        logger.info(f'Trying to locate element with selector: {selector}')
                        await page.wait_for_selector(selector, timeout=5000)
                        logger.info(f'Found element with selector: {selector}')
                        break
                    except Exception as se:
                        logger.warning(f"Selector '{selector}' not found: {se}")

                # Extract the HTML content after JS rendering
                logger.info('Extracting page content')
                content = await page.content()

                # Save HTML for debugging using tempfile for security
                with tempfile.NamedTemporaryFile(
                    prefix='terraform_aws_debug_playwright_',
                    suffix='.html',
                    mode='w',
                    encoding='utf-8',
                    delete=False,
                ) as temp_file:
                    temp_file.write(content)
                    debug_file_path = temp_file.name
                logger.debug(f'Saved rendered HTML content to {debug_file_path}')

                # Parse the HTML
                soup: BeautifulSoup = BeautifulSoup(content, 'html.parser')

                # First try the specific provider-docs-menu-content selector
                menu_content = soup.select_one('.provider-docs-menu-content')

                if not menu_content:
                    logger.warning(
                        "Couldn't find the .provider-docs-menu-content element, trying alternatives"
                    )

                    # Try each selector that might contain the menu
                    for selector in selectors:
                        menu_content = soup.select_one(selector)
                        if menu_content:
                            logger.info(f'Found menu content with selector: {selector}')
                            break

                    # If still not found, look for any substantial navigation
                    if not menu_content:
                        logger.warning("Still couldn't find navigation using standard selectors")

                        # Try to find any element with many links as a potential menu
                        potential_menus: List[Tuple[Tag, int]] = []
                        for elem in soup.find_all(['div', 'nav', 'ul']):
                            if isinstance(elem, Tag):  # Type guard to ensure elem is a Tag
                                links = elem.find_all('a')
                                if (
                                    len(links) > 10
                                ):  # Any element with many links might be navigation
                                    potential_menus.append((elem, len(links)))

                        # Sort by number of links, highest first
                        potential_menus.sort(key=lambda x: x[1], reverse=True)

                        if potential_menus:
                            menu_content = potential_menus[0][0]
                            logger.info(
                                f'Using element with {potential_menus[0][1]} links as menu'
                            )

                    # If we still have nothing, use fallback
                    if not menu_content:
                        logger.error("Couldn't find any navigation element, using fallback data")
                        await browser.close()
                        return cast(
                            ProviderResult,
                            {'categories': get_fallback_resource_data(), 'version': 'unknown'},
                        )

                # Find all category titles (excluding 'guides' and 'functions')
                category_titles = menu_content.select('.menu-list-category-link-title')

                if not category_titles:
                    logger.error("Couldn't find any .menu-list-category-link-title elements")
                    await browser.close()
                    return cast(
                        ProviderResult,
                        {'categories': get_fallback_resource_data(), 'version': 'unknown'},
                    )

                logger.info(f'Found {len(category_titles)} category titles')

                # First collect all categories that we need to process
                categories_to_process = []
                for category_el in category_titles:
                    category_name = category_el.get_text(strip=True)

                    # Skip non-service entries like 'Guides' and 'Functions'
                    if category_name.lower() in ['guides', 'functions', 'aws provider']:
                        logger.debug(f'Skipping category: {category_name}')
                        continue

                    logger.debug(f'Will process category: {category_name}')
                    categories_to_process.append((category_name, category_el))

                    # Initialize category entry
                    categories[category_name] = {'resources': [], 'data_sources': []}

                # Process a smaller set of categories if there are too many (for testing/development)
                MAX_CATEGORIES = int(os.environ.get('MAX_CATEGORIES', '999'))
                if len(categories_to_process) > MAX_CATEGORIES:
                    logger.info(
                        f'Limiting to {MAX_CATEGORIES} categories (from {len(categories_to_process)})'
                    )
                    categories_to_process = categories_to_process[:MAX_CATEGORIES]

                logger.info(
                    f'Processing {len(categories_to_process)} categories with click interaction'
                )

                # Now process each category by clicking on it first
                for category_idx, (category_name, category_el) in enumerate(categories_to_process):
                    try:
                        # Get the DOM path or some identifier for this category
                        # Try to find a unique identifier for the category to click on
                        # First, try to get the href attribute from the parent <a> tag
                        href = None
                        parent_a = category_el.parent
                        if parent_a and parent_a.name == 'a':
                            href = parent_a.get('href')

                        logger.info(
                            f'[{category_idx + 1}/{len(categories_to_process)}] Clicking on category: {category_name}'
                        )

                        # Handle potential cookie consent banner interference
                        try:
                            # Check if banner reappeared
                            consent_banner = await page.query_selector('#consent-banner')
                            if consent_banner:
                                logger.info(
                                    'Cookie consent banner detected again, removing via JavaScript'
                                )
                                await page.evaluate("""() => {
                                    const banner = document.getElementById('consent-banner');
                                    if (banner) banner.remove();
                                    return true;
                                }""")
                        except Exception:
                            pass  # Ignore errors in this extra banner check

                        # Click with increased timeout and multiple attempts
                        click_success = False
                        click_attempts = 0
                        max_attempts = 3

                        while not click_success and click_attempts < max_attempts:
                            click_attempts += 1
                            try:
                                if href:
                                    # If we have an href, use that to locate the element
                                    try:
                                        selector = f"a[href='{href}']"
                                        await page.click(
                                            selector, timeout=8000
                                        )  # Increased timeout
                                        logger.debug(
                                            f'Clicked category using href selector: {selector}'
                                        )
                                        click_success = True
                                    except Exception as click_error:
                                        logger.warning(
                                            f'Failed to click using href, trying text: {click_error}'
                                        )
                                        # If that fails, try to click by text content
                                        escaped_name = category_name.replace("'", "\\'")
                                        await page.click(
                                            f"text='{escaped_name}'", timeout=8000
                                        )  # Increased timeout
                                        click_success = True
                                else:
                                    # Otherwise try to click by text content
                                    escaped_name = category_name.replace("'", "\\'")
                                    await page.click(
                                        f"text='{escaped_name}'", timeout=8000
                                    )  # Increased timeout
                                    click_success = True

                            except Exception as click_error:
                                logger.warning(
                                    f'Click attempt {click_attempts} failed for {category_name}: {click_error}'
                                )
                                if click_attempts >= max_attempts:
                                    logger.error(
                                        f'Failed to click category {category_name} after {max_attempts} attempts'
                                    )
                                    # Don't break the loop, continue with next category
                                    raise click_error

                                # Try removing any overlays before next attempt
                                try:
                                    await page.evaluate("""() => {
                                        // Remove common overlay patterns
                                        document.querySelectorAll('[id*="banner"],[id*="overlay"],[id*="popup"],[class*="banner"],[class*="overlay"],[class*="popup"]')
                                            .forEach(el => el.remove());
                                        return true;
                                    }""")
                                    await asyncio.sleep(0.5)  # Brief pause between attempts
                                except Exception:
                                    pass  # Ignore errors in overlay removal

                        # Wait briefly for content to load
                        await asyncio.sleep(0.3)

                        # Extract resources and data sources from the now-expanded category
                        # We need to use the HTML structure to locate the specific sections for this category
                        try:
                            # Get the updated HTML after clicking
                            current_html = await page.content()
                            current_soup = BeautifulSoup(current_html, 'html.parser')

                            resource_count = 0
                            data_source_count = 0

                            # Find the clicked category element in the updated DOM
                            # This is important because the structure changes after clicking
                            # First, find the category span by its text
                            category_spans = current_soup.find_all(
                                'span', class_='menu-list-category-link-title'
                            )
                            clicked_category_span = None
                            for span in category_spans:
                                if span.get_text(strip=True) == category_name:
                                    clicked_category_span = span
                                    break

                            if not clicked_category_span:
                                logger.warning(
                                    f'Could not find clicked category {category_name} in updated DOM'
                                )
                                continue

                            # Navigate up to find the parent LI, which contains all content for this category
                            parent_li = clicked_category_span.find_parent('li')
                            if not parent_li:
                                logger.warning(
                                    f'Could not find parent LI for category {category_name}'
                                )
                                continue

                            # Find the ul.menu-list that contains both Resources and Data Sources sections
                            category_menu_list = safe_find(
                                parent_li, 'ul', attrs={'class': 'menu-list'}
                            )
                            if not category_menu_list:
                                logger.warning(
                                    f'Could not find menu-list for category {category_name}'
                                )
                                continue

                            # Process Resources section
                            # Find the span with text "Resources"
                            resource_spans = category_menu_list.find_all(
                                'span', class_='menu-list-category-link-title'
                            )
                            resource_section = None
                            for span in resource_spans:
                                if span.get_text(strip=True) == 'Resources':
                                    # Use parent property safely to find parent li
                                    parent_elem = span
                                    resource_section_li = None
                                    while parent_elem and parent_elem.parent:
                                        parent_elem = parent_elem.parent
                                        if (
                                            isinstance(parent_elem, Tag)
                                            and parent_elem.name == 'li'
                                        ):
                                            resource_section_li = parent_elem
                                            break

                                    if resource_section_li:
                                        resource_section = safe_find(
                                            resource_section_li, 'ul', attrs={'class': 'menu-list'}
                                        )
                                    break

                            # Extract resources
                            if resource_section:
                                resource_links = safe_find_all(
                                    resource_section, 'li', class_='menu-list-link'
                                )
                                for item in resource_links:
                                    link = safe_find(item, 'a')
                                    if not isinstance(link, Tag):
                                        continue

                                    # Safely get href attribute
                                    href = None
                                    if hasattr(link, 'attrs') and 'href' in link.attrs:
                                        href = link.attrs['href']
                                    if not href:
                                        continue

                                    link_text = safe_get_text(link, strip=True)
                                    if not link_text:
                                        continue

                                    # Complete the URL if it's a relative path
                                    full_url = (
                                        f'https://registry.terraform.io{href}'
                                        if isinstance(href, str) and href.startswith('/')
                                        else href
                                    )

                                    # Add to resources
                                    resource = {
                                        'name': link_text,
                                        'url': full_url,
                                        'type': 'resource',
                                    }

                                    categories[category_name]['resources'].append(resource)
                                    resource_count += 1

                            # Process Data Sources section
                            # Find the span with text "Data Sources"
                            data_spans = category_menu_list.find_all(
                                'span', class_='menu-list-category-link-title'
                            )
                            data_section = None
                            for span in data_spans:
                                if span.get_text(strip=True) == 'Data Sources':
                                    # Use parent property safely to find parent li
                                    parent_elem = span
                                    data_section_li = None
                                    while parent_elem and parent_elem.parent:
                                        parent_elem = parent_elem.parent
                                        if (
                                            isinstance(parent_elem, Tag)
                                            and parent_elem.name == 'li'
                                        ):
                                            data_section_li = parent_elem
                                            break

                                    if data_section_li:
                                        data_section = safe_find(
                                            data_section_li, 'ul', attrs={'class': 'menu-list'}
                                        )
                                    break

                            # Extract data sources
                            if data_section:
                                data_links = safe_find_all(
                                    data_section, 'li', class_='menu-list-link'
                                )
                                for item in data_links:
                                    link = safe_find(item, 'a')
                                    if not isinstance(link, Tag):
                                        continue

                                    # Safely get href attribute
                                    href = None
                                    if hasattr(link, 'attrs') and 'href' in link.attrs:
                                        href = link.attrs['href']
                                    if not href:
                                        continue

                                    link_text = safe_get_text(link, strip=True)
                                    if not link_text:
                                        continue

                                    # Complete the URL if it's a relative path
                                    full_url = (
                                        f'https://registry.terraform.io{href}'
                                        if isinstance(href, str) and href.startswith('/')
                                        else href
                                    )

                                    # Add to data sources
                                    data_source = {
                                        'name': link_text,
                                        'url': full_url,
                                        'type': 'data_source',
                                    }

                                    categories[category_name]['data_sources'].append(data_source)
                                    data_source_count += 1

                            logger.info(
                                f'Category {category_name}: found {resource_count} resources, {data_source_count} data sources'
                            )

                        except Exception as extract_error:
                            logger.error(
                                f'Error extracting resources for {category_name}: {extract_error}'
                            )

                    except Exception as click_error:
                        logger.warning(
                            f'Error interacting with category {category_name}: {click_error}'
                        )

                # Close the browser
                await browser.close()

                # Count statistics for logging
                service_count = len(categories)
                resource_count = sum(len(cat['resources']) for cat in categories.values())
                data_source_count = sum(len(cat['data_sources']) for cat in categories.values())

                duration = time.time() - start_time
                logger.info(
                    f'Extracted {service_count} service categories with {resource_count} resources and {data_source_count} data sources in {duration:.2f} seconds'
                )

                # Return the structure if we have data
                if service_count > 0:
                    return {'categories': categories, 'version': provider_version}
                else:
                    logger.warning('No categories found, using fallback data')
                    return {'categories': get_fallback_resource_data(), 'version': 'unknown'}

        except Exception as e:
            logger.error(f'Error extracting AWS provider resources: {str(e)}')
            # Return fallback data in case of error
            return cast(
                ProviderResult, {'categories': get_fallback_resource_data(), 'version': 'unknown'}
            )


def get_fallback_resource_data() -> Dict[str, CategoryData]:
    """Provide fallback resource data in case the scraping fails.

    Returns:
        A dictionary with pre-defined AWS resources and data sources
    """
    logger.warning('Using pre-defined resource structure as fallback')

    # Pre-defined structure of AWS services and their resources/data sources
    categories: Dict[str, CategoryData] = {
        'ACM (Certificate Manager)': {
            'resources': [
                {
                    'name': 'aws_acm_certificate',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acm_certificate',
                    'type': 'resource',
                },
                {
                    'name': 'aws_acm_certificate_validation',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acm_certificate_validation',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_acm_certificate',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/acm_certificate',
                    'type': 'data_source',
                }
            ],
        },
        'API Gateway': {
            'resources': [
                {
                    'name': 'aws_api_gateway_account',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_account',
                    'type': 'resource',
                },
                {
                    'name': 'aws_api_gateway_api_key',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_api_key',
                    'type': 'resource',
                },
                {
                    'name': 'aws_api_gateway_authorizer',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_authorizer',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_api_gateway_api_key',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_api_key',
                    'type': 'data_source',
                }
            ],
        },
        'AMP (Managed Prometheus)': {
            'resources': [
                {
                    'name': 'aws_prometheus_workspace',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_workspace',
                    'type': 'resource',
                },
                {
                    'name': 'aws_prometheus_alert_manager_definition',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_alert_manager_definition',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_prometheus_workspace',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/prometheus_workspace',
                    'type': 'data_source',
                }
            ],
        },
        'CloudWatch': {
            'resources': [
                {
                    'name': 'aws_cloudwatch_metric_alarm',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_metric_alarm',
                    'type': 'resource',
                },
                {
                    'name': 'aws_cloudwatch_log_group',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_cloudwatch_log_group',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_log_group',
                    'type': 'data_source',
                }
            ],
        },
        'EC2': {
            'resources': [
                {
                    'name': 'aws_instance',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance',
                    'type': 'resource',
                },
                {
                    'name': 'aws_security_group',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group',
                    'type': 'resource',
                },
                {
                    'name': 'aws_vpc',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc',
                    'type': 'resource',
                },
                {
                    'name': 'aws_subnet',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_instance',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/instance',
                    'type': 'data_source',
                },
                {
                    'name': 'aws_vpc',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc',
                    'type': 'data_source',
                },
            ],
        },
        'IAM': {
            'resources': [
                {
                    'name': 'aws_iam_role',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role',
                    'type': 'resource',
                },
                {
                    'name': 'aws_iam_policy',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy',
                    'type': 'resource',
                },
                {
                    'name': 'aws_iam_user',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_iam_role',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_role',
                    'type': 'data_source',
                },
                {
                    'name': 'aws_iam_policy',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy',
                    'type': 'data_source',
                },
            ],
        },
        'Lambda': {
            'resources': [
                {
                    'name': 'aws_lambda_function',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function',
                    'type': 'resource',
                },
                {
                    'name': 'aws_lambda_permission',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_lambda_function',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_function',
                    'type': 'data_source',
                }
            ],
        },
        'S3': {
            'resources': [
                {
                    'name': 'aws_s3_bucket',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket',
                    'type': 'resource',
                },
                {
                    'name': 'aws_s3_bucket_policy',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_policy',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_s3_bucket',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket',
                    'type': 'data_source',
                },
                {
                    'name': 'aws_s3_object',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_object',
                    'type': 'data_source',
                },
            ],
        },
        'DynamoDB': {
            'resources': [
                {
                    'name': 'aws_dynamodb_table',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table',
                    'type': 'resource',
                },
                {
                    'name': 'aws_dynamodb_table_item',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table_item',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_dynamodb_table',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dynamodb_table',
                    'type': 'data_source',
                }
            ],
        },
        'Route53': {
            'resources': [
                {
                    'name': 'aws_route53_zone',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_zone',
                    'type': 'resource',
                },
                {
                    'name': 'aws_route53_record',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_record',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_route53_zone',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_zone',
                    'type': 'data_source',
                }
            ],
        },
        'SNS': {
            'resources': [
                {
                    'name': 'aws_sns_topic',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic',
                    'type': 'resource',
                },
                {
                    'name': 'aws_sns_topic_subscription',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_subscription',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_sns_topic',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sns_topic',
                    'type': 'data_source',
                }
            ],
        },
        'SQS': {
            'resources': [
                {
                    'name': 'aws_sqs_queue',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue',
                    'type': 'resource',
                },
                {
                    'name': 'aws_sqs_queue_policy',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue_policy',
                    'type': 'resource',
                },
            ],
            'data_sources': [
                {
                    'name': 'aws_sqs_queue',
                    'url': 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sqs_queue',
                    'type': 'data_source',
                }
            ],
        },
    }

    return categories


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
        # markdown.append('## Table of Contents')
        # for category in sorted_categories:
        #     sanitized_category = (
        #         category.replace(' ', '-').replace('(', '').replace(')', '').lower()
        #     )
        #     markdown.append(f'- [{category}](#{sanitized_category})')
        # markdown.append('')

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
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown))

        print(f'Successfully generated markdown file at: {args.output}')
        print(f'Generation completed in {duration.total_seconds():.2f} seconds')
        return 0

    except Exception as e:
        print(f'Error generating AWS provider resources: {str(e)}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
