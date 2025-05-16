import boto3
import os
import pytest
import sys
from moto import mock_aws


# Set the script on PATH to avoid import errors for the awslabs.aws_waf_mcp_server.server file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
print(SCRIPT_DIR)
sys.path.append(os.path.dirname(SCRIPT_DIR))

# Import the functions to test
from awslabs.aws_waf_mcp_server.server import (
    associate_web_acl_to_alb,
    create_ip_set,
    create_waf_acl,
    get_application_load_balancer_arn_by_name,
)


# Constants
IP_SET_NAME = 'IP_TEST_MOCK'
ALB_NAME = 'ALB_TEST_MOCK'
WEB_ACL_NAME = 'WAF_ACL_TEST_MOCK'
IP_SET_NAME_IP_ADDRESSES = ['192.0.2.0/24', '192.0.3.0/24']
WEB_ACL_JSON_RULES = [
    # Rule 1: Rate limiting rule
    {
        'Name': 'RateLimitRule',
        'Priority': 1,
        'Statement': {
            'RateBasedStatement': {
                'Limit': 2000,  # Number of requests per 5 minutes
                'AggregateKeyType': 'IP',
            }
        },
        'Action': {'Block': {}},
        'VisibilityConfig': {
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': f'{WEB_ACL_NAME}-RateLimit',
        },
    },
    # Rule 2: Block requests with specific headers
    {
        'Name': 'BlockMaliciousHeaders',
        'Priority': 2,
        'Statement': {
            'ByteMatchStatement': {
                'SearchString': 'malicious-header-value',
                'FieldToMatch': {'SingleHeader': {'Name': 'x-custom-header'}},
                'TextTransformations': [{'Priority': 1, 'Type': 'NONE'}],
                'PositionalConstraint': 'EXACTLY',
            }
        },
        'Action': {'Block': {}},
        'VisibilityConfig': {
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': f'{WEB_ACL_NAME}-MaliciousHeaders',
        },
    },
]


# Configure mock objects for AWS API
mock = mock_aws()
mock.start()
wafv2_client = boto3.client('wafv2')
elbv2_client = boto3.client('elbv2')
ec2_client = boto3.client('ec2')


class TestWafMcpServer:
    """Test suite for WAF MCP Server functionality.

    This class contains test cases for WAF Web ACL creation, association with ALB,
    and IP set management operations.
    """

    @pytest.mark.asyncio
    async def test_create_waf_acl(self):
        """Test successful creation of a WAF Web ACL.

        This test verifies that:
        1. The function returns a response dictionary.
        2. The response contains the expected Web ACL name.
        3. The response includes confirmation of creation.
        4. The test mock identifier is present in the response.

        Returns:
            None
        """
        response = await create_waf_acl(
            WEB_ACL_NAME, WEB_ACL_JSON_RULES, wafv2_client=wafv2_client
        )
        # Verify the response
        assert isinstance(response, str)
        assert 'Web ACL created' in response
        assert 'TEST_MOCK' in response

    @pytest.mark.asyncio
    async def test_create_waf_acl_invalid_input(self):
        """Test WAF ACL creation with invalid input parameters.

        Verifies that the function properly handles invalid inputs by:
        1. Attempting to create a WAF ACL with empty name
        2. Attempting to create a WAF ACL with empty rules
        3. Checking for appropriate error message in response

        Returns:
            None
        """
        name = ''  # Invalid name
        rules = ''  # Invalid rules

        response = await create_waf_acl(name, rules, wafv2_client)
        assert 'Error creating Web ACL' in response

    @pytest.mark.asyncio
    async def test_associate_web_acl_to_alb(self):
        """Test association between WAF ACL and Application Load Balancer.

        This test:
        1. Creates a new WAF ACL
        2. Creates a new Application Load Balancer
        3. Associates the WAF ACL with the ALB
        4. Verifies the association is successful

        Returns:
            None
        """
        await create_waf_acl(WEB_ACL_NAME, WEB_ACL_JSON_RULES, wafv2_client=wafv2_client)
        alb_arn = elbv2_client.create_load_balancer(
            Name=ALB_NAME, Subnets=[ec2_client.describe_subnets()['Subnets'][0]['SubnetId']]
        )['LoadBalancers'][0]['LoadBalancerArn']
        web_acl_arn = wafv2_client.list_web_acls(Scope='REGIONAL')['WebACLs'][0]['ARN']
        response = await associate_web_acl_to_alb(web_acl_arn, alb_arn, wafv2_client)
        assert response == 'Web ACL associated'

    @pytest.mark.asyncio
    async def test_get_application_load_balancer_arn_by_name(self):
        """Test retrieval of Application Load Balancer ARN using its name.

        Verifies that:
        1. The correct ALB ARN is retrieved when given a valid ALB name
        2. The retrieved ARN matches the expected ARN from the describe_load_balancers call

        Returns:
            None
        """
        alb_arn = elbv2_client.describe_load_balancers()['LoadBalancers'][0]['LoadBalancerArn']
        arn = await get_application_load_balancer_arn_by_name(ALB_NAME, elbv2_client)
        assert alb_arn == arn

    @pytest.mark.asyncio
    async def test_get_alb_arn_not_found(self):
        """Test error handling when retrieving non-existent ALB ARN.

        Verifies that:
        1. Appropriate error message is returned when ALB name doesn't exist
        2. Function handles the not-found case gracefully

        Returns:
            None
        """
        response = await get_application_load_balancer_arn_by_name(
            'non-existent-alb', elbv2_client
        )
        assert 'Load balancer not found' in response

    @pytest.mark.asyncio
    async def test_create_ip_set_success(self):
        """Test successful creation of an IP set in WAF.

        This test verifies:
        1. IP set creation with multiple CIDR ranges
        2. Correct response structure is returned
        3. IP set name matches the provided name
        4. Response contains expected summary information

        Args:
            None

        Returns:
            None
        """
        ip_addresses = ['192.0.2.0/24', '192.0.3.0/24']
        response = await create_ip_set(
            name=IP_SET_NAME,
            ip_addresses=ip_addresses,
            description='Test IP set',
            wafv2_client=wafv2_client,
        )
        assert isinstance(response, dict)
        assert response['Summary']['Name'] == IP_SET_NAME
