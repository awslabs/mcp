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

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional


class EsmDiagnosisTool:
    """Comprehensive diagnostic tool for AWS Lambda Event Source Mapping (ESM) troubleshooting.

    This class provides specialized diagnostic capabilities for identifying and resolving
    issues in Kafka Event Source Mappings. It analyzes connection patterns, authentication failures,
    and network connectivity problems to pinpoint root causes and provide targeted resolution strategies.
    """

    def __init__(self, mcp: FastMCP):
        """Initialize the ESM diagnosis tool and register diagnostic capabilities.

        Args:
            mcp: FastMCP instance for tool registration
        """
        # Register Kafka-specific diagnostic tools
        mcp.tool(name='esm_kafka_diagnosis')(self.esm_kafka_diagnosis_tool)
        mcp.tool(name='esm_kafka_resolution')(self.esm_kafka_resolution_tool)

    async def esm_kafka_diagnosis_tool(
        self,
        ctx: Context,
    ) -> Dict[str, Any]:
        """Diagnoses timeout issues in Kafka Event Source Mappings by identifying when they occur.

        This tool analyzes logs, metrics, and configurations to determine if timeouts happen
        before reaching the broker, after reaching the broker, or during Lambda processing.
        It provides specific indicators for each scenario to help pinpoint the root cause.

        Args:
            ctx: The execution context

        Returns:
            Dict containing diagnostic indicators and next steps for resolving the timeout
        """
        await ctx.info('Getting self-diagnosis steps for MSK Kafka event source')

        # Critical architectural facts about MSK ESM that affect troubleshooting approach
        # Understanding these concepts is essential for proper diagnosis
        important_facts = [
            "- Lambda event source mappings don't inherit the virtual private \
            cloud (VPC) network configuration of the Lambda function. This is true for \
            both Amazon MSK and self-managed Kafka triggers. An Amazon MSK event source \
            mapping uses the subnet and security group configurations that you configured \
            on the target MSK cluster.",
            '- The security group of ESM is equal to the one of the MSK cluster.',
            '- The lambda consumer function need not to be inside the cluster VPC.',
            '- Any VPC endpoints is unnecessary because we assume provisioned mode ESM is used.',
            '- Refer to the following documentations for troubleshooting detail:',
            'https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html,',
            'https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster,',
            'and https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html.',
        ]

        issues = ['To determine when a timeout occurs, analyze these indicators:']

        # Categorized timeout scenarios with specific diagnostic indicators
        # Each category represents a different failure point in the ESM-MSK communication chain
        timeout_indicators = {
            # Timeout occurs before ESM reaches Kafka brokers - network/security issue
            'pre-broker-timeout': [
                'PROBLEM: Connection error. Please check your event source connection \
                    configuration.',
                'The first attempt to connection failed in the ESM log.',
                'The system log for Kafka received did not receive anything from ESM.',
                "Network and security group settings block the event source mapping's requests to \
                    the broker endpoints.",
            ],
            # Timeout occurs after ESM reaches brokers but before completion - broker issue
            'post-broker-timeout': [
                'PROBLEM: Connection error. Please check your event source connection \
                    configuration.',
                'Some transactions earlier has completed successfully.',
                'The Kafka cluster was offline when the issue occurred.',
                'The Kafka cluster experienced high CPU or high memory when the issue occurred.',
                "The broker receives the event source mapping's request, but it can't complete \
                    the request.",
            ],
            # ESM can reach Kafka but cannot invoke Lambda function - Lambda/IAM issue
            'lambda-unreachable': [
                'PROBLEM: SASL authentication failed.',
                'PROBLEM: Cluster failed to authorize Lambda.',
                'PROBLEM: Connection error. Your event source VPC must be able to connect to \
                    Lambda and STS, Secrets Manager (if event source authentication is required), \
                    and the OnFailure Destination (if one is configured).',
                'The ESM has polled the Kafka cluster and called the Lambda API.',
                'The Lambda function or its API endpoint did not receive any records from the ESM \
                    side.',
                'The event source mapping can access your Kafka cluster and poll records \
                    successfully, but calls to the Lambda API fail or time out.',
            ],
            # ESM cannot reach configured failure destination - destination connectivity issue
            'on-failure-destination-unreachable': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to \
                    Lambda and STS, Secrets Manager (if event source authentication is required), \
                    and the OnFailure Destination (if one is configured).',
                'There were error(s) during the Lambda function was processing the data.',
                'The service used for the on-failure destination did not received any records from \
                    the ESM side.',
                'On-failure destination, such as Amazon Simple Storage Service (Amazon S3) or \
                    Amazon Simple Notification Service (Amazon SNS) is configured. However, when \
                    your function invocations end with an error, calls to the API of the \
                    on-failure destination fail or time out.',
            ],
            # ESM cannot reach AWS STS for role assumption - STS connectivity/IAM issue
            'sts-unreachable': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to \
                    Lambda and STS, Secrets Manager (if event source authentication is required), \
                    and the OnFailure Destination (if one is configured).',
                'PROBLEM: Lambda failed to assume your function execution role.',
                'No VPC endpoint policy allows the lambda:InvokeFunction action.',
                "lambda.amazonaws.com is not listed as a trusted service in the IAM role's trust \
                    policy.",
                'sts:AssumeRole is not allowed in the VPC endpoint policy.',
                'The event source mapping is configured in a VPC, and calls to the AWS STS API fail \
                    or timeout.',
            ],
        }

        # General diagnostic steps to identify the specific timeout scenario
        resolutions = [
            'Use AWS CLI to get the error message (LastProcessingResult) from ESM: \
                aws lambda get-event-source-mapping --uuid <ESM UUID>.',
            'Once timeout location is identified, use esm_kafka_resolution_tool with the \
                appropriate issue_type:',
        ]

        # Available resolution tools for each identified timeout scenario
        next_actions = [
            "esm_kafka_resolution_tool(issue_type='pre-broker-timeout')",
            "esm_kafka_resolution_tool(issue_type='post-broker-timeout')",
            "esm_kafka_resolution_tool(issue_type='lambda-unreachable')",
            "esm_kafka_resolution_tool(issue_type='on-failure-destination-unreachable')",
            "esm_kafka_resolution_tool(issue_type='sts-unreachable')",
        ]

        response = {
            'diagnosis': {
                'important_facts': important_facts,
                'issues': issues,
                'timeout_indicators': timeout_indicators,
                'resolutions': resolutions,
                'next_actions': next_actions,
            }
        }

        return response

    async def esm_kafka_resolution_tool(
        self,
        ctx: Context,
        issue_type: Optional[
            Literal[
                'pre-broker-timeout',
                'post-broker-timeout',
                'lambda-unreachable',
                'on-failure-destination-unreachable',
                'sts-unreachable',
                'others',
            ]
        ] = Field(default='others', description='Type of issues for which to get resolutions'),
    ) -> Dict[str, Any]:
        """Provides targeted resolutions for Kafka Event Source Mapping timeout issues.

        Based on the identified timeout location (pre-broker, post-broker, etc.),
        this tool offers specific troubleshooting steps and configuration recommendations
        to resolve connectivity, authentication, and processing issues between
        Lambda functions and MSK Kafka clusters.

        Args:
            ctx: The execution context
            issue_type: The specific timeout scenario to address

        Returns:
            Dict containing issue descriptions and step-by-step resolution instructions
        """
        await ctx.info('Getting resolution steps for Kafka event source')

        issues = []
        resolutions = {}

        # Standard requirements that apply to all resolution scenarios
        # These ensure proper deployment practices and maintainability
        base_requirements = [
            '# You MUST also do:',
            '- Follow the steps and rules in the resolutions.',
            '- Assume user is using IAM authentication, if not provided.',
            '- Create a deploy script file that can deploy the SAM template to update changes.',
            '- Create a cleanup script file that can delete the SAM stack and undo all changes.',
            '- Create a test script file that can verify what has been deployed.',
            '- Whenever creating a new stack or component, prepend its name with '
            'the cluster name or the username of the credential.',
            '- Use SAM template as much as possible when deploying resources.',
            '- Use both CAPABILITY_NAMED_IAM and CAPABILITY_IAM in SAM deploy command.',
            '- Confirm the syntax is correct among all generated scripts.',
            '- Confirm resource ARNs are correct in the generated template.',
            '- If the ESM is already exist, then use its UUID to update the configuration '
            'in the template.',
            '- Summarize what you have done in a README.md file.',
        ]

        # Handle network connectivity issues - ESM cannot reach Kafka brokers
        if issue_type == 'pre-broker-timeout':
            issues.append(
                "Network and security group settings block the event source mapping's requests to "
                'the broker endpoints.'
            )
            resolutions['steps'] = [
                '# Focus on investigating security group settings, fix the security group only.',
                '## To check whether your security groups allow the required traffic and ports, '
                'complete the following steps:',
                '1. List all security groups and subnets that the MSK cluster uses, run the '
                '`aws kafka describe-cluster --cluster-arn <cluster-arn>` AWS CLI command.',
                '2. Show all inbound and outbound rules: run the `aws ec2 '
                'describe-security-groups --group-ids <security group id>` command on the '
                'security groups listed in the output of the describe-cluster command.',
                '3. Configure the rules in the listed security groups to allow traffic between '
                'the security group of ESM VPC (equal to MSK cluster itself) and the MSK '
                'cluster: outbound all-traffic, inbound: 9092-9098.',
                '## To update the inbound/outbound configurations, refer to `esm_security_group_tool`.',
                '## Reactivate the ESM after the security group is updated.',
            ]
            # Strict rules to prevent unintended changes that could break other components
            resolutions['rules'] = [
                "Don't modify any resources other than security groups.",
                "Don't modify the Lambda function, its security group, policies, and IAM role.",
                'Call AWS CLI and fill in the security group IDs on users behalf.',
                'You MUST only update the security groups associated with the MSK cluster.',
            ]
        # Handle broker-side issues - ESM reaches brokers but they cannot complete requests
        elif issue_type == 'post-broker-timeout':
            issues.append(
                "The broker receives the event source mapping's request, but it can't complete "
                'the request.'
            )
            resolutions['steps'] = [
                'Check the broker status at the time of failure.',
                'If the cluster was offline when the issue occurred, then reactivate the event '
                'source mapping when the cluster is back online and available.',
                'If Timed out requests occur when the cluster is out of disk space or it '
                'reaches 100% CPU usage, or when a broker endpoint fails, set the event source '
                "mapping's batch size to 1, and then re-activate the trigger.",
                "Examine the broker's access logs and system logs for more information.",
            ]
        # Handle IAM and authentication issues - ESM cannot invoke Lambda or access services
        elif issue_type == 'lambda-unreachable':
            issues += [
                'The event source mapping can access your Kafka cluster and poll records '
                'successfully, but calls to the Lambda API fail or time out.',
                'The event source mapping is configured to use Secrets Manager cluster '
                'authentication, but calls to the Secrets Manager API fail or timeout.',
            ]
            resolutions['steps'] = [
                '# Focus on investigating the IAM permissions.',
                '## To check whether the lambda function has sufficient permissions to poll records:',
                '1. Get the ARN of the cluster and the ARN of the lambda execution role.',
                '2. Get the current configurations of the ESM.',
                '3. Create a new policy using `esm_msk_policy_tool` and attach it to the lambda execution role.',
                "4. Also check if the cluster's security group allows inbound port 9092-9098. "
                'If there is one already, then do NOT to make changes for security group. '
                'Otherwise, fix the security group using `esm_msk_security_group_tool.`',
                '5. Update the ESM with the following configurations: ',
                '- Re-activate the trigger. ',
                '- Configure it as provisioned mode. ',
                '- Enable cluster authentication in the template.',
                '6. When creating Event Source Mapping:',
                '- Use exact resource ARNs instead of asterisks in the template.',
                '- The ESM must depend on the policy deployment.',
            ]
            # Strict rules to prevent breaking existing Lambda functions or creating circular dependencies
            resolutions['rules'] = [
                '- Do NOT create/modify anything other than the policies and IAM roles.',
                '- Do NOT use AWS::CloudFormation::CustomResource because CloudFormation will not be able to catch the response.',
                '- Do NOT create/modify any Lambda function, build local script instead.',
            ]
        # Handle failure destination connectivity issues
        elif issue_type == 'on-failure-destination-unreachable':
            issues.append(
                'On-failure destination, such as Amazon Simple Storage Service (Amazon S3) or '
                'Amazon Simple Notification Service (Amazon SNS) is configured. However, when '
                'your function invocations end with an error, calls to the API of the '
                'on-failure destination fail or time out.'
            )
            resolutions['steps'] = [
                'Create a VPC endpoint for your on-failure destination. Example destinations '
                'include Amazon SNS or Amazon S3. This VPC endpoint must be in the VPC that '
                'contains the MSK cluster.',
            ]
        # Handle STS connectivity issues - ESM cannot assume IAM roles
        elif issue_type == 'sts-unreachable':
            issues.append(
                'The event source mapping is configured in a VPC, and calls to the AWS STS API '
                'fail or timeout.'
            )
            resolutions['steps'] = [
                'Create a STS VPC endpoint in the VPC that contains the MSK cluster.',
                'Make sure that the lambda.amazonaws.com service principal is listed as a '
                "trusted service in the IAM role's trust policy",
                'Make sure that the STS VPC endpoint policy allows the Lambda service '
                'principal to call the sts:AssumeRole. For more information about how to '
                'configure your VPC, see Configure network security.',
            ]
        # Fallback case for unrecognized or general issues
        else:
            issues.append(f'Unknown issue type: {issue_type}')
            resolutions['steps'] = [
                'Please refer to the following documentation for troubleshooting steps:',
                'https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html',
                'and https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster',
            ]

        # Always require user confirmation before making changes to prevent accidental modifications
        next_actions = ['Confirm with the user before deployment using `esm_deployment_precheck`.']

        response = {
            'response': {
                'issues': issues,
                'resolutions': resolutions,
                'base_requirements': base_requirements,
                'next_actions': next_actions,
            }
        }

        return response
