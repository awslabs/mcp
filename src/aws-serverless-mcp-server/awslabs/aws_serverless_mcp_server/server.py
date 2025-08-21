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

"""Serverless MCP Server implementation."""

import argparse
import os
import sys
import threading
import time
from awslabs.aws_serverless_mcp_server import __version__
from awslabs.aws_serverless_mcp_server.resources import (
    handle_deployment_details,
    handle_deployments_list,
    handle_template_details,
    handle_template_list,
)
from awslabs.aws_serverless_mcp_server.tools.guidance import (
    DeployServerlessAppHelpTool,
    GetIaCGuidanceTool,
    GetLambdaEventSchemasTool,
    GetLambdaGuidanceTool,
    GetServerlessTemplatesTool,
)
from awslabs.aws_serverless_mcp_server.tools.sam import (
    SamBuildTool,
    SamDeployTool,
    SamInitTool,
    SamLocalInvokeTool,
    SamLogsTool,
)
from awslabs.aws_serverless_mcp_server.tools.schemas import (
    DescribeSchemaTool,
    ListRegistriesTool,
    SearchSchemaTool,
)
from awslabs.aws_serverless_mcp_server.tools.webapps import (
    ConfigureDomainTool,
    DeployWebAppTool,
    GetMetricsTool,
    UpdateFrontendTool,
    WebappDeploymentHelpTool,
)
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from awslabs.aws_serverless_mcp_server.utils.const import AWS_REGION, DEPLOYMENT_STATUS_DIR
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


IDLE_TIMEOUT_SECONDS = 3600  # 1 hour timer for auto shut down of server


class AutoShutdownServer(FastMCP):
    """FastMCP server with automatic shutdown after idle timeout."""

    def __init__(self, name, idle_timeout=IDLE_TIMEOUT_SECONDS):
        """Initialize the auto-shutdown server.

        Args:
            name: Server name
            idle_timeout: Timeout in seconds before shutdown
        """
        super().__init__(name)
        self.last_activity_time = time.time()
        self.idle_timeout = idle_timeout
        self.shutdown_thread = threading.Thread(target=self._monitor_idle_time, daemon=True)

    def _monitor_idle_time(self):
        while True:
            time.sleep(60)
            if time.time() - self.last_activity_time > self.idle_timeout:
                print(f'Server idle for over {self.idle_timeout} seconds, shutting down')
                sys.exit(0)

    def run(self):
        """Start the server with idle monitoring."""
        self.shutdown_thread.start()
        super().run()


# Initialize boto3 client
schemas_client = get_aws_client('schemas', AWS_REGION)

mcp = AutoShutdownServer(
    'awslabs.aws-serverless-mcp-server',
    instructions="""AWS Serverless MCP

    The AWS Serverless Model Context Protocol (MCP) Server is an open-source tool that combines
    AI assistance with serverless expertise to streamline how developers build serverless applications.
    It provides contextual guidance specific to serverless development, helping developers make informed
    decisions about architecture, implementation, and deployment throughout the entire application development
    lifecycle. With AWS Serverless MCP, developers can build reliable, efficient, and production-ready serverless
    applications with confidence.

    ## Features
    1. Serverless Application Lifecycle
    - Initialize, build, and deploy Serverless Application Model (SAM) applications with SAM CLI
    - Test Lambda functions locally and remotely
    2. Web Application Deployment & Management
    - Deploy fullstack, frontend, and backend web applications onto AWS Serverless using Lambda Web Adapter.
    - Update frontend assets and optionally invalidate CloudFront caches
    - Create custom domain names, including certificate and DNS setup.
    3. Observability
    - Retrieve and logs and metrics of serverless resources
    4. Guidance, Templates, and Deployment Help
    - Provides guidance on AWS Lambda use-cases, selecting an IaC framework, and deployment process onto AWS Serverless
    - Provides sample SAM templates for different serverless application types from [Serverless Land](https://serverlessland.com/)
    - Provides schema types for different Lambda event sources and runtimes

    ## Usage Notes
    - By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations and public resource creation.
    - Access to sensitive data (Lambda function and API GW logs) requires the `--allow-sensitive-data-access` flag.

    ## Prerequisites
    1. Have an AWS account
    2. Configure AWS CLI with your credentials and profile. Set AWS_PROFILE environment variable if not using default
    3. Set AWS_REGION environment variable if not using default
    4. Install AWS CLI and SAM CLI
    """,
    dependencies=['pydantic', 'boto3', 'loguru'],
)


