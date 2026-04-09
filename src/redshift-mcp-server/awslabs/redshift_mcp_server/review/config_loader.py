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

"""Config loader for review JSON config files."""

import json
from pathlib import Path
from typing import Literal, TypedDict

from typing_extensions import NotRequired


class QueryEntry(TypedDict):
    """A single diagnostic query entry."""

    SQL: str


class SignalEntry(TypedDict):
    """A single signal definition within a section."""

    Signal: str
    Criteria: str
    PopulationCriteria: NotRequired[str]
    Recommendation: list[str]


class SectionEntry(TypedDict):
    """A section grouping signals for a diagnostic query."""

    Signals: list[SignalEntry]


class RecommendationEntry(TypedDict):
    """A single recommendation definition."""

    text: str
    description: str
    effort: Literal['Small', 'Medium', 'Large']
    documentation_links: list[str]


def load_queries_config(path: Path) -> dict[str, QueryEntry]:
    """Load the queries config from a JSON file.

    Args:
        path: Path to the queries.json file.

    Returns:
        Dictionary mapping query names to QueryEntry objects.

    Raises:
        ValueError: If the file is missing or contains malformed JSON.
    """
    return _load_json(path, 'queries')


def load_signals_config(path: Path) -> dict[str, SectionEntry]:
    """Load the signals config from a JSON file.

    Args:
        path: Path to the signals.json file.

    Returns:
        Dictionary mapping section names to SectionEntry objects.

    Raises:
        ValueError: If the file is missing or contains malformed JSON.
    """
    return _load_json(path, 'signals')


def load_recommendations_config(path: Path) -> dict[str, RecommendationEntry]:
    """Load the recommendations config from a JSON file.

    Args:
        path: Path to the recommendations.json file.

    Returns:
        Dictionary mapping recommendation IDs to RecommendationEntry objects.

    Raises:
        ValueError: If the file is missing or contains malformed JSON.
    """
    return _load_json(path, 'recommendations')


def _load_json(path: Path, config_name: str) -> dict:
    """Load and parse a JSON config file.

    Args:
        path: Path to the JSON file.
        config_name: Human-readable name for error messages.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        ValueError: If the file is missing or contains malformed JSON.
    """
    if not path.exists():
        raise ValueError(f'{config_name} config file not found: {path}')
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f'{config_name} config file contains malformed JSON: {path}: {e}') from e
    if not isinstance(data, dict):
        raise ValueError(f'{config_name} config file must contain a JSON object: {path}')
    return data
