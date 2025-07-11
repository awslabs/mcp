"""Explanation generator for AWS resources."""

from typing import Any


def _format_value(value: Any) -> str:
    """Format any value for display."""
    if isinstance(value, str):
        return f'"{value[:100]}"' + ('...' if len(value) > 100 else '')
    elif isinstance(value, (int, float, bool)):
        return str(value)
    elif isinstance(value, dict):
        return f'{{dict with {len(value)} keys}}'
    elif isinstance(value, list):
        return f'[list with {len(value)} items]'
    else:
        return f'{type(value).__name__} object'


def _explain_dict(data: dict, format: str) -> str:
    """Explain dictionary content comprehensively."""
    explanation = f'**Configuration Summary:** Dictionary with {len(data)} properties\n\n'

    for key, value in data.items():
        if key.startswith('_'):
            continue

        if key == 'Tags' and isinstance(value, list):
            # Special handling for AWS tags
            explanation += f'**{key}:** ({len(value)} tags)\n'
            default_tags = []
            user_tags = []

            for tag in value:
                if isinstance(tag, dict):
                    tag_key = tag.get('Key', '')
                    tag_value = tag.get('Value', '')
                    if tag_key in ['MANAGED_BY', 'MCP_SERVER_SOURCE_CODE', 'MCP_SERVER_VERSION']:
                        default_tags.append(f'  • {tag_key}: {tag_value} (DEFAULT)')
                    else:
                        user_tags.append(f'  • {tag_key}: {tag_value}')

            if user_tags:
                explanation += '  *User Tags:*\n' + '\n'.join(user_tags) + '\n'
            if default_tags:
                explanation += '  *Management Tags:*\n' + '\n'.join(default_tags) + '\n'

        elif isinstance(value, dict):
            explanation += f'**{key}:** (Nested configuration with {len(value)} properties)\n'
            if format == 'detailed':
                for sub_key, sub_value in list(value.items())[:5]:
                    explanation += f'  • {sub_key}: {_format_value(sub_value)}\n'
                if len(value) > 5:
                    explanation += f'  • ... and {len(value) - 5} more properties\n'

        elif isinstance(value, list):
            explanation += f'**{key}:** (List with {len(value)} items)\n'
            if format == 'detailed' and value:
                for i, item in enumerate(value[:3]):
                    explanation += f'  • Item {i + 1}: {_format_value(item)}\n'
                if len(value) > 3:
                    explanation += f'  • ... and {len(value) - 3} more items\n'

        else:
            explanation += f'**{key}:** {_format_value(value)}\n'

        explanation += '\n'

    return explanation


def _explain_list(data: list, format: str) -> str:
    """Explain list content comprehensively."""
    explanation = f'**List Summary:** {len(data)} items\n\n'

    if format == 'detailed':
        for i, item in enumerate(data[:10]):  # Limit to first 10
            if isinstance(item, dict):
                explanation += f'**Item {i + 1}:** (Dictionary with {len(item)} keys)\n'
                for key, value in list(item.items())[:3]:
                    explanation += f'  • {key}: {_format_value(value)}\n'
                if len(item) > 3:
                    explanation += f'  • ... and {len(item) - 3} more properties\n'
            else:
                explanation += f'**Item {i + 1}:** {_format_value(item)}\n'
            explanation += '\n'

        if len(data) > 10:
            explanation += f'... and {len(data) - 10} more items\n'

    return explanation


def generate_explanation(
    content: Any, context: str, operation: str, format: str, user_intent: str
) -> str:
    """Generate comprehensive explanation for any type of content."""
    content_type = type(content).__name__

    # Build header
    if context:
        header = (
            f'## {context} - {operation.title()} Operation'
            if operation != 'analyze'
            else f'## {context} Analysis'
        )
    else:
        header = f'## Data Analysis ({content_type})'

    if user_intent:
        header += f'\n\n**User Intent:** {user_intent}'

    explanation = header + '\n\n'

    # Handle different content types
    if isinstance(content, dict):
        explanation += _explain_dict(content, format)
    elif isinstance(content, list):
        explanation += _explain_list(content, format)
    elif isinstance(content, str):
        explanation += f'**Content:** {content[:500]}{"..." if len(content) > 500 else ""}'
    elif isinstance(content, (int, float, bool)):
        explanation += f'**Value:** {content} ({content_type})'
    else:
        explanation += f'**Content Type:** {content_type}\n**Value:** {str(content)[:500]}'

    # Add operation-specific notes
    if operation in ['create', 'update', 'delete']:
        explanation += '\n\n**Infrastructure Operation Notes:**'
        explanation += '\n• This operation will modify AWS resources'
        explanation += '\n• Default management tags will be applied for tracking'
        explanation += '\n• Changes will be applied to the specified AWS region'

    return explanation