# Template resources
@mcp.resource(
    'template://list',
    description="""List of SAM deployment templates that can be used with the deploy_webapp_tool.
                Includes frontend, backend, and fullstack templates. """,
)
def template_list() -> Dict[str, Any]:
    """Retrieves a list of all available deployment templates.

    Returns:
        Dict[str, Any]: A dictionary containing the list of available templates.
    """
    return handle_template_list()


@mcp.resource(
    'template://{template_name}',
    description="""Returns details of a deployment template including compatible frameworks,
                template schema, and example usage of the template""",
)
def template_details(template_name: str) -> Dict[str, Any]:
    """Retrieves detailed information about a specific deployment template.

    Args:
        template_name (str): The name of the template to retrieve details for.

    Returns:
        Dict[str, Any]: A dictionary containing the template details.
    """
    return handle_template_details(template_name)


# Deployment resources
@mcp.resource(
    'deployment://list', description='Lists CloudFormation deployments managed by this MCP server.'
)
async def deployment_list() -> Dict[str, Any]:
    """Asynchronously retrieves a list of all AWS deployments managed by the MCP server.

    Returns:
        Dict[str, Any]: A dictionary containing the list of deployments.
    """
    return await handle_deployments_list()


@mcp.resource(
    'deployment://{project_name}',
    description="""Returns details of a CloudFormation deployment managed by this MCP server, including
                deployment type, status, and stack outputs.""",
)
async def deployment_details(project_name: str) -> Dict[str, Any]:
    """Asynchronously retrieves detailed information about a specific deployment.

    Args:
        project_name (str): The name of the project deployment to retrieve details for.

    Returns:
        Dict[str, Any]: A dictionary containing the deployment details.
    """
    return await handle_deployment_details(project_name)


# ESM Documentation Resource
@mcp.resource(
    'esm://documentation',
    description="""ESM MCP Server documentation providing comprehensive guidance on Event Source Mapping
                management between MSK/SMK clusters and Lambda functions. Contains usage patterns,
                troubleshooting guides, and parameter references.""",
)
def esm_documentation() -> Dict[str, Any]:
    """Retrieves ESM MCP Server documentation for AI agent context.

    Returns:
        Dict[str, Any]: A dictionary containing the ESM documentation content.
    """
    try:
        readme_path = os.path.join(os.path.dirname(__file__), 'tools', 'poller', 'README.md')
        with open(readme_path, 'r') as f:
            content = f.read()
        return {
            'content': content,
            'type': 'documentation',
            'scope': 'ESM Event Source Mapping Management',
        }
    except Exception as e:
        return {
            'error': f'Could not load ESM documentation: {str(e)}',
            'content': 'ESM documentation not available',
        }


# ESM Helper Functions
def _wait_and_validate_esm(
    function_name: str, esm_uuid: str, event_source_arn: str, kafka_topic: str
) -> str:
    """Wait for ESM to be enabled and run end-to-end test."""
    from awslabs.aws_serverless_mcp_server.tools.poller.ESM_Testing import ESMTesting
    from awslabs.aws_serverless_mcp_server.tools.poller.listEventSourceMapping import (
        ListEventSourceMapping,
    )

    lister = ListEventSourceMapping()
    tester = ESMTesting()

    for attempt in range(4):  # 30, 60, 90, 119 seconds
        wait_time = 30 if attempt < 3 else 29
        print(f'\nValidation Attempt {attempt + 1}/4')
        print(f' Waiting {wait_time} seconds to check ESM status...')
        time.sleep(wait_time)

        try:
            esm_list = lister.list_esm_by_function(function_name)
            target_esm = None
            for esm in esm_list.get('EventSourceMappings', []):
                if esm.get('UUID') == esm_uuid:
                    target_esm = esm
                    break

            if not target_esm:
                print('ESM not found during validation')
                continue

            state = target_esm.get('State', 'Unknown')
            print(f'Current State: {state}')

            if state == 'Enabled':
                print('✅ ESM is enabled, running end-to-end test...')
                success = tester.run_end_to_end_test(esm_uuid)
                return ' End-to-end test PASSED' if success else '❌ End-to-end test FAILED'
            elif state == 'Disabled':
                return ' ESM is disabled - something went wrong during creation'
            elif attempt < 3:
                print(f' ESM still {state}, will check again...')

        except Exception as e:
            print(f'Error checking ESM status: {str(e)}')
            if attempt == 3:
                return f'❌ Error during validation: {str(e)}'

    return 'ESM is taking too long to enable, check status manually later'


