# AWS IoT SiteWise MCP Server

## Overview

A comprehensive MCP (Model Context Protocol) server that provides full AWS IoT SiteWise functionality for industrial IoT asset management, data ingestion, monitoring, and analytics. This server enables AI assistants to interact with AWS IoT SiteWise through a rich set of tools and prompts.

## Features

### Core AWS IoT SiteWise Capabilities

#### 🏭 Asset Management

- **Asset Creation & Management**: Create, update, delete, and describe industrial assets
- **Asset Hierarchies**: Associate and disassociate assets in hierarchical structures
- **Asset Models**: Define and manage asset models with properties, hierarchies, and composite models
- **Asset Properties**: Manage measurements, attributes, transforms, and metrics

#### 📊 Data Operations

- **Data Ingestion**: Batch and real-time data ingestion with quality indicators
- **Historical Data**: Retrieve time-series data with flexible time ranges and filtering
- **Aggregations**: Calculate averages, sums, counts, min/max, and standard deviations
- **Interpolation**: Get interpolated values for missing data points
- **Batch Operations**: Efficient bulk data operations for multiple assets

#### 🌐 Gateway & Connectivity

- **Gateway Management**: Create and configure IoT SiteWise Edge gateways
- **Capability Configuration**: Manage gateway capabilities for different protocols
- **Time Series Management**: Associate and manage time series data streams
- **Edge Computing**: Support for local data processing and intermittent connectivity

#### 📦 Bulk Operations & Metadata Transfer

- **Bulk Export**: Export ALL IoT SiteWise resources (asset models, assets, etc.) in one operation using metadata transfer jobs
- **Bulk Import Schema**: Create and validate structured schemas for bulk asset/model imports
- **Metadata Transfer Jobs**: Manage large-scale data migration between S3 and IoT SiteWise
- **Job Monitoring**: Track progress and status of bulk operations
- **Multi-Source Support**: Transfer data between S3 buckets and IoT SiteWise
- **Schema Validation**: Ensure data integrity with comprehensive validation before import

#### 🤖 Anomaly Detection & Computation Models

- **Anomaly Detection Models**: Create and manage ML-powered anomaly detection for industrial assets
- **Computation Models**: Define custom data processing and analytics logic for asset properties
- **Training & Inference**: Execute training jobs and real-time inference for anomaly detection
- **Model Versioning**: Manage multiple versions of trained models with automatic promotion
- **Automated Retraining**: Set up scheduled retraining to adapt to changing operational patterns
- **Asset & Asset Model Level Configuration**: Flexible binding to specific assets or reusable across asset models
- **Execution Monitoring**: Track training progress, inference status, and model performance
- **Action Management**: Execute, monitor, and manage actions on computation models and assets

#### 🔒 Security & Configuration

- **Access Policies**: Fine-grained access control for users and resources
- **Encryption**: Configure default encryption settings with KMS integration
- **Logging**: Comprehensive logging configuration and management
- **Storage Configuration**: Multi-layer storage with hot and warm tiers

### Intelligent Prompts

#### 🔍 Asset Hierarchy Visualization

Comprehensive analysis and visualization of asset hierarchies including:

- Complete hierarchy tree diagrams
- Property analysis and current values
- Health checks and status monitoring
- Optimization recommendations

#### 📥 Data Ingestion Helper

Step-by-step guidance for setting up data ingestion:

- Asset model design recommendations
- Gateway configuration templates
- Data mapping strategies
- Performance optimization tips

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-iot-sitewise-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlvdC1zaXRld2lzZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IoT%20SiteWise%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iot-sitewise-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### Prerequisites

- Python 3.10 or higher
- AWS credentials configured for IoT SiteWise access

### Option 1: UVX (Recommended)

```bash
# Install UV if you don't have it yet
curl -sSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iot-sitewise-mcp-server

# Install as a uv tool (this makes it available globally via uvx)
uv tool install .

# The server is now available globally via uvx
uvx awslabs.aws-iot-sitewise-mcp-server
# use @latest flag for automatically pull updates on server
uvx awslabs.aws-iot-sitewise-mcp-server@latest

# Note: The server runs silently, waiting for MCP client connections.
# You'll need to configure an MCP client to connect to it.
```

### Option 2: Pip

```bash
# Install from PyPI (when published)
pip install awslabs.aws-iot-sitewise-mcp-server

# Or install from source
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iot-sitewise-mcp-server
pip install .

# Run the server
python -m awslabs.aws_iot_sitewise_mcp_server.server
```

