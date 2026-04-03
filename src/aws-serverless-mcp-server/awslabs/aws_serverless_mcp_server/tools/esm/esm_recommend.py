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

import json
import logging
import os
from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from awslabs.aws_serverless_mcp_server.utils.data_scrubber import DataScrubber
from boto3 import client as boto3_client
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


class EsmRecommendTool(BaseTool):
    """Advanced recommendation tool for optimizing AWS Lambda Event Source Mapping (ESM) configurations.

    This class provides intelligent configuration recommendations based on optimization targets
    such as failure rate, latency, throughput, and cost. It analyzes configuration tradeoffs,
    validates settings against AWS limits, and ensures compliance with event source restrictions.
    """

    # Latest supported Lambda runtime versions - update these when new versions are released
    LATEST_PYTHON_RUNTIME = 'python3.13'
    LATEST_NODEJS_RUNTIME = 'nodejs22.x'

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
        # SQS supports most ESM features but has specific limitations
        'sqs': {
            'not_allowed': [
                'ParallelizationFactor',  # SQS uses ScalingConfig instead
                'TumblingWindowInSeconds',  # Not applicable to SQS
                'ProvisionedPollerConfig',  # SQS uses different polling model
            ],
        },
    }

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ESM recommendation tool and AWS client connections.

        Args:
            mcp: FastMCP instance for tool registration
            allow_write: Whether write operations are allowed
        """
        super().__init__(allow_write=allow_write)
        self.allow_write = allow_write
        # Register consolidated ESM optimization tool - MAIN USER-FACING TOOL
        mcp.tool(
            name='esm_optimize',
            description='Optimize streaming data processing performance and costs. Analyzes Lambda function configurations for Kafka, Kinesis, DynamoDB, and SQS event sources. Provides recommendations for batch sizes, concurrency, throughput, and cost optimization. Validates configurations and generates deployment templates.',
        )(self.esm_optimize_tool)

        # Cache for AWS API limits to avoid repeated API calls
        self._cached_limits: Optional[Dict[str, Any]] = None

        # Initialize AWS Lambda client for ESM operations
        self.lambda_client = self._initialize_lambda_client()

    async def esm_optimize_tool(
        self,
        ctx: Context,
        action: Literal['analyze', 'validate', 'generate_template'] = Field(
            default='analyze',
            description='Optimization action: "analyze" for tradeoff analysis, "validate" for config validation, "generate_template" for SAM template generation',
        ),
        optimization_targets: Optional[
            List[Literal['failure_rate', 'latency', 'throughput', 'cost']]
        ] = Field(
            default=None,
            description='Optimization goals for analysis (required for analyze action)',
        ),
        event_source: Optional[Literal['kinesis', 'dynamodb', 'kafka', 'sqs']] = Field(
            default=None,
            description='Event source type for validation (required for validate action)',
        ),
        configs: Optional[Dict[str, Any]] = Field(
            default=None,
            description='ESM configuration to validate (required for validate action)',
        ),
        esm_uuid: Optional[str] = Field(
            default=None,
            description='ESM UUID for template generation (required for generate_template action)',
        ),
        optimized_configs: Optional[Dict[str, Any]] = Field(
            default=None,
            description='Optimized configuration for template generation (required for generate_template action)',
        ),
        region: str = Field(default='us-east-1', description='AWS region'),
        project_name: str = Field(
            default='esm-optimization', description='Project name for template generation'
        ),
    ) -> Dict[str, Any]:
        """Comprehensive ESM optimization tool combining analysis, validation, and template generation.

        This consolidated tool provides three main optimization functions:
        1. Analyze configuration tradeoffs for optimization targets
        2. Validate ESM configurations against AWS limits and best practices
        3. Generate SAM templates for ESM updates

        Args:
            ctx: MCP context for logging
            action: Type of optimization action to perform
            optimization_targets: List of optimization goals for analysis
            event_source: Event source type for validation
            configs: Configuration to validate
            esm_uuid: ESM UUID for template generation
            optimized_configs: Optimized configuration for template
            region: AWS region
            project_name: Project name for generated templates

        Returns:
            Dict containing optimization results, validation status, or SAM template
        """
        # Check tool access permissions for write operations (template generation)
        if action == 'generate_template':
            self.checkToolAccess()

        await ctx.info(f'Running ESM optimization action: {action}')

        if action == 'analyze':
            # Handle FieldInfo objects and None values
            actual_targets = (
                optimization_targets if isinstance(optimization_targets, list) else None
            )
            if not actual_targets:
                return {'error': 'optimization_targets required for analyze action'}
            result = await self.esm_get_config_tradeoff_tool(ctx, actual_targets)

            # Add specific recommendations for throughput optimization
            if 'throughput' in actual_targets:
                result['kafka_throughput_recommendations'] = (
                    self._get_kafka_throughput_recommendations()
                )

            return result

        elif action == 'validate':
            if not event_source or not configs:
                return {'error': 'event_source and configs required for validate action'}
            return await self.esm_validate_configs_tool(ctx, event_source, configs)

        elif action == 'generate_template':
            # Handle FieldInfo objects
            actual_esm_uuid = esm_uuid if isinstance(esm_uuid, str) else None
            actual_optimized_configs = (
                optimized_configs if isinstance(optimized_configs, dict) else None
            )

            if not actual_esm_uuid or not actual_optimized_configs:
                return {
                    'error': 'esm_uuid and optimized_configs required for generate_template action'
                }
            result = await self.esm_generate_update_template_tool(
                ctx, actual_esm_uuid, actual_optimized_configs, region, project_name
            )

            # Add sam_deploy integration guidance with user confirmation requirement
            if 'sam_template' in result:
                result['deployment_guidance'] = {
                    'CRITICAL_WARNING': 'MUST ask user for explicit confirmation before deployment',
                    'confirmation_required': f'Ask user: "Do you want to deploy these ESM optimization changes for {esm_uuid} to AWS?" before proceeding',
                    'next_step': 'Use sam_deploy tool ONLY after user confirms deployment',
                    'sam_deploy_params': {
                        'application_name': project_name,
                        'project_directory': f'./{project_name}-esm-update',
                        'template_file': 'template.yaml',
                        'capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                        'region': region,
                    },
                    'setup_instructions': [
                        f'1. Create project directory: mkdir {project_name}-esm-update',
                        f'2. Save SAM template as: {project_name}-esm-update/template.yaml',
                        '3. WAIT for user confirmation before deployment',
                        '4. Use sam_deploy tool ONLY after user approves',
                    ],
                }
                result['safety_note'] = (
                    'This tool generates templates but does NOT automatically deploy them. User confirmation is required for all deployments.'
                )

            # Scrub sensitive data from result before returning
            return self.scrub_response_data(result)

        else:
            return {
                'error': f'Unknown action: {action}. Use "analyze", "validate", or "generate_template"'
            }

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
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Higher throughput - waits to fill larger batches before processing',
                        'Lower': 'Lower throughput - processes smaller batches more frequently',
                    },
                },
                'Kinesis/DynamoDB-specific': {
                    'ParallelizationFactor': {
                        'Higher': 'Higher throughput - more concurrent processing of different shards, but more Lambda invocations',
                        'Lower': 'Lower throughput - sequential processing limits overall capacity, but fewer Lambda invocations',
                        'Note': 'Only applicable to Kinesis and DynamoDB streams, NOT Kafka or SQS',
                    },
                },
                # Kafka-specific throughput configurations
                'Kafka-specific': {
                    'ProvisionedPollerConfig.MinimumPollers': {
                        'General idea': 'MSK Kafka only, one event poller offers up to 5 MB/s throughput',
                        'Higher': 'Higher initial throughput - more poller instances available initialized to pull data from Kafka',
                        'Lower': 'Lower initial throughput - fewer poller instances, slower startup but lower resource usage',
                        'Recommended for 10-100 MB/s': 'Set to 2-4 pollers for initial capacity',
                    },
                    'ProvisionedPollerConfig.MaximumPollers': {
                        'General idea': 'MSK Kafka only, one event poller offers up to 5 MB/s throughput',
                        'Higher': 'Higher peak throughput - can scale up to more pollers under load, but higher resource costs',
                        'Lower': 'Lower peak throughput - limited scaling capacity, but controlled resource usage',
                        'Recommended for 10-100 MB/s': 'Set to 4-20 pollers for peak capacity',
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
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Lower cost - batches more records together, fewer total invocations',
                        'Lower': 'Higher cost - processes smaller batches more frequently',
                    },
                },
                'Kinesis/DynamoDB-specific': {
                    'ParallelizationFactor': {
                        'Higher': 'Higher cost - more concurrent Lambda executions running simultaneously',
                        'Lower': 'Lower cost - fewer concurrent executions, reduced compute charges',
                        'Note': 'Only applicable to Kinesis and DynamoDB streams, NOT Kafka or SQS',
                    },
                },
                # Kafka-specific cost considerations
                'Kafka-specific': {
                    'ProvisionedPollerConfig.MinimumPollers': 'Higher values = higher baseline cost for event polling infrastructure',
                    'ProvisionedPollerConfig.MaximumPollers': 'Higher values = higher potential peak cost, but allows better throughput scaling',
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
            # SQS-specific cost and performance considerations
            'sqs': {
                'Primary configurations': {
                    'BatchSize': {
                        'Higher': 'Lower cost - fewer Lambda invocations, reduced per-invocation charges',
                        'Lower': 'Higher cost - more frequent invocations, higher per-invocation overhead',
                    },
                    'MaximumConcurrency (ScalingConfig)': {
                        'Higher': 'Higher cost - more concurrent Lambda executions, but better throughput',
                        'Lower': 'Lower cost - fewer concurrent executions, but potential message delays',
                    },
                    'MaximumBatchingWindowInSeconds': {
                        'Higher': 'Lower cost - waits to fill larger batches, fewer total invocations',
                        'Lower': 'Higher cost - processes smaller batches more frequently',
                    },
                },
                'Secondary configurations': {
                    'FunctionResponseTypes (ReportBatchItemFailures)': {
                        'Enabled': 'Lower cost - prevents reprocessing of successful messages in failed batches',
                        'Disabled': 'Higher cost - entire batch reprocessed on any failure',
                    },
                    'ReservedConcurrency': {
                        'Set': 'Predictable cost - guarantees capacity but may limit scaling',
                        'Unset': 'Variable cost - uses account concurrency pool, potential throttling',
                    },
                },
                'Queue configurations (indirect impact)': {
                    'VisibilityTimeout': {
                        'Optimized (6x function timeout)': 'Lower cost - prevents duplicate processing',
                        'Too low': 'Higher cost - messages reprocessed due to timeout',
                    },
                    'Dead Letter Queue': {
                        'Configured': 'Lower cost - prevents infinite retry loops',
                        'Not configured': 'Higher cost - failed messages consume processing resources',
                    },
                },
            },
        }

        # Get current ESM configurations for reference
        current_configs = self._get_esm_configs()

        # Recommended next steps for configuration optimization
        next_actions = [
            'Generate SAM template with optimized ESM configuration',
            'Create deployment script to apply the changes',
            'Validate the generated configurations using `esm_validate_configs_tool`',
            'Confirm with the user before deployment using `esm_deployment_precheck`',
            'Provide cleanup script to revert changes if needed',
        ]

        # Filter tradeoffs to only include requested optimization targets
        # Handle FieldInfo objects by extracting actual values
        actual_targets = optimization_targets if isinstance(optimization_targets, list) else []

        merged_tradeoffs: Dict[str, Any] = {}
        for target in actual_targets:
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
        event_source: Literal['kinesis', 'dynamodb', 'kafka', 'sqs'] = Field(
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
        # Scrub sensitive data from configs before logging
        scrubbed_configs = DataScrubber.scrub_esm_config(configs)
        await ctx.info(f'Validating ESM configurations: {scrubbed_configs}')

        # Handle FieldInfo objects (when parameter not provided)
        if not isinstance(configs, dict):
            return {
                'validation_result': 'failed',
                'failed_causes': [{'error': 'Empty configuration'}],
            }

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

        result = {'validation_result': validation_result, 'failed_causes': failed}
        # Scrub sensitive data from result before returning
        return self.scrub_response_data(result)

    async def esm_generate_update_template_tool(
        self,
        ctx: Context,
        esm_uuid: str = Field(description='ESM UUID to update'),
        optimized_configs: Dict[str, Any] = Field(
            description='Optimized ESM configuration parameters'
        ),
        region: str = Field(description='AWS region', default='us-east-1'),
        project_name: str = Field(
            description='Project name for the template', default='esm-optimization'
        ),
    ) -> Dict[str, Any]:
        """Generate SAM template and deployment scripts for ESM configuration updates.

        Creates a complete infrastructure-as-code solution for updating ESM configurations
        including SAM template, deployment script, and validation.

        Args:
            ctx: MCP context for logging
            esm_uuid: UUID of the ESM to update
            optimized_configs: Dictionary of optimized configuration parameters
            region: AWS region where the ESM is located
            project_name: Name for the generated project

        Returns:
            Dict containing SAM template, deployment script, and instructions
        """
        # Scrub sensitive data from configs before logging
        scrubbed_uuid = DataScrubber.scrub_text(esm_uuid)
        await ctx.info(f'Generating SAM template for ESM {scrubbed_uuid} optimization')

        # Generate SAM template for ESM update
        sam_template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Transform': 'AWS::Serverless-2016-10-31',
            'Description': f'ESM Configuration Update for {esm_uuid}',
            'Parameters': {
                'ESMUuid': {
                    'Type': 'String',
                    'Default': esm_uuid,
                    'Description': 'UUID of the Event Source Mapping to update',
                }
            },
            'Resources': {
                'ESMConfigUpdate': {
                    'Type': 'AWS::CloudFormation::CustomResource',
                    'Properties': {
                        'ServiceToken': {'Fn::GetAtt': ['ESMUpdateFunction', 'Arn']},
                        'ESMUuid': {'Ref': 'ESMUuid'},
                        'Configuration': optimized_configs,
                    },
                },
                'ESMUpdateFunction': {
                    'Type': 'AWS::Serverless::Function',
                    'Properties': {
                        'FunctionName': f'{project_name}-esm-updater',
                        'Runtime': self.LATEST_PYTHON_RUNTIME,
                        'Handler': 'index.lambda_handler',
                        'Timeout': 60,
                        'Policies': [
                            {
                                'Version': '2012-10-17',
                                'Statement': [
                                    {
                                        'Effect': 'Allow',
                                        'Action': [
                                            'lambda:UpdateEventSourceMapping',
                                            'lambda:GetEventSourceMapping',
                                        ],
                                        'Resource': '*',
                                    }
                                ],
                            }
                        ],
                        'InlineCode': """
