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

"""Cross-account CloudWatch tools for MCP server."""

import asyncio
import json
import time
from awslabs.cross_account_cloudwatch_mcp_server.config import (
    ConfigNotProvidedError,
    load_cloudwatch_config,
)
from awslabs.cross_account_cloudwatch_mcp_server.aws_client import get_cross_account_client
from awslabs.cross_account_cloudwatch_mcp_server.config import CloudWatchConfig
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Dict, List


MAX_PARALLEL_QUERIES = 3
MAX_QUERY_RESULTS = 10_000
MIN_PARTITION_SECONDS = 300


class CrossAccountCloudWatchTools:
    """Tools for querying CloudWatch Logs across AWS accounts via STS AssumeRole."""

    async def list_cw_targets(self, ctx: Context) -> Dict:
        """Return configured cross-account CloudWatch targets from the required YAML file."""
        try:
            config, config_path = load_cloudwatch_config()
            return {
                'configPath': str(config_path),
                'found': True,
                'accounts': config.model_dump()['accounts'],
            }
        except ConfigNotProvidedError as e:
            message = str(e)
            logger.error(message)
            await ctx.error(message)
            return {
                'configPath': '',
                'found': False,
                'accounts': [],
                'message': message,
            }
        except Exception as e:
            logger.error(f'Error loading CloudWatch config: {e}')
            await ctx.error(f'Error loading CloudWatch config: {e}')
            return {
                'configPath': '',
                'found': False,
                'accounts': [],
                'message': str(e),
            }

    def _process_query_results(self, response: Dict, query_id: str) -> Dict:
        """Normalize CloudWatch Logs Insights results."""
        return {
            'queryId': query_id,
            'status': response['status'],
            'statistics': response.get('statistics', {}),
            'results': [
                {field['field']: field['value'] for field in row if field['field'] != '@ptr'}
                for row in response.get('results', [])
            ],
        }

    def _merge_statistics(self, query_results: List[Dict]) -> Dict:
        """Aggregate numeric CloudWatch query statistics across partitions."""
        merged: Dict[str, float] = {}
        for result in query_results:
            for key, value in result.get('statistics', {}).items():
                if isinstance(value, (int, float)):
                    merged[key] = merged.get(key, 0) + value
        return merged

    def _run_partition_query(
        self,
        logs_client,
        log_group: str,
        query_string: str,
        start_time: int,
        end_time: int,
        max_timeout: int,
    ) -> Dict:
        """Run a single partition query synchronously for use with asyncio threads."""
        response = logs_client.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query_string,
        )
        query_id = response['queryId']
        logger.info(f'Started partition query {query_id} for {log_group}')

        poll_start = time.monotonic()
        while time.monotonic() - poll_start < max_timeout:
            result = logs_client.get_query_results(queryId=query_id)
            status = result['status']

            if status in ('Complete', 'Failed', 'Cancelled'):
                processed_result = self._process_query_results(result, query_id)
                processed_result['window'] = {'startTime': start_time, 'endTime': end_time}
                return processed_result

            time.sleep(1)

        msg = (
            f'Query {query_id} did not complete within {max_timeout}s for window '
            f'{start_time}-{end_time}.'
        )
        logger.warning(msg)
        return {
            'queryId': query_id,
            'status': 'Polling Timeout',
            'message': msg,
            'statistics': {},
            'results': [],
            'window': {'startTime': start_time, 'endTime': end_time},
        }

    async def _run_query_window(
        self,
        semaphore: asyncio.Semaphore,
        logs_client,
        log_group: str,
        query_string: str,
        start_time: int,
        end_time: int,
        max_timeout: int,
    ) -> Dict:
        """Run a query and split the time window only when the result ceiling is reached."""
        async with semaphore:
            result = await asyncio.to_thread(
                self._run_partition_query,
                logs_client,
                log_group,
                query_string,
                start_time,
                end_time,
                max_timeout,
            )

        if result['status'] != 'Complete':
            return result

        if len(result['results']) < MAX_QUERY_RESULTS:
            return result

        window_seconds = end_time - start_time

        midpoint = start_time + (window_seconds // 2)
        if midpoint <= start_time or midpoint >= end_time:
            result['message'] = (
                f'Query {result["queryId"]} hit the CloudWatch {MAX_QUERY_RESULTS}-row limit '
                'and could not be partitioned further.'
            )
            return result

        logger.info(
            f'Partitioning query window {start_time}-{end_time} after reaching '
            f'{MAX_QUERY_RESULTS} rows'
        )
        left_result, right_result = await asyncio.gather(
            self._run_query_window(
                semaphore,
                logs_client,
                log_group,
                query_string,
                start_time,
                midpoint,
                max_timeout,
            ),
            self._run_query_window(
                semaphore,
                logs_client,
                log_group,
                query_string,
                midpoint,
                end_time,
                max_timeout,
            ),
        )

        child_results = [left_result, right_result]
        complete_results = [child for child in child_results if child['status'] == 'Complete']
        partial_failures = [child for child in child_results if child['status'] != 'Complete']

        return {
            'queryId': '',
            'queryIds': [
                query_id
                for child in child_results
                for query_id in child.get('queryIds', [child.get('queryId', '')])
                if query_id
            ],
            'status': 'Complete' if not partial_failures else 'Partial',
            'statistics': self._merge_statistics(complete_results),
            'results': [
                row for child in complete_results for row in child.get('results', [])
            ],
            'partitions': [
                partition
                for child in child_results
                for partition in child.get('partitions', [child['window']])
            ],
            **(
                {
                    'message': (
                        f'{len(partial_failures)} partition queries did not complete '
                        'successfully.'
                    )
                }
                if partial_failures
                else {}
            ),
        }

    def _validate_query_target(
        self,
        config: CloudWatchConfig,
        account_id: str,
        region: str,
        role_name: str,
        log_group: str,
    ) -> str | None:
        """Validate that the requested query target exists in the configured allowlist."""
        for account in config.accounts:
            if (
                account.accountId == account_id
                and account.region == region
                and account.roleName == role_name
            ):
                for configured_group in account.logGroups:
                    if configured_group.name == log_group:
                        return configured_group.description
                return None
        return None

    def _normalize_query_time(self, timestamp: datetime) -> datetime:
        """Normalize query input timestamps to UTC.

        Naive datetimes are treated as UTC to keep the tool behavior explicit.
        """
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    def _build_assume_role_access_denied_message(self, account_id: str, role_name: str) -> str:
        """Build customer-facing guidance for AssumeRole access denials."""
        role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'
        trust_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': '<caller-principal-arn>'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }
        caller_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'sts:AssumeRole',
                    'Resource': role_arn,
                }
            ],
        }
        return (
            f'AccessDenied when assuming role {role_arn}. Update IAM on both sides, then retry.\n\n'
            '1. Target account trust relationship must allow the caller principal to assume the role:\n'
            f'{json.dumps(trust_policy, indent=2)}\n\n'
            '2. Caller identity policy must allow sts:AssumeRole on the target role:\n'
            f'{json.dumps(caller_policy, indent=2)}\n\n'
            'Replace <caller-principal-arn> with the IAM user or role ARN that runs this MCP server.'
        )

    async def query_logs(
        self,
        ctx: Context,
        account_id: Annotated[
            str,
            Field(description='12-digit AWS account ID to query.', pattern=r'^\d{12}$'),
        ],
        log_group: Annotated[
            str,
            Field(description='CloudWatch log group name to query.'),
        ],
        query_string: Annotated[
            str,
            Field(
                description='CloudWatch Logs Insights query string. See https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html'
            ),
        ],
        start_time: Annotated[
            datetime,
            Field(
                description='Start time for the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC.'
            ),
        ],
        end_time: Annotated[
            datetime,
            Field(
                description='End time for the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC.'
            ),
        ],
        role_name: Annotated[
            str,
            Field(description='IAM role name to assume in the target account.'),
        ] = 'DevAccessReadOnly',
        region: Annotated[
            str,
            Field(description='AWS region. Defaults to us-west-2.'),
        ] = 'us-west-2',
        max_timeout: Annotated[
            int,
            Field(description='Max seconds to wait for query completion. Defaults to 30.', gt=0),
        ] = 30,
    ) -> Dict:
        """Query CloudWatch Logs for a target present in the configured allowlist.

        Validates the requested account, region, role, and log group against cw_config,
        then assumes the configured role in the target account, starts a CloudWatch Logs
        Insights query, and polls for results.

        CRITICAL: Always include a limit in your query_string (e.g. '| limit 50')
        to avoid overwhelming the agent context window.

        Returns:
            Dictionary with query status and results.
        """
        try:
            config, _config_path = load_cloudwatch_config()

            log_group_description = self._validate_query_target(
                config, account_id, region, role_name, log_group
            )
            if log_group_description is None:
                message = (
                    'Requested CloudWatch target is not present in cw_config. '
                    'Use list_cw_targets to inspect the configured accounts and log groups.'
                )
                await ctx.error(message)
                return {'queryId': '', 'status': 'Error', 'message': message, 'results': []}

            start_time_utc = self._normalize_query_time(start_time)
            end_time_utc = self._normalize_query_time(end_time)
            if end_time_utc <= start_time_utc:
                message = 'end_time must be later than start_time.'
                await ctx.error(message)
                return {'queryId': '', 'status': 'Error', 'message': message, 'results': []}

            logs = get_cross_account_client('logs', account_id, role_name, region)

            start_timestamp = int(start_time_utc.timestamp())
            end_timestamp = int(end_time_utc.timestamp())
            semaphore = asyncio.Semaphore(MAX_PARALLEL_QUERIES)
            result = await self._run_query_window(
                semaphore,
                logs,
                log_group,
                query_string,
                start_timestamp,
                end_timestamp,
                max_timeout,
            )

            if 'queryIds' not in result:
                result['queryIds'] = [result['queryId']] if result.get('queryId') else []
            if 'partitions' not in result:
                result['partitions'] = [result['window']]

            if result.get('message') and result['status'] != 'Complete':
                await ctx.warning(result['message'])

            result['target'] = {
                'accountId': account_id,
                'region': region,
                'roleName': role_name,
                'logGroup': log_group,
                'description': log_group_description,
            }
            result['requestedWindow'] = {
                'startTimeUtc': start_time_utc.isoformat(),
                'endTimeUtc': end_time_utc.isoformat(),
            }
            return result

        except ConfigNotProvidedError as e:
            message = str(e)
            logger.error(message)
            await ctx.error(message)
            return {'queryId': '', 'status': 'Error', 'message': message, 'results': []}
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in {'AccessDenied', 'AccessDeniedException'} and (
                getattr(e, 'operation_name', '') == 'AssumeRole' or 'AssumeRole' in str(e)
            ):
                message = self._build_assume_role_access_denied_message(account_id, role_name)
                logger.error(message)
                await ctx.error(message)
                return {'queryId': '', 'status': 'Error', 'message': message, 'results': []}
            logger.error(f'Error querying logs in account {account_id}: {e}')
            await ctx.error(f'Error querying cross-account logs: {e}')
            return {'queryId': '', 'status': 'Error', 'message': str(e), 'results': []}
        except Exception as e:
            logger.error(f'Error querying logs in account {account_id}: {e}')
            await ctx.error(f'Error querying cross-account logs: {e}')
            return {'queryId': '', 'status': 'Error', 'message': str(e), 'results': []}