### AWS Configuration

Configure AWS credentials with permissions for:
- AWS IoT SiteWise (full access for write operations)
- AWS IoT TwinMaker (for metadata transfer operations)
- Amazon S3 (for bulk import/export operations)

```bash
# AWS CLI (recommended)
aws configure

# Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2

# Or use AWS profiles
export AWS_PROFILE=your-profile-name
```

### Usage with MCP Clients

#### Claude Desktop

Add to your `claude_desktop_config.json`:

**Option 1: UVX (Recommended) - Read-Only Mode**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 1: UVX with Write Operations Enabled**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: Direct Python Execution - Read-Only Mode**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: Direct Python with Write Operations Enabled**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

#### Claude Code

Configure in your workspace or global settings:

**Option 1: UVX (Recommended) - Read-Only Mode**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 1: UVX with Write Operations Enabled**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: Direct Python Execution - Read-Only Mode**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: Direct Python with Write Operations Enabled**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**Notes:**

- Replace `your-profile-name` with your actual AWS profile name, or remove the `AWS_PROFILE` line to use default credentials
- The UVX option is recommended as it's cleaner and doesn't require path configuration
- For development workflows, see [development guidelines](https://github.com/awslabs/mcp/blob/main/DEVELOPER_GUIDE.md)

## Tools Reference

### Asset Management Tools

| Tool Name | Description |
|-----------|-------------|
| `create_asset` | Create a new asset from an asset model |
| `describe_asset` | Get detailed asset information |
| `list_assets` | List assets with filtering options |
| `update_asset` | Update asset properties |
| `delete_asset` | Delete an asset |
| `associate_assets` | Create parent-child relationships |
| `disassociate_assets` | Remove asset relationships |
| `list_associated_assets` | List related assets |

### Asset Model Management Tools

| Tool Name | Description |
|-----------|-------------|
| `create_asset_model` | Create asset model definitions |
| `describe_asset_model` | Get asset model details |
| `list_asset_models` | List available asset models |
| `update_asset_model` | Modify asset model properties |
| `delete_asset_model` | Remove asset models |
| `list_asset_model_properties` | List model properties |
| `create_asset_model_composite_model` | Create composite models |

### Data Operations Tools

| Tool Name | Description |
|-----------|-------------|
| `batch_put_asset_property_value` | Ingest data in batches |
| `get_asset_property_value` | Get current property values |
| `get_asset_property_value_history` | Retrieve historical data |
| `get_asset_property_aggregates` | Calculate aggregated values |
| `get_interpl_asset_property_values` | Get interpolated data |
| `batch_get_asset_property_value` | Bulk current value retrieval |
| `batch_get_asset_property_value_hist` | Bulk historical data |
| `batch_get_asset_property_aggregates` | Bulk aggregations |
| `create_bulk_import_job` | Create bulk import jobs for bulk data ingestion |
| `create_buffered_ingestion_job` | Create buffered ingestion jobs |
| `create_bulk_import_iam_role` | Create IAM roles for bulk import operations |
| `list_bulk_import_jobs` | List bulk import jobs |
| `describe_bulk_import_job` | Retrieve bulk import job information |
| `execute_query` | Execute SQL-like queries for advanced analytics |

### Gateway & Time Series Tools

| Tool Name | Description |
|-----------|-------------|
| `create_gateway` | Create IoT SiteWise Edge gateways |
| `describe_gateway` | Get gateway information |
| `list_gateways` | List available gateways |
| `update_gateway` | Modify gateway settings |
| `delete_gateway` | Remove gateways |
| `describe_gateway_capability_config` | Get capability config |
| `update_gateway_capability_config` | Update capabilities |
| `list_time_series` | List time series data streams |
| `describe_time_series` | Get time series details |
| `link_time_series_asset_property` | Link data streams |
| `unlink_time_series_asset_property` | Unlink streams |
| `delete_time_series` | Remove time series |

### Computation Models & Anomaly Detection Tools

| Tool Name | Description |
|-----------|-------------|
| `create_computation_model` | Create generic computation models with custom configuration and data bindings - supports Asset Model Level (reusable) and Asset Level (specific) configurations |
| `create_anomaly_detection_model` | **🤖 SPECIALIZED TOOL** - Create anomaly detection models with simplified configuration |
| `describe_computation_model` | Get detailed computation model information including action definitions |
| `list_computation_models` | List computation models with optional filtering by type |
| `update_computation_model` | Update computation model configuration, data bindings, and metadata |
| `delete_computation_model` | Delete computation models (irreversible operation) |
| `describe_computation_model_execution_summary` | Get execution summary with intelligent configuration detection - automatically handles Asset Model vs Asset Level configurations, with smart resolve parameter usage and optional performance optimization |
| `list_computation_model_data_binding_usages` | Find computation models using specific assets or properties |
| `list_computation_model_resolve_to_resources` | List resources that computation models resolve to - shows specific assets associated through resolve-to relationships |

### Action & Execution Management Tools

| Tool Name | Description |
|-----------|-------------|
| `execute_action` | Execute generic actions on target resources (assets or computation models) - supports training, inference |
| `execute_training_action` | **🎯 SPECIALIZED TOOL** - Execute training actions for anomaly detection models |
| `execute_inference_action` | **🎯 SPECIALIZED TOOL** - Execute inference actions for real-time anomaly detection |
| `list_actions` | List actions for specific target resources with filtering options |
| `describe_action` | Get detailed action information including payload and execution details |
| `list_executions` | List executions for actions with status and progress tracking |
| `describe_execution` | Get detailed execution information including results and error details |

### Metadata Transfer & Bulk Import Tools

| Tool Name | Description |
|-----------|-------------|
| `create_bulk_import_schema` | Construct and validate bulk import schemas for asset models and assets |
| `create_metadata_transfer_job` | **🚀 PRIMARY TOOL for bulk export/import operations** - Use this for exporting all resources |
| `cancel_metadata_transfer_job` | Cancel running metadata transfer jobs |
| `get_metadata_transfer_job` | Get detailed information about metadata transfer jobs |
| `list_metadata_transfer_jobs` | List metadata transfer jobs with filtering options |

### Access Control & Configuration Tools

| Tool Name | Description |
|-----------|-------------|
| `create_access_policy` | Create access control policies |
| `describe_access_policy` | Get policy details |
| `list_access_policies` | List access policies |
| `update_access_policy` | Modify access permissions |
| `delete_access_policy` | Remove access policies |
| `describe_default_encryption_config` | Get encryption settings |
| `put_default_encryption_configuration` | Configure encryption |
| `describe_logging_options` | Get logging configuration |
| `put_logging_options` | Configure logging |
| `describe_storage_configuration` | Get storage settings |
| `put_storage_configuration` | Configure storage tiers |

## Prompts Reference

### Asset Hierarchy Visualization

```example
/prompts get asset_hierarchy_visualization_prompt <asset_id>
```

Provides comprehensive analysis of asset hierarchies including tree diagrams, property analysis, and health checks.

### Data Ingestion Helper

```example
/prompts get data_ingestion_helper_prompt <data_source> <target_assets>
```

Step-by-step guidance for setting up industrial data ingestion with best practices and examples.

### Data Exploration Helper

```example
/prompts get data_exploration_helper_prompt <exploration_goal> <time_range>
```

Comprehensive guidance for exploring IoT data using the executeQuery API with SQL-like analytics capabilities.

### Bulk Import Workflow

```example
/prompts get bulk_import_workflow_helper_prompt
```

Step-by-step guidance for setting up bulk data import from S3, including CSV validation, IAM role creation, job configuration, and monitoring.

### Anomaly Detection Workflow

```example
/prompts get anomaly_detection_workflow_helper_prompt
```

Comprehensive guide for setting up anomaly detection in AWS IoT SiteWise, including:

- **Configuration Strategy**: Choose between Asset Model Level (reusable across assets) or Asset Level (specific asset bindings)
- **Asset & Property Discovery**: Step-by-step guidance for identifying input properties and result storage
- **Model Creation**: Create anomaly detection computation models with proper data bindings
- **Training Execution**: Configure and execute training jobs with historical data, sampling rates, and evaluation options
- **Inference Setup**: Start real-time anomaly detection with configurable frequency and operating windows
- **Automated Retraining**: Set up scheduled retraining to adapt to changing operational patterns
- **Monitoring & Results**: Track anomaly scores, model performance, and execution status
- **Best Practices**: Optimization strategies, troubleshooting guidance, and operational recommendations

## Usage Examples

### Creating an Asset Model and Asset

```python
# Create an asset model for a wind turbine
asset_model = sitewise_create_asset_model(
    asset_model_name="WindTurbineModel",
    asset_model_description="Model for wind turbine assets",
    asset_model_properties=[
        {
            "name": "WindSpeed",
            "dataType": "DOUBLE",
            "unit": "m/s",
            "type": {
                "measurement": {}
            }
        },
        {
            "name": "PowerOutput",
            "dataType": "DOUBLE",
            "unit": "kW",
            "type": {
                "measurement": {}
            }
        }
    ]
)

# Create an asset from the model
asset = sitewise_create_asset(
    asset_name="WindTurbine001",
    asset_model_id=asset_model["asset_model_id"],
    asset_description="Wind turbine #001 in the north field"
)
```

### Ingesting Data

```python
# Ingest real-time data
entries = [
    {
        "entryId": "entry1",
        "assetId": asset["asset_id"],
        "propertyId": "wind_speed_property_id",
        "propertyValues": [
            {
                "value": {"doubleValue": 12.5},
                "timestamp": {"timeInSeconds": 1640995200},
                "quality": "GOOD"
            }
        ]
    }
]

result = sitewise_batch_put_asset_property_value(entries=entries)
```

### Setting Up Anomaly Detection

```python
# Create an anomaly detection model for pump monitoring
anomaly_model = create_anomaly_detection_model(
    computation_model_name="PumpAnomalyDetection",
    input_properties=[
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "temperature_property_id"}},
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "pressure_property_id"}},
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "vibration_property_id"}}
    ],
    result_property={
        "assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "anomaly_score_property_id"}
    },
    computation_model_description="Detects operational anomalies in industrial pumps using temperature, pressure, and vibration data"
)

# Train the model with historical data
training_result = execute_training_action(
    training_action_definition_id="training_action_id",  # From describe_computation_model
    training_mode="TRAIN_MODEL",
    target_resource={"computationModelId": anomaly_model["computationModelId"]},
    export_data_start_time=1717225200,  # 90 days ago
    export_data_end_time=1722789360,    # Recent data
    target_sampling_rate="PT15M"        # 15-minute intervals
)

# Start real-time inference
inference_result = execute_inference_action(
    inference_action_definition_id="inference_action_id",  # From describe_computation_model
    inference_mode="START",
    target_resource={"computationModelId": anomaly_model["computationModelId"]},
    data_upload_frequency="PT15M",      # Process data every 15 minutes
    weekly_operating_window={
        "monday": ["08:00-17:00"],      # Business hours only
        "tuesday": ["08:00-17:00"],
        "wednesday": ["08:00-17:00"],
        "thursday": ["08:00-17:00"],
        "friday": ["08:00-17:00"]
    },
    inference_time_zone="America/Chicago"
)

# Monitor anomaly scores
anomaly_scores = get_asset_property_value_history(
    asset_id="pump_asset_id",
    property_id="anomaly_score_property_id",
    start_date="2024-11-01T00:00:00Z",
    end_date="2024-11-04T23:59:59Z"
)
```

## Testing and Validation

### Comprehensive Testing Strategy

The AWS IoT SiteWise MCP server includes multiple layers of testing to ensure reliability and API compliance:

#### 1. Parameter Validation

- **Input Validation**: All parameters are validated against AWS IoT SiteWise constraints
- **Format Checking**: Asset names, IDs, and other identifiers follow AWS naming conventions
- **Quota Enforcement**: Service quotas and limits are enforced before API calls
- **Type Safety**: Full type checking with mypy

#### 2. Integration Testing

- **API Constraint Verification**: Tests validate against actual AWS API specifications
- **Error Handling**: Comprehensive error handling for all AWS service exceptions
- **Real-world Scenarios**: Tests include realistic industrial IoT use cases

#### 3. Validation Features

- **Pre-flight Checks**: Parameters validated before AWS API calls
- **Service Quota Awareness**: Built-in knowledge of AWS IoT SiteWise limits
- **Format Validation**: Proper validation of timestamps, ARNs, and other AWS formats
- **Constraint Enforcement**: Enforces character limits, array sizes, and other constraints

### Running Tests

```bash
# Run all tests
pytest

# Run tests with verbose output (shows individual test names)
pytest -v

# Run specific test file
pytest test/test_sitewise_tools.py -v
```

### Resource Cleanup Guarantees

The test suite includes **comprehensive resource cleanup** to prevent AWS resource leaks:

#### Automatic Cleanup Features

- **Context Managers**: All tests use `sitewise_test_resources()` context manager
- **Resource Tracking**: Every created resource is automatically registered for cleanup
- **State Waiting**: Waits for resources to reach deletable states before cleanup
- **Error Handling**: Cleanup continues even if individual deletions fail

#### Emergency Cleanup

- **Signal Handlers**: Cleanup triggered on Ctrl+C or process termination
- **Atexit Handlers**: Cleanup runs even if tests crash unexpectedly
- **Orphan Detection**: Scans for and cleans up resources from previous failed runs
- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Global Registry**: Emergency cleanup registry for process-wide resource tracking

#### Cleanup Order

1. Asset associations and time series associations
2. Dashboards
3. Projects
4. Access policies
5. Time series
6. Assets
7. Gateways
8. Asset models (last, as assets depend on them)

#### Pytest Integration

```python
def test_asset_creation(sitewise_tracker):
    """Test using the pytest fixture for automatic cleanup."""
    # Create asset model
    model_result = create_asset_model(name="TestModel", ...)
    sitewise_tracker.register_asset_model(model_result['asset_model_id'])

    # Create asset
    asset_result = create_asset(name="TestAsset", ...)
    sitewise_tracker.register_asset(asset_result['asset_id'])

    # Test operations...

    # Resources automatically cleaned up when test ends
```

#### Robust Error Handling

- **AWS Credential Validation**: Tests automatically skip if credentials unavailable
- **Service Availability**: Graceful handling of service outages
- **Permission Errors**: Proper handling of access denied scenarios
- **Network Issues**: Retry logic for transient network problems
- **Resource State Conflicts**: Waits for resources to reach appropriate states

### Validation Examples

The server includes comprehensive parameter validation:

```python
# Asset name validation
create_asset("", "model-id")  # ❌ Fails: Empty name
create_asset("a" * 257, "model-id")  # ❌ Fails: Too long
create_asset("asset@invalid", "model-id")  # ❌ Fails: Invalid characters
create_asset("Valid_Asset-Name", "model-id")  # ✅ Passes validation

# Batch size validation
batch_put_asset_property_value([])  # ❌ Fails: Empty batch
batch_put_asset_property_value([...] * 11)  # ❌ Fails: Too many entries
batch_put_asset_property_value([...] * 5)  # ✅ Passes validation

# Service quota awareness
create_asset_model(properties=[...] * 201)  # ❌ Fails: Too many properties
create_asset_model(properties=[...] * 50)   # ✅ Passes validation
```

### Error Handling

All tools provide consistent error handling:

```python
{
    "success": False,
    "error": "Validation error: Asset name cannot exceed 256 characters",
    "error_code": "ValidationException"
}
```

### API Compliance

The implementation is validated against:

- **AWS IoT SiteWise API Reference**: All parameters match official documentation
- **Service Quotas**: Current AWS service limits are enforced
- **Data Formats**: Proper validation of timestamps, ARNs, and identifiers
- **Error Codes**: Consistent with AWS error response patterns
- Use meaningful names and descriptions for assets and properties
- Define appropriate data types and units
- Organize assets in logical hierarchies
- Use composite models for reusable components

### Data Ingestion

- Implement proper error handling and retry logic
- Use batch operations for efficiency
- Include quality indicators with data points
- Plan for data validation and cleansing

### Security
- Use least-privilege access policies
- Enable encryption for sensitive data
- Configure comprehensive logging
- Regular security audits and reviews

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure AWS credentials are properly configured
   - Check IAM permissions for IoT SiteWise operations
   - Verify region settings

2. **Asset Creation Failures**
   - Validate asset model definitions
   - Check for naming conflicts
   - Ensure proper property configurations

3. **Data Ingestion Issues**
   - Verify property aliases and IDs
   - Check timestamp formats
   - Validate data types and ranges

4. **Metadata Transfer Issues**
   - Verify IoT TwinMaker service permissions
   - Check S3 bucket access for source/destination operations
   - Validate bulk import schema format
   - Monitor job status for detailed error messages

5. **Bulk Import Schema Errors**
   - Ensure asset model external IDs are unique
   - Verify property data types match requirements
   - Check hierarchy references are valid
   - Use create_bulk_import_schema tool for validation

### Getting Help

- Check AWS IoT SiteWise documentation
- Review CloudWatch logs for detailed error messages
- Use the diagnostic prompts for troubleshooting guidance

## Contributing

This MCP server is designed to be extensible. To add new functionality:

1. Create new tool functions in the appropriate module
2. Add tool definitions using the `Tool.from_function` pattern
3. Register tools in the main server configuration
4. Update documentation and examples

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-iot-sitewise/LICENSE) file for details.

---

**Built with ❤️ by AWS Gen AI Labs and AWS IoT Sitewise Engineering teams**
