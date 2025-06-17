# Observability for OpenAPI MCP Server

[← Back to main README](README.md)

This document provides information about the observability features in the OpenAPI MCP Server, including metrics, logging, and monitoring.

## Metrics System

The OpenAPI MCP Server includes a pluggable metrics system with different backends.

### Metrics Providers

The server supports multiple metrics provider implementations:

| Provider | Description | Requirements |
|----------|-------------|--------------|
| **InMemoryMetricsProvider** | Default provider that stores metrics in memory | None (built-in) |
| **PrometheusMetricsProvider** | Exports metrics to Prometheus | `prometheus_client` package |

### Configuration

The metrics system can be configured through environment variables:

```bash
# Maximum number of API calls to keep in history (default: 100)
export METRICS_MAX_HISTORY=500

# Whether to use the Prometheus metrics provider (default: False)
export USE_PROMETHEUS=True

# Port to expose Prometheus metrics on (default: 0, disabled)
export PROMETHEUS_PORT=9090
```

### Available Metrics

The metrics system tracks the following:

- **API Calls**: Path, method, status code, duration
- **Tool Usage**: Tool name, duration, success/failure
- **Error Rates**: Count and details of recent errors
- **Performance**: Response times, latency distributions

### Usage Examples

#### Accessing Metrics Programmatically

```python
from awslabs.openapi_mcp_server.utils.metrics_provider import metrics

# Get API call statistics
api_stats = metrics.get_api_stats()

# Get tool usage statistics
tool_stats = metrics.get_tool_stats()

# Get recent errors
recent_errors = metrics.get_recent_errors(limit=10)

# Get a summary of all metrics
summary = metrics.get_summary()
```

#### Using Metrics Decorators

```python
from awslabs.openapi_mcp_server.utils.metrics_provider import api_call_timer, tool_usage_timer

@api_call_timer
async def handle_api_request(path, method, ...):
    # Handle the request
    return response

@tool_usage_timer
async def my_tool():
    # Tool implementation
    return result
```

#### Accessing Prometheus Metrics

When using the PrometheusMetricsProvider with a configured port:

1. Start the server with Prometheus enabled:
   ```bash
   export USE_PROMETHEUS=True
   export PROMETHEUS_PORT=9090
   python -m awslabs.openapi_mcp_server.server
   ```

2. Access metrics at: `http://localhost:9090/metrics`

3. Configure Prometheus to scrape this endpoint:
   ```yaml
   scrape_configs:
     - job_name: 'openapi_mcp_server'
       static_configs:
         - targets: ['localhost:9090']
   ```

## Logging System

The OpenAPI MCP Server uses a structured logging system that provides detailed information about server operations.

### Log Levels

The server supports the following log levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| DEBUG | Detailed debugging information | Development and troubleshooting |
| INFO | General operational information | Normal operation |
| WARNING | Potential issues that don't affect operation | Monitoring for potential problems |
| ERROR | Error conditions that affect operation | Error tracking and alerting |
| CRITICAL | Critical conditions requiring immediate attention | Critical alerts |

### Configuration

Logging can be configured through command-line arguments or environment variables:

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --log-level DEBUG

# Environment variable
export LOG_LEVEL=DEBUG
```

### Log Format

Logs are output in a structured format that includes:

- Timestamp
- Log level
- Module/component name
- Message
- Additional context (when available)

Example:
```
2025-05-17 12:44:42.096 | INFO | awslabs.openapi_mcp_server.auth.register | Registered Bearer authentication provider
```

### Authentication Logging

The authentication system includes enhanced logging with:

- Structured error types
- Detailed error information
- Secure credential handling
- Authentication attempt tracking

#### Secure Logging Practices

The authentication system follows these secure logging practices:

1. **No Sensitive Data in Logs**: Passwords, tokens, and API keys are never logged, even at DEBUG level
2. **Credential Length Logging**: For debugging, only the length of credentials is logged, not the actual values
3. **Structured Error Details**: Error messages provide helpful information without exposing sensitive data
4. **Username Logging**: Usernames may be logged for audit purposes, but passwords are never logged
5. **Hash-Based Identification**: Credentials are hashed before being used in cache keys or logs

## Health Checks

The server provides health check endpoints to monitor its status:

- `/health`: Basic health check that returns 200 OK if the server is running
- `/health/detailed`: Detailed health check with component status

## Integration with External Systems

The observability features are designed to integrate with external systems:

- **Prometheus**: Metrics export via the PrometheusMetricsProvider
- **ELK Stack**: Log forwarding for centralized logging
- **CloudWatch**: Compatible log format for AWS environments
- **Grafana**: Dashboard templates available for visualization

## Best Practices

1. **Production Environments**:
   - Enable Prometheus metrics
   - Set log level to INFO
   - Configure external log aggregation

2. **Development Environments**:
   - Use DEBUG log level
   - Use InMemoryMetricsProvider for simplicity
   - Monitor recent errors via the metrics API

3. **Troubleshooting**:
   - Increase log level to DEBUG
   - Check recent errors in metrics
   - Examine API call statistics for performance issues
