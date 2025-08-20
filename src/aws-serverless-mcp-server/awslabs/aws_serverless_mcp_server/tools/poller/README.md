# ESM MCP Server - Event Source Mapping Model Context Protocol Server

## Overview

The ESM MCP Server is a Model Context Protocol (MCP) server that provides comprehensive management of AWS Event Source Mappings (ESM) between Amazon Managed Streaming for Apache Kafka (MSK) clusters, Self-Managed Kafka (SMK) clusters, and AWS Lambda functions. This server implements the MCP specification to enable AI agents to help customers create, update, delete, and manage MSK/SMK-Lambda integrations through a standardized interface.

## Architecture

### Core Components

The server is built using FastMCP and consists of several key modules:

- **AutoShutdownServer**: Extended FastMCP server with automatic shutdown after 1 hour of inactivity to prevent indefinite resource usage
- **CreateEventSourceMapping**: Tool for creating new ESM connections between MSK clusters and Lambda functions
- **UpdateEventSourceMapping**: Tool for modifying existing ESM configurations
- **DeleteEventSourceMapping**: Tool for removing ESM connections
- **ListEventSourceMapping**: Tool for querying and displaying existing ESM configurations
- **IAMHelper**: Utility for managing IAM permissions required for MSK-Lambda integration, with SASL/TLS authentication support
- **MCPValidator**: Tool for validating Lambda function processing by monitoring ESM state changes
- **MCPProducer**: Tool for producing test messages to Kafka topics for ESM validation
- **RoleCreator**: Helper for creating and managing IAM roles (referenced but not fully implemented)

### Authentication and Configuration

The server uses AWS credentials from environment variables:
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key  
- `AWS_REGION`: AWS region (required - no default)

All tools initialize boto3 clients with these credentials and validate connectivity during initialization.

## Available Tools

### create_event_source_mapping

Creates a new Event Source Mapping between an MSK/SMK cluster and Lambda function.

**Required Parameters:**
- `target`: Lambda function name or ARN
- `kafka_topic`: Kafka topic name
- Either `event_source_arn` (MSK) OR `kafka_bootstrap_servers` (SMK)

**MSK Parameters:**
- `event_source_arn`: MSK cluster ARN

**SMK Parameters:**
- `kafka_bootstrap_servers`: Comma-separated bootstrap server addresses
- `source_access_configurations`: JSON array of authentication/VPC configs

**Optional Parameters:**
- `batch_size`: Records per batch (1-10000, default 100)
- `starting_position`: LATEST, TRIM_HORIZON, or AT_TIMESTAMP
- `kafka_consumer_group_id`: Consumer group identifier
- `max_batching_window`: Batching window in seconds (0-300)
- `enabled`: Enable/disable the mapping (default true)
- `min_pollers`/`max_pollers`: Provisioned concurrency settings (default 1/2)
- `report_batch_item_failures`: Enable partial failure reporting
- `retry_attempts`: Maximum retry attempts (0-10000)
- `bisect_batch_on_error`: Split batches on error
- `max_record_age`: Maximum record age in seconds (60-604800)
- `tumbling_window`: Tumbling window duration (0-900 seconds)

**Automatic Features:**
- Automatically adds required MSK permissions to Lambda execution role
- Handles IAM policy creation for VPC, Kafka cluster access, and networking permissions
- Provides detailed error handling for resource conflicts

### add_msk_permissions

Adds necessary MSK permissions to a Lambda function's execution role.

**Parameters:**
- `function_name`: Lambda function name or ARN

**Permissions Added:**
- Kafka cluster operations (describe, get bootstrap brokers)
- Kafka cluster data access (connect, read/write data, topic operations)
- VPC networking permissions for MSK in VPC environments

### update_event_source_mapping

Updates existing Event Source Mapping configurations.

**Update Methods:**
1. By UUID: Direct update using mapping UUID
2. By function and source: Finds mapping by Lambda function and MSK cluster ARN

**Updatable Parameters:**
- Batch processing settings (batch_size, max_batching_window)
- Error handling (bisect_batch_on_error, retry_attempts, max_record_age)
- State management (enabled/disabled)
- Provisioned concurrency (min_pollers, max_pollers)
- Response handling (report_batch_item_failures)
- Windowing (tumbling_window)

### delete_event_source_mapping

Removes Event Source Mappings.

**Deletion Methods:**
1. By UUID: Direct deletion using mapping UUID
2. By function and source: Finds and deletes mapping by Lambda function and MSK cluster ARN

