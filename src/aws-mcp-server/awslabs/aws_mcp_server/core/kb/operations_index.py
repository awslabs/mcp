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

import re
from ..aws.services import driver
from awscli.clidriver import ServiceCommand
from botocore import xform_name
from difflib import SequenceMatcher
from typing import Any


# Minimal stop words - keep domain-specific terms
skip_words = frozenset(
    {
        'the',
        'a',
        'an',
        'and',
        'or',
        'but',
        'in',
        'on',
        'at',
        'to',
        'for',
        'with',
        'by',
        'about',
        'as',
        'is',
        'are',
        'was',
        'were',
        'be',
        'been',
        'have',
        'has',
        'had',
        'do',
        'does',
        'did',
        'will',
        'would',
        'shall',
        'should',
        'can',
        'could',
        'may',
        'might',
        'must',
        'this',
        'that',
        'these',
        'those',
        'you',
        'your',
        'it',
        'its',
        'they',
        'them',
        'their',
    }
)


def _clean_text(text: str) -> str:
    """Clean and normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text."""
    text = _clean_text(text)
    words = text.split()

    return {word for word in words if word and len(word) > 1 and word not in skip_words}


def calculate_similarity(query: str, operation_description: str) -> float:
    """Calculate similarity between query and operation description."""
    if not operation_description:
        return 0.0

    query_clean = _clean_text(query)
    clean_description = _clean_text(operation_description)

    if not query_clean or not clean_description:
        return 0.0

    query_keywords = _extract_keywords(query_clean)
    desc_keywords = _extract_keywords(clean_description)

    if not query_keywords:
        return 0.0

    keyword_overlap = len(query_keywords.intersection(desc_keywords))
    keyword_score = keyword_overlap / len(query_keywords)

    sequence_score = SequenceMatcher(None, query_clean, clean_description).ratio()

    # Look for exact phrase matches (higher weight)
    phrase_score = 0.0
    query_words = query_clean.split()
    for i in range(len(query_words)):
        for j in range(i + 2, min(i + 6, len(query_words) + 1)):  # 2-5 word phrases
            phrase = ' '.join(query_words[i:j])
            if phrase in clean_description:
                phrase_score = max(phrase_score, len(phrase.split()) / len(query_words))

    final_score = (keyword_score * 0.5) + (sequence_score * 0.3) + (phrase_score * 0.2)

    return min(final_score, 1.0)


def _get_all_aws_operations() -> list[dict[str, Any]]:
    """Get all available AWS operations with CLI-style names."""
    operations = []
    command_table = driver._get_command_table()

    def _to_cli_style(name: str) -> str:
        return xform_name(name).replace('_', '-')

    for service_name, command in command_table.items():
        if not isinstance(command, ServiceCommand):
            continue

        try:
            service_command_table = command._get_command_table()
            for operation_name, operation in service_command_table.items():
                if hasattr(operation, '_operation_model'):
                    model = operation._operation_model
                    description = []
                    params = {}

                    # Add documentation
                    if clean_documentation := _clean_text(model.documentation):
                        description.append(clean_documentation)

                    # Add input parameters
                    if input_shape := model.input_shape:
                        for param_name, member in input_shape.members.items():
                            key = f'{_to_cli_style(param_name)} ({member.type_name})'
                            params[key] = (
                                _clean_text(member.documentation)
                                if hasattr(member, 'documentation')
                                else 'No description'
                            )
                        if params:
                            description.append('Parameters: ' + '; '.join(params.keys()))

                    operations.append(
                        {
                            'service': service_name,
                            'operation': operation_name,
                            'parameters': params,
                            'full_description': ' | '.join(description),
                            'clean_description': clean_documentation,
                        }
                    )
        except Exception:
            continue

    return operations


class KeyWordSearch:
    """Keyword search for AWS operations."""

    def __init__(self):
        """Initialize the keyword search for AWS operations."""
        self.aws_operations_index = _get_all_aws_operations()

    def get_suggestions(self, query: str, **kwargs) -> dict[str, list[dict]]:
        """Get suggestions for AWS operations based on the query."""
        scored_operations = []
        for operation in self.aws_operations_index:
            score = calculate_similarity(
                query,
                f'{operation["service"]} {operation["operation"]} {operation["full_description"]}',
            )
            if score > 0.2:
                scored_operations.append((operation, score))

        top_operations = sorted(scored_operations, key=lambda x: x[1], reverse=True)[:10]

        # Format suggestions
        suggestions = [
            {
                'command': f'aws {operation["service"]} {operation["operation"]}',
                'similarity': round(score, 3),
                'parameters': operation['parameters'],
                'description': operation['clean_description'][:1000] + '...'
                if len(operation['clean_description']) > 1000
                else operation['clean_description'],
            }
            for operation, score in top_operations[:10]
        ]

        return {'suggestions': suggestions}
