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
    """Advanced recommendation tool for optimizing AWS Lambda Event Source Mapping (ESM) configurations.

    This class provides intelligent configuration recommendations based on optimization targets
    such as failure rate, latency, throughput, and cost. It analyzes configuration tradeoffs,
    validates settings against AWS limits, and ensures compliance with event source restrictions.
    """

    # Event source specific configuration restrictions
    # These restrictions are enforced by AWS and prevent invalid ESM configurations
    EVENT_SOURCE_RESTRICTIONS = {
        # Kinesis streams don't support advanced polling or scaling configurations
        'kinesis': {
            'not_allowed': ['ProvisionedPollerConfig', 'Queues', 'ScalingConfig'],
        },
        # DynamoDB streams have similar restrictions to Kinesis
        'dynamodb': {
            'not_allowed': ['ProvisionedPollerConfig', 'Queues', 'ScalingConfig'],
        },
        # Kafka has the most restrictions due to its different polling model
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
        """Initialize the ESM recommendation tool and AWS client connections.

        Args:
            mcp: FastMCP instance for tool registration
        """
        # Register configuration analysis and validation tools
        mcp.tool(name='esm_get_config_tradeoff')(self.esm_get_config_tradeoff_tool)
        mcp.tool(name='esm_validate_configs')(self.esm_validate_configs_tool)

        # Cache for AWS API limits to avoid repeated API calls
        self._cached_limits: Optional[Dict[str, Any]] = None

        # Initialize AWS Lambda client for ESM operations
        self.lambda_client = self._initialize_lambda_client()

    def _initialize_lambda_client(self):
        """Initialize AWS Lambda client with proper error handling.

        Returns:
            Configured boto3 Lambda client

        Raises:
            RuntimeError: If AWS client initialization fails
        """
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
        """Retrieve current ESM configurations from AWS Lambda service.

        Supports multiple query methods to find ESM configurations:
        - By UUID: Get specific ESM configuration
        - By event source ARN: Get all ESMs for a specific event source
        - By function name: Get all ESMs for a specific Lambda function
        - No parameters: Get all ESMs in the account/region

        Args:
            uuid: Specific ESM UUID to retrieve
            event_source_arn: ARN of event source to filter by
            function_name: Lambda function name to filter by

        Returns:
            List of ESM configuration dictionaries
        """
        try:
            if uuid:
                # Get specific ESM by UUID
                response = self.lambda_client.get_event_source_mapping(UUID=uuid)
                return [response]
            elif event_source_arn:
                # Get all ESMs for a specific event source
                response = self.lambda_client.list_event_source_mappings(
                    EventSourceArn=event_source_arn
                )
                return response.get('EventSourceMappings', [])
            elif function_name:
                # Get all ESMs for a specific Lambda function
                response = self.lambda_client.list_event_source_mappings(
                    FunctionName=function_name
                )
                return response.get('EventSourceMappings', [])
            else:
                # Get all ESMs in the account/region
                response = self.lambda_client.list_event_source_mappings()
                return response.get('EventSourceMappings', [])
        except Exception:
            logging.warning('Error getting ESM configurations')
            return []

    def _get_esm_limits_from_aws(self) -> Dict[str, Dict]:
        """Retrieve ESM configuration limits from AWS service model metadata.

        Extracts min/max limits for ESM parameters from the AWS Lambda service model.
        Results are cached to avoid repeated API introspection calls.

        Returns:
            Dict mapping parameter names to their min/max limits
        """
        # Return cached limits if available to avoid repeated API calls
        if self._cached_limits is not None:
            return self._cached_limits

        try:
            limits = {}
            # Access the AWS service model to get parameter constraints
            operation = self.lambda_client._service_model.operation_model(
                'CreateEventSourceMapping'
            )
            input_shape = operation.input_shape

            # Extract min/max constraints from parameter metadata
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

        # Cache the results for future use
        self._cached_limits = limits
        return limits

    async def esm_get_config_tradeoff_tool(
        self,
        ctx: Context,
        optimization_targets: List[
            Literal['failure_rate', 'latency', 'throughput', 'cost']
        ] = Field(description='Optimization target for event source mapping.'),
    ) -> Dict[str, Any]:
        """Analyze ESM configuration tradeoffs for specific optimization targets.

        Provides comprehensive analysis of how different ESM configuration parameters
        affect failure rate, latency, throughput, and cost. Includes current AWS limits,
        existing configurations, and detailed tradeoff explanations.

        Args:
            ctx: MCP context for logging
            optimization_targets: List of optimization goals (failure_rate, latency, throughput, cost)

        Returns:
            Dict containing limits, current configs, tradeoffs, and next actions
        """
        await ctx.info(
            f'Getting ESM configuration tradeoffs for the target: {optimization_targets}'
        )

        # Retrieve current AWS limits for validation
        config_limits = self._get_esm_limits_from_aws()

        # Comprehensive configuration tradeoff analysis for each optimization target
        # Each configuration parameter's impact is categorized by optimization goal
        config_tradeoffs = {
            # Failure rate optimization - focus on reliability and error recovery
            'failure_rate': {
                'Primary configurations': {
                    'MaximumRetryAttempts': {
                        'Higher': 'Lower failure rate - more retry attempts before giving up',
                        'Lower': 'Higher failure rate - fewer chances to recover from transient errors',
                    },
                    'BisectBatchOnFunctionError': {
                        'Enabled': 'Lower failure rate - splits failed batches to isolate bad records',
                        'Disabled': 'Higher failure rate - entire batch fails if any record causes error',
                    },
                },
                'Secondary configurations': {
                    'BatchSize': {
                        'Higher': 'Higher failure rate - more records lost when batch fails',
                        'Lower': 'Lower failure rate - fewer records affected per failure',
                    },
                    'FilterCriteria': {
                        'Present': 'Lower failure rate - filters out records that might cause errors',
                        'Absent': 'Higher failure rate - processes all records including problematic ones',
                    },
                },
            },
            # Latency optimization - focus on processing speed and responsiveness
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
                        '-1': 'Potential very high latency - old records are never discarded',
                        'Higher': 'Can increase latency - allows older records to accumulate',
                        'Lower': 'Can reduce latency - discards old records faster',
                    },
                },
            },
            # Throughput optimization - focus on processing volume and efficiency
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
                # Kafka-specific throughput configurations
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
                # Lambda function settings that indirectly affect ESM throughput
                'Lambda function configurations (indirect impact)': {
                    'ReservedConcurrency': {
                        'Higher': 'Higher throughput - prevents throttling bottlenecks',
                        'Lower': 'Lower throughput - throttling limits processing capacity',
                    },
                    'ProvisionedConcurrency': {
                        'Higher': 'Higher sustained throughput - eliminates cold start delays that can create processing bottlenecks',
                        'Lower': 'Lower initial throughput - cold starts create delays when scaling up',
                    },
                },
            },
            # Cost optimization - focus on minimizing AWS charges
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
                # Kafka-specific cost considerations
                'Kafka-specific': {
                    'MinimumPollers/MaximumPollers': 'Higher values = higher cost for event polling infrastructure',
                },
                'Secondary configurations': {
                    'MaximumRetryAttempts': {
                        'Higher': 'Higher cost due to retry executions',
                        'Lower': 'Lower cost with fewer retries',
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
                # Lambda function settings that affect overall cost
                'Lambda function configurations': {
                    'ProvisionedConcurrency': {
                        'Higher': 'Higher cost - paying for idle pre-warmed capacity',
                        'Lower/Disabled': 'Lower cost - only pay for actual execution time',
                    },
                },
            },
        }

        # Get current ESM configurations for reference
        current_configs = self._get_esm_configs()

        # Recommended next steps for configuration optimization
        next_actions = [
            'Validate the generated configurations using `esm_validate_configs_tool`.',
            'Confirm with the user before deployment using `esm_deployment_precheck`.',
        ]

        # Filter tradeoffs to only include requested optimization targets
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
        """Validate ESM configurations against AWS limits and event source restrictions.

        Performs comprehensive validation including:
        1. Event source specific restrictions (unsupported parameters)
        2. AWS service limits (min/max values)
        3. Configuration compatibility checks

        Args:
            ctx: MCP context for logging
            event_source: Type of event source (kinesis, dynamodb, kafka)
            configs: ESM configuration dictionary to validate

        Returns:
            Dict with validation results and detailed error information
        """
        await ctx.info(f'Validating ESM configurations: {configs}')

        # Validate that configuration is not empty
        if not configs:
            return {
                'validation_result': 'failed',
                'failed_causes': [{'error': 'Empty configuration'}],
            }

        failed = []

        # Phase 1: Check event source specific restrictions
        # Each event source has different supported parameters
        restrictions_passed = True

        # Validate event source is supported
        if event_source not in self.EVENT_SOURCE_RESTRICTIONS:
            return {
                'validation_result': 'failed',
                'failed_causes': [{'error': f'Unsupported event source: {event_source}'}],
            }

        # Check for unsupported parameters for this event source type
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

        # Phase 2: Check AWS service limits on numeric parameters
        # Validate that numeric values fall within AWS-defined min/max ranges
        limits_passed = True
        limits = self._get_esm_limits_from_aws()

        for prop, value in configs.items():
            # Only validate numeric properties that have defined limits
            if prop in limits and isinstance(value, (int, float)):
                limit = limits[prop]
                min_val = limit.get('min')
                max_val = limit.get('max')

                # Check if value exceeds AWS service limits
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

        # Determine overall validation result
        validation_result = 'passed' if restrictions_passed and limits_passed else 'failed'

        return {'validation_result': validation_result, 'failed_causes': failed}
