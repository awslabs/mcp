# AWS Best Practices in OpenAPI MCP Server

[← Back to main README](README.md)

This document details the AWS best practices implemented in the OpenAPI MCP Server for building resilient, observable, and efficient cloud applications.

## Caching

The OpenAPI MCP Server implements a robust caching system with multiple backend options to improve performance and reduce load on backend services.

### Features

- **Pluggable Cache Providers**: The server supports multiple caching backends through a pluggable architecture:
  - **In-Memory Cache**: Default provider that stores cache entries in memory with TTL support
  - **Cachetools Integration**: Optional integration with the `cachetools` library for more efficient caching with LRU and TTL policies

- **TTL-based Caching**: All cached items have configurable time-to-live settings to ensure data freshness
  - Default TTL is configurable via environment variables
  - Per-cache TTL overrides are supported
  - Automatic expiration of stale entries

- **Automatic Cleanup**: Expired cache entries are automatically removed to prevent memory leaks
  - In-memory provider includes a cleanup method to purge expired entries
  - Cachetools provider handles this automatically

- **Cache Decorator**: Simple `@cached` decorator for easily caching function results
  - Automatically generates cache keys based on function name and arguments
  - Supports custom TTL settings per decorated function

- **Configurable Cache Size**: Limit memory usage with configurable maximum cache size
  - Prevents unbounded memory growth
  - Implements LRU (Least Recently Used) eviction policy when using cachetools

### Implementation

The caching system is implemented in `awslabs/openapi_mcp_server/utils/cache_provider.py` with the following components:

- `CacheProvider`: Abstract base class defining the caching interface
- `InMemoryCacheProvider`: Simple in-memory implementation with TTL support
- `CachetoolsProvider`: More efficient implementation using the cachetools library
- `create_cache_provider`: Factory function to create the appropriate provider based on configuration
- `@cached`: Decorator for caching function results

### Configuration

```bash
# Enable cachetools (more efficient than in-memory)
export USE_CACHETOOLS=true

# Configure cache settings
export CACHE_TTL=300  # Cache TTL in seconds
export CACHE_MAXSIZE=1000  # Maximum number of cache entries
```

## Resilience

The OpenAPI MCP Server implements resilience patterns to handle transient failures and ensure high availability.

### Features

- **Retry Logic**: Automatic retries for transient failures with exponential backoff
  - Configurable maximum retry attempts
  - Exponential backoff with jitter to prevent thundering herd problems
  - Different retry strategies for different types of failures

- **Circuit Breaking**: Prevents cascading failures by failing fast when a service is unavailable
  - Implemented through the tenacity library when enabled
  - Automatically detects when services are unavailable
  - Prevents overwhelming failing services with requests

- **Timeout Management**: Configurable timeouts for all external requests
  - Global default timeout settings
  - Per-request timeout overrides
  - Separate connect, read, and write timeouts

- **Connection Pooling**: Efficient connection reuse with configurable limits
  - Configurable maximum connections
  - Configurable maximum keepalive connections
  - Automatic connection management

- **Fallback Mechanisms**: Graceful degradation when services are unavailable
  - Fallback to simpler implementations when advanced features are unavailable
  - Graceful handling of missing optional dependencies

### Implementation

The resilience features are primarily implemented in `awslabs/openapi_mcp_server/utils/http_client.py` with the following components:

- `HttpClientFactory`: Creates HTTP clients with enhanced functionality
- Optional integration with the tenacity library for advanced retry and circuit breaking

### Configuration

```bash
# Enable tenacity for advanced retry logic
export USE_TENACITY=true

# Configure HTTP client settings
export HTTP_MAX_CONNECTIONS=100  # Maximum number of connections
export HTTP_MAX_KEEPALIVE=20  # Maximum number of keepalive connections
export HTTP_TIMEOUT=30  # Default timeout in seconds
```

## Observability

The OpenAPI MCP Server provides comprehensive observability features to monitor performance, track errors, and gain insights into system behavior.

### Features

- **Metrics Collection**: Tracks API calls, tool usage, errors, and performance
  - Request counts by endpoint
  - Error rates and types
  - Response times
  - Tool usage statistics

- **Prometheus Integration**: Optional export of metrics to Prometheus
  - Exposes metrics on a configurable port
  - Standard Prometheus metric types (Counter, Gauge, Histogram)
  - Custom metrics for API calls and tool usage

- **Structured Logging**: Detailed logs with configurable verbosity
  - Different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Contextual information in log messages
  - Performance information for API calls and tool usage

