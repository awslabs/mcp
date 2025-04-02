"""CDK Nag rules parsing utilities."""

import httpx
import re
import urllib.parse
from typing import Any, Dict, Optional, Tuple


# Constants
CDK_NAG_RULES_URL = 'https://raw.githubusercontent.com/cdklabs/cdk-nag/main/RULES.md'


# Helper functions
async def fetch_cdk_nag_content() -> str:
    """Fetch the CDK Nag rules content from GitHub.

    Returns:
        The raw content of the RULES.md file from the CDK Nag repository.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(CDK_NAG_RULES_URL)
        return response.text


def extract_rule_pack_section(content: str, rule_pack: str) -> str:
    """Extract a specific rule pack section from the content.

    Args:
        content: The full content of the RULES.md file.
        rule_pack: The name of the rule pack to extract.

    Returns:
        The section of the content for the specified rule pack.
        If the rule pack is not found, returns an error message.
    """
    # Use a direct string search approach
    start_marker = f'## {rule_pack}'
    start_pos = content.find(start_marker)

    if start_pos < 0:
        return f"Rule pack '{rule_pack}' not found in CDK Nag documentation."

    # Find the next section heading
    next_section_pos = content.find('\n## ', start_pos + len(start_marker))

    if next_section_pos >= 0:
        rule_pack_section = content[start_pos:next_section_pos]
    else:
        # If no next section, take until the end of the content
        rule_pack_section = content[start_pos:]

    return rule_pack_section


def extract_section_by_marker(section: str, marker: str) -> Tuple[bool, str]:
    """Extract a subsection based on a marker (e.g., '### Warnings').

    Args:
        section: The section to extract from.
        marker: The marker to look for (e.g., '### Warnings').

    Returns:
        A tuple containing:
        - A boolean indicating whether the marker was found.
        - The extracted subsection if found, or an error message if not found.
    """
    marker_pos = section.find(marker)

    if marker_pos < 0:
        return False, f'No {marker.lstrip("#").strip()} found.'

    # Find the next subsection heading
    next_subsection_pos = section.find('\n### ', marker_pos + len(marker))

    if next_subsection_pos >= 0:
        subsection = section[marker_pos:next_subsection_pos]
    else:
        # If no next subsection, take until the end of the section
        subsection = section[marker_pos:]

    return True, subsection


def extract_rule_info(content: str, rule_id: str) -> Optional[Dict[str, str]]:
    """Extract information about a specific rule from the content.

    Args:
        content: The full content of the RULES.md file.
        rule_id: The ID of the rule to extract information for.

    Returns:
        A dictionary containing the rule information, or None if the rule is not found.
    """
    # Find the rule in the table
    # The table format is: | Rule ID | Cause | Explanation | [Relevant Control ID(s)] |
    pattern = rf'\|\s*{re.escape(rule_id)}\s*\|(.*?)\|(.*?)\|'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return None

    result = {
        'rule_id': rule_id,
        'cause': match.group(1).strip(),
        'explanation': match.group(2).strip(),
    }

    # Check if there's a fourth column (Relevant Control ID(s))
    control_pattern = rf'\|\s*{re.escape(rule_id)}\s*\|(.*?)\|(.*?)\|(.*?)\|'
    control_match = re.search(control_pattern, content, re.DOTALL)

    if control_match and len(control_match.groups()) >= 3:
        result['control_ids'] = control_match.group(3).strip()

    return result


def format_rule_info(rule_info: Optional[Dict[str, str]]) -> str:
    """Format rule information as a markdown string.

    Args:
        rule_info: A dictionary containing rule information.

    Returns:
        A formatted markdown string.
    """
    if not rule_info:
        return 'Rule information not found.'

    result = f'# {rule_info["rule_id"]}\n\n'
    result += f'## Cause\n\n{rule_info["cause"]}\n\n'
    result += f'## Explanation\n\n{rule_info["explanation"]}\n\n'

    if 'control_ids' in rule_info:
        result += f'## Relevant Control ID(s)\n\n{rule_info["control_ids"]}\n\n'

    return result


# Main functions
async def get_rule_pack(rule_pack: str) -> str:
    """Get the full content for a rule pack.

    Args:
        rule_pack: The name of the rule pack to get.

    Returns:
        The full content for the specified rule pack.
    """
    # Decode the rule pack name if it's URL-encoded
    rule_pack = urllib.parse.unquote(rule_pack)

    # Fetch the content
    content = await fetch_cdk_nag_content()

    # Extract the section for this rule pack
    return extract_rule_pack_section(content, rule_pack)


async def get_warnings(rule_pack: str) -> str:
    """Get only the warnings section for a rule pack.

    Args:
        rule_pack: The name of the rule pack to get warnings for.

    Returns:
        The warnings section for the specified rule pack.
    """
    # Decode the rule pack name if it's URL-encoded
    rule_pack = urllib.parse.unquote(rule_pack)

    # Fetch the content
    content = await fetch_cdk_nag_content()

    # Extract the section for this rule pack
    rule_pack_section = extract_rule_pack_section(content, rule_pack)

    # Check if we got an error message
    if rule_pack_section.startswith(f"Rule pack '{rule_pack}' not found"):
        return rule_pack_section

    # Extract the warnings section
    found, warnings_section = extract_section_by_marker(rule_pack_section, '### Warnings')

    if not found:
        return f"No warnings found for rule pack '{rule_pack}'."

    return warnings_section


async def get_errors(rule_pack: str) -> str:
    """Get only the errors section for a rule pack.

    Args:
        rule_pack: The name of the rule pack to get errors for.

    Returns:
        The errors section for the specified rule pack.
    """
    # Decode the rule pack name if it's URL-encoded
    rule_pack = urllib.parse.unquote(rule_pack)

    # Fetch the content
    content = await fetch_cdk_nag_content()

    # Extract the section for this rule pack
    rule_pack_section = extract_rule_pack_section(content, rule_pack)

    # Check if we got an error message
    if rule_pack_section.startswith(f"Rule pack '{rule_pack}' not found"):
        return rule_pack_section

    # Extract the errors section
    found, errors_section = extract_section_by_marker(rule_pack_section, '### Errors')

    if not found:
        return f"No errors found for rule pack '{rule_pack}'."

    return errors_section


async def get_rule(rule_id: str) -> str:
    """Get information about a specific rule.

    Args:
        rule_id: The ID of the rule to get information for.

    Returns:
        A formatted string containing information about the rule.
    """
    # Fetch the content
    content = await fetch_cdk_nag_content()

    # Extract the rule information
    rule_info = extract_rule_info(content, rule_id)

    # Format the rule information
    if rule_info:
        return format_rule_info(rule_info)
    else:
        return f'Rule {rule_id} not found in CDK Nag documentation.'


def check_cdk_nag_suppressions(
    code: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if CDK code contains Nag suppressions that require human review.

    This function scans TypeScript/JavaScript code for any instances of NagSuppressions being used
    and flags them for human review. It helps ensure that security suppressions are only
    applied with proper human oversight and justification.

    Args:
        code: CDK code to analyze (TypeScript/JavaScript)
        file_path: Path to a file containing CDK code to analyze

    Returns:
        Dictionary with analysis results including:
        - has_suppressions: Whether suppressions were found
        - suppressions: List of detected suppressions with line numbers and context
        - recommendation: Security guidance for human developers
    """
    # Validate input parameters
    if code is None and file_path is None:
        return {'error': 'Either code or file_path must be provided', 'status': 'error'}

    if code is not None and file_path is not None:
        return {'error': 'Only one of code or file_path should be provided', 'status': 'error'}

    # If file_path is provided, read the file content
    if file_path is not None:
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            return {'error': f'Failed to read file: {str(e)}', 'status': 'error'}

    # Ensure code is not None at this point
    if code is None:
        code = ''  # Default to empty string if somehow still None

    # Define patterns to look for
    patterns = [
        (
            r'import\s+{\s*.*NagSuppressions.*\s*}\s+from\s+[\'"]cdk-nag[\'"]',
            'NagSuppressions import',
        ),
        (r'NagSuppressions\.addStackSuppressions', 'Stack-level suppression'),
        (r'NagSuppressions\.addResourceSuppressions', 'Resource-level suppression'),
        (r'NagSuppressions\.addResourceSuppressionsByPath', 'Path-based suppression'),
    ]

    # Find all matches
    suppressions_found = []
    lines = code.split('\n')

    for i, line in enumerate(lines):
        for pattern, suppression_type in patterns:
            if re.search(pattern, line):
                # Get context (3 lines before and after)
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                context = '\n'.join(lines[start:end])

                suppressions_found.append(
                    {
                        'line_number': i + 1,
                        'line': line.strip(),
                        'type': suppression_type,
                        'context': context,
                    }
                )

    # Generate response
    if suppressions_found:
        return {
            'has_suppressions': True,
            'suppressions': suppressions_found,
            'recommendation': '⚠️ SECURITY ALERT: This code contains CDK Nag suppressions that require human review.',
            'action_required': 'Review each suppression and ensure it has proper justification.',
            'security_impact': 'CDK Nag suppressions can bypass important security checks. Each suppression should be carefully reviewed by a human developer and have a documented justification.',
            'best_practice': 'Fix the underlying security issue rather than suppressing the warning whenever possible.',
            'status': 'success',
        }
    else:
        return {
            'has_suppressions': False,
            'message': 'No CDK Nag suppressions detected in the provided code.',
            'status': 'success',
        }
