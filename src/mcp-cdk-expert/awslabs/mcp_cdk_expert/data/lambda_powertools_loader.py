"""Lambda Powertools guidance loader module."""

import os
from typing import Dict


def get_topic_map() -> Dict[str, str]:
    """Get a dictionary mapping topic names to their descriptions."""
    return {
        'index': 'Overview and table of contents',
        'logging': 'Structured logging implementation',
        'tracing': 'Tracing implementation',
        'metrics': 'Metrics implementation',
        'cdk': 'CDK integration patterns',
        'dependencies': 'Dependencies management',
        'insights': 'Lambda Insights integration',
        'bedrock': 'Bedrock Agent integration',
    }


def get_lambda_powertools_section(topic: str = '') -> str:
    """Get a specific section of the Lambda Powertools guidance.

    Args:
        topic: The topic to get guidance on. If empty or "index", returns the index.

    Returns:
        The guidance for the specified topic
    """
    topic_map = get_topic_map()

    # Handle the index case
    if not topic or topic.lower() == 'index':
        topic = 'index'

    if topic.lower() in topic_map:
        file_path = os.path.join(
            os.path.dirname(__file__), 'static', 'lambda_powertools', f'{topic.lower()}.md'
        )
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File for topic '{topic}' not found."
    else:
        # Topic not found
        topic_list = '\n'.join([f'- {t}: {desc}' for t, desc in topic_map.items() if t != 'index'])
        return f"# Lambda Powertools Guidance\n\nTopic '{topic}' not found. Available topics:\n\n{topic_list}"