import boto3
import json
import cfnresponse

def lambda_handler(event, context):
    try:
        lambda_client = boto3.client('lambda')

        if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
            esm_uuid = event['ResourceProperties']['ESMUuid']
            config = event['ResourceProperties']['Configuration']

            # Update the ESM configuration
            response = lambda_client.update_event_source_mapping(
                UUID=esm_uuid,
                **config
            )

            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'ESMArn': response.get('EventSourceArn', ''),
                'State': response.get('State', ''),
                'LastModified': str(response.get('LastModified', ''))
            })
        else:
            # Delete - no action needed for ESM updates
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
""",
                    },
                },
            },
            'Outputs': {
                'ESMUuid': {'Description': 'Updated ESM UUID', 'Value': {'Ref': 'ESMUuid'}},
                'OptimizedConfiguration': {
                    'Description': 'Applied configuration',
                    'Value': json.dumps(optimized_configs),
                },
            },
        }

        # Generate deployment script using f-string to avoid Bandit false positive
        deployment_script = f"""#!/bin/bash

# ESM Configuration Update Deployment Script
# Generated for ESM UUID: {esm_uuid}

set -e

PROJECT_NAME="{project_name}"
REGION="{region}"
ESM_UUID="{esm_uuid}"

echo "🚀 Deploying ESM Configuration Update..."
echo "Project: $PROJECT_NAME"
echo "Region: $REGION"
echo "ESM UUID: $ESM_UUID"
echo