# ESM Tools
@mcp.tool(
    description='Creates an Event Source Mapping between MSK/SMK cluster and Lambda function'
)
def create_event_source_mapping(
    target: str,
    kafka_topic: str,
    # MSK parameters
    event_source_arn: str = None,
    # SMK parameters
    kafka_bootstrap_servers: str = None,
    source_access_configurations: list = None,
    max_concurrency: int = None,
    # Common parameters
    batch_size: int = None,
    starting_position: str = 'LATEST',
    kafka_consumer_group_id: str = None,
    max_batching_window: int = None,
    enabled: bool = True,
    report_batch_item_failures: bool = None,
    retry_attempts: int = None,
    # MSK-only parameters
    bisect_batch_on_error: bool = None,
    max_record_age: int = None,
    tumbling_window: int = None,
    min_pollers: int = 1,
    max_pollers: int = 2,
    run_validation: bool = False,
) -> str:
    """Create an Event Source Mapping between MSK/SMK cluster and Lambda function."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.createEventSourceMapping import (
            CreateEventSourceMapping,
        )
        from awslabs.aws_serverless_mcp_server.tools.poller.iamHelper import IAMHelper

        # Read ESM documentation for context (available via esm://documentation resource)

        # Smart detection and clarification
        if event_source_arn and kafka_bootstrap_servers:
            return 'Both MSK ARN and bootstrap servers provided. Please specify: Are you creating an MSK (managed) or SMK (self-managed) Event Source Mapping? Use only event_source_arn for MSK or only kafka_bootstrap_servers for SMK.'

        if not event_source_arn and not kafka_bootstrap_servers:
            return 'Error: Must provide either event_source_arn (MSK) or kafka_bootstrap_servers (SMK)'

        creator = CreateEventSourceMapping()

        if event_source_arn:
            # MSK path
            try:
                iam_helper = IAMHelper()
                iam_helper.add_msk_permissions(target, 'MSK')
            except Exception as e:
                print(f'Warning: IAM permission setup: {str(e)}')

            result = creator.create_esm(
                target=target,
                event_source_arn=event_source_arn,
                kafka_topic=kafka_topic,
                batch_size=batch_size,
                starting_position=starting_position,
                kafka_consumer_group_id=kafka_consumer_group_id,
                max_batching_window=max_batching_window,
                enabled=enabled,
                min_pollers=min_pollers,
                max_pollers=max_pollers,
                report_batch_item_failures=report_batch_item_failures,
                retry_attempts=retry_attempts,
                bisect_batch_on_error=bisect_batch_on_error,
                max_record_age=max_record_age,
                tumbling_window=tumbling_window,
            )
        else:
            # SMK path
            try:
                iam_helper = IAMHelper()
                iam_helper.add_msk_permissions(target, 'SMK')
            except Exception as e:
                print(f'Warning: IAM permission setup: {str(e)}')

            bootstrap_servers_list = [s.strip() for s in kafka_bootstrap_servers.split(',')]
            source_configs = source_access_configurations or []

            result = creator.create_smk_esm(
                target=target,
                kafka_bootstrap_servers=bootstrap_servers_list,
                kafka_topic=kafka_topic,
                source_access_configurations=source_configs,
                batch_size=batch_size,
                starting_position=starting_position,
                kafka_consumer_group_id=kafka_consumer_group_id,
                max_batching_window=max_batching_window,
                max_concurrency=max_concurrency,
                enabled=enabled,
                min_pollers=min_pollers,
                max_pollers=max_pollers,
                report_batch_item_failures=report_batch_item_failures,
                retry_attempts=retry_attempts,
            )

        if event_source_arn:
            initial_message = (
                f'MSK: {event_source_arn.split("/")[-2]}\n'
                f'{event_source_arn}\n'
                f'State: {result.get("State", "Creating")}\n'
                f'Details\n'
                f'Activate trigger: {"Yes" if enabled else "No"}\n'
                f'Batch size: {batch_size or 100}\n'
                f'Consumer group ID: {result.get("UUID")}\n'
                f'Event source mapping ARN: {result.get("EventSourceArn")}\n'
                f'Last processing result: No records processed\n'
                f'Maximum event pollers: {max_pollers}\n'
                f'Minimum event pollers: {min_pollers}\n'
                f'On-failure destination: None\n'
                f'Provisioned mode: Yes\n'
                f'Starting position: {starting_position}\n'
                f'Tags: View\n'
                f'Topic name: {kafka_topic}\n'
                f'UUID: {result.get("UUID")}\n'
            )
        else:
            initial_message = (
                f'SMK: Self-Managed Kafka\n'
                f'Bootstrap Servers: {kafka_bootstrap_servers}\n'
                f'State: {result.get("State", "Creating")}\n'
                f'Details\n'
                f'Activate trigger: {"Yes" if enabled else "No"}\n'
                f'Batch size: {batch_size or 100}\n'
                f'Consumer group ID: {result.get("UUID")}\n'
                f'Last processing result: No records processed\n'
                f'Maximum concurrency: {max_concurrency or "Default"}\n'
                f'Maximum event pollers: {max_pollers}\n'
                f'Minimum event pollers: {min_pollers}\n'
                f'On-failure destination: None\n'
                f'Starting position: {starting_position}\n'
                f'Tags: View\n'
                f'Topic name: {kafka_topic}\n'
                f'UUID: {result.get("UUID")}\n'
            )

        print(initial_message)

        if run_validation and event_source_arn:
            validation_result = _wait_and_validate_esm(
                target, result['UUID'], event_source_arn, kafka_topic
            )
            return f'{initial_message}\n{validation_result}'
        elif run_validation and kafka_bootstrap_servers:
            return f'{initial_message}\nValidation skipped for SMK - requires manual bootstrap server configuration'

        return initial_message

    except Exception as e:
        error_msg = f'Failed to create ESM: {str(e)}'
        if 'ResourceConflictException' in str(e) and 'already exists' in str(e):
            import re

            uuid_match = re.search(r'UUID ([a-f0-9-]+)', str(e))
            uuid = uuid_match.group(1) if uuid_match else 'unknown'
            return (
                f'Event Source Mapping already exists:\n'
                f'UUID: {uuid}\n'
                f'Use list_event_source_mappings() to check current status.'
            )
        return error_msg


@mcp.tool(
    description='Updates an Event Source Mapping between MSK/SMK cluster and Lambda function'
)
def update_event_source_mapping(
    uuid: str = None,
    function_name: str = None,
    event_source_arn: str = None,
    kafka_bootstrap_servers: str = None,
    kafka_topic: str = None,
    batch_size: int = None,
    bisect_batch_on_error: bool = None,
    enabled: bool = None,
    max_batching_window: int = None,
    max_record_age: int = None,
    report_batch_item_failures: bool = None,
    retry_attempts: int = None,
    tumbling_window: int = None,
    min_pollers: int = None,
    max_pollers: int = None,
    run_validation: bool = False,
) -> str:
    """Update an Event Source Mapping between MSK/SMK cluster and Lambda function."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.updateEventSourceMapping import (
            UpdateEventSourceMapping,
        )

        updater = UpdateEventSourceMapping()

        if uuid:
            print(f'Updating ESM with UUID={uuid}')
            result = updater.update_esm_by_uuid(
                uuid=uuid,
                batch_size=batch_size,
                bisect_batch_on_error=bisect_batch_on_error,
                enabled=enabled,
                function_name=function_name,
                max_batching_window=max_batching_window,
                max_record_age=max_record_age,
                report_batch_item_failures=report_batch_item_failures,
                retry_attempts=retry_attempts,
                tumbling_window=tumbling_window,
                min_pollers=min_pollers,
                max_pollers=max_pollers,
            )
        elif function_name and (event_source_arn or kafka_bootstrap_servers):
            if event_source_arn and kafka_bootstrap_servers:
                return 'Both MSK ARN and bootstrap servers provided. Please specify only one for update.'

            source_identifier = event_source_arn or kafka_bootstrap_servers
            print(
                f'Updating ESM with function={function_name}, source={source_identifier}, topic={kafka_topic}'
            )
            result = updater.update_esm_by_function_and_source(
                function_name=function_name,
                event_source_arn=event_source_arn,
                kafka_bootstrap_servers=kafka_bootstrap_servers,
                kafka_topic=kafka_topic,
                batch_size=batch_size,
                bisect_batch_on_error=bisect_batch_on_error,
                enabled=enabled,
                max_batching_window=max_batching_window,
                max_record_age=max_record_age,
                report_batch_item_failures=report_batch_item_failures,
                retry_attempts=retry_attempts,
                tumbling_window=tumbling_window,
                min_pollers=min_pollers,
                max_pollers=max_pollers,
            )
        else:
            return 'Error: Either UUID or both function_name and (event_source_arn OR kafka_bootstrap_servers) must be provided'

        print('ESM updated successfully')

        if run_validation:
            esm_uuid = uuid if uuid else result.get('UpdatedEventSourceMapping', {}).get('UUID')
            validation_result = _wait_and_validate_esm(
                function_name, esm_uuid, event_source_arn or kafka_bootstrap_servers, kafka_topic
            )
            return f'Successfully updated Event Source Mapping. State: {result.get("UpdatedEventSourceMapping", {}).get("State")}. Validation: {validation_result}'

        return f'Successfully updated Event Source Mapping. State: {result.get("UpdatedEventSourceMapping", {}).get("State")}'
    except Exception as e:
        error_msg = f'Failed to update ESM: {str(e)}'
        print(f'ESM update error: {error_msg}')
        return f'Error updating Event Source Mapping: {error_msg}'


