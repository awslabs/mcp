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

"""Path normalization utilities for mock configurations.

Converts relative fixture file paths to absolute paths in mock configurations.
This allows fixture files to be referenced with short relative paths (e.g., 'services.json')
which are then resolved to full paths (e.g., '/path/to/fixtures/services.json') for loading.

Supported fixture file formats:
- .json - Loaded and parsed as JSON by the mock handler
- .txt - Loaded as plain text by the mock handler

Other file extensions are treated as inline values and not loaded from disk.
"""

from .mcp_dependency_mocking_handler import REQUEST, RESPONSE
from pathlib import Path
from typing import Any, Dict


class MockConfigPathNormalizer:
    """Normalizes relative fixture file paths to absolute paths in mock configurations.

    This utility is used during task setup to convert relative fixture references
    in mock configs to absolute paths, enabling the mock handlers to load the files.
    """

    # Supported fixture file extensions
    _FIXTURE_EXTENSIONS = ('.json', '.txt')

    @staticmethod
    def is_fixture_file_reference(value: Any) -> bool:
        """Check if a value is a fixture file reference.

        Args:
            value: Value to check

        Returns:
            True if value is a string ending with a supported fixture file extension
        """
        return isinstance(value, str) and any(
            value.endswith(ext) for ext in MockConfigPathNormalizer._FIXTURE_EXTENSIONS
        )

    @staticmethod
    def resolve_mock_config(mock_config: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Resolve all relative fixture paths in a mock configuration to absolute paths.

        Args:
            mock_config: Mock configuration dictionary (may contain relative paths)
            fixtures_dir: Base directory for resolving relative fixture paths

        Returns:
            Mock configuration with all relative paths converted to absolute paths

        Example:
            Input: {'boto3': {'s3': {'list_buckets': [{'request': {}, 'response': 'buckets.json'}]}}}
            With fixtures_dir = Path('/fixtures')
            Output: {'boto3': {'s3': {'list_buckets': [{'request': {}, 'response': '/fixtures/buckets.json'}]}}}
        """
        return MockConfigPathNormalizer._resolve_fixture_paths(mock_config, fixtures_dir)

    @staticmethod
    def has_fixture_references(mock_config: Dict[str, Any]) -> bool:
        """Check if mock configuration contains relative fixture file references.

        Returns:
            True if any relative file paths are found, False otherwise
        """
        for key, value in mock_config.items():
            if isinstance(value, dict):
                if MockConfigPathNormalizer.has_fixture_references(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and RESPONSE in item:
                        response = item[RESPONSE]
                        if MockConfigPathNormalizer.is_fixture_file_reference(response):
                            if not Path(response).is_absolute():
                                return True
            elif MockConfigPathNormalizer.is_fixture_file_reference(value):
                if not Path(value).is_absolute():
                    return True
        return False

    @staticmethod
    def _resolve_fixture_paths(mock_config: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Recursively resolve fixture file paths to absolute paths."""
        resolved = {}
        for key, value in mock_config.items():
            if isinstance(value, dict):
                resolved[key] = MockConfigPathNormalizer._resolve_fixture_paths(
                    value, fixtures_dir
                )
            elif isinstance(value, list):
                resolved[key] = [
                    MockConfigPathNormalizer._resolve_request_response_pair(item, fixtures_dir)
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _resolve_request_response_pair(pair: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
        """Resolve a request/response pair, converting relative response path to absolute.

        Args:
            pair: Dict with 'request' and 'response' keys
            fixtures_dir: Base directory for resolving relative paths

        Returns:
            Request/response pair with absolute path for response if it's a file reference
        """
        if not isinstance(pair, dict) or REQUEST not in pair or RESPONSE not in pair:
            raise ValueError(
                f"Expected request/response pair dict with 'request' and 'response' keys, got: {pair}"
            )

        # TODO: Add support for file references in request field (currently only response supports files)
        response = pair[RESPONSE]
        if MockConfigPathNormalizer.is_fixture_file_reference(response):
            response = str(fixtures_dir / response)

        return {REQUEST: pair[REQUEST], RESPONSE: response}
