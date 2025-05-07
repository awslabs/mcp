#!/usr/bin/env python
"""Functional test for openapi-mcp-server with Petstore API.

This script tests the openapi-mcp-server integration with the Swagger Petstore API.
It starts an MCP server connected to the Petstore API and runs several operations
to verify that the server correctly handles OpenAPI integration.
"""

import argparse
import asyncio
import httpx
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


# Add the project root to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


class SimpleMcpClient:
    """A simple client for interacting with an MCP server over HTTP."""

    def __init__(self, host: str = 'localhost', port: int = 8888):
        """Initialize the client with the server host and port.

        Args:
            host: The server host
            port: The server port
        """
        self.host = host
        self.port = port
        self.base_url = f'http://{host}:{port}'

    async def get_server_info(self) -> Dict[str, Any]:
        """Get information about the MCP server.

        Returns:
            Dict[str, Any]: Server information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{self.base_url}/mcp')
            response.raise_for_status()
            return response.json()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List the available tools.

        Returns:
            List[Dict[str, Any]]: List of tools
        """
        server_info = await self.get_server_info()
        return server_info.get('tools', [])

    async def use_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Use a tool from the MCP server.

        Args:
            tool_name: The name of the tool to use
            arguments: Arguments to pass to the tool

        Returns:
            Any: The result of the tool invocation
        """
        if arguments is None:
            arguments = {}

        # Create a tool call message
        tool_call = {
            'id': str(uuid.uuid4()),
            'type': 'tool_call',
            'tool': {'name': tool_name, 'arguments': arguments},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(f'{self.base_url}/mcp/exchange', json=tool_call)
            response.raise_for_status()
            result = response.json()

            # Wait for the tool execution to complete
            while result.get('type') == 'tool_start':
                # Use the returned exchange ID to get updates
                exchange_id = result.get('exchangeId')
                await asyncio.sleep(0.5)
                response = await client.get(f'{self.base_url}/mcp/exchange/{exchange_id}')
                response.raise_for_status()
                result = response.json()

            # Return the result data
            if result.get('type') == 'tool_result':
                return result.get('data')
            elif result.get('type') == 'tool_error':
                raise Exception(f'Tool error: {result.get("error")}')
            else:
                raise Exception(f'Unexpected response: {result}')


class PetstoreTestRunner:
    """Runner for Petstore API functional tests."""

    def __init__(self, port: int = 8888, verbose: bool = False):
        """Initialize the test runner.

        Args:
            port: The port to run the server on
            verbose: Whether to print verbose output
        """
        self.port = port
        self.verbose = verbose
        self.server_process = None

    def log(self, message: str):
        """Print a message if verbose is enabled.

        Args:
            message: The message to print
        """
        if self.verbose:
            print(f'[TEST] {message}')

    @contextmanager
    def start_server(self):
        """Start the MCP server as a subprocess and yield.

        Yields:
            None
        """
        try:
            # Set up environment for the server
            env = os.environ.copy()
            env['SERVER_PORT'] = str(self.port)
            env['SERVER_HOST'] = '127.0.0.1'  # Explicitly set to localhost for testing

            # Start the server process
            self.log(f'Starting MCP server on port {self.port} (host: 127.0.0.1)')

            # Build command - use the module directly for clean execution
            # Make sure to use the correct argument names: --api-url and --spec-url
            cmd = [
                sys.executable,
                '-m',
                'awslabs.openapi_mcp_server.server',
                '--sse',
                '--port',
                str(self.port),
                '--api-name',
                'petstore',
                '--api-url',
                'https://petstore3.swagger.io/api/v3',
                '--spec-url',
                'https://petstore3.swagger.io/api/v3/openapi.json',
            ]

            # Start the process, redirecting output to temp files if not verbose
            if self.verbose:
                self.server_process = subprocess.Popen(cmd, env=env)
            else:
                stdout_file = tempfile.NamedTemporaryFile(delete=False)
                stderr_file = tempfile.NamedTemporaryFile(delete=False)
                self.server_process = subprocess.Popen(
                    cmd, env=env, stdout=stdout_file, stderr=stderr_file
                )
                stdout_file.close()
                stderr_file.close()
                self.stdout_path = stdout_file.name
                self.stderr_path = stderr_file.name

            # Give the server a moment to start up
            self.log('Waiting for server to start...')
            time.sleep(2)

            yield

        finally:
            # Clean up the server process
            if self.server_process:
                self.log('Stopping MCP server...')
                self.server_process.send_signal(signal.SIGINT)
                self.server_process.wait(timeout=5)

            # Print output files if not verbose but we had an error
            if not self.verbose and hasattr(self, 'stdout_path') and hasattr(self, 'stderr_path'):
                with open(self.stdout_path, 'r') as f:
                    stdout = f.read()
                    if stdout:
                        print('\nServer stdout:')
                        print(stdout)

                with open(self.stderr_path, 'r') as f:
                    stderr = f.read()
                    if stderr:
                        print('\nServer stderr:')
                        print(stderr)

                # Clean up temp files
                os.unlink(self.stdout_path)
                os.unlink(self.stderr_path)

    async def test_find_pets_by_status(self, client: SimpleMcpClient) -> bool:
        """Test the findPetsByStatus operation.

        Args:
            client: The MCP client

        Returns:
            bool: Whether the test passed
        """
        self.log('Testing findPetsByStatus operation...')

        try:
            # Call the MCP tool
            result = await client.use_tool('findPetsByStatus', {'status': 'available'})

            # Validate result
            assert isinstance(result, list), 'Expected a list of pets'
            assert len(result) > 0, 'Expected at least one pet'

            # Check a sample pet
            sample_pet = result[0]
            assert 'id' in sample_pet, 'Pet should have an ID'
            assert 'name' in sample_pet, 'Pet should have a name'

            self.log(f'Found {len(result)} available pets')
            self.log(f'Sample pet: {sample_pet["name"]} (ID: {sample_pet["id"]})')
            return True

        except Exception as e:
            self.log(f'Error in findPetsByStatus test: {e}')
            return False

    async def test_get_pet_by_id(self, client: SimpleMcpClient) -> bool:
        """Test the getPetById operation.

        Args:
            client: The MCP client

        Returns:
            bool: Whether the test passed
        """
        self.log('Testing getPetById operation...')

        try:
            # First get a list of pets to find a valid ID
            pets = await client.use_tool('findPetsByStatus', {'status': 'available'})
            if not pets or len(pets) == 0:
                self.log('No pets available to test getPetById')
                return False

            # Get a pet ID
            pet_id = pets[0]['id']

            # Call the MCP tool
            result = await client.use_tool('getPetById', {'petId': pet_id})

            # Validate result
            assert result['id'] == pet_id, f'Expected pet ID {pet_id}, got {result["id"]}'
            assert 'name' in result, 'Pet should have a name'

            self.log(f'Successfully retrieved pet: {result["name"]} (ID: {result["id"]})')
            return True

        except Exception as e:
            self.log(f'Error in getPetById test: {e}')
            return False

    async def test_inventory(self, client: SimpleMcpClient) -> bool:
        """Test the getInventory operation.

        Args:
            client: The MCP client

        Returns:
            bool: Whether the test passed
        """
        self.log('Testing getInventory operation...')

        try:
            # Call the MCP tool
            result = await client.use_tool('getInventory')

            # Validate result
            assert isinstance(result, dict), 'Expected a dictionary of inventory counts'
            assert len(result) > 0, 'Expected at least one inventory status'

            # Print inventory
            self.log('Inventory status:')
            for status, count in result.items():
                self.log(f'  {status}: {count}')

            return True

        except Exception as e:
            self.log(f'Error in getInventory test: {e}')
            return False

    async def run_tests(self):
        """Run all tests against the MCP server.

        Returns:
            bool: Whether all tests passed
        """
        try:
            # Connect to the server
            self.log(f'Connecting to MCP server at http://localhost:{self.port}')
            client = SimpleMcpClient('localhost', self.port)

            # Wait for server to initialize fully
            await asyncio.sleep(1)

            try:
                # Get the server info
                info = await client.get_server_info()
                self.log(f'Connected to server: {info.get("name", "Unknown")}')
                if 'instructions' in info:
                    self.log(f'Server instructions: {info["instructions"][:100]}...')

                # Get available tools
                tools = await client.list_tools()
                self.log(f'Available tools: {", ".join(t["name"] for t in tools)}')

                # Run tests
                test_results = []
                test_results.append(await self.test_find_pets_by_status(client))
                test_results.append(await self.test_get_pet_by_id(client))
                test_results.append(await self.test_inventory(client))

                # Report results
                passed = sum(1 for t in test_results if t)
                total = len(test_results)

                print(f'\n✅ {passed}/{total} tests passed')

                return all(test_results)
            except Exception as e:
                print(f'\n❌ Error during tests: {e}')
                return False

        except Exception as e:
            print(f'\n❌ Error connecting to MCP server: {e}')
            return False

    def run(self):
        """Run the test suite.

        Returns:
            int: The exit code (0 for success, 1 for failure)
        """
        with self.start_server():
            try:
                result = asyncio.run(self.run_tests())
                return 0 if result else 1
            except Exception as e:
                print(f'\n❌ Error running tests: {e}')
                return 1


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description='Functional test for openapi-mcp-server with Petstore API'
    )
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    # Run the tests
    runner = PetstoreTestRunner(port=args.port, verbose=args.verbose)
    return runner.run()


if __name__ == '__main__':
    sys.exit(main())
