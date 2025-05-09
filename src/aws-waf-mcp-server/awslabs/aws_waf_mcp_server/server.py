import boto3
import os
from mcp.server.fastmcp import FastMCP
from typing import List, Optional


# Initialize FastMCP server
mcp = FastMCP('aws_waf')

session = boto3.Session(
    profile_name=os.getenv('AWS_PROFILE'), region_name=os.getenv('AWS_DEAFULT_REGION')
)

# clients

global_wafv2_client = None


def get_wafv2_client():
    """Get a WAFv2 client for the specified region.

    Returns:
        boto3.client: WAFv2 client
    """
    session = boto3.Session(
        profile_name=os.getenv('AWS_PROFILE'), region_name=os.getenv('AWS_DEAFULT_REGION')
    )
    return session.client('wafv2')


global_elbv2_client = None


def get_elbv2_client():
    """Get a WAFv2 client for the specified region.

    Returns:
        boto3.client: WAFv2 client
    """
    session = boto3.Session(
        profile_name=os.getenv('AWS_PROFILE'), region_name=os.getenv('AWS_DEAFULT_REGION')
    )
    return session.client('elbv2')


@mcp.tool()
async def create_waf_acl(name, json_rules_acl, wafv2_client=None) -> dict:
    """Creates a WAFv2 Web ACL (Web Application Firewall Access Control List) with specified rules.

    When creating rules, follow these steps:
    Follow this steps
    1. Group rules into group rules as much as possible
    2. Follow this order in priority
    * Blocked lists
    * Allowed lists
    * Amazon IP reputation lists
    * Amazon Anonymous IP list
    * AWS baseline managed rule groups
    Then use
    - Core rule set
    - Known bad inputs rule group
    Then use AWS use case specific rule groups
    - For example Linux OS rule group
    Then use Rate based rules
    Then use Intelligent bot threath mitigation rulegroups
    - Bot control rule set
    - Account takeover prevention
    - Account creation Fraud prevention
    - Use scope down statements

    Args:
        name (str): The name of the Web ACL to be created. This name must be unique within the scope
                   and will be used to generate the CloudWatch metric name.
        json_rules_acl (list): A list of rule objects that define the security rules for the Web ACL.
                              Each rule should contain statements for matching web requests and actions
                              to take when requests match.
        wafv2_client (boto3.client): Override the client for unit tests.

    Returns:
        str: Response containing the result and the created Web ACL ARN if successful

    Raises:
        Exception: If there's an error during Web ACL creation, including:
                  - WAFLimitsExceededException: If you exceed the maximum number of Web ACLs
                  - WAFInvalidParameterException: If any parameter is malformed
                  - WAFDuplicateItemException: If the ACL name already exists
                  - Other AWS WAF-related exceptions

    Example:
        rules = [
            {
                'Name': 'RateLimit',
                'Priority': 1,
                'Statement': {
                    'RateBasedStatement': {
                        'Limit': 2000,
                        'AggregateKeyType': 'IP'
                    }
                },
                'Action': {
                    'Block': {}
                },
                'VisibilityConfig': {
                    'SampledRequestsEnabled': True,
                    'CloudWatchMetricsEnabled': True,
                    'MetricName': 'RateLimitRule'
                }
            }
        ]

        response = await create_waf_acl('MyWebACL', rules)
    """
    # Init WAFv2 client
    global global_wafv2_client
    if wafv2_client is None:
        if global_wafv2_client is None:
            global_wafv2_client = get_wafv2_client()
        wafv2_client = global_wafv2_client

    try:
        # Create Web ACL
        response = wafv2_client.create_web_acl(
            Name=name,
            Scope='REGIONAL',  # Use 'CLOUDFRONT' for CloudFront distributions
            Description='Created by MCP',
            DefaultAction={
                'Allow': {}  # Default action to allow requests
            },
            Rules=json_rules_acl,
            VisibilityConfig={
                'SampledRequestsEnabled': False,
                'CloudWatchMetricsEnabled': True,
                'MetricName': f'{name}Metric',
            },
        )

        return f'Web ACL created. ARN is {response["Summary"]["ARN"]}'

    except Exception as e:
        return f'Error creating Web ACL: {str(e)}'


