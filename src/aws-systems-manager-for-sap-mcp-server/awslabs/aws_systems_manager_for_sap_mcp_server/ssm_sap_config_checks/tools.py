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

"""SSM for SAP configuration check tools for MCP server."""

from awslabs.aws_systems_manager_for_sap_mcp_server.client_factory import get_aws_client
from awslabs.aws_systems_manager_for_sap_mcp_server.common import format_datetime
from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.models import (
    ConfigCheckDefinition,
    ConfigCheckOperation,
    ConfigCheckSummary,
    StartConfigChecksResponse,
    SubCheckResult,
)
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List


class SSMSAPConfigCheckTools:
    """SSM for SAP configuration check tools."""

    def __init__(self):
        """Initialize the configuration check tools."""
        pass

    def register(self, mcp):
        """Register all configuration check tools with the MCP server."""
        mcp.tool(name='list_config_check_definitions')(self.list_config_check_definitions)
        mcp.tool(name='start_config_checks')(self.start_config_checks)
        mcp.tool(name='get_config_check_summary')(self.get_config_check_summary)
        mcp.tool(name='get_config_check_operation')(self.get_config_check_operation)
        mcp.tool(name='list_sub_check_results')(self.list_sub_check_results)
        mcp.tool(name='list_sub_check_rule_results')(self.list_sub_check_rule_results)

    async def list_config_check_definitions(
        self,
        ctx: Context,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> List[ConfigCheckDefinition]:
        """List all configuration check types and their metadata offered by SSM for SAP.

        Use this to discover which configuration checks are available before running them.

        Args:
            ctx: MCP context object.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            List of ConfigCheckDefinition with check IDs and descriptions.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.list_configuration_check_definitions()
            definitions = []
            for check in response.get('ConfigurationChecks', []):
                definitions.append(
                    ConfigCheckDefinition(
                        id=check.get('Id', ''),
                        name=check.get('Name'),
                        description=check.get('Description'),
                    )
                )
            return definitions
        except Exception as e:
            logger.error(f'Error listing config check definitions: {e}')
            return [ConfigCheckDefinition(id='ERROR', description=str(e))]

    async def start_config_checks(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        check_ids: Annotated[
            List[str],
            Field(
                description='List of configuration check IDs to run (e.g., ["SAP_CHECK_01"]). Use list_config_check_definitions to discover available checks.'
            ),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> StartConfigChecksResponse:
        """Trigger configuration checks against a specified SSM for SAP application.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            check_ids: List of check IDs to run.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            StartConfigChecksResponse with initiated operation details.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.start_configuration_checks(
                ApplicationId=application_id,
                ConfigurationCheckIds=check_ids,
            )
            return StartConfigChecksResponse(
                status='success',
                message=f'Configuration checks initiated for {application_id}',
                operations=response.get('ConfigurationCheckOperations'),
            )
        except ClientError as e:
            return StartConfigChecksResponse(
                status='error',
                message=f'{e.response["Error"]["Code"]}: {e.response["Error"]["Message"]}',
            )
        except Exception as e:
            logger.error(f'Error starting config checks: {e}')
            return StartConfigChecksResponse(status='error', message=str(e))

    async def get_config_check_summary(
        self,
        ctx: Context,
        application_id: Annotated[
            str,
            Field(description='The unique identifier of the SAP application.'),
        ],
        include_subchecks: Annotated[
            bool,
            Field(description='Whether to include subcheck details. Default: True.'),
        ] = True,
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> ConfigCheckSummary:
        """Get a comprehensive summary of the latest configuration check results.

        Lists the most recent result for each configuration check type, with optional
        subcheck details.

        Args:
            ctx: MCP context object.
            application_id: The application ID.
            include_subchecks: Whether to include subcheck details.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            ConfigCheckSummary with check results and counts.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.list_configuration_check_operations(
                ApplicationId=application_id,
                ListMode='LATEST_PER_CHECK',
            )
            check_operations = response.get('ConfigurationCheckOperations', [])

            checks = []
            status_counts: Dict[str, int] = {}
            result_counts: Dict[str, int] = {}

            for check_op in check_operations:
                check_id = check_op.get('ConfigurationCheckId', 'UNKNOWN')
                check_status = check_op.get('Status', 'UNKNOWN')
                result = check_op.get('Result', 'UNKNOWN')
                operation_id = check_op.get('OperationId', '')

                status_counts[check_status] = status_counts.get(check_status, 0) + 1
                result_counts[result] = result_counts.get(result, 0) + 1

                checks.append(
                    ConfigCheckOperation(
                        check_id=check_id,
                        operation_id=operation_id if operation_id else None,
                        status=check_status,
                        result=result if result != 'UNKNOWN' else None,
                        last_updated=format_datetime(check_op.get('LastUpdatedTime')),
                    )
                )

            return ConfigCheckSummary(
                application_id=application_id,
                total_checks=len(check_operations),
                by_status=status_counts,
                by_result=result_counts,
                checks=checks,
            )
        except Exception as e:
            logger.error(f'Error getting config check summary: {e}')
            return ConfigCheckSummary(
                application_id=application_id,
                checks=[
                    ConfigCheckOperation(
                        check_id='ERROR', status='ERROR', result=str(e)
                    )
                ],
            )

    async def get_config_check_operation(
        self,
        ctx: Context,
        operation_id: Annotated[
            str,
            Field(description='The unique identifier of the configuration check operation.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> Dict[str, Any]:
        """Get the details of a specific configuration check operation.

        Args:
            ctx: MCP context object.
            operation_id: The operation ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            Dictionary with configuration check operation details.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.get_configuration_check_operation(OperationId=operation_id)
            return response.get('ConfigurationCheckOperation', {})
        except Exception as e:
            logger.error(f'Error getting config check operation: {e}')
            return {'error': str(e)}

    async def list_sub_check_results(
        self,
        ctx: Context,
        operation_id: Annotated[
            str,
            Field(description='The unique identifier of the configuration check operation.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> List[SubCheckResult]:
        """List the sub-check results for a specific configuration check operation.

        Args:
            ctx: MCP context object.
            operation_id: The operation ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            List of SubCheckResult with sub-check details.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.list_sub_check_results(OperationId=operation_id)
            results = []
            for sc in response.get('SubCheckResults', []):
                results.append(
                    SubCheckResult(
                        id=sc.get('Id', ''),
                        name=sc.get('Name', 'UNKNOWN'),
                        result=sc.get('Result', 'UNKNOWN'),
                        description=sc.get('Description'),
                    )
                )
            return results
        except Exception as e:
            logger.error(f'Error listing sub check results: {e}')
            return [SubCheckResult(id='ERROR', name='ERROR', result=str(e))]

    async def list_sub_check_rule_results(
        self,
        ctx: Context,
        subcheck_result_id: Annotated[
            str,
            Field(description='The unique identifier of the sub-check result.'),
        ],
        region: Annotated[
            str | None,
            Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name.'),
        ] = None,
    ) -> List[Dict[str, Any]]:
        """List the rule evaluation results for a specific sub-check.

        Args:
            ctx: MCP context object.
            subcheck_result_id: The sub-check result ID.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            List of rule result dictionaries.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)
            response = client.list_sub_check_rule_results(
                SubCheckResultId=subcheck_result_id
            )
            return response.get('RuleResults', [])
        except Exception as e:
            logger.error(f'Error listing sub check rule results: {e}')
            return [{'error': str(e)}]