@mcp.tool(
    description='Deletes an Event Source Mapping between MSK/SMK cluster and Lambda function'
)
def delete_event_source_mapping(
    uuid: str = None,
    function_name: str = None,
    event_source_arn: str = None,
    kafka_bootstrap_servers: str = None,
    kafka_topic: str = None,
) -> str:
    """Delete an Event Source Mapping between MSK/SMK cluster and Lambda function."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.deleteEventSourceMapping import (
            DeleteEventSourceMapping,
        )

        deleter = DeleteEventSourceMapping()
        if uuid:
            print(f'Deleting ESM with UUID={uuid}')
            result = deleter.delete_esm_by_uuid(uuid=uuid)
            return f'Successfully deleted Event Source Mapping with UUID: {uuid}. State: {result.get("State")}'
        elif function_name and (event_source_arn or kafka_bootstrap_servers):
            if event_source_arn and kafka_bootstrap_servers:
                return 'Both MSK ARN and bootstrap servers provided. Please specify only one for deletion.'

            source_identifier = event_source_arn or kafka_bootstrap_servers
            source_type = 'MSK ARN' if event_source_arn else 'SMK Bootstrap Servers'
            print(
                f'Deleting ESM with function={function_name}, {source_type}={source_identifier}, topic={kafka_topic}'
            )
            result = deleter.delete_esm_by_function_and_source(
                function_name=function_name,
                event_source_arn=event_source_arn,
                kafka_bootstrap_servers=kafka_bootstrap_servers,
                kafka_topic=kafka_topic,
            )
            return f'Successfully deleted {result.get("Count", 0)} Event Source Mapping(s) for {source_type}: {source_identifier}'
        else:
            return 'Error: Either UUID or both function_name and (event_source_arn OR kafka_bootstrap_servers) must be provided'
    except Exception as e:
        error_msg = f'Failed to delete ESM: {str(e)}'
        print(f'ESM deletion error: {error_msg}')
        return f'Error deleting Event Source Mapping: {error_msg}'


@mcp.tool(description='Lists Event Source Mappings between MSK/SMK clusters and Lambda functions')
def list_event_source_mappings(
    function_name: str = None, event_source_arn: str = None, max_items: int = None
) -> str:
    """List Event Source Mappings between MSK/SMK clusters and Lambda functions."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.listEventSourceMapping import (
            ListEventSourceMapping,
        )

        lister = ListEventSourceMapping()

        if function_name:
            print(f'Listing ESMs for function={function_name}')
            result = lister.list_esm_by_function(function_name=function_name)
        elif event_source_arn:
            print(f'Listing ESMs for source={event_source_arn}')
            result = lister.list_esm_by_source(event_source_arn=event_source_arn)
        else:
            print('Listing all ESMs')
            result = lister.list_all_esm(max_items=max_items)

        count = result.get('Count', 0)
        if count == 0:
            return 'No Event Source Mappings found'
        else:
            return (
                f'Found {count} Event Source Mapping(s): {result.get("EventSourceMappings", [])}'
            )
    except Exception as e:
        error_msg = f'Failed to list ESMs: {str(e)}'
        print(f'ESM listing error: {error_msg}')
        return f'Error listing Event Source Mappings: {error_msg}'


