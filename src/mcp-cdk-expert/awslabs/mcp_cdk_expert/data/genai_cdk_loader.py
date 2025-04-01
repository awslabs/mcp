"""GenAI CDK constructs static content loader."""

import logging
import os
from awslabs.mcp_cdk_expert.data.construct_descriptions import get_construct_descriptions
from enum import Enum
from typing import Any, Dict, List, Optional


# Set up logging
logger = logging.getLogger(__name__)


class ConstructType(str, Enum):
    """GenAI CDK construct types."""

    BEDROCK = 'bedrock'
    OPENSEARCH_SERVERLESS = 'opensearchserverless'
    OPENSEARCH_VECTOR_INDEX = 'opensearch-vectorindex'


def get_construct_types() -> List[str]:
    """Get a list of available construct types."""
    return [ct.value for ct in ConstructType]


def get_construct_map() -> Dict[str, str]:
    """Get a dictionary mapping construct types to their descriptions."""
    return {
        'bedrock': 'Amazon Bedrock constructs for agents, knowledge bases, and more',
        'opensearchserverless': 'Amazon OpenSearch Serverless constructs for vector search',
        'opensearch-vectorindex': 'Amazon OpenSearch vector index constructs',
    }


def get_genai_cdk_overview(construct_type: str = '') -> str:
    """Get an overview of GenAI CDK constructs.

    Args:
        construct_type: Optional construct type to get overview for.
                       If empty, returns the best practices.

    Returns:
        The overview content as a string.
    """
    # Normalize construct type
    construct_type = construct_type.lower()

    # Validate construct type
    if construct_type not in get_construct_types():
        construct_list = '\n'.join([f'- {t}: {desc}' for t, desc in get_construct_map().items()])
        return f"# GenAI CDK Constructs\n\nConstruct type '{construct_type}' not found. Available types:\n\n{construct_list}"

    # Get overview file
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
        'static',
        'genai_cdk',
        construct_type,
        'overview.md',
    )
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Overview file for '{construct_type}' not found."


def list_available_sections(construct_type: str, construct_name: str) -> List[str]:
    """List available sections for a specific construct.

    Args:
        construct_type: The construct type (e.g., 'bedrock')
        construct_name: The name of the construct (e.g., 'agent', 'knowledgebases')

    Returns:
        List of available sections.
    """
    sections = []
    base_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
        'static',
        'genai_cdk',
        construct_type,
        construct_name,
    )

    if not os.path.exists(base_path):
        return sections

    # Walk through the directory structure
    for root, dirs, files in os.walk(base_path):
        rel_path = os.path.relpath(root, base_path)

        for file in files:
            if file.endswith('.md') and file != 'overview.md':
                section_name = file[:-3]  # Remove .md extension

                # For files in the base directory
                if rel_path == '.':
                    sections.append(section_name)
                else:
                    # For files in subdirectories
                    if rel_path != '.':
                        section_path = os.path.join(rel_path, section_name)
                        # Replace backslashes with forward slashes for consistency
                        section_path = section_path.replace('\\', '/')
                        sections.append(section_path)

    return sections


