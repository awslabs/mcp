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

"""Example script demonstrating the get_managed_policy_document function.

This script shows how to use the new function to retrieve and examine
managed policy documents for wildcards and other permissions.
"""

import asyncio
import json
from awslabs.iam_mcp_server.server import get_managed_policy_document, list_policies


async def main():
    """Demonstrate getting managed policy documents."""
    print('=== IAM Managed Policy Document Retrieval Example ===\n')

    try:
        # First, list some policies to get their ARNs
        print('1. Listing local managed policies...')
        policies_result = await list_policies(scope='Local', max_items=5)

        if not policies_result['Policies']:
            print('No local managed policies found.')
            return

        print(f'Found {len(policies_result["Policies"])} policies:\n')

        # Display policy information and get documents
        for i, policy in enumerate(policies_result['Policies'], 1):
            print(f'{i}. Policy: {policy["PolicyName"]}')
            print(f'   ARN: {policy["Arn"]}')
            print(f'   Version: {policy["DefaultVersionId"]}')

            try:
                # Get the policy document
                print('   Getting policy document...')
                doc_result = await get_managed_policy_document(policy['Arn'])

                # Parse the policy document to look for wildcards
                policy_doc = json.loads(doc_result.policy_document)
                wildcards_found = []

                # Check for wildcards in the policy
                for statement in policy_doc.get('Statement', []):
                    # Check Actions
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    for action in actions:
                        if '*' in action:
                            wildcards_found.append(f'Action: {action}')

                    # Check Resources
                    resources = statement.get('Resource', [])
                    if isinstance(resources, str):
                        resources = [resources]
                    for resource in resources:
                        if '*' in resource:
                            wildcards_found.append(f'Resource: {resource}')

                if wildcards_found:
                    print('   WILDCARDS FOUND:')
                    for wildcard in wildcards_found:
                        print(f'      - {wildcard}')
                else:
                    print('   No wildcards found in this policy')

                print()

            except Exception as e:
                print(f'   Error getting policy document: {e}')
                print()

    except Exception as e:
        print(f'Error: {e}')


if __name__ == '__main__':
    asyncio.run(main())