@mcp.tool(description='Run load testing on ESM with small/medium/large message volumes')
def run_esm_load_test(
    function_name: str,
    esm_uuid: str,
    kafka_topic: str,
    event_source_arn: str = None,
    kafka_bootstrap_servers: str = None,
    test_size: str = 'small',
) -> str:
    """Run load testing on ESM with small/medium/large message volumes."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.ESM_Testing import ESMTesting
        from awslabs.aws_serverless_mcp_server.tools.poller.iamHelper import IAMHelper

        if test_size not in ['small', 'medium', 'large', 'end_to_end']:
            return 'Invalid test size. Use: end_to_end, small, medium, or large'

        if not event_source_arn and not kafka_bootstrap_servers:
            return 'Error: Must provide either event_source_arn (MSK) or kafka_bootstrap_servers (SMK) for testing'

        tester = ESMTesting()
        print(f'\nStarting {test_size} load test for ESM {esm_uuid}')

        if kafka_bootstrap_servers:
            bootstrap_servers = kafka_bootstrap_servers
        else:
            iam_helper = IAMHelper()
            brokers = iam_helper.get_msk_bootstrap_brokers(event_source_arn)
            bootstrap_servers = brokers.get('sasl_iam', '').replace('sasl_iam://', '')

        if test_size == 'end_to_end':
            result, output = tester.run_end_to_end_test(
                esm_uuid, bootstrap_servers=bootstrap_servers, kafka_topic=kafka_topic
            )
        elif test_size == 'small':
            result, output = tester.run_small_load_test(
                esm_uuid, bootstrap_servers=bootstrap_servers, kafka_topic=kafka_topic
            )
        elif test_size == 'medium':
            result, output = tester.run_medium_load_test(
                esm_uuid, bootstrap_servers=bootstrap_servers, kafka_topic=kafka_topic
            )
        else:  # large
            result, output = tester.run_large_load_test(
                esm_uuid, bootstrap_servers=bootstrap_servers, kafka_topic=kafka_topic
            )

        return output

    except Exception as e:
        error_msg = f'Load test error: {str(e)}'
        print(f'{error_msg}')
        return f'Load test failed: {error_msg}'


@mcp.tool(description="Add MSK permissions to a Lambda function's execution role")
def add_msk_permissions(function_name: str) -> str:
    """Add MSK permissions to a Lambda function's execution role."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.iamHelper import IAMHelper

        iam_helper = IAMHelper()
        result = iam_helper.add_msk_permissions(function_name)
        print(f'IAM permissions added successfully: {result}')
        return "Successfully added MSK permissions to Lambda function's execution role"
    except Exception as e:
        error_msg = f'Failed to add MSK permissions: {str(e)}'
        print(f'IAM error: {error_msg}')
        return f'Error adding MSK permissions: {error_msg}'


