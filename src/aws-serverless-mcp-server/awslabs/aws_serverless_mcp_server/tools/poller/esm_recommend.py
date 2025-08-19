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

import logging
import os
from boto3 import client as boto3_client
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


class EsmRecommendTool:
    """Tool to offer recommandation on EventSourceMapping(ESM) configurations."""

    EVENT_SOURCE_RESTRICTIONS = {
        'kinesis': {
            'not_allowed': ['ProvisionedPollerConfig', 'Queues', 'ScalingConfig'],
        },
        'dynamodb': {
            'not_allowed': ['ProvisionedPollerConfig', 'Queues', 'ScalingConfig'],
        },
        'kafka': {
            'not_allowed': [
                'BisectBatchOnFunctionError',
                'MaximumRecordAgeInSeconds',
                'MaximumRetryAttempts',
                'ParallelizationFactor',
                'Queues',
                'ScalingConfig',
                'TumblingWindowInSeconds',
            ],
        },
    }

    def __init__(self, mcp: FastMCP):
        """Initialize the ESM config recommendation tool."""
        mcp.tool(name='esm_get_config_tradeoff')(self.esm_get_config_tradeoff_tool)
        mcp.tool(name='esm_validate_configs')(self.esm_validate_configs_tool)
        self._cached_limits: Optional[Dict[str, Any]] = None
        self.lambda_client = self._initialize_lambda_client()

    def _initialize_lambda_client(self):
        try:
            return boto3_client(
                'lambda', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
            )
        except Exception as e:
            logging.error(f'Failed to initialize AWS Lambda client: {e}')
            raise RuntimeError(
                'AWS client initialization failed. Please check your AWS credentials and configuration.'
            ) from e

    def _get_esm_configs(
        self,
        uuid: Optional[str] = None,
        event_source_arn: Optional[str] = None,
        function_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns the current ESM configurations."""
        try:
            if uuid:
                response = self.lambda_client.get_event_source_mapping(UUID=uuid)
                return [response]
            elif event_source_arn:
                response = self.lambda_client.list_event_source_mappings(
                    EventSourceArn=event_source_arn
                )
                return response.get('EventSourceMappings', [])
            elif function_name:
                response = self.lambda_client.list_event_source_mappings(
                    FunctionName=function_name
                )
                return response.get('EventSourceMappings', [])
            else:
                response = self.lambda_client.list_event_source_mappings()
                return response.get('EventSourceMappings', [])
        except Exception:
            logging.warning('Error getting ESM configurations')
            return []

    def _get_esm_limits_from_aws(self) -> Dict[str, Dict]:
        """Get ESM configuration limits from AWS APIs."""
        if self._cached_limits is not None:
            return self._cached_limits

        try:
            limits = {}
            operation = self.lambda_client._service_model.operation_model(
                'CreateEventSourceMapping'
            )
            input_shape = operation.input_shape

            for param_name, param_shape in input_shape.members.items():
                if hasattr(param_shape, 'metadata'):
                    metadata = param_shape.metadata
                    if 'min' in metadata or 'max' in metadata:
                        limits[param_name] = {
                            'min': metadata.get('min'),
                            'max': metadata.get('max'),
                        }
        except Exception as e:
            logging.warning(f'Error getting ESM limits from AWS: {e}')
            return {}
        self._cached_limits = limits
        return limits

    async def esm_get_config_tradeoff_tool(
        self,
        ctx: Context,
        optimization_targets: List[
            Literal['failure_rate', 'latency', 'throughput', 'cost']
        ] = Field(description='Optimization target for event source mapping.'),
    ) -> Dict[str, Any]:
        """Get ESM configuration metadata with limits, current configs, and pros/cons."""
        await ctx.info(
            f'Getting ESM configuration tradeoffs for the target: {optimization_targets}'
        )

        config_limits = self._get_esm_limits_from_aws()

        # Configuration pros/cons for optimization targets
        config_tradeoffs = {
            'failure_rate': {
                'Primary configurations': {
                    'MaximumRetryAttempts': {
                        'Higher': 'Lower failure rate - more retry attempts before giving up',
                        'Lower': ' Higher failure rate - fewer chances to recover from transient errors',
                    },
                    'BisectBatchOnFunctionError': {
                        'Enabled': 'Lower failure rate - splits failed batches to isolate bad records',
                        'Disabled': 'Higher failure rate - entire batch fails if any record causes error',
                    },
                },
                'Secondary configurations': {
                    'BatchSize': {
                        'Higher': 'Higher failure rate - more records lost when batch fail',
                        'Lower': 'Lower failure rate - fewer records affected per failure',
                    },
                    'FilterCriteria': {
                        'Present': 'Lower failure rate - filters out records that might cause errors',
                        'Absent': 'Higher failure rate - processes all records including problematic ones',
                    },
                },
            },
            'latency': {
                'Primary configurations': {
                    'BatchSize': {
                        'Higher': 'Higher latency - waits to collect more records before invoking Lambda',
                        'Lower': 'Lower latency - processes records more immediately with smaller batches',
                    },
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Higher latency - waits longer to fill batches before processing',
                        'Lower': 'Lower latency - processes available records more quickly',
                    },
                    'ParallelizationFactor': {
                        'Higher': 'Lower latency - parallel processing reduces overall processing time',
                        'Lower': 'Higher latency - sequential processing creates bottlenecks',
                    },
                },
                'Secondary configurations': {
                    'MaximumRetryAttempts': {
                        '-1': 'Potential very high latency - unlimited retry could bring very high latency',
                        'Higher': 'Higher latency - retry delays add to total processing time',
                        'Lower': 'Lower latency - fails faster without retry delays',
                    },
                    'MaximumRecordAgeInSeconds': {
                        '-1': 'Potential very high latency - old records are never discarded.',
                        'Higher': 'Can increase latency - allows older records to accumulate',
                        'Lower': 'Can reduce latency - discards old records faster',
                    },
                },
            },
            'throughput': {
                'Primary configurations': {
                    'BatchSize': {
                        'Higher': 'Higher throughput - processes more records per Lambda invocation',
                        'Lower': 'Lower throughput - processes fewer records per invocation, more overhead',
                    },
                    'ParallelizationFactor': {
                        'Higher': 'Higher throughput - more concurrent processing of different shards, but more Lambda invocations',
                        'Lower': 'Lower throughput - sequential processing limits overall capacity, but fewer Lambda invocations',
                    },
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Higher throughput - waits to fill larger batches before processing',
                        'Lower': 'Lower throughput - processes smaller batches more frequently',
                    },
                },
                'Kafka-specific': {
                    'MinimumPollers': {
                        'General idea': 'MSK Kafka only, one event poller offers up to 5 MB/s throughput',
                        'Higher': 'Higher initial throughput - more poller instances available initialized to pull data from Kafka',
                        'Lower': 'Lower initial throughput - fewer poller instances, slower startup but lower resource usage',
                    },
                    'MaximumPollers': {
                        'General idea': 'MSK Kafka only, one event poller offers up to 5 MB/s throughput',
                        'Higher': 'Higher peak throughput - can scale up to more pollers under load, but higher resource costs',
                        'Lower': 'Lower peak throughput - limited scaling capacity, but controlled resource usage',
                    },
                },
                'Secondary configurations': {
                    'MaximumRetryAttempts': {
                        'Higher': 'Lower throughput - retry overhead reduces processing capacity',
                        'Lower': 'Higher throughput - less time spent on retries',
                    },
                    'BisectBatchOnFunctionError': {
                        'Disabled': 'Higher throughput - processes full batches without splitting',
                        'Enabled': 'Lower throughput - batch splitting adds processing overhead',
                    },
                },
                'Lambda function configurations (indriect impact)': {
                    'ReservedConcurrency': {
                        'Higher': 'Higher throughput - prevents throttling bottlenecks',
                        'Lower': 'Lower throughput - throttling limits processing capacity',
                    },
                    'ProvisionConcurrency': {
                        'Higher': 'Higher sustained throughput - eliminates cold start delays that can create processing bottlenecks',
                        'Lower': 'Lower initial throughput - cold starts create delays when scaling up',
                    },
                },
            },
            'cost': {
                'Primary configurations': {
                    'BatchSize': {
                        'Higher': 'Lower cost - fewer Lambda invocations, reduced per-invocation charges',
                        'Lower': 'Higher cost - more frequent invocations, higher per-invocation overhead',
                    },
                    'ParallelizationFactor': {
                        'Higher': 'Higher cost - more concurrent Lambda executions running simultaneously',
                        'Lower': 'Lower cost - fewer concurrent executions, reduced compute charges',
                    },
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Lower cost - batches more records together, fewer total invocations',
                        'Lower': 'Higher cost - processes smaller batches more frequently',
                    },
                },
                'Kafka-specific': {
                    'MinimumPollers/MaximumPollers': 'Higher values = higher cost for event polling infrastructure',
                },
                'Secondary configurations': {
                    'MaximumRetryAttempts': {
                        'high': 'Higher cost due to retry executions',
                        'low': 'Lower cost with fewer retries',
                    },
                    'MaximumRecordAgeInSeconds': {
                        'Higher': 'Higher cost - processes more records including old ones',
                        'Lower': 'Lower cost - discards old records, processes less data',
                    },
                    'BisectBatchOnFunctionError': {
                        'Enabled': 'Higher cost - batch splitting creates additional invocations',
                        'Disabled': 'Lower cost - single invocation per batch regardless of errors',
                    },
                },
                'Lambda function configurations': {
                    'ProvisionedConcurrency': {
                        'Higher': 'Higher cost - paying for idle pre-warmed capacity',
                        'Lower/Disabled': 'Lower cost - only pay for actual execution time',
                    },
                },
            },
        }

        current_configs = self._get_esm_configs()
        next_actions = [
            'Validate the generated configurations using `esm_validate_configs_tool`.',
            'Confirm with the user before deployment using `esm_deployment_precheck`.',
        ]

        merged_tradeoffs: Dict[str, Any] = {}

        for target in optimization_targets:
            if target not in config_tradeoffs:
                merged_tradeoffs[target] = {}
            else:
                merged_tradeoffs[target] = config_tradeoffs[target]

        return {
            'limits': config_limits,
            'current_configs': current_configs,
            'tradeoffs': merged_tradeoffs,
            'next_actions': next_actions,
        }

    async def esm_validate_configs_tool(
        self,
        ctx: Context,
        event_source: Literal['kinesis', 'dynamodb', 'kafka'] = Field(
            description='Event source type to validate ESM configurations for.'
        ),
        configs: Dict[str, Any] = Field(
            description='ESM configuration to validate. Each entry must be a valid ESM configuration.'
        ),
    ) -> Dict[str, Any]:
        """Validate ESM configurations against their limits and restrictions."""
        await ctx.info(f'Validating ESM configurations: {configs}')

        if not configs:
            return {
                'validation_result': 'failed',
                'failed_causes': [{'error': 'Empty configuration'}],
            }

        failed = []

        # Check event source specific restrictions
        restrictions_passed = True

        if event_source not in self.EVENT_SOURCE_RESTRICTIONS:
            return {
                'validation_result': 'failed',
                'failed_causes': [{'error': f'Unsupported event source: {event_source}'}],
            }
        restrictions = self.EVENT_SOURCE_RESTRICTIONS[event_source]
        for not_allowed_prop in restrictions.get('not_allowed', []):
            if not_allowed_prop in configs:
                restrictions_passed = False
                failed.append(
                    {
                        'property': not_allowed_prop,
                        'value': configs[not_allowed_prop],
                        'error': f'Property {not_allowed_prop} is not allowed for {event_source} event sources',
                    }
                )

        # Check limits on event source properties
        limits_passed = True
        limits = self._get_esm_limits_from_aws()
        for prop, value in configs.items():
            if prop in limits and isinstance(value, (int, float)):
                limit = limits[prop]
                min_val = limit.get('min')
                max_val = limit.get('max')

                if (min_val is not None and value < min_val) or (
                    max_val is not None and value > max_val
                ):
                    limits_passed = False
                    failed.append(
                        {
                            'property': prop,
                            'value': value,
                            'error': f'Value {value} outside range [{min_val}, {max_val}]',
                        }
                    )

        validation_result = 'passed' if restrictions_passed and limits_passed else 'failed'

        return {'validation_result': validation_result, 'failed_causes': failed}