**Optional Parameters:**
- `kafka_topic`: Additional filter for topic-specific deletion

### list_event_source_mappings

Queries and displays existing Event Source Mappings.

**Query Methods:**
1. List all MSK-related mappings in the account
2. List mappings for specific Lambda function
3. List mappings for specific MSK cluster

**Response Format:**
- Formatted mapping details with human-readable information
- Function names extracted from ARNs
- Timestamp formatting
- State and configuration summaries

## Error Handling

The server implements comprehensive error handling:

- **AWS API Errors**: Captures and formats ClientError exceptions with error codes and messages
- **Credential Issues**: Validates AWS credentials during initialization
- **Resource Conflicts**: Handles existing mapping conflicts with UUID extraction
- **Validation Errors**: Validates required parameters before API calls
- **Permission Warnings**: Continues operation if IAM permission updates fail

## Auto-Shutdown Feature

The server includes an automatic shutdown mechanism:
- Monitors activity with 1-hour idle timeout
- Updates activity timestamp on each tool invocation
- Background thread monitors idle time and shuts down server when timeout exceeded
- Prevents indefinite server execution and resource waste

## Usage Patterns

### Creating MSK-Lambda Integration

1. Use `create_event_source_mapping` with Lambda function, MSK cluster ARN, and topic
2. Server automatically handles IAM permissions
3. Returns mapping UUID and status information

### Managing Existing Mappings

1. Use `list_event_source_mappings` to discover existing mappings
2. Use `update_event_source_mapping` to modify configurations
3. Use `delete_event_source_mapping` to remove mappings

### Testing MSK-Lambda Integration

1. Use `MCPValidator.get_initial_offset()` to capture initial Lambda state
2. Use `MCPProducer.produce_messages()` to send test messages to Kafka topic
3. Use `MCPValidator.check_offset_after_production()` to verify Lambda processed messages
4. Use `IAMHelper.test_kafka_connection()` to validate authentication configurations

### Troubleshooting

1. Check IAM permissions using `add_msk_permissions`
2. Verify mapping status with `list_event_source_mappings`
3. Test Kafka connectivity using `IAMHelper.test_kafka_connection()`
4. Validate message processing using `MCPValidator` tools
5. Review error messages for AWS API issues or configuration problems

## Testing and Validation Tools

### MCPValidator

Validates Lambda function processing by monitoring Event Source Mapping state changes.

**Key Methods:**
- `get_initial_offset()`: Captures Lambda ESM state before message production
- `check_offset_after_production()`: Compares state after waiting (default 30 seconds) to detect processing
- `validate_esm_processing()`: Complete validation flow combining both methods

**Usage Pattern:**
1. Get initial Lambda ESM state
2. Produce test messages using MCPProducer
3. Wait for processing (configurable, default 30 seconds)
4. Check for state changes indicating message processing

### MCPProducer

Produces test messages to Kafka topics for ESM validation testing.

**Key Methods:**
- `create_producer()`: Creates Kafka producer with authentication support
- `generate_test_message()`: Creates messages of specified size with test metadata
- `produce_messages()`: Sends X messages of Y size to specified topic

**Message Features:**
- Configurable message count and size
- Unique message IDs and timestamps
- Sequence numbering for tracking
- Partitioning support via message keys

**Authentication Support:**
- PLAINTEXT (no authentication)
- SSL (TLS encryption)
- SASL_SSL with SCRAM-SHA-256/512
- Mutual TLS with client certificates

### Enhanced IAMHelper Authentication

Extended with SASL and TLS support for comprehensive MSK authentication testing.

**New Methods:**
- `get_secret_from_arn()`: Retrieves secrets from AWS Secrets Manager with fallback to manual input
- `prompt_for_credentials()`: Interactive credential input when secrets aren't accessible
- `get_msk_bootstrap_brokers()`: Gets MSK bootstrap brokers for different authentication types
- `test_kafka_connection()`: Tests Kafka connectivity with various authentication methods

**Supported Authentication Types:**
- **SASL_SCRAM_256_AUTH**: SASL SCRAM-SHA-256 authentication
- **SASL_SCRAM_512_AUTH**: SASL SCRAM-SHA-512 authentication  
- **CLIENT_CERTIFICATE_TLS_AUTH**: Mutual TLS with client certificates
- **SERVER_ROOT_CA_CERTIFICATE**: TLS with custom CA certificates
- **BASIC_AUTH**: Username/password authentication for self-managed Kafka

