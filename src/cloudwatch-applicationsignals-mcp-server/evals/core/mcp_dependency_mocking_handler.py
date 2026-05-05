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

"""Mocking system for MCP evaluation framework.

Provides extensible mocking for external dependencies (boto3, requests, etc.)
used by MCP servers during evaluation.

Current limitations:
- Only supports request -> String/JSON response mapping (no exception mocking)
- Depends on MagicMock for client method patching
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


# TODO: Move these constants to dedicated constants module during core/ directory refactor
REQUEST = 'request'
RESPONSE = 'response'


class UnmockedMethodError(Exception):
    """Raised when code attempts to call a method that hasn't been mocked.

    This indicates incomplete mock configuration. The error message clearly indicates
    what method is missing and how to fix it.

    TODO: Investigate fail-fast behavior where UnmockedMethodError terminates the eval task
    immediately instead of propagating to the agent (requires subprocess error propagation).
    """

    def __init__(self, service_name: str, method_name: str, available_methods: List[str]):
        """Initialize UnmockedMethodError.

        Args:
            service_name: Name of the service (e.g., 'cloudwatch')
            method_name: Name of the unmocked method that was called
            available_methods: List of methods that are mocked
        """
        self.service_name = service_name
        self.method_name = method_name
        self.available_methods = available_methods
        super().__init__(
            f"Unmocked method '{method_name}' called on {service_name} client. "
            f'Available mocked methods: {available_methods}. '
            f"Add '{method_name}' to your mock configuration to fix this."
        )


class McpDependencyMockingHandler(ABC):
    """Base class for library-specific mock handlers.

    Subclasses implement patching logic for specific libraries
    (e.g., boto3, requests, database clients).
    """

    @abstractmethod
    def get_library_name(self) -> str:
        """Return the name of the library this handler mocks.

        Returns:
            Library name (e.g., 'boto3', 'requests')
        """
        pass

    @abstractmethod
    def patch(self, mock_config: Dict[str, Any]) -> None:
        """Apply patches to the library.

        Args:
            mock_config: Mock configuration dictionary for this library (fixture paths must be absolute)
        """
        pass

    @abstractmethod
    def unpatch(self) -> None:
        """Remove all patches applied by this handler."""
        pass

    def resolve_method_mock_config(self, arg_response_pair: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a single method mock configuration.

        Takes a dict with 'request' and 'response' keys. If 'response' is a file path,
        loads the fixture data.

        Args:
            arg_response_pair: Dict with 'request' and 'response' keys (fixture paths must be absolute)

        Returns:
            Resolved mock response with loaded fixture data
        """
        if REQUEST not in arg_response_pair or RESPONSE not in arg_response_pair:
            raise ValueError(
                f"Invalid mock config structure. Expected dict with 'request' and 'response' keys, "
                f'got keys: {list(arg_response_pair.keys())}'
            )

        # TODO: Add support for exception mocking (e.g., {'request': {...}, 'exception': SomeException(...)})
        response = arg_response_pair[RESPONSE]

        # Import here to avoid circular dependency (mock_config_path_normalizer imports REQUEST/RESPONSE from this module)
        from .mock_config_path_normalizer import MockConfigPathNormalizer

        if MockConfigPathNormalizer.is_fixture_file_reference(response):
            fixture_path = Path(response)
            if not fixture_path.exists():
                raise FileNotFoundError(f'Fixture file not found: {response}')

            if response.endswith('.json'):
                with open(fixture_path, 'r') as f:
                    response = json.load(f)
            else:
                with open(fixture_path, 'r') as f:
                    response = f.read()

        return {REQUEST: arg_response_pair[REQUEST], RESPONSE: response}

    def resolve_method_mock_configs(
        self, arg_response_pairs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve a list of method mock configurations.

        Note: Empty service configs like {'boto3': {}} are valid for preventing real API calls
        for that specific library without defining specific mocks. All operations on the patched
        library will return UnmockedMethodError to the agent (eval continues, but operations fail).
        If you define an operation, it must have at least one request/response pair.

        Args:
            arg_response_pairs: List of dicts with 'request' and 'response' keys (fixture paths must be absolute)

        Returns:
            List of resolved mock responses

        Raises:
            ValueError: If arg_response_pairs is empty (operation defined but no mocks provided)
        """
        if not arg_response_pairs:
            raise ValueError(
                'Invalid mock configuration: operation defined with empty list. '
                "Each operation must have at least one mock with 'request' and 'response' keys. "
                "To patch a library without defining mocks, use empty service config: {'boto3': {}}."
            )

        return [self.resolve_method_mock_config(pair) for pair in arg_response_pairs]

    def _create_parameter_aware_mock(self, operation: str, matchers: list) -> MagicMock:
        """Create a mock that matches on parameters.

        Matching rules:
        - Empty request dict {} matches any parameters (wildcard)
        - Non-empty request dict matches when all specified params are present and equal

        Args:
            operation: Operation name (for error messages)
            matchers: List of dicts with 'request' and 'response' keys

        Returns:
            MagicMock that returns responses based on parameter matching
        """

        def mock_implementation(**kwargs):
            for matcher in matchers:
                request_params = matcher.get(REQUEST, {})
                response = matcher.get(RESPONSE)

                if not request_params:
                    return response

                # TODO: Add support for more flexible matching (wildcards, negations, regex, etc.)
                if all(kwargs.get(key) == value for key, value in request_params.items()):
                    return response

            raise ValueError(
                f'No mock response found for {operation} with parameters: {kwargs}\n'
                f'Available request patterns: {[m.get("request") for m in matchers]}'
            )

        return MagicMock(side_effect=mock_implementation)


class Boto3DependencyMockingHandler(McpDependencyMockingHandler):
    """Mock handler for boto3 clients.

    Patches boto3.client() to return mocked clients with predefined responses.
    """

    def __init__(self):
        """Initialize Boto3DependencyMockingHandler with empty state."""
        self.original_client = None
        self.service_method_mock_configs: Dict[str, Dict[str, Any]] = {}

    def get_library_name(self) -> str:
        """Return library name."""
        return 'boto3'

    def patch(self, mock_config: Dict[str, Any]) -> None:
        """Patch boto3.client() to return mocked clients.

        Args:
            mock_config: Dict mapping service names to operation responses
                Example: {'cloudwatch': {'GetMetricData': {...}}}
                Fixture paths must be absolute.
        """
        import boto3

        self.original_client = boto3.client

        resolved_config = {}
        for service, operations in mock_config.items():
            resolved_config[service] = {}
            for operation, response in operations.items():
                resolved_config[service][operation] = self.resolve_method_mock_configs(response)

        self.service_method_mock_configs = resolved_config
        boto3.client = self._create_mock_client

    def unpatch(self) -> None:
        """Restore original boto3.client."""
        if self.original_client:
            import boto3

            boto3.client = self.original_client
            self.original_client = None
            self.service_method_mock_configs = {}

    def _create_mock_client(self, service_name: str, **kwargs):
        """Create a mocked boto3 client.

        Args:
            service_name: AWS service name (e.g., 'cloudwatch')
            **kwargs: Additional client parameters (ignored)

        Returns:
            Mocked client with predefined responses. Calls to unmocked methods will raise UnmockedMethodError.
        """
        method_mock_configs = self.service_method_mock_configs.get(service_name, {})

        class MockClient:
            """Dynamic mock client that raises UnmockedMethodError for unmocked methods."""

            def __getattr__(self, name):
                raise UnmockedMethodError(service_name, name, list(method_mock_configs.keys()))

        mock_client = MockClient()

        for operation, response_data in method_mock_configs.items():
            mock_method = self._create_parameter_aware_mock(operation, response_data)
            setattr(mock_client, operation, mock_method)

        return mock_client


class McpDependencyMockingHandlerRegistry:
    """Registry for mock handlers.

    Provides centralized management and discovery of available mock handlers.
    """

    def __init__(self):
        """Initialize McpDependencyMockingHandlerRegistry and register built-in handlers."""
        self._handlers: Dict[str, McpDependencyMockingHandler] = {}
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register built-in mock handlers."""
        self.register(Boto3DependencyMockingHandler())

    def register(self, handler: McpDependencyMockingHandler):
        """Register a mock handler.

        Args:
            handler: McpDependencyMockingHandler instance
        """
        library_name = handler.get_library_name()
        self._handlers[library_name] = handler

    def get_handler(self, library_name: str) -> Optional[McpDependencyMockingHandler]:
        """Get handler for a library.

        Args:
            library_name: Name of library (e.g., 'boto3')

        Returns:
            McpDependencyMockingHandler instance or None if not found
        """
        return self._handlers.get(library_name)

    def list_supported_libraries(self) -> list[str]:
        """List all supported mock libraries.

        Returns:
            List of library names
        """
        return list(self._handlers.keys())

    def patch_all(self, mock_config: Dict[str, Any]) -> None:
        """Apply all mocks from configuration.

        Args:
            mock_config: Full mock configuration dict (fixture paths must be absolute)
        """
        for library_name, library_config in mock_config.items():
            handler = self.get_handler(library_name)
            if handler:
                handler.patch(library_config)
            else:
                raise ValueError(
                    f"No mock handler registered for '{library_name}'. "
                    f'Supported libraries: {", ".join(self.list_supported_libraries())}'
                )

    def unpatch_all(self) -> None:
        """Remove all patches."""
        for handler in self._handlers.values():
            handler.unpatch()


# Global registry instance
_registry = McpDependencyMockingHandlerRegistry()


def get_registry() -> McpDependencyMockingHandlerRegistry:
    """Get the global mock handler registry.

    Returns:
        McpDependencyMockingHandlerRegistry instance
    """
    return _registry
