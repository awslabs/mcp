"""Utility functions for AWS Documentation MCP Server."""

import markdownify
import readabilipy.simple_json
from awslabs.aws_documentation_mcp_server.models import RecommendationResult
from typing import Any, Dict, List


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
    if not ret['content']:
        return '<e>Page failed to be simplified from HTML</e>'
    content = markdownify.markdownify(
        ret['content'],
        heading_style=markdownify.ATX,
    )
    return content


def is_html_content(page_raw: str, content_type: str) -> bool:
    """Determine if content is HTML.

    Args:
        page_raw: Raw page content
        content_type: Content-Type header

    Returns:
        True if content is HTML, False otherwise
    """
    return '<html' in page_raw[:100] or 'text/html' in content_type or not content_type


def format_documentation_result(url: str, content: str, start_index: int, max_length: int) -> str:
    """Format documentation result with pagination information.

    Args:
        url: Documentation URL
        content: Content to format
        start_index: Start index for pagination
        max_length: Maximum content length

    Returns:
        Formatted documentation result
    """
    original_length = len(content)

    if start_index >= original_length:
        return f'AWS Documentation from {url}:\n\n<e>No more content available.</e>'

    # Calculate the end index, ensuring we don't go beyond the content length
    end_index = min(start_index + max_length, original_length)
    truncated_content = content[start_index:end_index]

    if not truncated_content:
        return f'AWS Documentation from {url}:\n\n<e>No more content available.</e>'

    actual_content_length = len(truncated_content)
    remaining_content = original_length - (start_index + actual_content_length)

    result = f'AWS Documentation from {url}:\n\n{truncated_content}'

    # Only add the prompt to continue fetching if there is still remaining content
    if remaining_content > 0:
        next_start = start_index + actual_content_length
        result += f'\n\n<e>Content truncated. Call the read_documentation tool with start_index={next_start} to get more content.</e>'

    return result


def parse_recommendation_results(data: Dict[str, Any]) -> List[RecommendationResult]:
    """Parse recommendation API response into RecommendationResult objects.

    Args:
        data: Raw API response data

    Returns:
        List of recommendation results
    """
    results = []

    # Process highly rated recommendations
    if 'highlyRated' in data and 'items' in data['highlyRated']:
        for item in data['highlyRated']['items']:
            context = item.get('abstract') if 'abstract' in item else None

            results.append(
                RecommendationResult(
                    url=item.get('url', ''), title=item.get('assetTitle', ''), context=context
                )
            )

    # Process journey recommendations (organized by intent)
    if 'journey' in data and 'items' in data['journey']:
        for intent_group in data['journey']['items']:
            intent = intent_group.get('intent', '')
            if 'urls' in intent_group:
                for url_item in intent_group['urls']:
                    # Add intent as part of the context
                    context = f'Intent: {intent}' if intent else None

                    results.append(
                        RecommendationResult(
                            url=url_item.get('url', ''),
                            title=url_item.get('assetTitle', ''),
                            context=context,
                        )
                    )

    # Process new content recommendations
    if 'new' in data and 'items' in data['new']:
        for item in data['new']['items']:
            # Add "New content" label to context
            date_created = item.get('dateCreated', '')
            context = f'New content added on {date_created}' if date_created else 'New content'

            results.append(
                RecommendationResult(
                    url=item.get('url', ''), title=item.get('assetTitle', ''), context=context
                )
            )

    # Process similar recommendations
    if 'similar' in data and 'items' in data['similar']:
        for item in data['similar']['items']:
            context = item.get('abstract') if 'abstract' in item else 'Similar content'

            results.append(
                RecommendationResult(
                    url=item.get('url', ''), title=item.get('assetTitle', ''), context=context
                )
            )

    return results
