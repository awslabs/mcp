# AWS Core Network MCP Server

A Model Context Protocol (MCP) server providing comprehensive tools for troubleshooting and analyzing AWS core networking services including Cloud WAN, Transit Gateway, VPC, Network Firewall, and VPN connections.

### Key Features

- **Systematic troubleshooting**: Built-in methodology for network path tracing and connectivity analysis
- **Multi-service coverage**: Unified interface for Cloud WAN, Transit Gateway, VPC, Network Firewall, and VPN
- **Flow log analysis**: Query and filter VPC, Transit Gateway, and Network Firewall flow logs from CloudWatch
- **Inspection detection**: Automatically identify firewalls in traffic paths for security analysis
- **Multi-region support**: Search for resources across all AWS regions
- **Read-only operations**: Safe troubleshooting without risk of configuration changes

### AWS Core Network capabilities

- **Path tracing**: Systematic methodology for analyzing network connectivity issues
- **IP discovery**: Locate network interfaces by IP address across regions
- **Security analysis**: Examine security groups, NACLs, and firewall rules
- **Routing analysis**: Trace traffic paths through VPC, Transit Gateway, and Cloud WAN
- **Traffic verification**: Query flow logs to confirm actual traffic patterns
- **Inspection detection**: Identify AWS Network Firewall and third-party firewalls in traffic paths

### Tools

#### General Tools
1. `get_path_trace_methodology`: Get comprehensive network troubleshooting methodology (ALWAYS call this first)
2. `find_ip_address`: Locate ENI by IP address with multi-region search support
3. `get_eni_details`: Get comprehensive ENI details including security groups, NACLs, and routing

#### Cloud WAN Tools
4. `list_core_networks`: List all Cloud WAN core networks in a region
5. `get_cloudwan_details`: Get comprehensive core network configuration and state
6. `get_cloudwan_routes`: Get routes for specific segment and region
7. `get_all_cloudwan_routes`: Get all routing tables across all segments and regions
8. `get_cloudwan_attachment_details`: Get detailed attachment information by type
9. `detect_cloudwan_inspection`: Detect Network Function Groups performing inspection
10. `list_cloudwan_peerings`: List all Transit Gateway peerings for a core network
11. `get_cloudwan_peering_details`: Get peering details from both Cloud WAN and TGW perspectives
12. `get_cloudwan_logs`: Retrieve event logs for topology changes and routing updates
13. `simulate_cloud_wan_route_change`: Simulate network changes for a single region

#### Transit Gateway Tools
14. `list_transit_gateways`: List all Transit Gateways in a region
15. `get_tgw_details`: Get basic Transit Gateway configuration and operational details
16. `get_tgw_routes`: Get routes from specific route table with filtering
17. `get_all_tgw_routes`: Get all route tables and routes in one call
18. `get_tgw_flow_logs`: Retrieve Transit Gateway flow logs from CloudWatch
19. `list_tgw_peerings`: List all Transit Gateway peerings
20. `detect_tgw_inspection`: Detect AWS Network Firewall and third-party firewalls attached to TGW

#### VPC Tools
21. `list_vpcs`: List all VPCs in a region
22. `get_vpc_network_details`: Get comprehensive VPC network configuration
23. `get_vpc_flow_logs`: Get VPC flow logs from CloudWatch with filtering

#### Network Firewall Tools
24. `list_network_firewalls`: List all AWS Network Firewalls in a region
25. `get_firewall_rules`: Get stateless and stateful firewall rules
26. `get_network_firewall_flow_logs`: Retrieve firewall flow logs from CloudWatch

#### VPN Tools
27. `list_vpn_connections`: List all Site-to-Site VPN connections in a region

## Prerequisites
- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using uv python install 3.10 (or a more recent version)
- This MCP server can only be run locally on the same host as your LLM client.

## Configuration

You can download the AWS Network MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Kiro, Cursor, or Cline.

```json
{
  "mcpServers": {
    "awslabs.aws-network-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-network-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-west-2"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-network-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-network-mcp-server@latest",
        "awslabs.aws-network-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### AWS Authentication

Preferred authentication method is [AWS Named Profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). This MCP is able to do fast account switching by using named profiles.

AWS Credentials in environment variables will also work but allows only single account usage.

#### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkAcls",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeVpcEndpoints",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayAttachments",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:DescribeTransitGatewayPeeringAttachments",
        "ec2:DescribeVpnConnections",
        "ec2:DescribeFlowLogs",
        "ec2:DescribeRegions",
        "networkmanager:GetCoreNetwork",
        "networkmanager:GetCoreNetworkPolicy",
        "networkmanager:GetNetworkRoutes",
        "networkmanager:GetVpcAttachment",
        "networkmanager:GetConnectAttachment",
        "networkmanager:GetDirectConnectGatewayAttachment",
        "networkmanager:GetSiteToSiteVpnAttachment",
        "networkmanager:GetTransitGatewayRouteTableAttachment",
        "networkmanager:GetTransitGatewayPeering",
        "networkmanager:GetTransitGatewayRegistrations",
        "networkmanager:GetTransitGatewayRouteTableAssociations",
        "networkmanager:ListCoreNetworks",
        "networkmanager:ListAttachments",
        "networkmanager:ListPeerings",
        "network-firewall:DescribeFirewall",
        "network-firewall:DescribeFirewallPolicy",
        "network-firewall:DescribeRuleGroup",
        "network-firewall:DescribeLoggingConfiguration",
        "network-firewall:ListFirewalls",
        "elasticloadbalancing:DescribeLoadBalancers",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Multi-Account Access

Use the `profile_name` parameter in tools to specify different AWS CLI profiles for cross-account access. Some tools support separate profiles for different resources (e.g., `tgw_account_profile_name` and `cloudwan_account_profile_name`).

### Data Usage

This MCP server operates entirely locally and makes direct API calls to AWS services. No data is sent to third-party services. All AWS API calls are subject to AWS service terms and your organization's AWS policies.

### FAQs

#### 1. Do I need an AWS account?

Yes. This server makes API calls to AWS services and requires valid AWS credentials with appropriate IAM permissions.

#### 2. What AWS regions are supported?

All AWS commercial regions are supported. Tools that support multi-region search (like `find_ip_address`) can search across all enabled regions in your account.

#### 3. Why do some tools require Network Manager registration?

Transit Gateway route tools (`get_tgw_routes`, `get_all_tgw_routes`) require the Transit Gateway to be registered with AWS Network Manager (Cloud WAN Global Network). This is an AWS requirement for accessing route table information via the Network Manager API.

#### 4. Do flow log tools work without CloudWatch Logs?

No. Flow log tools (`get_vpc_flow_logs`, `get_tgw_flow_logs`, `get_network_firewall_flow_logs`) require that flow logging is enabled and configured to send logs to CloudWatch Logs (not S3 or Kinesis Data Firehose).

#### 5. Can this server make changes to my AWS infrastructure?

No. All tools are read-only and only perform Describe, Get, and List operations. The server cannot create, modify, or delete any AWS resources.

#### 6. How do I troubleshoot "No flow logs found" errors?

Verify that:
- Flow logging is enabled on the resource (VPC, Transit Gateway, or Network Firewall)
- Logs are configured to send to CloudWatch Logs
- The time range includes periods when traffic was flowing
- Your IAM permissions include `logs:FilterLogEvents`