- **Error Tracking**: Captures and reports detailed error information
  - Error type and message
  - Stack traces for debugging
  - Context information to help diagnose issues

- **Performance Monitoring**: Tracks response times and error rates
  - Average response time by endpoint
  - Error rates by endpoint
  - Tool execution times

### Implementation

The observability features are primarily implemented in `awslabs/openapi_mcp_server/utils/metrics_provider.py` with the following components:

- `MetricsProvider`: Abstract base class defining the metrics interface
- `InMemoryMetricsProvider`: Simple in-memory implementation for metrics collection
- `PrometheusMetricsProvider`: Implementation that exports metrics to Prometheus
- `create_metrics_provider`: Factory function to create the appropriate provider based on configuration
- `@api_call_timer`: Decorator for timing API calls and recording metrics
- `@tool_usage_timer`: Decorator for timing tool usage and recording metrics

### Configuration

```bash
# Enable Prometheus metrics
export ENABLE_PROMETHEUS=true
export PROMETHEUS_PORT=9090  # Port for Prometheus metrics server

# Configure metrics settings
export METRICS_MAX_HISTORY=1000  # Maximum number of metrics entries to keep

# Configure logging
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## AWS Integration Best Practices

When deploying the OpenAPI MCP Server in AWS environments, the following best practices are recommended:

### Security

- Use IAM roles for EC2 instances or containers instead of hardcoded credentials
- Store sensitive configuration in AWS Secrets Manager or Parameter Store
- Use VPC endpoints for accessing AWS services without traversing the public internet
- Implement least privilege access for all AWS resources

### Scalability

- Deploy behind an Application Load Balancer for horizontal scaling
- Use Auto Scaling Groups to automatically adjust capacity based on demand
- Consider using AWS Lambda for serverless deployment
- Implement rate limiting to protect against traffic spikes

### High Availability

- Deploy across multiple Availability Zones
- Use Amazon RDS or DynamoDB for persistent storage with multi-AZ replication
- Implement health checks and automatic instance replacement
- Consider using AWS Global Accelerator for global deployments

### Cost Optimization

- Use Spot Instances for non-critical workloads
- Implement auto-scaling to match capacity with demand
- Use AWS Cost Explorer to identify optimization opportunities
- Consider using AWS Graviton processors for better price/performance

### Monitoring and Alerting

- Set up CloudWatch alarms for key metrics
- Configure CloudWatch Logs for centralized logging
- Use X-Ray for distributed tracing
- Set up SNS notifications for critical alerts

## Integration with AWS Services

The OpenAPI MCP Server can be integrated with various AWS services to enhance its capabilities:

### Amazon CloudWatch

- Use CloudWatch Logs for centralized logging
- Set up CloudWatch Metrics for monitoring key performance indicators
- Create CloudWatch Alarms for alerting on critical issues
- Use CloudWatch Dashboards for visualizing metrics

### Amazon Managed Service for Prometheus

- Use Amazon Managed Service for Prometheus for scalable metrics storage
- Configure remote write from the OpenAPI MCP Server to Amazon Managed Service for Prometheus
- Set up IAM roles with appropriate permissions for metrics access
- Integrate with Amazon Managed Grafana for visualization

### Amazon Managed Grafana

- Create dashboards for visualizing metrics from Amazon Managed Service for Prometheus
- Set up alerts based on metric thresholds
- Create custom dashboards for different user roles
- Share dashboards with team members

### AWS X-Ray

- Enable X-Ray tracing for distributed request tracking
- Analyze service dependencies and bottlenecks
- Identify performance issues and errors
- Visualize request flows through your application

### AWS Lambda

- Note that SSE transport is not supported by AWS Lambda due to its request-response model
- For non-SSE use cases, consider deploying as a Lambda function for serverless operation
- Use Lambda layers for dependencies
- Configure appropriate memory and timeout settings

### Amazon ECS/EKS

- Deploy as a container in ECS or EKS for scalable operation
- Use Fargate for serverless container execution
- Implement service discovery for microservices architecture
- Configure auto-scaling based on CPU/memory utilization

### Amazon API Gateway

- For SSE transport, be aware of API Gateway timeout limitations
- Consider using Application Load Balancer instead for SSE connections
- For non-SSE use cases, use API Gateway as a front-end for the server
- Implement request validation and transformation

### AWS Secrets Manager

- Store API keys, tokens, and other sensitive information
- Rotate credentials automatically
- Integrate with IAM for access control
- Use encryption for data at rest and in transit
