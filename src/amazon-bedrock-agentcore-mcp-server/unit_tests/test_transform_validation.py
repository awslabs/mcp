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
"""Test: Validate transformation generates correct AgentCore patterns.

This test validates that our transform_to_agentcore function generates
code that follows the correct AgentCore patterns.
"""

import os
import sys
import tempfile
from pathlib import Path


# Add our MCP server to the path
sys.path.insert(0, str(Path(__file__).parent / 'awslabs' / 'amazon_bedrock_agentcore_mcp_server'))


async def test_transformation_patterns():
    """Test that transformation generates correct patterns."""
    print('🔍 TESTING TRANSFORMATION PATTERNS')
    print('=' * 50)

    # Create test input files
    strands_agent = """#!/usr/bin/env python3
from strands import Agent

agent = Agent()

async def process_message(msg):
    return await agent(msg)
"""

    generic_agent = """#!/usr/bin/env python3
def handle_message(msg):
    return f"Response: {msg}"
"""

    test_cases = [
        ('strands_test.py', strands_agent, 'strands'),
        ('generic_test.py', generic_agent, 'generic'),
    ]

    try:
        from server import create_server

        server = create_server()

        for input_file, input_code, framework in test_cases:
            print(f'\n📋 Testing {framework} transformation...')

            # Write test input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(input_code)
                input_path = f.name

            try:
                # Transform the code
                result = await server.call_tool(
                    'transform_to_agentcore',
                    {
                        'file_path': input_path,
                        'agent_name': f'test_{framework}',
                        'output_file': f'test_{framework}_agentcore.py',
                    },
                )

                output_text = result[0][0].text
                print(f'✅ Transformation completed for {framework}')
                print(output_text)

                # Validate the generated file exists
                output_file = f'test_{framework}_agentcore.py'
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        generated_code = f.read()

                    # Validate correct patterns
                    checks = []

                    # Check 1: No parentheses in decorator
                    if '@app.entrypoint\n' in generated_code:
                        checks.append('✅ Correct decorator (@app.entrypoint)')
                    else:
                        checks.append('❌ Wrong decorator pattern')

                    # Check 2: payload parameter
                    if 'def handle_request(payload)' in generated_code:
                        checks.append('✅ Correct parameter (payload)')
                    else:
                        checks.append('❌ Wrong parameter pattern')

                    # Check 3: Dict return format
                    if 'return {"result":' in generated_code:
                        checks.append('✅ Correct return format (dict)')
                    else:
                        checks.append('❌ Wrong return format')

                    # Check 4: No RequestContext import
                    if 'RequestContext' not in generated_code:
                        checks.append('✅ No RequestContext usage')
                    else:
                        checks.append('❌ Still using RequestContext')

                    # Check 5: payload.get() access
                    if 'payload.get(' in generated_code:
                        checks.append('✅ Correct payload access')
                    else:
                        checks.append('❌ Wrong payload access')

                    # Framework-specific checks
                    if framework == 'strands':
                        if 'from strands import Agent' in generated_code:
                            checks.append('✅ Strands import preserved')
                        else:
                            checks.append('❌ Missing Strands import')

                    print(f'\n📊 Validation Results for {framework}:')
                    for check in checks:
                        print(f'  {check}')

                    # Show generated code snippet
                    print('\n📄 Generated Code Preview:')
                    lines = generated_code.split('\n')
                    for i, line in enumerate(lines[20:35], 21):  # Show around the entrypoint
                        print(f'  {i:2d}: {line}')

                    # Cleanup
                    os.unlink(output_file)

                else:
                    print(f'❌ Output file not created: {output_file}')

            finally:
                # Cleanup input file
                os.unlink(input_path)

        print('\n✅ TRANSFORMATION TESTING COMPLETE')
        return True

    except Exception as e:
        print(f'❌ Test failed: {str(e)}')
        return False


async def main():
    """Run transformation validation."""
    success = await test_transformation_patterns()
    return 0 if success else 1


if __name__ == '__main__':
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
