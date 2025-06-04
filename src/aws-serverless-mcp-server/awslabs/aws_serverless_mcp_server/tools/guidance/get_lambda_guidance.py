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
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import json
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


class WhenToUseScenario:
    """Scenario when to use Lambda."""

    def __init__(self, scenario: str, description: str, examples: Optional[List[str]] = None):
        """Initializes a new instance of the class with the specified scenario, description, and optional examples.

        Args:
            scenario (str): The scenario for which guidance is provided.
            description (str): A description of the guidance.
            examples (Optional[List[str]], optional): Example usages or cases related to the guidance. Defaults to None.
        """
        self.scenario = scenario
        self.description = description
        self.examples = examples

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {'scenario': self.scenario, 'description': self.description}
        if self.examples:
            result['examples'] = json.dumps(self.examples)
        return result


class WhenNotToUseScenario:
    """Scenario when not to use Lambda."""

    def __init__(self, scenario: str, description: str, alternatives: Optional[List[str]] = None):
        """Initializes a new instance of the class with the given scenario, description, and optional alternatives.

        Args:
            scenario (str): The scenario for which guidance is provided.
            description (str): A description of the guidance.
            alternatives (Optional[List[str]], optional): A list of alternative options. Defaults to None.
        """
        self.scenario = scenario
        self.description = description
        self.alternatives = alternatives

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {'scenario': self.scenario, 'description': self.description}
        if self.alternatives:
            result['alternatives'] = json.dumps(self.alternatives)
        return result


class DecisionCriterion:
    """Decision criterion for using Lambda."""

    def __init__(self, criterion: str, description: str):
        """Initializes the object with a criterion and its description.

        Args:
            criterion (str): The criterion to be used.
            description (str): A description of the criterion.
        """
        self.criterion = criterion
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'criterion': self.criterion, 'description': self.description}


class UseCaseSpecificGuidance:
    """Guidance specific to a use case."""

    def __init__(
        self,
        title: str,
        suitability: str,
        description: str,
        best_practices: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
        alternatives: Optional[List[str]] = None,
    ):
        """Initializes a new instance of the class with guidance information for a Lambda function.

        Args:
            title (str): The title of the guidance.
            suitability (str): The suitability of the guidance.
            description (str): A detailed description of the guidance.
            best_practices (Optional[List[str]], optional): A list of best practices related to the guidance. Defaults to None.
            limitations (Optional[List[str]], optional): A list of limitations associated with the guidance. Defaults to None.
            alternatives (Optional[List[str]], optional): A list of alternative approaches or solutions. Defaults to None.
        """
        self.title = title
        self.suitability = suitability
        self.description = description
        self.best_practices = best_practices
        self.limitations = limitations
        self.alternatives = alternatives

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'title': self.title,
            'suitability': self.suitability,
            'description': self.description,
        }
        if self.best_practices:
            result['bestPractices'] = json.dumps(self.best_practices)
        if self.limitations:
            result['limitations'] = json.dumps(self.limitations)
        if self.alternatives:
            result['alternatives'] = json.dumps(self.alternatives)
        return result