# Build the SAM application
echo "Building SAM application..."
sam build

# Deploy the application
echo "Deploying ESM configuration update..."
sam deploy \\
    --stack-name "$PROJECT_NAME-esm-update" \\
    --region "$REGION" \\
    --capabilities CAPABILITY_IAM \\
    --parameter-overrides ESMUuid="$ESM_UUID" \\
    --no-confirm-changeset \\
    --no-fail-on-empty-changeset

echo
echo "ESM configuration update completed!"
echo
echo "Verify the update:"
echo "aws lambda get-event-source-mapping --uuid $ESM_UUID --region $REGION"
"""

        # Generate cleanup script using f-string to avoid Bandit false positive
        cleanup_script = f'''#!/bin/bash

# ESM Configuration Cleanup Script
# This script removes the update stack but does NOT revert ESM changes

set -e

PROJECT_NAME="{project_name}"
REGION="{region}"
STACK_NAME="$PROJECT_NAME-esm-update"

echo "Cleaning up ESM update stack..."
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo

# Delete the CloudFormation stack
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"

echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"

echo "Cleanup completed!"
echo
echo "Note: ESM configuration changes are NOT reverted."
echo "To revert ESM settings, use the AWS CLI:"
echo "aws lambda update-event-source-mapping --uuid {esm_uuid} --region {region} [original-settings]"'''

        # Generate validation script with safe string formatting
        validation_script_parts = [
            '#!/bin/bash',
            '',
            '# ESM Configuration Validation Script',
            '',
            'ESM_UUID="' + str(esm_uuid) + '"',
            'REGION="' + str(region) + '"',
            '',
            'echo "🔍 Validating ESM Configuration..."',
            'echo "ESM UUID: $ESM_UUID"',
            'echo "Region: $REGION"',
            'echo',
            '',
            '# Get current ESM configuration',
            'echo "Current ESM Configuration:"',
            'aws lambda get-event-source-mapping --uuid "$ESM_UUID" --region "$REGION" --output table',
            '',
            'echo',
            'echo "Expected Configuration:"',
            'echo "Batch Size: ' + str(optimized_configs.get('BatchSize', 'Not specified')) + '"',
            'echo "Maximum Batching Window: '
            + str(optimized_configs.get('MaximumBatchingWindowInSeconds', 'Not specified'))
            + ' seconds"',
            'echo "Parallelization Factor: '
            + str(optimized_configs.get('ParallelizationFactor', 'Not specified'))
            + '"',
        ]

        # Add ScalingConfig if present
        if 'ScalingConfig' in optimized_configs:
            max_concurrency = optimized_configs['ScalingConfig'].get(
                'MaximumConcurrency', 'Not specified'
            )
            validation_script_parts.append(
                'echo "Maximum Concurrency: ' + str(max_concurrency) + '"'
            )

        # Add ProvisionedPollerConfig if present
        if 'ProvisionedPollerConfig' in optimized_configs:
            min_pollers = optimized_configs['ProvisionedPollerConfig'].get(
                'MinimumPollers', 'Not specified'
            )
            max_pollers = optimized_configs['ProvisionedPollerConfig'].get(
                'MaximumPollers', 'Not specified'
            )
            validation_script_parts.extend(
                [
                    'echo "Minimum Pollers: ' + str(min_pollers) + '"',
                    'echo "Maximum Pollers: ' + str(max_pollers) + '"',
                ]
            )

        validation_script_parts.extend(['', 'echo', 'echo "Validation completed!"'])

        validation_script = '\n'.join(validation_script_parts)

        result = {
            'sam_template': sam_template,
            'deployment_script': deployment_script,
            'cleanup_script': cleanup_script,
            'validation_script': validation_script,
            'instructions': {
                'setup': [
                    'Create project directory: mkdir {}-esm-update'.format(project_name),
                    'Save SAM template as: {}-esm-update/template.yaml'.format(project_name),
                    'Save deployment script as: {}-esm-update/deploy.sh'.format(project_name),
                    'Save cleanup script as: {}-esm-update/cleanup.sh'.format(project_name),
                    'Save validation script as: {}-esm-update/validate.sh'.format(project_name),
                    'Make scripts executable: chmod +x *.sh',
                ],
                'deployment': [
                    'cd {}-esm-update'.format(project_name),
                    './deploy.sh',
                    './validate.sh',
                ],
                'cleanup': ['./cleanup.sh'],
            },
            'optimized_configuration': optimized_configs,
            'esm_uuid': esm_uuid,
        }

        # Scrub sensitive data from result before returning
        return self.scrub_response_data(result)

    def _get_kafka_throughput_recommendations(self) -> Dict[str, Any]:
        """Generate specific Kafka throughput optimization recommendations.

        Returns:
            Dict containing Kafka-specific throughput optimization guidance
        """
        return {
            'throughput_targets': {
                '10-100 MB/s': {
                    'recommended_config': {
                        'BatchSize': 500,
                        'MaximumBatchingWindowInSeconds': 30,
                        'ProvisionedPollerConfig': {'MinimumPollers': 2, 'MaximumPollers': 20},
                    },
                    'explanation': {
                        'BatchSize': 'Large batch size reduces Lambda invocation overhead',
                        'MaximumBatchingWindowInSeconds': 'Allows batches to fill up for better efficiency',
                        'MinimumPollers': '2 pollers provide 10 MB/s baseline throughput',
                        'MaximumPollers': '20 pollers provide 100 MB/s peak throughput',
                    },
                    'cost_optimization': 'This configuration balances throughput with cost by using larger batches and controlled poller scaling',
                }
            },
            'poller_scaling_guide': {
                'rule': 'Each Kafka poller provides approximately 5 MB/s throughput',
                'calculation': 'Target throughput (MB/s) ÷ 5 = Required pollers',
                'examples': {
                    '10 MB/s': '2 pollers minimum',
                    '50 MB/s': '10 pollers',
                    '100 MB/s': '20 pollers',
                },
            },
            'additional_considerations': [
                'Ensure Kafka topic has sufficient partitions (ideally 1 partition per poller)',
                'Monitor Lambda function memory and timeout settings for batch processing',
                'Consider reserved concurrency to prevent throttling at high throughput',
            ],
        }
