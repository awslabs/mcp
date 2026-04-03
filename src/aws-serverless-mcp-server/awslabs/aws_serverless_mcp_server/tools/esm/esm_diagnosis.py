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

from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional


class EsmDiagnosisTool(BaseTool):
    """Comprehensive diagnostic tool for AWS Lambda Event Source Mapping (ESM) troubleshooting.

    This class provides specialized diagnostic capabilities for identifying and resolving
    issues in Kafka Event Source Mappings. It analyzes connection patterns, authentication failures,
    and network connectivity problems to pinpoint root causes and provide targeted resolution strategies.
    """

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ESM diagnosis tool and register diagnostic capabilities.

        Args:
            mcp: FastMCP instance for tool registration
            allow_write: Whether write operations are allowed
        """
        super().__init__(allow_write=allow_write)
        self.allow_write = allow_write
        # Register unified Kafka diagnostic and resolution tool
        mcp.tool(
            name='esm_kafka_troubleshoot',
            description='Troubleshoot Kafka streaming issues and connectivity problems. Diagnoses MSK cluster connectivity, Lambda function timeouts, authentication failures, and network configuration issues. Provides step-by-step resolution guidance for Kafka and Lambda integration problems.',
        )(self.esm_kafka_troubleshoot_tool)

    async def esm_kafka_troubleshoot_tool(
        self,
        ctx: Context,
        kafka_type: Optional[Literal['msk', 'self-managed', 'auto-detect']] = Field(
            default='auto-detect',
            description='Type of Kafka cluster: "msk" for Amazon MSK, "self-managed" for self-managed Apache Kafka, "auto-detect" to determine automatically',
        ),
        issue_type: Optional[
            Literal[
                'diagnosis',
                'pre-broker-timeout',
                'post-broker-timeout',
                'lambda-unreachable',
                'on-failure-destination-unreachable',
                'sts-unreachable',
                'authentication-failed',
                'network-connectivity',
                'others',
            ]
        ] = Field(
            default='diagnosis',
            description='Type of troubleshooting: "diagnosis" for identifying issues, or specific issue type for resolution steps',
        ),
    ) -> Dict[str, Any]:
        """Comprehensive Kafka ESM troubleshooting tool for both MSK and self-managed Kafka.

        This unified tool supports both Amazon MSK and self-managed Apache Kafka clusters.
        It can either diagnose timeout issues by analyzing when they occur,
        or provide targeted resolution steps for specific identified problems.

        Args:
            ctx: The execution context
            kafka_type: Type of Kafka cluster (MSK, self-managed, or auto-detect)
            issue_type: 'diagnosis' for problem identification, or specific issue type for resolution

        Returns:
            Dict containing diagnostic indicators or resolution steps based on kafka_type and issue_type
        """
        # Check tool access permissions for write operations (resolution steps may generate templates)
        if issue_type != 'diagnosis':
            self.checkToolAccess()

        if issue_type == 'diagnosis':
            return await self._get_diagnosis_info(ctx, kafka_type or 'auto-detect')
        else:
            return await self._get_resolution_steps(
                ctx, kafka_type or 'auto-detect', issue_type or 'diagnosis'
            )

    async def _get_diagnosis_info(self, ctx: Context, kafka_type: Optional[str]) -> Dict[str, Any]:
        """Get diagnostic information for Kafka ESM issues."""
        await ctx.info(f'Getting diagnostic steps for {kafka_type} Kafka event source')

        # Critical architectural facts about Kafka ESM that affect troubleshooting approach
        # Understanding these concepts is essential for proper diagnosis
        if kafka_type == 'msk':
            important_facts = [
                '# Amazon MSK (Managed Streaming for Apache Kafka) Specific Facts:',
                "- Lambda event source mappings don't inherit the VPC configuration of the Lambda function",
                '- MSK ESM uses the subnet and security group configurations of the target MSK cluster',
                '- The security group of ESM is equal to the one of the MSK cluster',
                '- The Lambda consumer function does not need to be inside the cluster VPC',
                '- VPC endpoints are unnecessary because provisioned mode ESM is used',
                '- MSK supports IAM authentication and SASL/SCRAM authentication',
                '- Refer to MSK-specific documentation:',
                '  https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html',
                '  https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster',
                '  https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html',
            ]
        elif kafka_type == 'self-managed':
            important_facts = [
                '# Self-Managed Apache Kafka Specific Facts:',
                "- Lambda event source mappings don't inherit the VPC configuration of the Lambda function",
                '- Self-managed Kafka ESM uses VPC configuration you specify in the ESM configuration',
                '- You must specify VPC subnets and security groups in the ESM configuration',
                '- The Lambda consumer function does not need to be inside the Kafka VPC',
                '- VPC endpoints may be required for Lambda service calls from private subnets',
                '- Self-managed Kafka supports SASL/SCRAM, SASL/PLAIN, and mTLS authentication',
                '- Bootstrap servers must be accessible from the configured ESM subnets',
                '- Refer to self-managed Kafka documentation:',
                '  https://docs.aws.amazon.com/lambda/latest/dg/with-kafka.html',
                '  https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-troubleshoot.html',
                '  https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-create-package.html',
            ]
        else:  # auto-detect
            important_facts = [
                '# General Kafka ESM Facts (Both MSK and Self-Managed):',
                "- Lambda event source mappings don't inherit the VPC configuration of the Lambda function",
                '- ESM uses either MSK cluster configuration or user-specified VPC configuration',
                '- The Lambda consumer function does not need to be inside the Kafka VPC',
                '- Authentication methods vary: IAM (MSK only), SASL/SCRAM, SASL/PLAIN, mTLS',
                '- Network connectivity requirements differ between MSK and self-managed setups',
                '',
                '# To determine your Kafka type:',
                "- MSK: Event source ARN contains 'kafka' service (arn:aws:kafka:region:account:cluster/...)",
                '- Self-managed: Event source ARN is empty or contains bootstrap servers',
                '',
                '# Documentation references:',
                '- MSK: https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html',
                '- Self-managed: https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-troubleshoot.html',
            ]

        issues = ['To determine when a timeout occurs, analyze these indicators:']

        # Categorized timeout scenarios with specific diagnostic indicators
        # Each category represents a different failure point in the ESM-Kafka communication chain
        timeout_indicators = {
            # Timeout occurs before ESM reaches Kafka brokers - network/security issue
            'pre-broker-timeout': [
                'PROBLEM: Connection error. Please check your event source connection configuration.',
                'The first attempt to connection failed in the ESM log.',
                'The system log for Kafka received did not receive anything from ESM.',
                "Network and security group settings block the event source mapping's requests to the broker endpoints.",
                # MSK-specific indicators
                '(MSK) Security groups on MSK cluster block ESM access on ports 9092-9098.',
                # Self-managed specific indicators
                '(Self-managed) Bootstrap servers are not accessible from ESM subnets.',
                '(Self-managed) Security groups on ESM subnets do not allow outbound access to Kafka ports.',
                '(Self-managed) Network ACLs block traffic between ESM subnets and Kafka brokers.',
            ],
            # Timeout occurs after ESM reaches brokers but before completion - broker issue
            'post-broker-timeout': [
                'PROBLEM: Connection error. Please check your event source connection configuration.',
                'Some earlier transactions have completed successfully.',
                'The Kafka cluster was offline when the issue occurred.',
                'The Kafka cluster experienced high CPU or high memory when the issue occurred.',
                "The broker receives the event source mapping's request, but it can't complete the request.",
                # Common to both MSK and self-managed
                'Kafka broker is overloaded or experiencing resource constraints.',
                'Topic does not exist or ESM lacks permissions to access the topic.',
            ],
            # Authentication failures - different for MSK vs self-managed
            'authentication-failed': [
                'PROBLEM: SASL authentication failed.',
                'PROBLEM: Cluster failed to authorize Lambda.',
                # MSK-specific authentication issues
                '(MSK) IAM authentication failed - check IAM policies and cluster configuration.',
                '(MSK) SASL/SCRAM authentication failed - check Secrets Manager configuration.',
                # Self-managed specific authentication issues
                '(Self-managed) SASL/SCRAM authentication failed - check username/password in Secrets Manager.',
                '(Self-managed) SASL/PLAIN authentication failed - check credentials configuration.',
                '(Self-managed) mTLS authentication failed - check client certificates and CA configuration.',
                '(Self-managed) Kafka ACLs deny access to the specified topic or consumer group.',
            ],
            # Network connectivity issues - different requirements for MSK vs self-managed
            'network-connectivity': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to Lambda and STS.',
                # MSK-specific network issues
                '(MSK) ESM inherits MSK cluster VPC configuration but cannot reach AWS services.',
                '(MSK) MSK cluster subnets lack NAT Gateway for outbound internet access.',
                # Self-managed specific network issues
                '(Self-managed) ESM subnets cannot reach bootstrap servers.',
                '(Self-managed) ESM subnets lack route to Kafka broker subnets.',
                '(Self-managed) Cross-VPC connectivity issues between ESM and Kafka VPCs.',
            ],
            # ESM can reach Kafka but cannot invoke Lambda function - Lambda/IAM issue
            'lambda-unreachable': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to Lambda and STS.',
                'The ESM has polled the Kafka cluster and called the Lambda API.',
                'The Lambda function or its API endpoint did not receive any records from the ESM side.',
                'The event source mapping can access your Kafka cluster and poll records successfully, but calls to the Lambda API fail or time out.',
                # Common Lambda connectivity issues
                'ESM subnets lack VPC endpoint or NAT Gateway for Lambda service access.',
                'Lambda function does not exist or ESM lacks invoke permissions.',
            ],
            # ESM cannot reach configured failure destination - destination connectivity issue
            'on-failure-destination-unreachable': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to OnFailure Destination.',
                'There were errors while the Lambda function was processing the data.',
                'The service used for the on-failure destination did not receive any records from the ESM side.',
                'On-failure destination (S3, SNS, SQS) is configured but calls to the destination API fail or time out.',
                # Common destination connectivity issues
                'ESM subnets lack VPC endpoint or NAT Gateway for destination service access.',
                'Destination resource does not exist or ESM lacks permissions.',
            ],
            # ESM cannot reach AWS STS for role assumption - STS connectivity/IAM issue
            'sts-unreachable': [
                'PROBLEM: Connection error. Your event source VPC must be able to connect to STS.',
                'PROBLEM: Lambda failed to assume your function execution role.',
                'The event source mapping is configured in a VPC, and calls to the AWS STS API fail or timeout.',
                # Common STS issues
                'ESM subnets lack VPC endpoint or NAT Gateway for STS service access.',
                "lambda.amazonaws.com is not listed as a trusted service in the IAM role's trust policy.",
                'sts:AssumeRole is not allowed in the VPC endpoint policy.',
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
            f"Use esm_kafka_troubleshoot with kafka_type='{kafka_type}' and specific issue_type:",
            "- issue_type='pre-broker-timeout'",
            "- issue_type='post-broker-timeout'",
            "- issue_type='authentication-failed'",
            "- issue_type='network-connectivity'",
            "- issue_type='lambda-unreachable'",
            "- issue_type='on-failure-destination-unreachable'",
            "- issue_type='sts-unreachable'",
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

        # No need to scrub diagnosis data as it contains no sensitive information
        return response

    async def _get_resolution_steps(
        self, ctx: Context, kafka_type: Optional[str], issue_type: Optional[str]
    ) -> Dict[str, Any]:
        """Get resolution steps for specific Kafka ESM issues."""
        await ctx.info(f'Getting resolution steps for {kafka_type} Kafka {issue_type} issue')

        issues = []
        resolutions = {}

        # Standard requirements that apply to all resolution scenarios
        # These ensure proper deployment practices and maintainability
        base_requirements = [
            '# CRITICAL SAFETY REQUIREMENTS:',
            '- NEVER deploy or make changes without explicit user confirmation',
            '- ALWAYS ask: "Do you want to apply these changes to your AWS infrastructure?" before any deployment',
            '- Generate SAM templates and scripts but do NOT execute deployment automatically',
            '- Use sam_deploy tool ONLY after user confirms the changes',
            '',
            '# Implementation Requirements:',
            '- Follow the steps and rules in the resolutions.',
            '- Assume user is using IAM authentication, if not provided.',
            '- Generate SAM template for infrastructure changes (do not deploy automatically).',
            '- Create a cleanup script file that can delete the SAM stack and undo all changes.',
            '- Create a test script file that can verify what has been deployed.',
            '- Whenever creating a new stack or component, prepend its name with '
            'the cluster name or the username of the credential.',
            '- Use SAM template as much as possible when deploying resources.',
            '- Use both CAPABILITY_NAMED_IAM and CAPABILITY_IAM in SAM deploy command.',
            '- Confirm the syntax is correct among all generated scripts.',
            '- Confirm resource ARNs are correct in the generated template.',
            '- If the ESM already exists, then use its UUID to update the configuration '
            'in the template.',
            '- Summarize what you have done in a README.md file.',
        ]

        # Handle network connectivity issues - ESM cannot reach Kafka brokers
        if issue_type == 'pre-broker-timeout':
            if kafka_type == 'msk':
                issues.append(
                    "Network and security group settings block the event source mapping's requests to "
                    'the MSK broker endpoints.'
                )
                resolutions['steps'] = [
                    '# MSK Pre-Broker Timeout Resolution',
                    '## Focus on investigating MSK security group settings:',
                    '1. List all security groups and subnets that the MSK cluster uses:',
                    '   `aws kafka describe-cluster --cluster-arn <cluster-arn>`',
                    '2. Show all inbound and outbound rules:',
                    '   `aws ec2 describe-security-groups --group-ids <security-group-id>`',
                    '3. Configure the MSK cluster security group rules to allow ESM traffic:',
                    '   - Inbound: ports 9092-9098 from self (same security group)',
                    '   - Outbound: all traffic to self (same security group)',
                    '4. Use `esm_msk_security_group` tool to generate proper security group rules.',
                    '5. Reactivate the ESM after the security group is updated.',
                ]
                resolutions['rules'] = [
                    "Don't modify any resources other than MSK cluster security groups.",
                    "Don't modify the Lambda function, its security group, policies, and IAM role.",
                    'You MUST only update the security groups associated with the MSK cluster.',
                ]
            elif kafka_type == 'self-managed':
                issues.append(
                    'Network connectivity issues prevent ESM from reaching self-managed Kafka brokers.'
                )
                resolutions['steps'] = [
                    '# Self-Managed Kafka Pre-Broker Timeout Resolution',
                    '## Check ESM VPC configuration:',
                    '1. Verify ESM subnets can reach Kafka bootstrap servers:',
                    '   - Check route tables for ESM subnets',
                    '   - Ensure routes exist to Kafka broker subnets/VPC',
                    '   - Verify NAT Gateway if Kafka is in different VPC',
                    '2. Check ESM security group outbound rules:',
                    '   - Allow outbound traffic to Kafka ports (typically 9092, 9093, 9094)',
                    '   - Allow outbound HTTPS (443) for AWS service calls',
                    '3. Check Kafka broker security groups:',
                    '   - Allow inbound traffic from ESM security groups on Kafka ports',
                    '4. Test connectivity from ESM subnets to bootstrap servers:',
                    '   - Use VPC Reachability Analyzer or test instance',
                    '5. Update ESM configuration with correct VPC settings:',
                    '   - Specify correct subnets (private subnets recommended)',
                    '   - Specify security group with proper outbound rules',
                ]
                resolutions['rules'] = [
                    'Focus on ESM VPC configuration and security groups.',
                    "Don't modify Kafka broker infrastructure unless necessary.",
                    'Ensure ESM subnets have outbound internet access for AWS service calls.',
                ]
            else:  # auto-detect
                issues.append(
                    'Network connectivity issues prevent ESM from reaching Kafka brokers. '
                    "Resolution depends on whether you're using MSK or self-managed Kafka."
                )
                resolutions['steps'] = [
                    '# General Pre-Broker Timeout Resolution',
                    '## First, determine your Kafka type:',
                    '1. Check ESM configuration for EventSourceArn:',
                    '   - MSK: arn:aws:kafka:region:account:cluster/cluster-name/uuid',
                    '   - Self-managed: empty or bootstrap server list',
                    '2. For MSK clusters: Focus on MSK cluster security groups',
                    '3. For self-managed: Focus on ESM VPC configuration and connectivity',
                    '## Then use specific kafka_type for detailed resolution steps.',
                ]
        # Handle authentication failures - different for MSK vs self-managed
        elif issue_type == 'authentication-failed':
            if kafka_type == 'msk':
                issues.append(
                    'MSK authentication failed - IAM or SASL/SCRAM authentication issues.'
                )
                resolutions['steps'] = [
                    '# MSK Authentication Failed Resolution',
                    '## For IAM Authentication (recommended for MSK):',
                    '1. Check Lambda execution role has MSK permissions:',
                    '   - Use `esm_msk_policy` tool to generate correct IAM policy',
                    '   - Attach policy to Lambda execution role',
                    '2. Verify MSK cluster has IAM authentication enabled:',
                    '   - Check cluster configuration: `aws kafka describe-cluster --cluster-arn <arn>`',
                    '   - Ensure client authentication includes IAM',
                    '3. Check ESM configuration:',
                    '   - Ensure no SASL authentication is configured for IAM mode',
                    '   - Verify ESM is in provisioned mode for IAM authentication',
                    '## For SASL/SCRAM Authentication:',
                    '1. Verify Secrets Manager secret exists and is accessible:',
                    '   - Check secret contains username and password',
                    '   - Verify Lambda execution role can access the secret',
                    '2. Check MSK cluster SASL configuration:',
                    '   - Ensure SASL/SCRAM is enabled on the cluster',
                    '   - Verify user exists in MSK user database',
                    '3. Update ESM configuration with correct authentication settings.',
                ]
            elif kafka_type == 'self-managed':
                issues.append(
                    'Self-managed Kafka authentication failed - SASL or mTLS authentication issues.'
                )
                resolutions['steps'] = [
                    '# Self-Managed Kafka Authentication Failed Resolution',
                    '## For SASL/SCRAM Authentication:',
                    '1. Verify Secrets Manager secret configuration:',
                    '   - Check secret contains correct username and password',
                    '   - Verify Lambda execution role can access the secret',
                    '   - Ensure secret is in same region as Lambda function',
                    '2. Check Kafka broker SASL configuration:',
                    '   - Verify SASL/SCRAM is enabled on brokers',
                    '   - Check user exists in Kafka user database',
                    '   - Verify user has appropriate ACL permissions',
                    '## For SASL/PLAIN Authentication:',
                    '1. Similar to SASL/SCRAM but check PLAIN mechanism is enabled',
                    '## For mTLS Authentication:',
                    '1. Verify client certificate configuration:',
                    '   - Check certificate is valid and not expired',
                    '   - Verify certificate is signed by trusted CA',
                    '   - Ensure private key matches certificate',
                    '2. Check Kafka broker TLS configuration:',
                    '   - Verify SSL is enabled and properly configured',
                    '   - Check CA certificate is configured on brokers',
                    '3. Update ESM configuration with correct certificate settings.',
                ]
            else:  # auto-detect
                issues.append(
                    'Kafka authentication failed. Resolution depends on authentication method and Kafka type.'
                )
                resolutions['steps'] = [
                    '# General Authentication Failed Resolution',
                    '1. Determine authentication method from ESM configuration',
                    '2. For MSK: Use IAM authentication (recommended) or SASL/SCRAM',
                    '3. For self-managed: Use SASL/SCRAM, SASL/PLAIN, or mTLS',
                    '4. Use specific kafka_type for detailed authentication resolution steps.',
                ]

        # Handle network connectivity issues - different requirements for MSK vs self-managed
        elif issue_type == 'network-connectivity':
            if kafka_type == 'msk':
                issues.append('MSK ESM network connectivity issues - cannot reach AWS services.')
                resolutions['steps'] = [
                    '# MSK Network Connectivity Resolution',
                    '## ESM inherits MSK cluster VPC configuration:',
                    '1. Check MSK cluster subnets have outbound internet access:',
                    '   - Verify NAT Gateway exists in public subnets',
                    '   - Check route tables for MSK subnets point to NAT Gateway',
                    '2. Create VPC endpoints for AWS services (optional but recommended):',
                    '   - Lambda VPC endpoint for function invocation',
                    '   - STS VPC endpoint for role assumption',
                    '   - Secrets Manager VPC endpoint (if using SASL authentication)',
                    '3. Verify MSK cluster security group allows outbound HTTPS (443):',
                    '   - Add outbound rule for 0.0.0.0/0 on port 443',
                    '4. Check MSK cluster is in private subnets (security best practice)',
                ]
            elif kafka_type == 'self-managed':
                issues.append('Self-managed Kafka ESM network connectivity issues.')
                resolutions['steps'] = [
                    '# Self-Managed Kafka Network Connectivity Resolution',
                    '## ESM uses specified VPC configuration:',
                    '1. Verify ESM subnets have outbound internet access:',
                    '   - Check route tables point to NAT Gateway or Internet Gateway',
                    '   - Ensure NAT Gateway has Elastic IP if using private subnets',
                    '2. Check connectivity between ESM subnets and Kafka brokers:',
                    '   - Verify routing between VPCs (if different VPCs)',
                    '   - Check VPC peering or Transit Gateway configuration',
                    '   - Test connectivity using VPC Reachability Analyzer',
                    '3. Verify ESM security group outbound rules:',
                    '   - Allow outbound to Kafka ports (9092, 9093, 9094, etc.)',
                    '   - Allow outbound HTTPS (443) for AWS service calls',
                    '4. Create VPC endpoints for AWS services (recommended for private subnets):',
                    '   - Lambda VPC endpoint',
                    '   - STS VPC endpoint',
                    '   - Secrets Manager VPC endpoint (if using SASL)',
                    '5. Check Kafka broker security groups allow ESM access',
                ]
            else:  # auto-detect
                issues.append(
                    'Network connectivity issues. Resolution depends on Kafka deployment type.'
                )
                resolutions['steps'] = [
                    '# General Network Connectivity Resolution',
                    '1. Determine if using MSK or self-managed Kafka',
                    '2. For MSK: Focus on MSK cluster VPC configuration',
                    '3. For self-managed: Focus on ESM VPC configuration and cross-VPC connectivity',
                    '4. Use specific kafka_type for detailed network resolution steps.',
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
        # Handle Lambda invocation issues - ESM cannot invoke Lambda or access services
        elif issue_type == 'lambda-unreachable':
            issues.append(
                'The event source mapping can access your Kafka cluster and poll records '
                'successfully, but calls to the Lambda API fail or time out.'
            )

            if kafka_type == 'msk':
                resolutions['steps'] = [
                    '# MSK Lambda Unreachable Resolution',
                    '## Focus on IAM permissions and network connectivity:',
                    '1. Check Lambda execution role permissions:',
                    '   - Use `esm_msk_policy` tool to generate correct IAM policy',
                    '   - Attach policy to Lambda execution role',
                    '2. Verify MSK cluster security group allows outbound Lambda calls:',
                    '   - Add outbound HTTPS (443) rule to 0.0.0.0/0',
                    '3. Check MSK cluster subnets have Lambda service access:',
                    '   - Verify NAT Gateway for outbound internet access',
                    '   - Or create Lambda VPC endpoint in MSK VPC',
                    '4. Update ESM configuration:',
                    '   - Re-activate the trigger',
                    '   - Configure as provisioned mode',
                    '   - Use exact resource ARNs in template',
                ]
            elif kafka_type == 'self-managed':
                resolutions['steps'] = [
                    '# Self-Managed Kafka Lambda Unreachable Resolution',
                    '## Focus on ESM VPC configuration and permissions:',
                    '1. Check Lambda execution role permissions:',
                    '   - Ensure lambda:InvokeFunction permission exists',
                    '   - Add VPC permissions if Lambda is in VPC',
                    '2. Verify ESM subnets can reach Lambda service:',
                    '   - Check route tables for outbound internet access',
                    '   - Verify NAT Gateway or Internet Gateway configuration',
                    '   - Or create Lambda VPC endpoint in ESM VPC',
                    '3. Check ESM security group outbound rules:',
                    '   - Allow outbound HTTPS (443) for Lambda API calls',
                    '4. Verify Lambda function exists and is accessible:',
                    '   - Check function name/ARN in ESM configuration',
                    '   - Verify function is in same region as ESM',
                ]
            else:  # auto-detect
                resolutions['steps'] = [
                    '# General Lambda Unreachable Resolution',
                    '1. Check Lambda execution role has appropriate permissions',
                    '2. Verify network connectivity from ESM to Lambda service',
                    '3. For MSK: Focus on MSK cluster VPC outbound connectivity',
                    '4. For self-managed: Focus on ESM subnet connectivity',
                    '5. Use specific kafka_type for detailed resolution steps.',
                ]

            resolutions['rules'] = [
                'Focus on IAM permissions and network connectivity.',
                'Do NOT modify Lambda function code or configuration.',
                'Ensure ESM can reach Lambda service endpoints.',
            ]
        # Handle failure destination connectivity issues
        elif issue_type == 'on-failure-destination-unreachable':
            issues.append(
                'On-failure destination (S3, SNS, SQS) is configured but calls to the '
                'destination API fail or time out when function invocations end with errors.'
            )

            if kafka_type == 'msk':
                resolutions['steps'] = [
                    '# MSK On-Failure Destination Unreachable Resolution',
                    '1. Create VPC endpoint for destination service in MSK cluster VPC:',
                    '   - S3 VPC endpoint for S3 destinations',
                    '   - SNS VPC endpoint for SNS destinations',
                    '   - SQS VPC endpoint for SQS destinations',
                    '2. Verify MSK cluster subnets have outbound internet access:',
                    '   - Check NAT Gateway configuration',
                    '   - Verify route tables point to NAT Gateway',
                    '3. Check MSK cluster security group allows outbound HTTPS (443)',
                    '4. Verify Lambda execution role has permissions for destination service',
                ]
            elif kafka_type == 'self-managed':
                resolutions['steps'] = [
                    '# Self-Managed Kafka On-Failure Destination Unreachable Resolution',
                    '1. Create VPC endpoint for destination service in ESM VPC:',
                    '   - S3 VPC endpoint for S3 destinations',
                    '   - SNS VPC endpoint for SNS destinations',
                    '   - SQS VPC endpoint for SQS destinations',
                    '2. Verify ESM subnets have outbound internet access:',
                    '   - Check NAT Gateway or Internet Gateway configuration',
                    '   - Verify route tables for outbound connectivity',
                    '3. Check ESM security group allows outbound HTTPS (443)',
                    '4. Verify Lambda execution role has permissions for destination service',
                ]
            else:  # auto-detect
                resolutions['steps'] = [
                    '# General On-Failure Destination Unreachable Resolution',
                    '1. Create VPC endpoints for destination services',
                    '2. Verify outbound internet connectivity from ESM VPC',
                    '3. Check security group outbound rules allow HTTPS',
                    '4. Verify IAM permissions for destination service',
                    '5. Use specific kafka_type for detailed resolution steps.',
                ]

        # Handle STS connectivity issues - ESM cannot assume IAM roles
        elif issue_type == 'sts-unreachable':
            issues.append(
                'The event source mapping is configured in a VPC, and calls to the AWS STS API '
                'fail or timeout during role assumption.'
            )

            if kafka_type == 'msk':
                resolutions['steps'] = [
                    '# MSK STS Unreachable Resolution',
                    '1. Create STS VPC endpoint in MSK cluster VPC:',
                    '   - Ensure endpoint policy allows sts:AssumeRole',
                    '   - Allow lambda.amazonaws.com principal access',
                    '2. Verify MSK cluster subnets have outbound internet access:',
                    '   - Check NAT Gateway configuration for STS API calls',
                    '3. Check Lambda execution role trust policy:',
                    '   - Ensure lambda.amazonaws.com is trusted service',
                    '   - Verify sts:AssumeRole is allowed',
                    '4. Check MSK cluster security group allows outbound HTTPS (443)',
                ]
            elif kafka_type == 'self-managed':
                resolutions['steps'] = [
                    '# Self-Managed Kafka STS Unreachable Resolution',
                    '1. Create STS VPC endpoint in ESM VPC:',
                    '   - Ensure endpoint policy allows sts:AssumeRole',
                    '   - Allow lambda.amazonaws.com principal access',
                    '2. Verify ESM subnets have outbound internet access:',
                    '   - Check NAT Gateway or Internet Gateway for STS API calls',
                    '3. Check Lambda execution role trust policy:',
                    '   - Ensure lambda.amazonaws.com is trusted service',
                    '   - Verify sts:AssumeRole is allowed',
                    '4. Check ESM security group allows outbound HTTPS (443)',
                ]
            else:  # auto-detect
                resolutions['steps'] = [
                    '# General STS Unreachable Resolution',
                    '1. Create STS VPC endpoint with proper policies',
                    '2. Verify outbound internet connectivity for STS API',
                    '3. Check Lambda execution role trust policy',
                    '4. Verify security group outbound rules',
                    '5. Use specific kafka_type for detailed resolution steps.',
                ]
        # Fallback case for unrecognized or general issues
        else:
            issues.append(f'Unknown issue type: {issue_type}')
            if kafka_type == 'msk':
                resolutions['steps'] = [
                    'Please refer to MSK-specific documentation:',
                    'https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html',
                    'https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster',
                    'https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html',
                ]
            elif kafka_type == 'self-managed':
                resolutions['steps'] = [
                    'Please refer to self-managed Kafka documentation:',
                    'https://docs.aws.amazon.com/lambda/latest/dg/with-kafka.html',
                    'https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-troubleshoot.html',
                    'https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-create-package.html',
                ]
            else:
                resolutions['steps'] = [
                    'Please refer to general Kafka ESM documentation:',
                    'MSK: https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html',
                    'Self-managed: https://docs.aws.amazon.com/lambda/latest/dg/with-kafka-troubleshoot.html',
                ]

        # Always require user confirmation before making changes to prevent accidental modifications
        next_actions = [
            'CRITICAL: Ask user for explicit confirmation before any deployment or infrastructure changes',
            'Required confirmation: "Do you want to apply these troubleshooting fixes to your AWS infrastructure?"',
            'Use sam_deploy tool ONLY after user confirms the changes',
        ]

        response = {
            'response': {
                'issues': issues,
                'resolutions': resolutions,
                'base_requirements': base_requirements,
                'next_actions': next_actions,
            }
        }

        # No need to scrub resolution data as it contains no sensitive information
        return response