@mcp.tool(description='Validate existing message processing without sending new messages')
def validate_existing_traffic(function_name: str, esm_uuid: str, wait_seconds: int = 90) -> str:
    """Validate existing message processing without sending new messages."""
    mcp.last_activity_time = time.time()
    try:
        from awslabs.aws_serverless_mcp_server.tools.poller.ESM_Testing import ESMTesting
        from awslabs.aws_serverless_mcp_server.tools.poller.iamHelper import IAMHelper
        from awslabs.aws_serverless_mcp_server.tools.poller.listEventSourceMapping import (
            ListEventSourceMapping,
        )

        lister = ListEventSourceMapping()
        esm_details = lister.list_esm_by_function(function_name)

        target_esm = next(
            (
                esm
                for esm in esm_details.get('EventSourceMappings', [])
                if esm.get('UUID') == esm_uuid
            ),
            None,
        )

        if not target_esm:
            return f'ESM with UUID {esm_uuid} not found'

        event_source_arn = target_esm.get('EventSourceArn')
        self_managed_source = target_esm.get('SelfManagedEventSource')
        kafka_topic = target_esm.get('Topics', [''])[0]

        if event_source_arn:
            iam_helper = IAMHelper()
            brokers = iam_helper.get_msk_bootstrap_brokers(event_source_arn)
            bootstrap_servers = brokers.get('sasl_scram', '').replace('sasl_scram://', '')
        elif self_managed_source:
            bootstrap_servers_list = self_managed_source.get('Endpoints', {}).get(
                'KAFKA_BOOTSTRAP_SERVERS', []
            )
            bootstrap_servers = ','.join(bootstrap_servers_list)
        else:
            return 'Could not determine cluster type for validation'

        if not bootstrap_servers:
            return 'Could not get bootstrap brokers for validation'

        tester = ESMTesting()
        tester.validate_existing_traffic(bootstrap_servers, kafka_topic, esm_uuid, wait_seconds)

        return 'Validation complete - check output above for details'

    except Exception as e:
        return f'Validation error: {str(e)}'


