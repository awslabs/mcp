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

"""Observability Admin tools for MCP server."""

from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client
from awslabs.cloudwatch_mcp_server.observability_admin.models import (
    DestinationConfiguration,
    GetTelemetryRuleResponse,
    ListResourceTelemetryResponse,
    ListTelemetryRulesResponse,
    TelemetryConfiguration,
    TelemetryEvaluationStatusResponse,
    TelemetryRuleDetail,
    TelemetryRuleSummary,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Dict, List, Optional


class ObservabilityAdminTools:
    """Observability Admin tools for MCP server."""

    def __init__(self):
        """Initialize the Observability Admin tools."""
        pass

    def register(self, mcp):
        """Register all Observability Admin tools with the MCP server."""
        mcp.tool(name='get_telemetry_evaluation_status')(self.get_telemetry_evaluation_status)
        mcp.tool(name='start_telemetry_evaluation')(self.start_telemetry_evaluation)
        mcp.tool(name='stop_telemetry_evaluation')(self.stop_telemetry_evaluation)
        mcp.tool(name='get_telemetry_evaluation_status_for_organization')(
            self.get_telemetry_evaluation_status_for_organization
        )
        mcp.tool(name='start_telemetry_evaluation_for_organization')(
            self.start_telemetry_evaluation_for_organization
        )
        mcp.tool(name='stop_telemetry_evaluation_for_organization')(
            self.stop_telemetry_evaluation_for_organization
        )
        mcp.tool(name='list_resource_telemetry')(self.list_resource_telemetry)
        mcp.tool(name='list_telemetry_rules')(self.list_telemetry_rules)
        mcp.tool(name='get_telemetry_rule')(self.get_telemetry_rule)
        mcp.tool(name='list_resource_telemetry_for_organization')(
            self.list_resource_telemetry_for_organization
        )
        mcp.tool(name='list_telemetry_rules_for_organization')(
            self.list_telemetry_rules_for_organization
        )
        mcp.tool(name='get_telemetry_rule_for_organization')(
            self.get_telemetry_rule_for_organization
        )

    async def get_telemetry_evaluation_status(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Returns the current onboarding status of the telemetry config feature.

        Use this tool to check whether telemetry evaluation is enabled for the account.
        The status indicates if the feature is running, stopped, starting, or has failed.

        Returns:
            TelemetryEvaluationStatusResponse: The current telemetry evaluation status.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            response = client.get_telemetry_evaluation_status()

            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'UNKNOWN'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in get_telemetry_evaluation_status: {str(e)}')
            await ctx.error(f'Error getting telemetry evaluation status: {str(e)}')
            raise

    async def start_telemetry_evaluation(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Begins onboarding the caller's AWS account to the telemetry config feature.

        This enables CloudWatch to discover and audit telemetry configurations across
        resources in the account. This is a free feature with no additional charges.
        See https://docs.aws.amazon.com/cloudwatch/latest/monitoring/telemetry-config.html

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to enable telemetry evaluation for their account.

        For a single account, evaluation typically becomes available almost immediately.
        After starting, use get_telemetry_evaluation_status to check progress.
        Use stop_telemetry_evaluation to disable it later if needed.

        Returns:
            TelemetryEvaluationStatusResponse: The status after initiating evaluation.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            client.start_telemetry_evaluation()

            # Fetch status after starting
            response = client.get_telemetry_evaluation_status()
            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'STARTING'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in start_telemetry_evaluation: {str(e)}')
            await ctx.error(f'Error starting telemetry evaluation: {str(e)}')
            raise

    async def stop_telemetry_evaluation(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Stops the telemetry config feature for the caller's AWS account.

        This disables CloudWatch telemetry configuration discovery and auditing.
        After stopping, use get_telemetry_evaluation_status to confirm the feature
        has been stopped.

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to disable telemetry evaluation for their account.

        Returns:
            TelemetryEvaluationStatusResponse: The status after stopping evaluation.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            client.stop_telemetry_evaluation()

            # Fetch status after stopping
            response = client.get_telemetry_evaluation_status()
            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'STOPPING'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in stop_telemetry_evaluation: {str(e)}')
            await ctx.error(f'Error stopping telemetry evaluation: {str(e)}')
            raise

    async def get_telemetry_evaluation_status_for_organization(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Returns the organization-level onboarding status of the telemetry config feature.

        Can only be called by the organization's management account or a delegated
        administrator account.

        Returns:
            TelemetryEvaluationStatusResponse: The current organization telemetry evaluation status.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            response = client.get_telemetry_evaluation_status_for_organization()

            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'UNKNOWN'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in get_telemetry_evaluation_status_for_organization: {str(e)}')
            await ctx.error(f'Error getting organization telemetry evaluation status: {str(e)}')
            raise

    async def start_telemetry_evaluation_for_organization(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Begins onboarding the organization and all member accounts to the telemetry config feature.

        Can only be called by the organization's management account or a delegated
        administrator account. This is a free feature with no additional charges.
        See https://docs.aws.amazon.com/cloudwatch/latest/monitoring/telemetry-config.html

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to enable telemetry evaluation for their organization.

        Onboarding time depends on organization size: a single account is nearly instant,
        while large organizations with thousands of accounts may take 20-30 minutes.
        After starting, use get_telemetry_evaluation_status_for_organization to check progress.
        Use stop_telemetry_evaluation_for_organization to disable it later if needed.

        Returns:
            TelemetryEvaluationStatusResponse: The status after initiating organization evaluation.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            client.start_telemetry_evaluation_for_organization()

            # Fetch status after starting
            response = client.get_telemetry_evaluation_status_for_organization()
            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'STARTING'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in start_telemetry_evaluation_for_organization: {str(e)}')
            await ctx.error(f'Error starting organization telemetry evaluation: {str(e)}')
            raise

    async def stop_telemetry_evaluation_for_organization(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> TelemetryEvaluationStatusResponse:
        """Stops the telemetry config feature for the organization and all member accounts.

        Can only be called by the organization's management account or a delegated
        administrator account. After stopping, use
        get_telemetry_evaluation_status_for_organization to confirm the feature
        has been stopped.

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to disable telemetry evaluation for their organization.

        Returns:
            TelemetryEvaluationStatusResponse: The status after stopping organization evaluation.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            client.stop_telemetry_evaluation_for_organization()

            # Fetch status after stopping
            response = client.get_telemetry_evaluation_status_for_organization()
            return TelemetryEvaluationStatusResponse(
                status=response.get('Status', 'STOPPING'),
                failure_reason=response.get('FailureReason'),
            )
        except Exception as e:
            logger.error(f'Error in stop_telemetry_evaluation_for_organization: {str(e)}')
            await ctx.error(f'Error stopping organization telemetry evaluation: {str(e)}')
            raise

    async def list_resource_telemetry(
        self,
        ctx: Context,
        resource_types: Annotated[
            Optional[List[str]],
            Field(
                description='Filter by resource types. Valid values: AWS::EC2::Instance, AWS::EC2::VPC, AWS::Lambda::Function, AWS::CloudTrail, AWS::EKS::Cluster, AWS::WAFv2::WebACL, AWS::ElasticLoadBalancingV2::LoadBalancer, AWS::Route53Resolver::ResolverEndpoint, AWS::BedrockAgentCore::Runtime, AWS::BedrockAgentCore::Browser, AWS::BedrockAgentCore::CodeInterpreter'
            ),
        ] = None,
        resource_identifier_prefix: Annotated[
            Optional[str],
            Field(
                description='Filter resources whose identifier starts with this prefix (min 3 chars).'
            ),
        ] = None,
        telemetry_configuration_state: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='Filter by telemetry state. Keys: Logs, Metrics, Traces. Values: Enabled, Disabled, NotApplicable. Example: {"Logs": "Enabled"}'
            ),
        ] = None,
        resource_tags: Annotated[
            Optional[Dict[str, str]],
            Field(description='Filter by resource tags. Example: {"Environment": "Production"}'),
        ] = None,
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return (default: 50).'),
        ] = 50,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> ListResourceTelemetryResponse:
        """Returns telemetry configurations for AWS resources in the account.

        Lists the telemetry state (Logs, Metrics, Traces) for resources like EC2 instances,
        Lambda functions, EKS clusters, etc. Requires telemetry evaluation to be running
        (use start_telemetry_evaluation first if needed). For a single account, evaluation
        is typically available almost immediately after starting. Use
        get_telemetry_evaluation_status to verify the status is RUNNING before querying.

        Usage: Use this to audit which resources have telemetry enabled or disabled,
        identify observability gaps, and verify monitoring coverage.

        Returns:
            ListResourceTelemetryResponse: List of resource telemetry configurations.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            client = get_aws_client('observabilityadmin', region, profile_name)

            kwargs = {}
            if resource_types:
                kwargs['ResourceTypes'] = resource_types
            if resource_identifier_prefix:
                kwargs['ResourceIdentifierPrefix'] = resource_identifier_prefix
            if telemetry_configuration_state:
                kwargs['TelemetryConfigurationState'] = telemetry_configuration_state
            if resource_tags:
                kwargs['ResourceTags'] = resource_tags

            paginator = client.get_paginator('list_resource_telemetry')
            page_iterator = paginator.paginate(
                **kwargs,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            configurations = []
            total_fetched = 0

            for page in page_iterator:
                for item in page.get('TelemetryConfigurations', []):
                    total_fetched += 1
                    if len(configurations) < max_items:
                        configurations.append(
                            TelemetryConfiguration(
                                account_identifier=item.get('AccountIdentifier', ''),
                                resource_type=item.get('ResourceType', ''),
                                resource_identifier=item.get('ResourceIdentifier', ''),
                                telemetry_configuration_state=item.get(
                                    'TelemetryConfigurationState', {}
                                ),
                                resource_tags=item.get('ResourceTags', {}),
                                last_update_timestamp=item.get('LastUpdateTimeStamp'),
                                telemetry_source_type=item.get('TelemetrySourceType'),
                            )
                        )

            has_more = total_fetched > max_items
            message = None
            if not configurations:
                message = 'No resource telemetry configurations found. Ensure telemetry evaluation is running.'
            elif has_more:
                message = f'Showing {len(configurations)} resources (more available)'

            return ListResourceTelemetryResponse(
                telemetry_configurations=configurations,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in list_resource_telemetry: {str(e)}')
            await ctx.error(f'Error listing resource telemetry: {str(e)}')
            raise

    async def list_telemetry_rules(
        self,
        ctx: Context,
        rule_name_prefix: Annotated[
            Optional[str],
            Field(description='Filter rules whose names begin with this prefix.'),
        ] = None,
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return (default: 50).'),
        ] = 50,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> ListTelemetryRulesResponse:
        """Lists all telemetry rules in the account.

        Telemetry rules control what telemetry (Logs, Metrics, Traces) is collected
        for specific resource types. Use this to audit your telemetry collection
        configuration.

        Returns:
            ListTelemetryRulesResponse: List of telemetry rule summaries.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            client = get_aws_client('observabilityadmin', region, profile_name)

            kwargs = {}
            if rule_name_prefix:
                kwargs['RuleNamePrefix'] = rule_name_prefix

            paginator = client.get_paginator('list_telemetry_rules')
            page_iterator = paginator.paginate(
                **kwargs,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            summaries = []
            total_fetched = 0

            for page in page_iterator:
                for item in page.get('TelemetryRuleSummaries', []):
                    total_fetched += 1
                    if len(summaries) < max_items:
                        summaries.append(
                            TelemetryRuleSummary(
                                rule_name=item.get('RuleName', ''),
                                rule_arn=item.get('RuleArn', ''),
                                resource_type=item.get('ResourceType', ''),
                                telemetry_type=item.get('TelemetryType', ''),
                                telemetry_source_types=item.get('TelemetrySourceTypes', []),
                                created_timestamp=item.get('CreatedTimeStamp'),
                                last_update_timestamp=item.get('LastUpdateTimeStamp'),
                            )
                        )

            has_more = total_fetched > max_items
            message = None
            if not summaries:
                message = 'No telemetry rules found'
            elif has_more:
                message = f'Showing {len(summaries)} rules (more available)'

            return ListTelemetryRulesResponse(
                telemetry_rule_summaries=summaries,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in list_telemetry_rules: {str(e)}')
            await ctx.error(f'Error listing telemetry rules: {str(e)}')
            raise

    async def get_telemetry_rule(
        self,
        ctx: Context,
        rule_identifier: Annotated[
            str,
            Field(description='The identifier (name or ARN) of the telemetry rule to retrieve.'),
        ],
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> GetTelemetryRuleResponse:
        """Retrieves the details of a specific telemetry rule in your account.

        Returns the full configuration of a telemetry rule including resource type,
        telemetry type, source types, destination configuration, and any
        resource-type-specific parameters (VPC Flow Logs, CloudTrail, ELB, WAF, etc.).

        Use list_telemetry_rules first to discover available rule names, then use this
        tool to get the full configuration details of a specific rule.

        Returns:
            GetTelemetryRuleResponse: The full telemetry rule details.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            response = client.get_telemetry_rule(RuleIdentifier=rule_identifier)
            return self._parse_telemetry_rule_response(response)
        except Exception as e:
            logger.error(f'Error in get_telemetry_rule: {str(e)}')
            await ctx.error(f'Error getting telemetry rule: {str(e)}')
            raise

    def _parse_telemetry_rule_response(self, response: dict) -> GetTelemetryRuleResponse:
        """Parse a get_telemetry_rule or get_telemetry_rule_for_organization response."""
        telemetry_rule_data = response.get('TelemetryRule')
        telemetry_rule = None
        if telemetry_rule_data:
            dest_config_data = telemetry_rule_data.get('DestinationConfiguration')
            dest_config = None
            if dest_config_data:
                dest_config = DestinationConfiguration(
                    destination_type=dest_config_data.get('DestinationType'),
                    destination_pattern=dest_config_data.get('DestinationPattern'),
                    retention_in_days=dest_config_data.get('RetentionInDays'),
                    vpc_flow_log_parameters=dest_config_data.get('VPCFlowLogParameters'),
                    cloudtrail_parameters=dest_config_data.get('CloudtrailParameters'),
                    elb_load_balancer_logging_parameters=dest_config_data.get(
                        'ELBLoadBalancerLoggingParameters'
                    ),
                    waf_logging_parameters=dest_config_data.get('WAFLoggingParameters'),
                    log_delivery_parameters=dest_config_data.get('LogDeliveryParameters'),
                )

            telemetry_rule = TelemetryRuleDetail(
                resource_type=telemetry_rule_data.get('ResourceType', ''),
                telemetry_type=telemetry_rule_data.get('TelemetryType', ''),
                telemetry_source_types=telemetry_rule_data.get('TelemetrySourceTypes', []),
                destination_configuration=dest_config,
                scope=telemetry_rule_data.get('Scope'),
                selection_criteria=telemetry_rule_data.get('SelectionCriteria'),
            )

        return GetTelemetryRuleResponse(
            rule_name=response.get('RuleName', ''),
            rule_arn=response.get('RuleArn', ''),
            created_timestamp=response.get('CreatedTimeStamp'),
            last_update_timestamp=response.get('LastUpdateTimeStamp'),
            telemetry_rule=telemetry_rule,
        )

    async def list_resource_telemetry_for_organization(
        self,
        ctx: Context,
        account_identifiers: Annotated[
            Optional[List[str]],
            Field(
                description='Filter by AWS account IDs (max 10). Each must be a 12-digit account ID.'
            ),
        ] = None,
        resource_types: Annotated[
            Optional[List[str]],
            Field(
                description='Filter by resource types. Valid values: AWS::EC2::Instance, AWS::EC2::VPC, AWS::Lambda::Function, AWS::CloudTrail, AWS::EKS::Cluster, AWS::WAFv2::WebACL, AWS::ElasticLoadBalancingV2::LoadBalancer, AWS::Route53Resolver::ResolverEndpoint, AWS::BedrockAgentCore::Runtime, AWS::BedrockAgentCore::Browser, AWS::BedrockAgentCore::CodeInterpreter'
            ),
        ] = None,
        resource_identifier_prefix: Annotated[
            Optional[str],
            Field(
                description='Filter resources whose identifier starts with this prefix (min 3 chars).'
            ),
        ] = None,
        telemetry_configuration_state: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='Filter by telemetry state. Keys: Logs, Metrics, Traces. Values: Enabled, Disabled, NotApplicable. Example: {"Logs": "Enabled"}'
            ),
        ] = None,
        resource_tags: Annotated[
            Optional[Dict[str, str]],
            Field(description='Filter by resource tags. Example: {"Environment": "Production"}'),
        ] = None,
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return (default: 50).'),
        ] = 50,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> ListResourceTelemetryResponse:
        """Returns telemetry configurations for AWS resources across the organization.

        Lists the telemetry state (Logs, Metrics, Traces) for resources across all accounts
        in the organization. Can only be called by the organization's management account
        or a delegated administrator account. Requires telemetry evaluation to be running.
        For large organizations with thousands of accounts, onboarding may take 20-30 minutes.
        Use get_telemetry_evaluation_status_for_organization to verify the status is RUNNING.

        Returns:
            ListResourceTelemetryResponse: List of resource telemetry configurations.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            client = get_aws_client('observabilityadmin', region, profile_name)

            kwargs = {}
            if account_identifiers:
                kwargs['AccountIdentifiers'] = account_identifiers
            if resource_types:
                kwargs['ResourceTypes'] = resource_types
            if resource_identifier_prefix:
                kwargs['ResourceIdentifierPrefix'] = resource_identifier_prefix
            if telemetry_configuration_state:
                kwargs['TelemetryConfigurationState'] = telemetry_configuration_state
            if resource_tags:
                kwargs['ResourceTags'] = resource_tags

            paginator = client.get_paginator('list_resource_telemetry_for_organization')
            page_iterator = paginator.paginate(
                **kwargs,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            configurations = []
            total_fetched = 0

            for page in page_iterator:
                for item in page.get('TelemetryConfigurations', []):
                    total_fetched += 1
                    if len(configurations) < max_items:
                        configurations.append(
                            TelemetryConfiguration(
                                account_identifier=item.get('AccountIdentifier', ''),
                                resource_type=item.get('ResourceType', ''),
                                resource_identifier=item.get('ResourceIdentifier', ''),
                                telemetry_configuration_state=item.get(
                                    'TelemetryConfigurationState', {}
                                ),
                                resource_tags=item.get('ResourceTags', {}),
                                last_update_timestamp=item.get('LastUpdateTimeStamp'),
                                telemetry_source_type=item.get('TelemetrySourceType'),
                            )
                        )

            has_more = total_fetched > max_items
            message = None
            if not configurations:
                message = 'No resource telemetry configurations found for the organization.'
            elif has_more:
                message = f'Showing {len(configurations)} resources (more available)'

            return ListResourceTelemetryResponse(
                telemetry_configurations=configurations,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in list_resource_telemetry_for_organization: {str(e)}')
            await ctx.error(f'Error listing organization resource telemetry: {str(e)}')
            raise

    async def list_telemetry_rules_for_organization(
        self,
        ctx: Context,
        rule_name_prefix: Annotated[
            Optional[str],
            Field(description='Filter rules whose names begin with this prefix.'),
        ] = None,
        source_account_ids: Annotated[
            Optional[List[str]],
            Field(
                description='Filter by source account IDs (max 10). Each must be a 12-digit account ID.'
            ),
        ] = None,
        source_organization_unit_ids: Annotated[
            Optional[List[str]],
            Field(description='Filter by organizational unit IDs, e.g. ou-xxxx-xxxxxxxx.'),
        ] = None,
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return (default: 50).'),
        ] = 50,
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> ListTelemetryRulesResponse:
        """Lists all organization telemetry rules.

        Can only be called by the organization's management account or a delegated
        administrator account. Supports filtering by rule name prefix, source account
        IDs, and organizational unit IDs.

        Returns:
            ListTelemetryRulesResponse: List of organization telemetry rule summaries.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            client = get_aws_client('observabilityadmin', region, profile_name)

            kwargs = {}
            if rule_name_prefix:
                kwargs['RuleNamePrefix'] = rule_name_prefix
            if source_account_ids:
                kwargs['SourceAccountIds'] = source_account_ids
            if source_organization_unit_ids:
                kwargs['SourceOrganizationUnitIds'] = source_organization_unit_ids

            paginator = client.get_paginator('list_telemetry_rules_for_organization')
            page_iterator = paginator.paginate(
                **kwargs,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            summaries = []
            total_fetched = 0

            for page in page_iterator:
                for item in page.get('TelemetryRuleSummaries', []):
                    total_fetched += 1
                    if len(summaries) < max_items:
                        summaries.append(
                            TelemetryRuleSummary(
                                rule_name=item.get('RuleName', ''),
                                rule_arn=item.get('RuleArn', ''),
                                resource_type=item.get('ResourceType', ''),
                                telemetry_type=item.get('TelemetryType', ''),
                                telemetry_source_types=item.get('TelemetrySourceTypes', []),
                                created_timestamp=item.get('CreatedTimeStamp'),
                                last_update_timestamp=item.get('LastUpdateTimeStamp'),
                            )
                        )

            has_more = total_fetched > max_items
            message = None
            if not summaries:
                message = 'No organization telemetry rules found'
            elif has_more:
                message = f'Showing {len(summaries)} rules (more available)'

            return ListTelemetryRulesResponse(
                telemetry_rule_summaries=summaries,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in list_telemetry_rules_for_organization: {str(e)}')
            await ctx.error(f'Error listing organization telemetry rules: {str(e)}')
            raise

    async def get_telemetry_rule_for_organization(
        self,
        ctx: Context,
        rule_identifier: Annotated[
            str,
            Field(
                description='The identifier (name or ARN) of the organization telemetry rule to retrieve.'
            ),
        ],
        region: Annotated[
            Optional[str],
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            Optional[str],
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> GetTelemetryRuleResponse:
        """Retrieves the details of a specific organization telemetry rule.

        Can only be called by the organization's management account or a delegated
        administrator account. Returns the full configuration including resource type,
        telemetry type, source types, destination configuration, and resource-type-specific
        parameters.

        Returns:
            GetTelemetryRuleResponse: The full organization telemetry rule details.
        """
        try:
            client = get_aws_client('observabilityadmin', region, profile_name)
            response = client.get_telemetry_rule_for_organization(RuleIdentifier=rule_identifier)
            return self._parse_telemetry_rule_response(response)
        except Exception as e:
            logger.error(f'Error in get_telemetry_rule_for_organization: {str(e)}')
            await ctx.error(f'Error getting organization telemetry rule: {str(e)}')
            raise
