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

"""CloudWatch Contributor Insights tools for MCP server."""

from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client
from awslabs.cloudwatch_mcp_server.contributor_insights.models import (
    DescribeInsightRulesResponse,
    GetInsightRuleReportResponse,
    InsightRuleContributor,
    InsightRuleMetricDatapoint,
    InsightRuleSummary,
    ListManagedInsightRulesResponse,
    ManagedInsightRuleSummary,
    ModifyInsightRulesResponse,
    PartialFailure,
    PutInsightRuleResponse,
)
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, List, Optional


class ContributorInsightsTools:
    """CloudWatch Contributor Insights tools for MCP server."""

    def __init__(self):
        """Initialize the Contributor Insights tools."""
        pass

    def register(self, mcp):
        """Register all Contributor Insights tools with the MCP server."""
        mcp.tool(name='describe_insight_rules')(self.describe_insight_rules)
        mcp.tool(name='get_insight_rule_report')(self.get_insight_rule_report)
        mcp.tool(name='list_managed_insight_rules')(self.list_managed_insight_rules)
        mcp.tool(name='put_insight_rule')(self.put_insight_rule)
        mcp.tool(name='enable_insight_rules')(self.enable_insight_rules)
        mcp.tool(name='disable_insight_rules')(self.disable_insight_rules)

    async def describe_insight_rules(
        self,
        ctx: Context,
        name_prefix: Annotated[
            Optional[str],
            Field(description='Filter rules whose names start with this prefix.'),
        ] = None,
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of rules to return (default: 50).'),
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
    ) -> DescribeInsightRulesResponse:
        """Lists all Contributor Insights rules in the account.

        Contributor Insights rules analyze log events in CloudWatch Logs log groups
        to identify top contributors (e.g., top IP addresses, top URLs, most throttled
        DynamoDB keys). Use this tool to discover existing rules before retrieving reports.

        Returns:
            DescribeInsightRulesResponse: List of insight rules in the account.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50
            if max_items < 1:
                raise ValueError('max_items must be at least 1')

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            paginator = cloudwatch_client.get_paginator('describe_insight_rules')
            pagination_config = {}
            if not name_prefix:
                # Without prefix filter, cap total fetched to avoid unnecessary API calls
                pagination_config['MaxItems'] = max_items + 1
            page_iterator = paginator.paginate(
                **({'PaginationConfig': pagination_config} if pagination_config else {})
            )

            rules: List[InsightRuleSummary] = []
            has_more = False

            for page in page_iterator:
                for rule in page.get('InsightRules', []):
                    name = rule.get('Name', '')
                    if name_prefix and not name.startswith(name_prefix):
                        continue
                    if len(rules) >= max_items:
                        has_more = True
                        break
                    rules.append(
                        InsightRuleSummary(
                            name=name,
                            state=rule.get('State', ''),
                            schema_version=rule.get('Schema', ''),
                            definition=rule.get('Definition', ''),
                            managed_rule=rule.get('ManagedRule', False),
                        )
                    )
                if has_more:
                    break

            message = None
            if not rules:
                message = 'No Contributor Insights rules found'
            elif has_more:
                message = f'Showing {len(rules)} rules (more available)'

            logger.info(f'Found {len(rules)} insight rules, has_more: {has_more}')

            return DescribeInsightRulesResponse(
                insight_rules=rules,
                has_more_results=has_more,
                message=message,
            )

        except Exception as e:
            logger.error(f'Error in describe_insight_rules: {str(e)}')
            await ctx.error(f'Error describing insight rules: {str(e)}')
            raise

    async def get_insight_rule_report(
        self,
        ctx: Context,
        rule_name: Annotated[
            str,
            Field(description='Name of the Contributor Insights rule to get the report for.'),
        ],
        start_time: Annotated[
            Optional[str],
            Field(
                description="Start time in ISO format (e.g., '2024-01-01T00:00:00Z'). Defaults to 1 hour ago."
            ),
        ] = None,
        end_time: Annotated[
            Optional[str],
            Field(
                description="End time in ISO format (e.g., '2024-01-01T01:00:00Z'). Defaults to now."
            ),
        ] = None,
        period: Annotated[
            Optional[int],
            Field(
                description='Aggregation period in seconds (e.g., 60, 300, 3600). Defaults to 300.'
            ),
        ] = 300,
        max_contributor_count: Annotated[
            Optional[int],
            Field(
                description='Maximum number of top contributors to include (1-100). Defaults to 10.'
            ),
        ] = 10,
        metrics: Annotated[
            Optional[List[str]],
            Field(
                description='Metrics to return. Valid: UniqueContributors, MaxContributorValue, SampleCount, Sum, Minimum, Maximum, Average. Defaults to [UniqueContributors, Sum].'
            ),
        ] = None,
        order_by: Annotated[
            Optional[str],
            Field(
                description='How to order contributors. Valid: Sum, Maximum, SampleCount. Defaults to Sum.'
            ),
        ] = None,
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
    ) -> GetInsightRuleReportResponse:
        """Gets the time-series data collected by a Contributor Insights rule.

        Returns the top contributors and time-series metric data for a rule. Use this
        to identify which keys (e.g., IP addresses, DynamoDB partition keys, API operations)
        are the highest contributors to log events matching the rule.

        Use describe_insight_rules first to find available rule names.

        Returns:
            GetInsightRuleReportResponse: Report with top contributors and metric data points.
        """
        try:
            if period is None or not isinstance(period, int):
                period = 300
            if max_contributor_count is None or not isinstance(max_contributor_count, int):
                max_contributor_count = 10
            max_contributor_count = max(1, min(100, max_contributor_count))
            if metrics is None:
                metrics = ['UniqueContributors', 'Sum']

            if end_time is None or not isinstance(end_time, str):
                end_time_dt = datetime.now(timezone.utc)
            else:
                end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            if start_time is None or not isinstance(start_time, str):
                start_time_dt = end_time_dt - timedelta(hours=1)
            else:
                start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            kwargs = {
                'RuleName': rule_name,
                'StartTime': start_time_dt,
                'EndTime': end_time_dt,
                'Period': period,
                'MaxContributorCount': max_contributor_count,
                'Metrics': metrics,
            }
            if order_by:
                kwargs['OrderBy'] = order_by

            logger.info(f'Getting insight rule report for {rule_name}')
            response = cloudwatch_client.get_insight_rule_report(**kwargs)

            # Parse contributors
            contributors = []
            for c in response.get('Contributors', []):
                contributors.append(
                    InsightRuleContributor(
                        keys=c.get('Keys', []),
                        approximate_aggregate_value=c.get('ApproximateAggregateValue', 0.0),
                        datapoints=[
                            {
                                'timestamp': dp.get('Timestamp', ''),
                                'value': dp.get('ApproximateValue', 0.0),
                            }
                            for dp in c.get('Datapoints', [])
                        ],
                    )
                )

            # Parse metric datapoints
            metric_datapoints = []
            for dp in response.get('MetricDatapoints', []):
                metric_datapoints.append(
                    InsightRuleMetricDatapoint(
                        timestamp=dp.get('Timestamp', datetime.now(timezone.utc)),
                        unique_contributors=dp.get('UniqueContributors'),
                        max_contributor_value=dp.get('MaxContributorValue'),
                        sample_count=dp.get('SampleCount'),
                        average=dp.get('Average'),
                        sum=dp.get('Sum'),
                        minimum=dp.get('Minimum'),
                        maximum=dp.get('Maximum'),
                    )
                )

            return GetInsightRuleReportResponse(
                key_labels=response.get('KeyLabels', []),
                aggregation_statistic=response.get('AggregationStatistic', ''),
                aggregate_value=response.get('AggregateValue'),
                approximate_unique_count=response.get('ApproximateUniqueCount', 0),
                contributors=contributors,
                metric_datapoints=metric_datapoints,
                message=None,
            )

        except Exception as e:
            logger.error(f'Error in get_insight_rule_report: {str(e)}')
            await ctx.error(f'Error getting insight rule report: {str(e)}')
            raise

    async def list_managed_insight_rules(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(
                description='ARN of the AWS resource to list managed rules for (e.g., DynamoDB table ARN).'
            ),
        ],
        max_items: Annotated[
            Optional[int],
            Field(description='Maximum number of rules to return (default: 50).'),
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
    ) -> ListManagedInsightRulesResponse:
        """Lists managed Contributor Insights rules for a specific AWS resource.

        Managed rules are automatically created by AWS services (e.g., DynamoDB creates
        rules to track throttled partition keys). Use this to discover what managed
        monitoring exists for a specific resource.

        Returns:
            ListManagedInsightRulesResponse: List of managed insight rules for the resource.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            paginator = cloudwatch_client.get_paginator('list_managed_insight_rules')
            page_iterator = paginator.paginate(
                ResourceARN=resource_arn,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            rules: List[ManagedInsightRuleSummary] = []
            has_more = False

            for page in page_iterator:
                for rule in page.get('ManagedRules', []):
                    if len(rules) >= max_items:
                        has_more = True
                        break
                    rules.append(
                        ManagedInsightRuleSummary(
                            template_name=rule.get('TemplateName', ''),
                            resource_arn=rule.get('ResourceARN', ''),
                            rule_state=rule.get('RuleState', {}).get('State', ''),
                        )
                    )
                if has_more:
                    break
            message = None
            if not rules:
                message = f'No managed insight rules found for {resource_arn}'
            elif has_more:
                message = f'Showing {len(rules)} managed rules (more available)'

            logger.info(f'Found {len(rules)} managed insight rules for {resource_arn}')

            return ListManagedInsightRulesResponse(
                managed_rules=rules,
                has_more_results=has_more,
                message=message,
            )

        except Exception as e:
            logger.error(f'Error in list_managed_insight_rules: {str(e)}')
            await ctx.error(f'Error listing managed insight rules: {str(e)}')
            raise

    async def put_insight_rule(
        self,
        ctx: Context,
        rule_name: Annotated[
            str,
            Field(description='Name for the Contributor Insights rule.'),
        ],
        rule_definition: Annotated[
            str,
            Field(
                description='JSON rule definition body. Must include Schema, LogGroupNames, and Contribution (Keys, ValueOf, Filters).'
            ),
        ],
        rule_state: Annotated[
            Optional[str],
            Field(
                description='Initial state of the rule: ENABLED or DISABLED. Defaults to ENABLED.'
            ),
        ] = 'ENABLED',
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
    ) -> PutInsightRuleResponse:
        """Creates or updates a Contributor Insights rule.

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to create or update this rule.

        Rules evaluate log events in a CloudWatch Logs log group, enabling you to find
        contributor data for the log events in that log group. For more information, see
        https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html

        Returns:
            PutInsightRuleResponse: Confirmation of rule creation/update.
        """
        try:
            if rule_state is None or not isinstance(rule_state, str):
                rule_state = 'ENABLED'
            if rule_state not in ('ENABLED', 'DISABLED'):
                raise ValueError(f"rule_state must be 'ENABLED' or 'DISABLED', got '{rule_state}'")

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            logger.info(f'Creating/updating insight rule: {rule_name}')
            cloudwatch_client.put_insight_rule(
                RuleName=rule_name,
                RuleDefinition=rule_definition,
                RuleState=rule_state,
            )

            return PutInsightRuleResponse(
                success=True,
                rule_name=rule_name,
                message=f'Rule "{rule_name}" created/updated successfully with state {rule_state}',
            )

        except Exception as e:
            logger.error(f'Error in put_insight_rule: {str(e)}')
            await ctx.error(f'Error creating/updating insight rule: {str(e)}')
            raise

    async def enable_insight_rules(
        self,
        ctx: Context,
        rule_names: Annotated[
            List[str],
            Field(description='List of rule names to enable.'),
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
    ) -> ModifyInsightRulesResponse:
        """Enables one or more Contributor Insights rules.

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to enable these rules. Enabled rules immediately begin
        analyzing log data and may incur costs.

        Returns:
            ModifyInsightRulesResponse: Result including any partial failures.
        """
        try:
            if not rule_names:
                raise ValueError('rule_names must not be empty')

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            logger.info(f'Enabling {len(rule_names)} insight rules')
            response = cloudwatch_client.enable_insight_rules(RuleNames=rule_names)

            failures = [
                PartialFailure(
                    failure_resource=f.get('FailureResource'),
                    exception_type=f.get('ExceptionType'),
                    failure_code=f.get('FailureCode'),
                    failure_description=f.get('FailureDescription'),
                )
                for f in response.get('Failures', [])
            ]

            message = f'Enabled {len(rule_names) - len(failures)}/{len(rule_names)} rules'
            if failures:
                message += f' ({len(failures)} failed)'

            return ModifyInsightRulesResponse(failures=failures, message=message)

        except Exception as e:
            logger.error(f'Error in enable_insight_rules: {str(e)}')
            await ctx.error(f'Error enabling insight rules: {str(e)}')
            raise

    async def disable_insight_rules(
        self,
        ctx: Context,
        rule_names: Annotated[
            List[str],
            Field(description='List of rule names to disable.'),
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
    ) -> ModifyInsightRulesResponse:
        """Disables one or more Contributor Insights rules.

        IMPORTANT: This is a mutating operation. Before calling this tool, confirm with
        the user that they want to disable these rules. Disabled rules do not analyze
        log groups and do not incur costs.

        Returns:
            ModifyInsightRulesResponse: Result including any partial failures.
        """
        try:
            if not rule_names:
                raise ValueError('rule_names must not be empty')

            cloudwatch_client = get_aws_client('cloudwatch', region, profile_name)

            logger.info(f'Disabling {len(rule_names)} insight rules')
            response = cloudwatch_client.disable_insight_rules(RuleNames=rule_names)

            failures = [
                PartialFailure(
                    failure_resource=f.get('FailureResource'),
                    exception_type=f.get('ExceptionType'),
                    failure_code=f.get('FailureCode'),
                    failure_description=f.get('FailureDescription'),
                )
                for f in response.get('Failures', [])
            ]

            message = f'Disabled {len(rule_names) - len(failures)}/{len(rule_names)} rules'
            if failures:
                message += f' ({len(failures)} failed)'

            return ModifyInsightRulesResponse(failures=failures, message=message)

        except Exception as e:
            logger.error(f'Error in disable_insight_rules: {str(e)}')
            await ctx.error(f'Error disabling insight rules: {str(e)}')
            raise
