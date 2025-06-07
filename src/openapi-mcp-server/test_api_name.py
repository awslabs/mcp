#!/usr/bin/env python3
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
#!/usr/bin/env python
"""Test script for API name extraction from OpenAPI spec."""

import json
import os
import sys
from pathlib import Path


# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from awslabs.openapi_mcp_server.api.config import load_config
from awslabs.openapi_mcp_server.utils.openapi import extract_api_name_from_spec, load_openapi_spec


# Create a temporary OpenAPI spec file
temp_spec_path = Path('temp_openapi_spec.json')
spec = {
    'openapi': '3.0.0',
    'info': {'title': 'Hotels API', 'version': '1.0.0', 'description': 'API for hotel bookings'},
    'paths': {},
}

with open(temp_spec_path, 'w') as f:
    json.dump(spec, f)

try:
    # Test 1: Extract API name directly from spec
    api_name = extract_api_name_from_spec(spec)
    print(f"Test 1: Extracted API name: '{api_name}'")
    assert api_name == 'Hotels API', f"Expected 'Hotels API', got '{api_name}'"

    # Test 2: Load spec from file and extract API name
    loaded_spec = load_openapi_spec(path=str(temp_spec_path))
    api_name = extract_api_name_from_spec(loaded_spec)
    print(f"Test 2: Extracted API name from loaded spec: '{api_name}'")
    assert api_name == 'Hotels API', f"Expected 'Hotels API', got '{api_name}'"

    # Test 3: Simulate the main function logic
    # Create a mock args object
    class MockArgs:
        """Mock command line arguments for testing."""

        api_name = None
        api_url = 'https://example.com/api'
        spec_path = str(temp_spec_path)
        spec_url = None
        auth_type = 'none'
        sse = False
        port = None
        debug = False
        log_level = 'INFO'
        auth_username = None
        auth_password = None
        auth_token = None
        auth_api_key = None
        auth_api_key_name = None
        auth_api_key_in = None
        auth_cognito_client_id = None
        auth_cognito_username = None
        auth_cognito_password = None
        auth_cognito_user_pool_id = None
        auth_cognito_region = None

    # Save original environment
    original_env = os.environ.copy()

    # Make sure API_NAME is not set in the environment
    if 'API_NAME' in os.environ:
        del os.environ['API_NAME']

    # Load configuration
    args = MockArgs()
    config = load_config(args)

    # Simulate the early API name extraction
    if not args.api_name and not os.environ.get('API_NAME') and args.spec_path:
        try:
            print('Test 3: Loading OpenAPI spec to extract API name')
            openapi_spec = load_openapi_spec(path=args.spec_path)

            # Extract API name from spec
            api_name = extract_api_name_from_spec(openapi_spec)
            if api_name:
                config.api_name = api_name
                print(f"Test 3: Using API name from OpenAPI spec title: '{config.api_name}'")
        except Exception as e:
            print(f'Test 3: Failed to extract API name from OpenAPI spec: {e}')

    print(f"Test 3: Final API name in config: '{config.api_name}'")
    assert config.api_name == 'Hotels API', f"Expected 'Hotels API', got '{config.api_name}'"

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

    print('All tests passed!')

finally:
    # Clean up
    if temp_spec_path.exists():
        temp_spec_path.unlink()
