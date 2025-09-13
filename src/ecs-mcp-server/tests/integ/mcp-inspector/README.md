# MCP Inspector ECS Troubleshooting Tools - Integration Test Suite

This directory contains an integration test suite for the ECS troubleshooting tools using the MCP Inspector CLI. The test creates ECS failure scenarios and systematically validates the troubleshooting tools.

## Structure

```
tests/integ/mcp-inspector/
├── scenarios/                          # Test scenarios
│   └── 01_comprehensive_troubleshooting/
│       ├── 01_create.sh                # Creates ECS infrastructure with failures
│       ├── 02_validate.sh              # Tests all 6 troubleshooting tools
│       ├── 03_cleanup.sh               # Cleans up AWS resources
│       ├── description.txt             # Scenario description
│       └── utils/                      # MCP utilities
│           ├── mcp_helpers.sh          # MCP Inspector CLI wrappers
│           └── validation_helpers.sh   # JSON response validation
├── run-tests.sh                        # Main entry point
└── README.md                           # This file
```

## Prerequisites

1. **AWS CLI** installed and configured with appropriate permissions
2. **MCP Inspector CLI**: `uvx pip install mcp-inspector`
3. **MCP Configuration** at `/tmp/mcp-config.json` (see example below)
4. **jq** command-line tool for JSON processing
5. **uv** package manager (required by MCP server)

## MCP Configuration

The test expects your MCP configuration at `/tmp/mcp-config.json` with the format:

```json
{
  "mcpServers": {
    "local-ecs-mcp-server": {
      "disabled": false,
      "timeout": 300,
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server",
        "run",
        "main.py"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO",
        "FASTMCP_LOG_FILE": "/tmp/ecs-mcp-server.log",
        "ALLOW_WRITE": "true",
        "ALLOW_SENSITIVE_DATA": "true"
      }
    }
  }
}
```

## Running the Tests

### Quick Start

To run the complete integration test suite:

```bash
cd src/ecs-mcp-server/tests/integ/mcp-inspector
./run-tests.sh
```

This will:
1. Validate prerequisites
2. Create ECS infrastructure with failure scenarios
3. Wait for failures to develop
4. Test all the troubleshooting tools
5. Clean up all AWS resources
6. Report results

### Individual Script Execution

You can also run each phase individually:

```bash
# Navigate to the scenario directory
cd scenarios/01_comprehensive_troubleshooting

# Phase 1: Create infrastructure
./01_create.sh

# Phase 2: Test all tools (after infrastructure is ready)
./02_validate.sh <cluster-name> <service-name>

# Phase 3: Clean up
./03_cleanup.sh <cluster-name> <service-name>
```

## Available Scenarios

### 01: Comprehensive Troubleshooting
Creates ECS cluster and service with network restrictions and invalid container images to generate multiple failure scenarios. Tests 6 troubleshooting tools via MCP Inspector CLI to validate they return proper JSON responses with diagnostic data.

## Tested Tools

The integration test validates these ECS troubleshooting tools:

### 1. get_ecs_troubleshooting_guidance
- **Purpose**: Initial assessment and troubleshooting guidance
- **Test**: Calls with cluster and service experiencing network issues
- **Validation**: Checks for `cluster_info` and guidance fields

### 2. detect_image_pull_failures
- **Purpose**: Detects container image pull failures
- **Test**: Analyzes task definition with non-existent images
- **Validation**: Checks for `image_issues` and `assessment` fields

### 3. fetch_service_events
- **Purpose**: Retrieves and analyzes ECS service events
- **Test**: Gets events from failing service
- **Validation**: Checks for `service_events` field

### 4. fetch_task_failures
- **Purpose**: Analyzes failed ECS tasks
- **Test**: Finds failed tasks in the cluster
- **Validation**: Checks for `failed_tasks` field

### 5. fetch_task_logs
- **Purpose**: Retrieves CloudWatch logs from ECS tasks
- **Test**: Gets logs from failed containers
- **Validation**: Checks for `log_entries` field

### 6. fetch_network_configuration
- **Purpose**: Analyzes VPC and network configuration
- **Test**: Examines VPC and cluster network setup
- **Validation**: Checks for `network_info` field

## MCP Inspector CLI Commands

The test uses direct MCP Inspector CLI commands in this format:

```bash
mcp-inspector \
  --config /tmp/mcp-config.json \
  --server local-ecs-mcp-server \
  --cli \
  --method tools/call \
  --tool-name ecs_troubleshooting_tool \
  --tool-arg "action=detect_image_pull_failures" \
  --tool-arg 'parameters={"cluster_name":"test-cluster"}'
```

### Manual Cleanup

If tests fail and automatic cleanup doesn't work:

```bash
# List and delete test clusters
aws ecs list-clusters --query 'clusterArns[*]' --output text | grep mcp-integration-test
aws ecs delete-cluster --cluster <cluster-name>

# List and delete test security groups
aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId,GroupName]' | grep mcp-integration-test
aws ec2 delete-security-group --group-id <sg-id>

# List and delete CloudWatch log groups
aws logs describe-log-groups --query 'logGroups[*].logGroupName' | grep mcp-integration-test
aws logs delete-log-group --log-group-name <log-group>
```