**Secret Management:**
- Automatic retrieval from AWS Secrets Manager
- Interactive fallback when secrets are inaccessible
- Secure password input using getpass module
- Support for certificate-based authentication

### Enhanced ESM Testing

ESM_Testing now supports dynamic configuration discovery:

**Configuration Sources (in priority order):**
1. **Secret ARN**: Pass a secret ARN containing full MSK configuration
2. **ESM Discovery**: Automatically extracts config from existing ESM
3. **Manual Input**: Session-only prompts for missing configuration

**Supported Secret Structure:**
```json
{
    "iam": {
        "bootstrap_servers": "broker1:9098,broker2:9098",
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "AWS_MSK_IAM"
    },
    "sasl": {
        "bootstrap_servers": "broker1:9096,broker2:9096",
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "SCRAM-SHA-512",
        "sasl_plain_username": "username",
        "sasl_plain_password": "password"
    },
    "topic": "your-topic-name",
    "cluster_arn": "arn:aws:kafka:region:account:cluster/name/uuid"
}
```

**Session-Only Storage:**
- All manually entered configuration is stored only for the current session
- No persistent storage of sensitive information
- Clear user messaging about temporary storage

## Dependencies

- `boto3>=1.34.0`: AWS SDK for Python
- `mcp>=1.0.0`: Model Context Protocol framework
- `botocore>=1.34.0`: AWS SDK core library
- `kafka-python>=2.0.2`: Kafka client library for testing and validation

## Configuration Requirements

### AWS Permissions

The server requires AWS credentials with permissions for:
- Lambda function management (get function, create/update/delete event source mappings)
- IAM role and policy management (get role, put role policy)
- MSK cluster access (describe cluster, get bootstrap brokers)
- VPC networking (describe security groups, subnets, network interfaces)
- Secrets Manager access (get secret value) for authentication credentials
- Kafka cluster operations for testing and validation

### Environment Setup

Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=your_region
```

**Note:** AWS_REGION is now required and has no default value. The server will use the region from your AWS configuration.

## Implementation Notes

### CDK-Inspired Design

The tools are designed to mirror AWS CDK EventSourceMapping construct behavior:
- Automatic IAM permission management
- Comprehensive parameter support
- Error handling and validation
- Resource lifecycle management

### Provisioned Concurrency

The server supports MSK provisioned concurrency settings:
- Minimum and maximum poller configuration
- Default values (1 minimum, 2 maximum pollers)
- Configurable through create and update operations

### Topic Management

- Single topic per mapping (follows AWS Lambda ESM limitations)
- Topic filtering in list and delete operations
- Topic validation during mapping creation

## MSK vs SMK Parameter Support

### Common Parameters (Both MSK and SMK)
- `FunctionName`, `Topics`, `BatchSize`, `MaximumBatchingWindowInSeconds`
- `StartingPosition`, `StartingPositionTimestamp`, `MaximumRetryAttempts`
- `Enabled`, `FunctionResponseTypes`, `ProvisionedPollerConfig`
- `DestinationConfig` (OnFailure/OnSuccess destinations)

### MSK-Specific Parameters
- `EventSourceArn`: MSK cluster ARN
- `AmazonManagedKafkaEventSourceConfig`: MSK consumer group and schema registry

### SMK-Specific Parameters
- `SelfManagedEventSource`: Bootstrap servers configuration
- `SelfManagedKafkaEventSourceConfig`: SMK consumer group and schema registry
- `SourceAccessConfigurations`: Authentication and VPC settings
  - `SASL_SCRAM_256_AUTH` / `SASL_SCRAM_512_AUTH`
  - `CLIENT_CERTIFICATE_TLS_AUTH` (mTLS)
  - `VPC_SUBNET` / `VPC_SECURITY_GROUP`
  - `BASIC_AUTH`, `SERVER_ROOT_CA_CERTIFICATE`

### Stream-Only Parameters (NOT for Kafka)
- `BisectBatchOnFunctionError`: Only for Kinesis and DynamoDB
- `MaximumRecordAgeInSeconds`: Only for Kinesis and DynamoDB
- `TumblingWindowInSeconds`: Only for Kinesis and DynamoDB
- `ParallelizationFactor`: Only for Kinesis and DynamoDB

### Smart Detection
When both MSK ARN and SMK bootstrap servers are provided, the server prompts for clarification to avoid ambiguity.

This server enables AI agents to provide comprehensive MSK/SMK-Lambda integration support, handling the complexity of AWS Event Source Mapping management while providing clear, actionable responses to customer queries.