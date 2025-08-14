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

"""Static content for CloudWAN MCP understanding."""

CLOUDWAN_UNDERSTANDING = """
# AWS CloudWAN MCP Server Understanding

This MCP server provides advanced network analysis and troubleshooting tools for AWS CloudWAN environments.

## Available Tools

### Core Network Discovery
- **list_core_networks**: Discover CloudWAN core networks in your AWS account
- **get_global_networks**: List all global networks across regions
- **get_core_network_policy**: Retrieve policy documents for core networks
- **get_core_network_change_set**: Analyze policy change sets
- **get_core_network_change_events**: Track policy change events

### Network Analysis
- **discover_vpcs**: Find VPCs across AWS regions
- **discover_ip_details**: Analyze IP address characteristics
- **validate_ip_cidr**: Validate IP addresses and CIDR blocks
- **trace_network_path**: Trace network paths between endpoints

### Network Function Groups
- **list_network_function_groups**: Discover network function groups
- **analyze_network_function_group**: Analyze NFG policies and performance

### Transit Gateway Operations
- **manage_tgw_routes**: Create, delete, and manage TGW routes
- **analyze_tgw_routes**: Comprehensive TGW route analysis
- **analyze_tgw_peers**: TGW peering connection analysis

### CloudWAN Segment Analysis
- **analyze_segment_routes**: CloudWAN segment routing analysis
- **validate_cloudwan_policy**: Validate CloudWAN policy configurations

## Usage Examples

### Basic Network Discovery
```
# List all core networks
list_core_networks(region="us-east-1")

# Discover VPCs in multiple regions
discover_vpcs(region="us-west-2")
```

### IP and CIDR Validation
```
# Validate IP address
validate_ip_cidr(operation="validate_ip", ip="10.0.1.100")

# Validate CIDR block
validate_ip_cidr(operation="validate_cidr", cidr="10.0.0.0/16")
```

### Transit Gateway Analysis
```
# Analyze TGW routes
analyze_tgw_routes(route_table_id="tgw-rtb-xxxxx", region="us-east-1")

# Manage TGW routes
manage_tgw_routes(operation="create", route_table_id="tgw-rtb-xxxxx", destination_cidr="10.1.0.0/16")
```

## Configuration

Set these environment variables:
- **AWS_DEFAULT_REGION**: Your default AWS region
- **AWS_PROFILE**: AWS profile to use (optional)

## Authentication

This server uses your AWS credentials through:
- AWS profiles configured via `aws configure`
- IAM roles if running on AWS infrastructure
- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

## Required AWS Permissions

The server requires permissions for:
- NetworkManager (CloudWAN operations)
- EC2 (VPC and TGW operations)
- IAM (for cross-account access if needed)

## Error Handling

All tools return JSON responses with:
- **success**: Boolean indicating operation success
- **error**: Error message if operation failed
- **error_code**: AWS error code for debugging

## Performance Notes

- Tools use connection pooling and caching for optimal performance
- Multi-region operations are supported
- Rate limiting is handled automatically
"""