@mcp.tool()
async def associate_web_acl_to_alb(web_acl_arn, alb_arn, wafv2_client=None) -> dict:
    """Associates an AWS WAF web ACL with an Application Load Balancer.

    This function creates a connection between a WAF web ACL and an ALB, enabling
    the web ACL to filter traffic going to the specified load balancer.

    Args:
        web_acl_arn (str): The Amazon Resource Name (ARN) of the WAF web ACL.
            Format: arn:aws:wafv2:region:account-id:regional/webacl/name/id
        alb_arn (str): The ARN of the Application Load Balancer.
            Format: arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/name/id
        wafv2_client (boto3.client): Override the client. For unit tests only

    Returns:
        dict: The response from the AWS WAF service containing details of the association.
              An empty response indicates a successful association.

    Raises:
        WAFInvalidParameterException: If either ARN is malformed or invalid
        WAFNonexistentItemException: If either the web ACL or ALB doesn't exist
        WAFInternalErrorException: If AWS WAF experiences an internal error
        WAFLimitsExceededException: If you've reached the maximum number of web ACL associations
        Exception: Any other unexpected errors during the association process

    Example:
        web_acl_arn = "arn:aws:wafv2:us-west-2:123456789012:regional/webacl/mywebacl/abcd1234"
        alb_arn = "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-alb/1234567890"

        try:
            response = await associate_web_acl_to_alb(web_acl_arn, alb_arn)
            print("Web ACL successfully associated with ALB")
        except Exception as e:
            print(f"Failed to associate Web ACL: {str(e)}")

    Note:
        - Only one web ACL can be associated with an ALB at a time
        - The web ACL and ALB must be in the same region
        - This operation requires appropriate IAM permissions for WAF and ELB services
    """
    # Init WAFv2 client
    global global_wafv2_client
    if wafv2_client is None:
        if global_wafv2_client is None:
            global_wafv2_client = get_wafv2_client()
        wafv2_client = global_wafv2_client
    try:
        wafv2_client.associate_web_acl(WebACLArn=web_acl_arn, ResourceArn=alb_arn)
        return 'Web ACL associated'
    except Exception as e:
        return f'Error associating Web ACL: {str(e)}'


@mcp.tool()
async def get_application_load_balancer_arn_by_name(alb_name, elbv2_client=None) -> str:
    """Retrieves the Amazon Resource Name (ARN) of an Application Load Balancer by its name.

    Args:
        alb_name (str): The name of the Application Load Balancer to look up.
            Must be the exact name as it appears in AWS.
        elbv2_client (boto3.client): Override the client. For unit tests only

    Returns:
        str: The ARN of the Application Load Balancer in the format:
            arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/name/id
            or the error description

    Example:
        try:
            alb_arn = await get_application_load_balancer_arn_by_name('my-load-balancer')
            print(f"Found ALB ARN: {alb_arn}")
        except Exception as e:
            print(f"Failed to get ALB ARN: {str(e)}")

    Note:
        - The function assumes the ALB exists in the current AWS region
        - The AWS credentials must have elasticloadbalancing:DescribeLoadBalancers permission
        - Only returns the first matching ALB if multiple exist with the same name
    """
    global global_elbv2_client
    if elbv2_client is None:
        if global_elbv2_client is None:
            global_elbv2_client = get_elbv2_client()
        elbv2_client = global_elbv2_client

    try:
        # Describe load balancers with the specified name
        response = elbv2_client.describe_load_balancers(Names=[alb_name])

        # Get the ARN from the first (and should be only) load balancer
        if response['LoadBalancers']:
            return response['LoadBalancers'][0]['LoadBalancerArn']
        else:
            return f'No ALB found with name: {alb_name}'

    except elbv2_client.exceptions.LoadBalancerNotFoundException:
        return f'Load balancer not found: {alb_name}'
    except Exception as e:
        return f'Error getting ALB ARN: {str(e)}'


@mcp.tool()
async def create_ip_set(
    name: str,
    ip_addresses: List[str],
    ip_version: str = 'IPV4',
    description: Optional[str] = None,
    scope: str = 'REGIONAL',
    wafv2_client=None,
) -> dict:
    """Creates an IP set in AWS WAFv2.

    Args:
        name (str): Name of the IP set
        ip_addresses (List[str]): List of IP addresses in CIDR notation
        ip_version (str): IP address version (IPV4 or IPV6)
        description (str, optional): Description for the IP set
        scope (str): Scope of the IP set (REGIONAL or CLOUDFRONT)
        wafv2_client (boto3.client): Override the client. For unit tests only

    Returns:
        dict: Response from the AWS WAF service containing the IP set details

    Example:
        ip_addresses = ['192.0.2.0/24', '198.51.100.0/24']
        response = create_ip_set(
            name='test-ipset',
            ip_addresses=ip_addresses,
            description='Block specific IP ranges'
        )
    """
    # Init WAFv2 client
    global global_wafv2_client
    if wafv2_client is None:
        if global_wafv2_client is None:
            global_wafv2_client = get_wafv2_client()
        wafv2_client = global_wafv2_client
    try:
        # Create the IP set
        create_params = {
            'Name': name,
            'Scope': scope,
            'IPAddressVersion': ip_version,
            'Addresses': ip_addresses,
        }

        # Add description if provided
        if description:
            create_params['Description'] = description

        response = wafv2_client.create_ip_set(**create_params)

        print(f'Successfully created IP set: {name}')
        return response

    except wafv2_client.exceptions.WAFDuplicateItemException:
        print(f'An IP set with the name {name} already exists')
        raise
    except wafv2_client.exceptions.WAFLimitsExceededException:
        print('You have exceeded the maximum number of IP sets for your account')
        raise
    except wafv2_client.exceptions.WAFInvalidParameterException as e:
        print(f'Invalid parameter: {str(e)}')
        raise
    except Exception as e:
        print(f'Error creating IP set: {str(e)}')
        raise


if __name__ == '__main__':
    # Initialize and run the server
    mcp.run(transport='stdio')
