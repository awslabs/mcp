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

"""Fixture path resolution for mock configurations.

Supported fixture file formats:
- .json - Loaded and parsed as JSON
- .txt - Loaded as plain text

Other file extensions are treated as inline values and not loaded from disk.
"""

from pathlib import Path
from typing import Any, Dict


class FixtureResolver:
    """Resolves fixture file paths in mock configurations."""

    @staticmethod
    def resolve_mock_config(mock_config: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Resolve all fixture paths in a mock configuration.

        Converts relative paths (e.g., 'services.json') to absolute paths
        (e.g., '/fixtures/services.json') based on fixtures_dir.
        """
        return FixtureResolver._resolve_fixture_paths(mock_config, fixtures_dir)

    @staticmethod
    def has_fixture_references(mock_config: Dict[str, Any]) -> bool:
        """Check if mock configuration contains relative fixture file references."""
        for key, value in mock_config.items():
            if isinstance(value, dict):
                if FixtureResolver.has_fixture_references(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'response' in item:
                        response = item['response']
                        if isinstance(response, str) and (
                            response.endswith('.json') or response.endswith('.txt')
                        ):
                            if not Path(response).is_absolute():
                                return True
            elif isinstance(value, str) and (value.endswith('.json') or value.endswith('.txt')):
                if not Path(value).is_absolute():
                    return True
        return False

    @staticmethod
    def _resolve_fixture_paths(mock_config: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Recursively resolve fixture file paths to absolute paths."""
        resolved = {}
        for key, value in mock_config.items():
            if isinstance(value, dict):
                resolved[key] = FixtureResolver._resolve_fixture_paths(value, fixtures_dir)
            elif isinstance(value, list):
                resolved[key] = [
                    FixtureResolver._resolve_request_response_pair(item, fixtures_dir)
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _resolve_request_response_pair(pair: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Resolve a request/response pair, converting relative response path to absolute."""
        if not isinstance(pair, dict) or 'request' not in pair or 'response' not in pair:
            raise ValueError(
                f"Expected request/response pair dict with 'request' and 'response' keys, got: {pair}"
            )

        response = pair['response']
        if isinstance(response, str) and (response.endswith('.json') or response.endswith('.txt')):
            response = str(fixtures_dir / response)

        return {'request': pair['request'], 'response': response}
