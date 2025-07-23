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

#!/usr/bin/env python3
"""Demo script showing inline policy management capabilities.

This script demonstrates how to use the new inline policy management tools
in the AWS IAM MCP Server.

Note: This is a demonstration script. In a real MCP environment, these tools
would be called through the MCP protocol by an AI assistant.
"""

import asyncio
from awslabs.iam_mcp_server.context import Context
from awslabs.iam_mcp_server.server import (
    delete_role_policy,
    delete_user_policy,
    get_role_policy,
    get_user_policy,
    list_role_policies,
    list_user_policies,
    put_role_policy,
    put_user_policy,
)


async def demo_user_inline_policies():
    """Demonstrate user inline policy management."""
    print('=== User Inline Policy Management Demo ===')

    # Sample policy document
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': ['s3:GetObject', 's3:PutObject'],
                'Resource': 'arn:aws:s3:::example-bucket/*',
            }
        ],
    }

    user_name = 'demo-user'
    policy_name = 'S3AccessPolicy'

    try:
        # Create an inline policy
        print(f"1. Creating inline policy '{policy_name}' for user '{user_name}'...")
        result = await put_user_policy(
            user_name=user_name, policy_name=policy_name, policy_document=policy_document
        )
        print(f'   ✓ {result.message}')

        # List user policies
        print(f"2. Listing inline policies for user '{user_name}'...")
        policies = await list_user_policies(user_name=user_name)
        print(f'   ✓ Found {policies.count} policies: {policies.policy_names}')

        # Retrieve the policy
        print(f"3. Retrieving policy '{policy_name}'...")
        policy = await get_user_policy(user_name=user_name, policy_name=policy_name)
        print(f'   ✓ Retrieved policy document (length: {len(policy.policy_document)} chars)')

        # Delete the policy
        print(f"4. Deleting policy '{policy_name}'...")
        result = await delete_user_policy(user_name=user_name, policy_name=policy_name)
        print(f'   ✓ {result["Message"]}')

    except Exception as e:
        print(f'   ✗ Error: {e}')
        print('   Note: This demo requires actual AWS credentials and an existing user.')


async def demo_role_inline_policies():
    """Demonstrate role inline policy management."""
    print('\n=== Role Inline Policy Management Demo ===')

    # Sample policy document
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [{'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': '*'}],
    }

    role_name = 'demo-role'
    policy_name = 'S3ReadOnlyPolicy'

    try:
        # Create an inline policy
        print(f"1. Creating inline policy '{policy_name}' for role '{role_name}'...")
        result = await put_role_policy(
            role_name=role_name, policy_name=policy_name, policy_document=policy_document
        )
        print(f'   ✓ {result.message}')

        # List role policies
        print(f"2. Listing inline policies for role '{role_name}'...")
        policies = await list_role_policies(role_name=role_name)
        print(f'   ✓ Found {policies.count} policies: {policies.policy_names}')

        # Retrieve the policy
        print(f"3. Retrieving policy '{policy_name}'...")
        policy = await get_role_policy(role_name=role_name, policy_name=policy_name)
        print(f'   ✓ Retrieved policy document (length: {len(policy.policy_document)} chars)')

        # Delete the policy
        print(f"4. Deleting policy '{policy_name}'...")
        result = await delete_role_policy(role_name=role_name, policy_name=policy_name)
        print(f'   ✓ {result["Message"]}')

    except Exception as e:
        print(f'   ✗ Error: {e}')
        print('   Note: This demo requires actual AWS credentials and an existing role.')


async def main():
    """Run the inline policy management demo."""
    print('AWS IAM MCP Server - Inline Policy Management Demo')
    print('=' * 50)

    # Initialize context (not in read-only mode for this demo)
    Context.initialize(readonly=False)

    print('Features demonstrated:')
    print('• Creating inline policies for users and roles')
    print('• Retrieving inline policy documents')
    print('• Listing all inline policies for a principal')
    print('• Deleting inline policies')
    print('• JSON validation for policy documents')
    print('• Read-only mode protection')
    print()

    await demo_user_inline_policies()
    await demo_role_inline_policies()

    print('\n=== Demo Complete ===')
    print('The inline policy management tools provide:')
    print('• Full CRUD operations for user and role inline policies')
    print('• Automatic JSON validation')
    print('• Comprehensive error handling')
    print('• Read-only mode protection')
    print('• Security best practices guidance')


if __name__ == '__main__':
    asyncio.run(main())
