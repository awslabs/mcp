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

"""Example usage of AWS Systems Manager MCP Server document tools."""

import asyncio
import json
from awslabs.systems_manager_mcp_server.models import (
    CreateDocumentRequest,
    DocumentFilter,
    DocumentListRequest,
    DocumentRequest,
)
from awslabs.systems_manager_mcp_server.tools.documents import (
    create_document,
    get_document,
    list_documents,
)


async def example_list_documents():
    """Example: List Systems Manager documents."""
    print('=== Listing Documents ===')

    # List all documents
    request = DocumentListRequest(max_results=10)
    result = list_documents(request)

    if result['success']:
        print(f'Found {result["count"]} documents:')
        for doc in result['documents']:
            print(f'  - {doc["Name"]} ({doc["DocumentType"]})')
    else:
        print(f'Error: {result["error"]}')

    print()


async def example_list_command_documents():
    """Example: List only Command documents."""
    print('=== Listing Command Documents ===')

    # List only Command documents
    request = DocumentListRequest(
        document_filter_list=[DocumentFilter(key='DocumentType', values=['Command'])],
        max_results=5,
    )
    result = list_documents(request)

    if result['success']:
        print(f'Found {result["count"]} command documents:')
        for doc in result['documents']:
            print(f'  - {doc["Name"]} (Owner: {doc.get("Owner", "Unknown")})')
    else:
        print(f'Error: {result["error"]}')

    print()


async def example_get_document():
    """Example: Get a specific document."""
    print('=== Getting Document Content ===')

    # Get the AWS-RunShellScript document
    request = DocumentRequest(name='AWS-RunShellScript', document_format='JSON')
    result = get_document(request)

    if result['success']:
        print(f'Document: {result["name"]}')
        print(f'Version: {result["document_version"]}')
        print(f'Status: {result["status"]}')
        print(f'Type: {result["document_type"]}')
        print('Content preview:')
        content = json.loads(result['content'])
        print(f'  Schema Version: {content.get("schemaVersion")}')
        print(f'  Description: {content.get("description")}')
    else:
        print(f'Error: {result["error"]}')

    print()


async def example_create_simple_document():
    """Example: Create a simple command document."""
    print('=== Creating Simple Document ===')

    # Define document content
    document_content = {
        'schemaVersion': '2.2',
        'description': 'Example document that echoes a message',
        'parameters': {
            'message': {
                'type': 'String',
                'description': 'Message to echo',
                'default': 'Hello from Systems Manager!',
            }
        },
        'mainSteps': [
            {
                'action': 'aws:runShellScript',
                'name': 'echoMessage',
                'inputs': {'runCommand': ["echo '{{ message }}'"]},
            }
        ],
    }

    # Create the document
    request = CreateDocumentRequest(
        name='ExampleEchoDocument',
        content=json.dumps(document_content, indent=2),
        document_type='Command',
        display_name='Example Echo Document',
        tags=[{'Key': 'Purpose', 'Value': 'Example'}, {'Key': 'CreatedBy', 'Value': 'MCP-Server'}],
    )

    result = create_document(request)

    if result['success']:
        doc_desc = result['document_description']
        print(f'Successfully created document: {doc_desc["Name"]}')
        print(f'Version: {doc_desc["DocumentVersion"]}')
        print(f'Status: {doc_desc["Status"]}')
    else:
        print(f'Error: {result["error"]}')
        if 'error_code' in result:
            print(f'Error Code: {result["error_code"]}')

    print()


async def example_create_automation_document():
    """Example: Create an automation document."""
    print('=== Creating Automation Document ===')

    # Define automation document content
    document_content = {
        'schemaVersion': '0.3',
        'description': 'Example automation to stop an EC2 instance',
        'assumeRole': '{{ AutomationAssumeRole }}',
        'parameters': {
            'InstanceId': {'type': 'String', 'description': 'EC2 Instance ID to stop'},
            'AutomationAssumeRole': {
                'type': 'String',
                'description': 'IAM role for automation execution',
            },
        },
        'mainSteps': [
            {
                'name': 'stopInstance',
                'action': 'aws:changeInstanceState',
                'inputs': {'InstanceIds': ['{{ InstanceId }}'], 'DesiredState': 'stopped'},
            },
            {
                'name': 'verifyInstanceStopped',
                'action': 'aws:waitForAwsResourceProperty',
                'inputs': {
                    'Service': 'ec2',
                    'Api': 'DescribeInstances',
                    'InstanceIds': ['{{ InstanceId }}'],
                    'PropertySelector': '$.Reservations[0].Instances[0].State.Name',
                    'DesiredValues': ['stopped'],
                },
            },
        ],
    }

    # Create the automation document
    request = CreateDocumentRequest(
        name='ExampleStopInstanceAutomation',
        content=json.dumps(document_content, indent=2),
        document_type='Automation',
        display_name='Example Stop Instance Automation',
        tags=[{'Key': 'Purpose', 'Value': 'Example'}, {'Key': 'Type', 'Value': 'Automation'}],
    )

    result = create_document(request)

    if result['success']:
        doc_desc = result['document_description']
        print(f'Successfully created automation: {doc_desc["Name"]}')
        print(f'Version: {doc_desc["DocumentVersion"]}')
        print(f'Status: {doc_desc["Status"]}')
    else:
        print(f'Error: {result["error"]}')
        if 'error_code' in result:
            print(f'Error Code: {result["error_code"]}')

    print()


async def example_api_usage():
    """Example: Using direct boto3 calls (API layer removed)."""
    print('=== Direct AWS API Usage ===')

    print('Note: API layer has been removed. Tools now use boto3 directly.')
    print('Use the tools functions instead for AWS Systems Manager operations.')

    print()


async def example_prompts_usage():
    """Example: Using prompts for guidance."""
    print('=== Using Prompts for Guidance ===')

    # Import prompts
    from awslabs.systems_manager_mcp_server.prompts.documents import (
        document_creation_guide,
        document_security_best_practices,
        document_troubleshooting_guide,
    )

    # Get creation guide
    creation_guide = document_creation_guide()
    print('Document Creation Guide (first 200 chars):')
    print(creation_guide[:200] + '...')

    # Get troubleshooting guide
    troubleshooting_guide = document_troubleshooting_guide()
    print('\nTroubleshooting Guide (first 200 chars):')
    print(troubleshooting_guide[:200] + '...')

    # Get security best practices
    security_guide = document_security_best_practices()
    print('\nSecurity Best Practices Guide (first 200 chars):')
    print(security_guide[:200] + '...')

    print('\n✓ All prompts are available and functional')
    print()


async def main():
    """Run all examples."""
    print('AWS Systems Manager MCP Server - Document Examples')
    print('=' * 50)

    try:
        await example_list_documents()
        await example_list_command_documents()
        await example_get_document()
        await example_create_simple_document()
        await example_create_automation_document()
        await example_api_usage()
        await example_prompts_usage()

        print('Examples completed successfully!')

    except Exception as e:
        print(f'Error running examples: {e}')
        print('Make sure you have:')
        print('1. AWS credentials configured')
        print('2. Proper IAM permissions for Systems Manager')
        print('3. The MCP server dependencies installed')


if __name__ == '__main__':
    asyncio.run(main())