def get_genai_cdk_construct_section(construct_type: str, construct_name: str, section: str) -> str:
    """Get a specific section of documentation for a GenAI CDK construct.

    Args:
        construct_type: The construct type (e.g., 'bedrock')
        construct_name: The name of the construct (e.g., 'agent', 'knowledgebases')
        section: The section name (e.g., 'actiongroups', 'vector/opensearch')

    Returns:
        The section documentation as a string.
    """
    # Normalize inputs
    construct_type = construct_type.lower()
    construct_name_lower = construct_name.lower()

    # Special handling for Agent_* and Knowledgebases_* constructs
    if construct_name_lower.startswith('agent_'):
        # Convert Agent_actiongroups to agent/actiongroups
        construct_name_lower = 'agent'
        section = construct_name_lower.split('_', 1)[1]
    elif construct_name_lower.startswith('knowledgebases_'):
        # Convert Knowledgebases_vector_opensearch to knowledgebases/vector/opensearch
        parts = construct_name_lower.split('_', 1)
        if len(parts) > 1:
            construct_name_lower = parts[0]
            # Handle nested paths with underscores (e.g., vector_opensearch -> vector/opensearch)
            section_parts = parts[1].split('_')
            if len(section_parts) > 1 and section_parts[0] == 'vector':
                # Special case for vector/* sections which are in a nested directory
                section = f'vector/{section_parts[1]}'
            else:
                section = parts[1]

    # Validate construct type
    if construct_type not in get_construct_types():
        return f"Error: Construct type '{construct_type}' not found."

    # Handle nested sections (e.g., vector/opensearch)
    if '/' in section:
        section_parts = section.split('/')
        file_path = (
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
                'static',
                'genai_cdk',
                construct_type,
                construct_name_lower,
                *section_parts,
            )
            + '.md'
        )
    else:
        # Regular section
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
            'static',
            'genai_cdk',
            construct_type,
            construct_name_lower,
            f'{section}.md',
        )

    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return (
            f"Error: Section '{section}' for '{construct_name}' in '{construct_type}' not found."
        )