def main() -> int:
    """Entry point for the AWS Serverless MCP server.

    This function is called when the `awslabs.aws-serverless-mcp-server` command is run.
    It starts the MCP server and handles command-line arguments.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    os.makedirs(DEPLOYMENT_STATUS_DIR, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

    parser = argparse.ArgumentParser(description='AWS Serverless MCP Server')
    parser.add_argument(
        '--allow-write', action='store_true', help='Enables MCP tools that make write operations'
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action='store_true',
        help='Returns sensitive data from tools (e.g. logs, environment variables)',
    )

    args = parser.parse_args()

    WebappDeploymentHelpTool(mcp)
    DeployServerlessAppHelpTool(mcp)
    GetIaCGuidanceTool(mcp)
    GetLambdaEventSchemasTool(mcp)
    GetLambdaGuidanceTool(mcp)
    GetServerlessTemplatesTool(mcp)

    SamBuildTool(mcp)
    SamDeployTool(mcp, args.allow_write)
    SamInitTool(mcp)
    SamLocalInvokeTool(mcp)
    SamLogsTool(mcp, args.allow_sensitive_data_access)

    ListRegistriesTool(mcp, schemas_client)
    SearchSchemaTool(mcp, schemas_client)
    DescribeSchemaTool(mcp, schemas_client)

    GetMetricsTool(mcp)
    ConfigureDomainTool(mcp, args.allow_write)
    DeployWebAppTool(mcp, args.allow_write)
    UpdateFrontendTool(mcp, args.allow_write)

    # Set AWS_EXECUTION_ENV to configure user agent of boto3. Setting it through an environment variable
    # because SAM CLI does not support setting user agents directly
    os.environ['AWS_EXECUTION_ENV'] = f'awslabs/mcp/aws-serverless-mcp-server/{__version__}'

    mode_info = []
    if not args.allow_write:
        mode_info.append('read-only mode')
    if not args.allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    try:
        logger.info(f'Starting AWS Serverless MCP Server in {", ".join(mode_info)}')
        mcp.run()
        return 0
    except Exception as e:
        logger.error(f'Error starting AWS Serverless MCP Server: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