class GetLambdaGuidanceTool:
    """Tool to provide guidance on when to use AWS Lambda as a deployment platform."""

    def __init__(self, mcp: FastMCP):
        """Initialize the GetLambdaGuidanceTool."""
        mcp.tool(name='get_lambda_guidance')(self.get_lambda_guidance)

    async def get_lambda_guidance(
        self,
        ctx: Context,
        use_case: str = Field(
            description='Description of the use case. (e.g. scheduled tasks, event-driven application)'
        ),
        include_examples: Optional[bool] = Field(
            default=True, description='Whether to include examples'
        ),
    ) -> Dict[str, Any]:
        """Use this tool to determine if AWS Lambda is suitable platform to deploy an application.

        Returns a comprehensive guide on when to choose AWS Lambda as a deployment platform.
        It includes scenarios when to use and not use Lambda, advantages and disadvantages,
        decision criteria, and specific guidance for various use cases (e.g. scheduled tasks, event-driven application).

        Returns:
            Dict: Lambda guidance information
        """
        # Base guidance
        base_guidance = {
            'title': 'When to Choose AWS Lambda as Your Deployment Platform',
            'overview': """AWS Lambda is a serverless compute service that runs your code in response to events and automatically manages
            the underlying compute resources. It allows you to run code without provisioning or managing servers, making it ideal for
            certain types of applications and workloads.""",
        }

        # Scenarios when to use Lambda
        when_to_use = [
            WhenToUseScenario(
                scenario='Event-driven applications',
                description='Lambda is ideal for applications that are triggered by events from other AWS services, HTTP requests, or scheduled events.',
                examples=[
                    'Processing uploads to S3 buckets',
                    'Handling API Gateway requests',
                    'Responding to DynamoDB table updates',
                    'Processing SQS messages',
                ],
            ),
            WhenToUseScenario(
                scenario='Microservices architecture',
                description='Lambda works well for implementing individual microservices that perform specific functions within a larger application.',
                examples=[
                    'User authentication service',
                    'Image processing service',
                    'Notification service',
                    'Data validation service',
                ],
            ),
            WhenToUseScenario(
                scenario='Intermittent workloads',
                description='Lambda is cost-effective for workloads that run intermittently or have variable traffic patterns.',
                examples=[
                    'Daily data processing jobs',
                    'Infrequent API calls',
                    'Scheduled reports generation',
                    'Low-traffic websites',
                ],
            ),
            WhenToUseScenario(
                scenario='Real-time file processing',
                description="Lambda can process files as soon as they're uploaded or modified.",
                examples=[
                    'Generating thumbnails from uploaded images',
                    'Validating CSV files',
                    'Converting document formats',
                    'Extracting metadata from files',
                ],
            ),
            WhenToUseScenario(
                scenario='Backend for mobile and web applications',
                description='Lambda can serve as a scalable backend for mobile and web applications.',
                examples=[
                    'User registration and authentication',
                    'Form processing',
                    'Data retrieval and storage',
                    'Real-time notifications',
                ],
            ),
        ]

        # Scenarios when not to use Lambda
        when_not_to_use = [
            WhenNotToUseScenario(
                scenario='Long-running processes',
                description='Lambda has a maximum execution time of 15 minutes, making it unsuitable for long-running processes.',
                alternatives=['AWS Batch', 'Amazon EC2', 'AWS Fargate'],
            ),
            WhenNotToUseScenario(
                scenario='Applications requiring consistent performance',
                description='Lambda can experience cold starts, which may introduce latency variability.',
                alternatives=['Amazon EC2', 'Amazon ECS', 'Amazon EKS'],
            ),
            WhenNotToUseScenario(
                scenario='Applications with high memory or CPU requirements',
                description='Lambda has limits on memory (10GB) and CPU allocation, making it unsuitable for compute-intensive applications.',
                alternatives=[
                    'Amazon EC2 with specialized instance types',
                    'AWS Batch',
                    'Amazon SageMaker',
                ],
            ),
            WhenNotToUseScenario(
                scenario='Applications requiring persistent local file system access',
                description='Lambda provides a non-persistent file system with limited capacity (512MB to 10GB depending on memory configuration).',
                alternatives=[
                    'Amazon EC2 with EBS volumes',
                    'Amazon ECS with EFS',
                    'AWS Fargate with EFS',
                ],
            ),
        ]

        # Advantages of using Lambda
        pros = [
            'No server management required',
            'Automatic scaling based on workload',
            'Pay only for compute time used (no charges when code is not running)',
            'Built-in high availability and fault tolerance',
            'Native integration with many AWS services',
            'Support for multiple programming languages',
            'Simplified deployment process',
            'Automatic security patches and updates',
            'Granular permission control via IAM',
            'Built-in monitoring and logging via CloudWatch',
        ]

        # Disadvantages of using Lambda
        cons = [
            'Cold start latency for infrequently used functions',
            'Maximum execution time limit (15 minutes)',
            'Limited memory and CPU allocation',
            'Non-persistent file system with size limitations',
            'Limited deployment package size',
            'Limited runtime environment customization',
            'Potential cost increases for high-volume, long-running functions',
        ]

        # Decision criteria
        decision_criteria = [
            DecisionCriterion(
                criterion='Execution duration',
                description='Choose Lambda if your tasks complete within 15 minutes; otherwise, consider alternatives like EC2, Fargate, or Batch.',
            ),
            DecisionCriterion(
                criterion='Execution frequency',
                description='Lambda is most cost-effective for intermittent workloads; for constant high-volume processing, EC2 or containers might be more economical.',
            ),
            DecisionCriterion(
                criterion='Resource requirements',
                description='If your application needs more than 10GB of memory or significant CPU resources, consider EC2 or specialized services.',
            ),
            DecisionCriterion(
                criterion='Latency sensitivity',
                description="For applications where consistent low latency is critical, Lambda's cold starts might be problematic; consider SnapStart, Provisioned Concurrency or non-serverless options.",
            ),
            DecisionCriterion(
                criterion='State management',
                description='Lambda functions are stateless; if your application requires significant state management, consider combining Lambda with a database or using a different service.',
            ),
            DecisionCriterion(
                criterion='Development complexity',
                description='Lambda simplifies infrastructure management but may require rethinking application architecture for serverless patterns.',
            ),
            DecisionCriterion(
                criterion='Ecosystem integration',
                description='Lambda integrates seamlessly with many AWS services; evaluate if your application benefits from these integrations.',
            ),
            DecisionCriterion(
                criterion='Cost model',
                description="Lambda's pay-per-use model works best for variable workloads; analyze your usage patterns to determine if this aligns with your budget.",
            ),
        ]

        # Use case specific guidance
        use_case_specific_guidance = None
        if use_case:
            if use_case == 'api':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for APIs',
                    suitability='High',
                    description='AWS Lambda paired with API Gateway is an excellent choice for building serverless APIs.',
                    best_practices=[
                        'Use API Gateway with Lambda for RESTful or WebSocket APIs',
                        'Implement caching at the API Gateway level for frequently accessed resources',
                        'Consider Lambda Provisioned Concurrency or SnapStart for latency-sensitive APIs',
                        'Use Lambda layers to share common code across API functions',
                        'Implement proper error handling and response formatting',
                    ],
                    limitations=[
                        'API Gateway has its own quotas and limitations',
                        'Cold starts may impact API response times',
                        'Complex transaction management across multiple services requires careful design',
                    ],
                    alternatives=[
                        'Amazon EC2 with Application Load Balancer for high-volume, consistent traffic',
                        'AWS App Runner for containerized web applications and APIs',
                        'Amazon ECS/EKS for complex API architectures requiring containers',
                    ],
                )
            elif use_case == 'data-processing':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for Data Processing',
                    suitability='High for batch processing and stream processing',
                    description='Lambda works well for processing data in response to events or on a schedule, especially when integrated with other AWS data services.',
                    best_practices=[
                        'Use S3 events to trigger processing of uploaded files',
                        'Process DynamoDB streams for change data capture workflows',
                        'Implement fan-out patterns using SNS or EventBridge for parallel processing',
                        'Use Step Functions for orchestrating complex data processing workflows',
                        'Consider Lambda destinations for success/failure handling',
                    ],
                    limitations=[
                        '15-minute execution limit may be insufficient for large datasets',
                        'Memory limitations constrain the size of data that can be processed in a single invocation',
                        'Stateless nature requires external storage for intermediate results',
                    ],
                    alternatives=[
                        'AWS Glue for ETL workloads',
                        'Amazon EMR for big data processing',
                        'Amazon Kinesis Data Analytics for real-time stream processing',
                        'AWS Batch for long-running batch jobs',
                    ],
                )
            elif use_case == 'real-time':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for Real-time Applications',
                    suitability='Medium',
                    description='Lambda can support real-time applications but requires careful design to address cold starts and ensure consistent performance.',
                    best_practices=[
                        'Use Provisioned Concurrency or SnapStart to eliminate cold starts',
                        'Implement WebSocket APIs with API Gateway and Lambda',
                        'Consider Amazon ElastiCache for low-latency data access',
                        'Use Amazon EventBridge for event-driven architectures',
                        'Optimize function code for performance',
                    ],
                    limitations=[
                        'Cold starts can introduce variable latency',
                        'Limited execution duration for long-lived connections',
                        'Network latency between Lambda and other services',
                    ],
                    alternatives=[
                        'Amazon EC2 with Auto Scaling for consistent performance',
                        'Amazon ECS with Fargate for containerized real-time applications',
                        'AWS App Runner for web applications requiring consistent performance',
                    ],
                )
            elif use_case == 'scheduled-tasks':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for Scheduled Tasks',
                    suitability='Very High',
                    description='Lambda combined with EventBridge (CloudWatch Events) is ideal for scheduled tasks and cron jobs.',
                    best_practices=[
                        'Use EventBridge rules to schedule Lambda invocations',
                        'Implement idempotent functions to handle potential duplicate invocations',
                        'Use Step Functions for complex scheduled workflows',
                        'Monitor execution times and set appropriate timeouts',
                        'Implement proper error handling and retries',
                    ],
                    limitations=[
                        'Minimum schedule interval is 1 minute',
                        '15-minute maximum execution time',
                        'Potential for missed invocations if previous invocation is still running',
                    ],
                    alternatives=[
                        'Amazon EC2 with cron for more complex scheduling needs',
                        'AWS Batch for scheduled batch processing jobs',
                        'Amazon ECS scheduled tasks for containerized workloads',
                    ],
                )
            elif use_case == 'web-app':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for Web Applications',
                    suitability='Medium to High',
                    description='Lambda can power web applications, especially when combined with other serverless services like API Gateway, S3, and CloudFront.',
                    best_practices=[
                        'Use Lambda@Edge or CloudFront Functions for edge computing needs',
                        'Implement static content hosting on S3 with CloudFront',
                        'Use API Gateway and Lambda for dynamic content and APIs',
                        'Consider DynamoDB for serverless database needs',
                        'Implement authentication with Amazon Cognito',
                    ],
                    limitations=[
                        'Cold starts can impact user experience',
                        'Complex session management requires additional services',
                        'Not ideal for monolithic web applications',
                        'Requires an adpater layer (e.g. Lambda Web Adapter) for common web frameworks like Next.js or Express.js',
                    ],
                    alternatives=[
                        'AWS Amplify for full-stack web applications',
                        'AWS Elastic Beanstalk for traditional web applications',
                        'Amazon EC2 or ECS for complex web applications with specific requirements',
                    ],
                )
            elif use_case == 'mobile-backend':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for Mobile Backend',
                    suitability='High',
                    description='Lambda works well as a backend for mobile applications, especially when combined with AWS AppSync or API Gateway.',
                    best_practices=[
                        'Use AWS AppSync for GraphQL APIs and real-time data synchronization',
                        'Implement authentication with Amazon Cognito',
                        'Use Amazon S3 for user-generated content storage',
                        'Leverage Amazon SNS for push notifications',
                        'Consider DynamoDB for serverless database needs',
                    ],
                    limitations=[
                        'Cold starts can impact mobile app responsiveness',
                        'Complex backend logic may require careful design',
                        'Offline data synchronization requires additional implementation',
                    ],
                    alternatives=[
                        'AWS Amplify for full-stack mobile app development',
                        'Amazon EC2 or ECS for complex backend requirements',
                    ],
                )
            elif use_case == 'iot':
                use_case_specific_guidance = UseCaseSpecificGuidance(
                    title='Using Lambda for IoT Applications',
                    suitability='High',
                    description='Lambda integrates well with AWS IoT services for processing device data and implementing IoT business logic.',
                    best_practices=[
                        'Use AWS IoT Core rules to trigger Lambda functions',
                        'Implement device shadows for state management',
                        'Use Amazon Timestream for time-series IoT data',
                        'Consider AWS IoT Analytics for advanced analytics',
                        'Implement proper error handling and dead-letter queues',
                    ],
                    limitations=[
                        'May not be suitable for ultra-high-frequency sensor data without aggregation',
                        'Limited local processing compared to IoT Greengrass',
                        'Stateless nature requires external storage for device state',
                    ],
                    alternatives=[
                        'AWS IoT Greengrass for edge computing needs',
                        'Amazon Kinesis for high-volume IoT data streams',
                        'Amazon MSK (Managed Streaming for Kafka) for complex IoT event processing',
                    ],
                )

        # Build response
        response = {**base_guidance}

        # Add information based on format
        if include_examples:
            response['whenToUse'] = json.dumps([scenario.to_dict() for scenario in when_to_use])
            response['whenNotToUse'] = json.dumps(
                [scenario.to_dict() for scenario in when_not_to_use]
            )
        else:
            # For concise format, include summarized versions
            response['whenToUse'] = json.dumps(
                [
                    {'scenario': scenario.scenario, 'description': scenario.description}
                    for scenario in when_to_use
                ]
            )
            response['whenNotToUse'] = json.dumps(
                [
                    {'scenario': scenario.scenario, 'description': scenario.description}
                    for scenario in when_not_to_use
                ]
            )

        # Add pros, cons, and decision criteria
        response['pros'] = json.dumps(pros)
        response['cons'] = json.dumps(cons)
        response['decisionCriteria'] = json.dumps(
            [criterion.to_dict() for criterion in decision_criteria]
        )

        # Add use case specific guidance if available
        if use_case_specific_guidance:
            response['useCaseSpecificGuidance'] = json.dumps(use_case_specific_guidance.to_dict())

        return response
