# Bedrock Advisor MCP Server Configuration Guide

This document provides detailed information about configuring the Bedrock Advisor MCP Server.

## Configuration Overview

The Bedrock Advisor MCP Server supports a flexible configuration system with multiple sources of configuration values, in the following order of precedence (highest to lowest):

1. Environment variables
2. Configuration file
3. Default values

## Configuration File

The server can be configured using a JSON configuration file. By default, the server looks for a configuration file in the following locations:

1. `./config.json` (current directory)
2. `./bedrock_advisor_config.json` (current directory)
3. `~/.bedrock_advisor/config.json` (user's home directory)
4. `/etc/bedrock_advisor/config.json` (system-wide configuration)

You can also specify a custom configuration file path using the `CONFIG_FILE` environment variable:

```bash
CONFIG_FILE=/path/to/config.json bedrock-advisor
```

### Configuration File Format

The configuration file should be in JSON format with the following structure:

```json
{
  "server": {
    "log_level": "INFO",
    "enable_metrics": false
  },
  "aws": {
    "region": "us-east-1",
    "profile": null,
    "endpoint_url": null
  },
  "model_data": {
    "cache_ttl_minutes": 60,
    "max_models": 100,
    "use_api": true
  },
  "recommendation": {
    "max_recommendations": 3,
    "weights": {
      "capability_match": 0.4,
      "performance": 0.2,
      "cost": 0.2,
      "availability": 0.1,
      "reliability": 0.1
    }
  },
  "availability": {
    "cache_ttl_seconds": 3600,
    "timeout_seconds": 10
  }
}
```

A template configuration file is provided at `config.template.json` in the project root directory.

## Environment Variables

You can also configure the server using environment variables. Environment variables should be prefixed with `BEDROCK_ADVISOR_` and use double underscores to indicate nesting. For example:

```bash
# Server configuration
export BEDROCK_ADVISOR_SERVER__LOG_LEVEL=INFO
export BEDROCK_ADVISOR_SERVER__ENABLE_METRICS=false

# AWS configuration
export BEDROCK_ADVISOR_AWS__REGION=us-east-1
export BEDROCK_ADVISOR_AWS__PROFILE=default

# Model data configuration
export BEDROCK_ADVISOR_MODEL_DATA__CACHE_TTL_MINUTES=60
export BEDROCK_ADVISOR_MODEL_DATA__MAX_MODELS=100
export BEDROCK_ADVISOR_MODEL_DATA__USE_API=true

# Recommendation configuration
export BEDROCK_ADVISOR_RECOMMENDATION__MAX_RECOMMENDATIONS=3
export BEDROCK_ADVISOR_RECOMMENDATION__WEIGHTS__CAPABILITY_MATCH=0.4
export BEDROCK_ADVISOR_RECOMMENDATION__WEIGHTS__PERFORMANCE=0.2
export BEDROCK_ADVISOR_RECOMMENDATION__WEIGHTS__COST=0.2
export BEDROCK_ADVISOR_RECOMMENDATION__WEIGHTS__AVAILABILITY=0.1
export BEDROCK_ADVISOR_RECOMMENDATION__WEIGHTS__RELIABILITY=0.1

# Availability configuration
export BEDROCK_ADVISOR_AVAILABILITY__CACHE_TTL_SECONDS=3600
export BEDROCK_ADVISOR_AVAILABILITY__TIMEOUT_SECONDS=10
```

## MCP Configuration

When using the Bedrock Advisor MCP Server with an MCP client like IDE Assistant or Amazon Q Developer, you can configure it using environment variables in your MCP configuration:

### Standard Configuration

```json
{
  "mcpServers": {
    "bedrock-advisor": {
      "command": "bedrock-advisor",
      "env": {
        "AWS_REGION": "us-west-2",
        "LOG_LEVEL": "DEBUG",
        "CONFIG_FILE": "/path/to/custom-config.json"
      }
    }
  }
}
```

### Local Development Configuration

For local development, you can configure the MCP server to use your local Python environment:

```json
{
  "mcpServers": {
    "bedrock-advisor-local": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "awslabs.bedrock_advisor_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MCP_TRANSPORT": "stdio",
        "PYTHONPATH": "/path/to/your/project"
      },
      "cwd": "/path/to/your/project",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Replace `/path/to/your/venv/bin/python` with the path to your Python interpreter in your virtual environment, and `/path/to/your/project` with the path to your project directory.

Available environment variables:

- `AWS_REGION`: AWS region for API calls (default: "us-east-1")
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARN, ERROR) (default: "INFO")
- `ENABLE_METRICS`: Enable performance metrics collection ("true" or "false") (default: "false")
- `CONFIG_FILE`: Path to custom configuration file

## Configuration Reference

### Server Configuration

| Key                     | Type    | Default  | Description                                           |
| ----------------------- | ------- | -------- | ----------------------------------------------------- |
| `server.log_level`      | string  | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `server.enable_metrics` | boolean | `false`  | Whether to enable performance metrics collection      |

### AWS Configuration

| Key                | Type   | Default       | Description                                |
| ------------------ | ------ | ------------- | ------------------------------------------ |
| `aws.region`       | string | `"us-east-1"` | AWS region for API calls                   |
| `aws.profile`      | string | `null`        | AWS profile to use (null for default)      |
| `aws.endpoint_url` | string | `null`        | Custom AWS endpoint URL (null for default) |

### Model Data Configuration

| Key                            | Type    | Default | Description                                       |
| ------------------------------ | ------- | ------- | ------------------------------------------------- |
| `model_data.cache_ttl_minutes` | integer | `60`    | Time-to-live for model data cache in minutes      |
| `model_data.max_models`        | integer | `100`   | Maximum number of models to cache                 |
| `model_data.use_api`           | boolean | `true`  | Whether to use the AWS Bedrock API for model data |

### Recommendation Configuration

| Key                                       | Type    | Default | Description                                           |
| ----------------------------------------- | ------- | ------- | ----------------------------------------------------- |
| `recommendation.max_recommendations`      | integer | `3`     | Maximum number of recommendations to return           |
| `recommendation.weights.capability_match` | float   | `0.4`   | Weight for capability match in recommendation scoring |
| `recommendation.weights.performance`      | float   | `0.2`   | Weight for performance in recommendation scoring      |
| `recommendation.weights.cost`             | float   | `0.2`   | Weight for cost in recommendation scoring             |
| `recommendation.weights.availability`     | float   | `0.1`   | Weight for availability in recommendation scoring     |
| `recommendation.weights.reliability`      | float   | `0.1`   | Weight for reliability in recommendation scoring      |

### Availability Configuration

| Key                              | Type    | Default | Description                                    |
| -------------------------------- | ------- | ------- | ---------------------------------------------- |
| `availability.cache_ttl_seconds` | integer | `3600`  | Time-to-live for availability cache in seconds |
| `availability.timeout_seconds`   | integer | `10`    | Timeout for availability checks in seconds     |

## Advanced Configuration

### Customizing Recommendation Weights

You can customize the weights used for scoring models in the recommendation engine by modifying the `recommendation.weights` configuration. The weights should sum to 1.0 for proper normalization.

Example:

```json
{
  "recommendation": {
    "weights": {
      "capability_match": 0.5, // Prioritize capability match
      "performance": 0.2,
      "cost": 0.1, // De-emphasize cost
      "availability": 0.1,
      "reliability": 0.1
    }
  }
}
```

### Configuring AWS Credentials

The server uses the standard AWS SDK credential resolution process. You can configure AWS credentials using:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM roles for Amazon EC2 or ECS

For more information, see the [AWS SDK for Python (Boto3) documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).

### Configuring Logging

The server uses structured JSON logging by default. You can configure the logging level using the `server.log_level` configuration or the `LOG_LEVEL` environment variable.

For more advanced logging configuration, you can modify the `setup_logging` function in `bedrock_advisor/utils/logging.py`.

## Troubleshooting

### Configuration Validation Errors

The server validates the configuration against a schema to ensure all values are of the correct type and within acceptable ranges. If there is a configuration error, the server will log an error message and exit.

Common configuration errors:

- **Missing required key**: A required configuration key is missing
- **Type error**: A configuration value is of the wrong type
- **Range error**: A configuration value is outside the acceptable range
- **Value error**: A configuration value is not one of the allowed values

### Configuration Precedence

If you're having trouble with configuration values not being applied, remember the order of precedence:

1. Environment variables
2. Configuration file
3. Default values

You can check the effective configuration by examining the server logs at startup.
