# AWS CloudWAN MCP Server

An MCP server that provides comprehensive AWS CloudWAN network analysis and troubleshooting capabilities.

## Overview

The AWS CloudWAN MCP Server enables AI assistants to analyze, troubleshoot, and manage AWS CloudWAN networks through natural language interactions. With 17 specialized tools, it provides complete visibility into CloudWAN infrastructure, path tracing, network function group (NFG) analysis, and policy validation.

## Features

- **🔍 Network Path Tracing** - Trace network paths between IP addresses with detailed hop analysis
- **📊 Core Network Management** - List and analyze CloudWAN core networks and segments  
- **🔧 Network Function Groups** - Comprehensive NFG analysis and troubleshooting
- **🌐 Multi-Region Discovery** - Discover VPCs and network resources across AWS regions
- **📝 Policy Validation** - Validate CloudWAN policies and configurations
- **🚦 Transit Gateway Integration** - Manage TGW routes and analyze peering
- **⚡ Real-time Analysis** - Live network troubleshooting and diagnostics
- **🏆 100% Test Coverage** - 172/172 tests passing with comprehensive validation

## Prerequisites

Before installing and using the AWS CloudWAN MCP Server, ensure you have:

### Required Software
- **Python 3.11+** - Required for running the MCP server
- **uv** or **uvx** - Recommended package manager ([install guide](https://docs.astral.sh/uv/))
- **Git** - For installation from source

### AWS Requirements
- **AWS CLI** configured with appropriate credentials
- **AWS CloudWAN** deployed in your AWS account
- **IAM Permissions** - See [IAM Permissions](#iam-permissions) section below

### Network Infrastructure
- Active **AWS CloudWAN Core Network** in your target regions
- **Transit Gateways** (if using TGW integration features)
- **VPC** resources for network discovery and analysis

### MCP Client
One of the following MCP-compatible clients:
- **Claude Desktop** - For conversational AI interactions
- **Claude Code** - For development workflow integration  
- **VS Code MCP Extension** - For IDE integration
- Any MCP-compatible client application

## Installation

> **⚠️ Pre-Release Note**: This package will be published to PyPI by the AWS Labs team. Until then, use the git-based installation method below.

### Using uvx (Recommended - Once Published to PyPI)

```bash
uvx awslabs-cloudwan-mcp-server
```

### Using uv (Once Published to PyPI)

```bash
uv add awslabs-cloudwan-mcp-server
```

### Pre-Release Installation (Current Method)

Until published to PyPI by AWS Labs, install from a local clone of the repository:

#### Step 1: Clone the Repository
```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/cloudwan-mcp-server
```

#### Step 2: Install Locally
```bash
# Using uvx (recommended)
uvx --from /path/to/mcp/src/cloudwan-mcp-server awslabs-cloudwan-mcp-server

# Or using uv
uv add --editable /path/to/mcp/src/cloudwan-mcp-server
```

### Docker

```bash
docker run -e AWS_PROFILE=your-profile -e AWS_DEFAULT_REGION=us-west-2 \
    awslabs/cloudwan-mcp-server:latest
```

## Configuration

Add to your MCP client configuration:

### Claude Desktop

#### Once Published to PyPI:
```json
{
  "mcpServers": {
    "awslabs.cloudwan_mcp_server": {
      "command": "uvx",
      "args": ["awslabs-cloudwan-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

#### Pre-Release (Current):
```json
{
  "mcpServers": {
    "awslabs.cloudwan_mcp_server": {
      "command": "uvx",
      "args": [
        "--from",
        "/path/to/mcp/src/cloudwan-mcp-server",
        "awslabs-cloudwan-mcp-server"
      ],
      "cwd": "/path/to/mcp/src/cloudwan-mcp-server",
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

### Claude Code

#### Once Published to PyPI:
```json
{
  "$schema": "https://schema.modelcontextprotocol.io/mcp.json",
  "mcpServers": {
    "awslabs.cloudwan_mcp_server": {
      "command": "uvx",
      "args": ["awslabs-cloudwan-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile", 
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

#### Pre-Release (Current):
```json
{
  "$schema": "https://schema.modelcontextprotocol.io/mcp.json",
  "mcpServers": {
    "awslabs.cloudwan_mcp_server": {
      "command": "uvx",
      "args": [
        "--from", 
        "/path/to/mcp/src/cloudwan-mcp-server", 
        "awslabs-cloudwan-mcp-server"
      ],
      "cwd": "/path/to/mcp/src/cloudwan-mcp-server",
      "env": {
        "AWS_PROFILE": "your-aws-profile", 
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

### VS Code MCP Extension

#### Once Published to PyPI:
```json
{
  "mcp": {
    "servers": {
      "awslabs.cloudwan_mcp_server": {
        "command": "uvx",
        "args": ["awslabs-cloudwan-mcp-server"],
        "env": {
          "AWS_PROFILE": "your-profile",
          "AWS_DEFAULT_REGION": "us-west-2"
        }
      }
    }
  }
}
```

#### Pre-Release (Current):
```json
{
  "mcp": {
    "servers": {
      "awslabs.cloudwan_mcp_server": {
        "command": "uvx",
        "args": [
          "--from", 
          "/path/to/mcp/src/cloudwan-mcp-server", 
          "awslabs-cloudwan-mcp-server"
        ],
        "cwd": "/path/to/mcp/src/cloudwan-mcp-server",
        "env": {
          "AWS_PROFILE": "your-profile",
          "AWS_DEFAULT_REGION": "us-west-2"
        }
      }
    }
  }
}
```

## Available Tools

The CloudWAN MCP Server provides 17 specialized tools:

### Network Analysis Tools
- **`trace_network_path`** - Trace network paths between IP addresses
- **`discover_ip_details`** - Enhanced IP address analysis with comprehensive AWS networking context including ENI associations, subnet/VPC details, routing tables, security groups, and associated resources
- **`validate_ip_cidr`** - Validate IP addresses and CIDR blocks

### Core Network Management
- **`get_global_networks`** - List available global network resources
- **`list_core_networks`** - List and analyze CloudWAN core networks
- **`get_core_network_policy`** - Retrieve core network policy documents
- **`get_core_network_change_set`** - Get policy change sets
- **`get_core_network_change_events`** - Retrieve policy change events

### Network Function Groups (NFG)
- **`list_network_function_groups`** - List available network function groups
- **`analyze_network_function_group`** - Detailed NFG analysis and configuration

### Segment & Route Analysis
- **`analyze_segment_routes`** - Analyze CloudWAN segment routing
- **`discover_vpcs`** - Discover VPCs across regions
- **`validate_cloudwan_policy`** - Validate CloudWAN policy configurations

### Transit Gateway Integration
- **`analyze_tgw_routes`** - Analyze Transit Gateway routes
- **`analyze_tgw_peers`** - Analyze TGW peering relationships
- **`manage_tgw_routes`** - Manage Transit Gateway routes

### Configuration Management
- **`aws_config_manager`** - Manage AWS configuration and profiles

## IAM Permissions

The following AWS IAM permissions are required:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "networkmanager:*",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets", 
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRegions",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:DescribeTransitGatewayPeeringAttachments",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

**Enhanced Permissions Note**: The additional EC2 permissions (`DescribeRouteTables`, `DescribeSecurityGroups`, `DescribeInstances`) are required for the enhanced `discover_ip_details` function to provide comprehensive networking context including route table analysis, security group rules, and associated AWS resource details.

## Environment Variables

- **`AWS_PROFILE`** (required) - AWS profile with CloudWAN permissions
- **`AWS_DEFAULT_REGION`** (required) - Primary AWS region
- **`CLOUDWAN_MCP_LOG_LEVEL`** (optional) - Logging level (DEBUG, INFO, WARNING, ERROR)
- **`CLOUDWAN_MCP_DEBUG`** (optional) - Enable debug logging (true/false)

## Usage Examples

### Network Troubleshooting
```
"Trace the network path from 10.1.51.65 to 100.69.1.106 and identify any issues"
```

### Core Network Analysis
```
"List all CloudWAN core networks and show their current status"
```

### Policy Validation
```
"Validate the CloudWAN policy for core-network-12345 and check for compliance issues"
```

### NFG Analysis
```
"Analyze the network function group 'production-nfg' and show its configuration"
```

### VPC Discovery
```
"Discover all VPCs in us-west-2 and us-east-1 regions and show their CloudWAN attachments"
```

### Enhanced IP Details Discovery
```
"Analyze IP address 10.1.51.65 and provide comprehensive AWS networking context"
```

**Enhanced Response Example:**
The `discover_ip_details` function now returns comprehensive networking information:

```json
{
  "success": true,
  "ip_address": "10.1.51.65",
  "region": "us-west-2",
  "ip_version": 4,
  "is_private": true,
  "is_multicast": false,
  "is_loopback": false,
  "timestamp": "2025-01-15T10:30:45.123456",
  "aws_networking_context": {
    "eni_details": {
      "eni_found": true,
      "eni_id": "eni-0123456789abcdef0",
      "eni_type": "interface",
      "subnet_id": "subnet-0abcdef1234567890",
      "vpc_id": "vpc-0123456789abcdef0",
      "availability_zone": "us-west-2a",
      "security_groups": ["sg-0123456789abcdef0", "sg-0987654321fedcba0"],
      "attachment": {
        "AttachmentId": "eni-attach-0123456789abcdef0",
        "InstanceId": "i-0123456789abcdef0",
        "Status": "attached"
      },
      "status": "in-use"
    },
    "routing_context": {
      "route_table_found": true,
      "route_table_id": "rtb-0123456789abcdef0",
      "routes": [
        {
          "DestinationCidrBlock": "10.0.0.0/16",
          "GatewayId": "local",
          "State": "active"
        },
        {
          "DestinationCidrBlock": "0.0.0.0/0",
          "TransitGatewayId": "tgw-0123456789abcdef0",
          "State": "active"
        }
      ]
    },
    "security_groups": {
      "security_groups_found": true,
      "security_groups": [
        {
          "group_id": "sg-0123456789abcdef0",
          "group_name": "web-tier-sg",
          "description": "Security group for web tier",
          "ingress_rules": [
            {
              "IpProtocol": "tcp",
              "FromPort": 80,
              "ToPort": 80,
              "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            }
          ],
          "egress_rules": [
            {
              "IpProtocol": "-1",
              "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            }
          ]
        }
      ],
      "total_count": 2
    },
    "associated_resources": {
      "resources_found": true,
      "instance_id": "i-0123456789abcdef0",
      "instance_type": "t3.medium",
      "instance_state": "running",
      "platform": "linux",
      "launch_time": "2025-01-15T09:00:00.000000",
      "tags": [
        {
          "Key": "Name",
          "Value": "WebServer-01"
        },
        {
          "Key": "Environment",
          "Value": "Production"
        }
      ]
    }
  },
  "services_queried": 4,
  "services_successful": 4
}
```

**Key Enhanced Features:**
- **Parallel Execution**: Uses `asyncio.gather()` for optimal performance
- **Comprehensive Context**: ENI details, routing tables, security groups, and associated resources
- **Graceful Degradation**: Returns partial results if some services are unavailable
- **Detailed Diagnostics**: Includes service query metrics and error details

## API Reference

### `discover_ip_details` Enhanced Response Schema

The enhanced `discover_ip_details` function returns a comprehensive JSON response with the following structure:

#### Base Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the operation completed successfully |
| `ip_address` | string | The analyzed IP address |
| `region` | string | AWS region used for the analysis |
| `ip_version` | integer | IP version (4 or 6) |
| `is_private` | boolean | Whether the IP is in private address space |
| `is_multicast` | boolean | Whether the IP is a multicast address |
| `is_loopback` | boolean | Whether the IP is a loopback address |
| `timestamp` | string | ISO 8601 timestamp when analysis was performed |

#### AWS Networking Context Fields
The `aws_networking_context` object contains four main sections:

##### ENI Details (`eni_details`)
| Field | Type | Description |
|-------|------|-------------|
| `eni_found` | boolean | Whether an ENI was found for this IP |
| `eni_id` | string | ENI identifier (if found) |
| `eni_type` | string | Type of network interface |
| `subnet_id` | string | Associated subnet ID |
| `vpc_id` | string | Associated VPC ID |
| `availability_zone` | string | AZ where the ENI is located |
| `security_groups` | array | List of security group IDs |
| `attachment` | object | ENI attachment details |
| `status` | string | Current ENI status |

##### Routing Context (`routing_context`)
| Field | Type | Description |
|-------|------|-------------|
| `route_table_found` | boolean | Whether route table was found |
| `route_table_id` | string | Route table identifier |
| `routes` | array | Array of route entries |
| `associations` | array | Route table associations |
| `propagating_vgws` | array | Virtual gateways propagating routes |

##### Security Groups (`security_groups`)
| Field | Type | Description |
|-------|------|-------------|
| `security_groups_found` | boolean | Whether security groups were found |
| `security_groups` | array | Array of security group details |
| `total_count` | integer | Number of security groups |

Each security group object contains:
- `group_id`: Security group ID
- `group_name`: Human-readable name
- `description`: Security group description  
- `ingress_rules`: Array of inbound rules
- `egress_rules`: Array of outbound rules
- `vpc_id`: Associated VPC ID

##### Associated Resources (`associated_resources`)
| Field | Type | Description |
|-------|------|-------------|
| `resources_found` | boolean | Whether associated resources were found |
| `instance_id` | string | EC2 instance ID (if attached) |
| `instance_type` | string | EC2 instance type |
| `instance_state` | string | Current instance state |
| `platform` | string | Operating system platform |
| `launch_time` | string | Instance launch timestamp |
| `tags` | array | Array of instance tags |

#### Service Query Metrics
| Field | Type | Description |
|-------|------|-------------|
| `services_queried` | integer | Total number of AWS services queried |
| `services_successful` | integer | Number of successful service responses |

#### Error Handling
When IP discovery fails or no AWS resources are found, the response includes:
- Descriptive error messages in the `message` field
- `possible_reasons` array explaining potential causes
- Partial results from successful service queries (graceful degradation)

## Troubleshooting

### Common Issues and Solutions

#### Authentication Errors
```bash
# Problem: "Unable to locate credentials"
# Solution: Configure AWS credentials
aws configure
# or set environment variables
export AWS_PROFILE=your-profile
export AWS_DEFAULT_REGION=us-west-2
```

#### MCP Connection Issues
```bash
# Problem: "MCP server failed to start"
# Solution: Verify installation and Python version
python --version  # Should be 3.11+
uvx --from git+https://github.com/awslabs/mcp.git#subdirectory=src/cloudwan-mcp-server cloudwan-mcp-server --version
```

#### Permission Errors
```bash
# Problem: "User is not authorized to perform..."
# Solution: Check IAM permissions in the IAM Permissions section
# Ensure your user/role has the necessary CloudWAN, EC2, and NetworkManager permissions
```

#### No CloudWAN Resources Found
```
# Problem: "No core networks found"
# Check: Verify CloudWAN is deployed in the target region
# Verify: Your AWS credentials have access to the CloudWAN resources
# Try: List regions and check other regions where CloudWAN might be deployed
```

#### Slow Performance or Timeouts
```bash
# Solution 1: Use custom endpoints for testing
export CLOUDWAN_AWS_CUSTOM_ENDPOINTS='{"networkmanager": "https://networkmanager.us-west-2.amazonaws.com"}'

# Solution 2: Check network connectivity and AWS service health
aws networkmanager list-core-networks --region us-west-2
```

#### IP Discovery Issues

##### ENI Not Found for IP Address
```bash
# Problem: "No AWS network interface found for this IP address"
# Possible Causes:
# 1. IP is not associated with an AWS resource
# 2. Insufficient permissions to view network interfaces  
# 3. IP is from a different AWS account or region

# Solutions:
# Check if IP exists in current region
aws ec2 describe-network-interfaces --filters "Name=addresses.private-ip-address,Values=10.1.51.65"

# Check public IP associations
aws ec2 describe-network-interfaces --filters "Name=association.public-ip,Values=203.0.113.1"

# Verify in different regions
for region in us-east-1 us-west-2 eu-west-1; do
  echo "Checking region: $region"
  aws ec2 describe-network-interfaces --region $region --filters "Name=addresses.private-ip-address,Values=10.1.51.65"
done
```

##### Partial Context Information
```bash
# Problem: "Some services returned incomplete information"
# This indicates graceful degradation - some AWS services responded but others failed

# Check specific service permissions:
# For routing context:
aws ec2 describe-route-tables --region us-west-2

# For security groups:
aws ec2 describe-security-groups --region us-west-2  

# For instance details:
aws ec2 describe-instances --region us-west-2
```

##### Permission Denied for Enhanced Features
```bash
# Problem: "User is not authorized to perform ec2:DescribeRouteTables/DescribeSecurityGroups/DescribeInstances"
# Solution: Ensure your IAM policy includes the enhanced permissions listed in the IAM Permissions section

# Test individual permissions:
aws ec2 describe-route-tables --region us-west-2 --dry-run
aws ec2 describe-security-groups --region us-west-2 --dry-run  
aws ec2 describe-instances --region us-west-2 --dry-run
```

### Debug Mode
Enable detailed logging for troubleshooting:
```bash
export PYTHONPATH=/path/to/cloudwan-mcp-server
export MCP_DEBUG=1
export CLOUDWAN_MCP_DEBUG=true
```

### Getting Help
- Check the [Issues](https://github.com/awslabs/mcp/issues) for known problems
- Review AWS CloudWAN documentation for infrastructure setup
- Verify your CloudWAN policy configuration
- Test with basic AWS CLI commands to confirm connectivity

## Testing

The CloudWAN MCP Server includes comprehensive testing with **100% test coverage**:

- **172 total tests** with **100% pass rate**
- Unit tests with realistic mock fixtures  
- Integration testing with AWS services
- Security validation and error handling
- AWS Labs compliance validation

Run tests:

```bash
uv run pytest --cov --cov-report=term-missing
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/cloudwan-mcp-server
uv sync --all-groups
```

### Run Server Locally

```bash
uv run python -m awslabs.cloudwan_mcp_server
```

### Code Quality

```bash
uv run ruff check .
uv run pyright .
```

## Architecture

The server is built with a modular architecture:

- **Thread-safe LRU caching** for optimal performance
- **Comprehensive error handling** with detailed diagnostics  
- **Multi-region support** for global CloudWAN deployments
- **Extensible tool framework** for easy enhancement
- **Production-ready logging** and monitoring

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/awslabs/mcp/issues) page.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) file for details on how to get started.