def get_genai_cdk_construct(construct_type: str, construct_name: str) -> str:
    """Get documentation for a specific GenAI CDK construct.

    Args:
        construct_type: The construct type (e.g., 'bedrock')
        construct_name: The name of the construct (e.g., 'Agent')

    Returns:
        The construct documentation as a string.
    """
    # Normalize inputs
    construct_type = construct_type.lower()
    construct_name_lower = construct_name.lower()

    # Special handling for Agent_* and Knowledgebases_* constructs
    if construct_name_lower.startswith('agent_'):
        # For Agent_actiongroups, redirect to agent/actiongroups section
        parent = 'agent'
        child = construct_name_lower.split('_', 1)[1]
        return get_genai_cdk_construct_section(construct_type, parent, child)
    elif construct_name_lower.startswith('knowledgebases_'):
        # For Knowledgebases_vector_opensearch, redirect to knowledgebases/vector/opensearch section
        parts = construct_name_lower.split('_', 1)
        if len(parts) > 1:
            parent = parts[0]
            # Handle nested paths with underscores (e.g., vector_opensearch -> vector/opensearch)
            section_parts = parts[1].split('_')
            if len(section_parts) > 1 and section_parts[0] == 'vector':
                # Special case for vector/* sections which are in a nested directory
                child = f'vector/{section_parts[1]}'
            else:
                child = parts[1]
            return get_genai_cdk_construct_section(construct_type, parent, child)

    # Special handling for agent and knowledgebases
    if construct_name_lower in ['agent', 'knowledgebases']:
        # For these special cases, return an overview or index of available sections
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
            'static',
            'genai_cdk',
            construct_type,
            construct_name_lower,
        )

        # Check if directory exists
        if not os.path.exists(base_path):
            return f"Error: Documentation for '{construct_name}' in '{construct_type}' not found."

        # List files in directory
        sections = []
        for file_name in os.listdir(base_path):
            if file_name.endswith('.md') and file_name != 'overview.md':
                sections.append(file_name[:-3])  # Remove .md extension

        # Also check subdirectories
        for root, dirs, files in os.walk(base_path):
            if root != base_path:  # Skip the base directory
                rel_path = os.path.relpath(root, base_path)
                for file_name in files:
                    if file_name.endswith('.md'):
                        section_path = os.path.join(rel_path, file_name[:-3])
                        section_path = section_path.replace('\\', '/')
                        sections.append(section_path)

        result = f'# {construct_name.capitalize()} Documentation\n\n'
        result += 'This documentation is split into sections for easier consumption.\n\n'
        result += '## Available Sections\n\n'

        for section in sorted(sections):
            result += f'- [{section}](genai-cdk-constructs://{construct_type}/{construct_name_lower}/{section})\n'

        return result

    # Special handling for key constructs
    key_construct_mapping = {
        'agent': 'agent',
        'agents': 'agent',
        'knowledgebase': 'knowledgebases',
        'knowledgebases': 'knowledgebases',
        'knowledge-base': 'knowledgebases',
        'knowledge-bases': 'knowledgebases',
        'agentactiongroup': 'agent/actiongroups',
        'action-group': 'agent/actiongroups',
        'actiongroup': 'agent/actiongroups',
        'agentalias': 'agent/alias',
        'guardrail': 'bedrockguardrails',
        'guardrails': 'bedrockguardrails',
        'bedrock-guardrails': 'bedrockguardrails',
    }

    # Normalize construct name
    if construct_name_lower in key_construct_mapping:
        mapped_name = key_construct_mapping[construct_name_lower]
        if '/' in mapped_name:
            # Handle redirects to sections
            parent, section = mapped_name.split('/', 1)
            return get_genai_cdk_construct_section(construct_type, parent, section)
        else:
            construct_name_lower = mapped_name

    # Validate construct type
    if construct_type not in get_construct_types():
        construct_list = '\n'.join([f'- {t}: {desc}' for t, desc in get_construct_map().items()])
        return f"# GenAI CDK Constructs\n\nConstruct type '{construct_type}' not found. Available types:\n\n{construct_list}"

    # Get construct file (flat structure)
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # Fix path to use parent directory
        'static',
        'genai_cdk',
        construct_type,
        f'{construct_name_lower}.md',
    )
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Try to see if this is a directory with an overview.md file
        overview_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static',
            'genai_cdk',
            construct_type,
            construct_name_lower,
            'overview.md',
        )
        try:
            with open(overview_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: Documentation for '{construct_name}' in '{construct_type}' not found."


def list_available_constructs(construct_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available constructs.

    Args:
        construct_type: Optional construct type to filter by.

    Returns:
        List of constructs with name, type, and description.
    """
    constructs = []

    # Determine which construct types to search
    construct_types = [construct_type.lower()] if construct_type else get_construct_types()

    # For each construct type, list files in the directory
    for ct in construct_types:
        if ct not in get_construct_types():
            continue

        # Get directory path - fix path to use parent directory
        dir_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'static', 'genai_cdk', ct
        )

        # Skip if directory doesn't exist
        if not os.path.exists(dir_path):
            continue

        # Process files in the main directory
        process_directory_files(dir_path, ct, constructs)

        # Process subdirectories recursively
        for root, dirs, files in os.walk(dir_path):
            # Skip the main directory as it's already processed
            if root == dir_path:
                continue

            # Get the relative path from the main directory
            rel_path = os.path.relpath(root, dir_path)
            # Use the relative path as the parent
            process_directory_files(root, ct, constructs, parent=rel_path.replace(os.sep, '_'))

    return constructs


def process_directory_files(
    dir_path: str, construct_type: str, constructs: List[Dict[str, Any]], parent: str = None
):
    """Process files in a directory and add them to the constructs list.

    Args:
        dir_path: Path to the directory
        construct_type: Type of construct
        constructs: List to add constructs to
        parent: Optional parent directory name
    """
    # List files in directory
    for file_name in os.listdir(dir_path):
        # Skip overview file, directories, and non-markdown files
        if (
            file_name == 'overview.md'
            or not file_name.endswith('.md')
            or os.path.isdir(os.path.join(dir_path, file_name))
        ):
            continue

        # Extract construct name from file name
        base_name = file_name[:-3]

        # Format the construct name
        if parent:
            construct_name = f'{parent}_{base_name}'
        else:
            construct_name = base_name

        display_name = construct_name.capitalize()

        # Define file_path here, before it's used
        file_path = os.path.join(dir_path, file_name)

        # Get description from fixed mapping or use default
        descriptions = get_construct_descriptions()
        description = descriptions.get(display_name, None)

        # If no fixed description, fall back to current behavior
        if description is None:
            try:
                with open(file_path, 'r') as f:
                    first_line = f.readline().strip()
                    description = (
                        first_line[1:].strip() if first_line.startswith('#') else display_name
                    )
            except Exception:
                description = f'A {construct_type} construct.'

        # Add to list
        constructs.append(
            {
                'name': display_name,
                'type': construct_type,
                'description': description,
            }
        )
