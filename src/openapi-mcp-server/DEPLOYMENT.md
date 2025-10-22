# Deployment Guide for OpenAPI MCP Server

[← Back to main README](README.md)

This document provides guidance on deploying the OpenAPI MCP Server in various environments, with a focus on AWS deployment options and considerations for the Server-Sent Events (SSE) transport.

## Building and Deploying with Docker

The project includes a Dockerfile that sets up the environment for running the OpenAPI MCP Server.

### Building the Docker Image

Navigate to the project directory and build the Docker image:

```bash
# Navigate to the project directory
cd /path/to/openapi-mcp-server

# Build the Docker image
docker build -t openapi-mcp-server:latest .
```

### Running the Container Locally

Once the image is built, you can run it locally:

```bash
# Run with Petstore API example
docker run -p 8000:8000 \
  -e API_NAME=petstore \
  -e API_BASE_URL=https://petstore3.swagger.io/api/v3 \
  -e API_SPEC_URL=https://petstore3.swagger.io/api/v3/openapi.json \
  openapi-mcp-server:latest

# Run with custom API configuration
docker run -p 8000:8000 \
  -e API_NAME=myapi \
  -e API_BASE_URL=https://api.example.com \
  -e API_SPEC_URL=https://api.example.com/openapi.json \
  -e SERVER_TRANSPORT=sse \
  -e ENABLE_PROMETHEUS=false \
  -e ENABLE_OPERATION_PROMPTS=true \
  openapi-mcp-server:latest
```

### Environment Variables for Docker

You can customize the container behavior using environment variables:

```bash
# Server configuration
-e SERVER_NAME="My API Server" \
-e SERVER_DEBUG=true \
-e SERVER_MESSAGE_TIMEOUT=60 \
-e SERVER_HOST="0.0.0.0" \
-e SERVER_PORT=8000 \
-e SERVER_TRANSPORT="sse" \
-e LOG_LEVEL="INFO" \

# API configuration
-e API_NAME="myapi" \
-e API_BASE_URL="https://api.example.com" \
-e API_SPEC_URL="https://api.example.com/openapi.json" \

# Authentication configuration
-e AUTH_TYPE="api_key" \
-e AUTH_API_KEY="YOUR_API_KEY" \
-e AUTH_API_KEY_NAME="X-API-Key" \
-e AUTH_API_KEY_IN="header" \

# Prometheus configuration
-e ENABLE_PROMETHEUS=false \
-e PROMETHEUS_PORT=9090 \
-e ENABLE_OPERATION_PROMPTS=true
```

### Graceful Shutdown

The OpenAPI MCP Server implements a robust graceful shutdown mechanism to ensure clean termination when the server is stopped or interrupted. This is particularly important for production deployments where abrupt termination could lead to connection errors, data loss, or incomplete operations.

#### How Graceful Shutdown Works

When the server receives a termination signal (SIGINT from Ctrl+C or SIGTERM from container orchestrators):

1. The server logs that it's shutting down gracefully
2. Final metrics are logged to provide visibility into the server's state at shutdown
3. For SIGINT (Ctrl+C), the server chains to the original handler after logging
4. Uvicorn's built-in graceful shutdown process handles the actual shutdown
5. Active connections are allowed to complete before the server exits

#### Configuration Options

The server's graceful shutdown can be configured through uvicorn options:

```bash
# Set a custom timeout for graceful shutdown (in seconds)
-e UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=5.0

# Enable/disable graceful shutdown (default: true)
-e UVICORN_GRACEFUL_SHUTDOWN=true
```

#### Best Practices for Container Environments

When running in container environments like Docker, Kubernetes, or ECS:

1. **Set appropriate termination grace periods** - Allow enough time for connections to complete
2. **Use SIGTERM for orchestrated shutdowns** - Container orchestrators typically send SIGTERM
3. **Configure health checks** - Ensure they fail appropriately during shutdown
4. **Monitor shutdown metrics** - Track shutdown times and any errors during shutdown

### Deploying to AWS

#### Push to Amazon ECR

```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if it doesn't exist)
aws ecr create-repository --repository-name openapi-mcp-server

# Tag and push the image
docker tag openapi-mcp-server:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/openapi-mcp-server:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/openapi-mcp-server:latest
```

#### Health Checks and Monitoring

The Docker container includes a health check script. You can monitor the container health with:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' container_id

# View container logs
docker logs container_id
```

#### Troubleshooting

If you encounter issues:

1. Check container logs: `docker logs container_id`
2. Verify environment variables are set correctly
3. Ensure the API specification URL is accessible from within the container
4. Check that the port mapping is correct (-p 8000:8000)
5. Verify network connectivity for external API access

## SSE Transport Considerations

### Important Notes on Transport Compatibility

- **SSE (Server-Sent Events)** is supported by the Model Context Protocol but not by AWS Lambda
- **WebSocket** is not yet supported by the Model Context Protocol
- **stdio** transport is supported for local development but not suitable for web deployments

### Using SSE with Amazon EKS

When deploying to Amazon EKS, SSE works well because containers can maintain persistent connections:

1. **Configure your EKS deployment** to use the SSE transport:

```yaml
# openapi-mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openapi-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: openapi-mcp-server
  template:
    metadata:
      labels:
        app: openapi-mcp-server
    spec:
      containers:
      - name: openapi-mcp-server
        image: YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/openapi-mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: SERVER_TRANSPORT
          value: "sse"  # Explicitly set SSE transport
        - name: API_NAME
          value: "myapi"
        - name: API_BASE_URL
          value: "https://api.example.com"
        - name: API_SPEC_URL
          value: "https://api.example.com/openapi.json"
```

2. **Ensure your ingress controller** is configured to support SSE connections:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: openapi-mcp-server-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: openapi-mcp-server
            port:
              number: 80
```

### API Gateway with SSE - Challenges and Solutions

API Gateway has limitations with SSE due to its timeout constraints:

1. **API Gateway HTTP APIs** have a maximum timeout of 29 seconds, which is insufficient for long-running SSE connections
2. **API Gateway REST APIs** have similar timeout limitations

#### Recommended Architecture for API Gateway

For production deployments requiring SSE with API Gateway:

1. **Use Amazon EKS or ECS** to host the OpenAPI MCP Server
2. **Place an Application Load Balancer (ALB)** in front of your EKS/ECS service
3. **Configure the ALB** with appropriate idle timeout settings (up to 4000 seconds)
4. **Use API Gateway** only for initial connection establishment and authentication
5. **Redirect clients** to the ALB endpoint for the actual SSE connection

```
Client → API Gateway (auth/initial connection) → Redirect → ALB → OpenAPI MCP Server (EKS/ECS)
```

### Best Practice for Production Deployment with SSE

For the most reliable SSE implementation with AWS services:

1. **Deploy on Amazon ECS with Fargate** for containerized deployment with auto-scaling
2. **Use an Application Load Balancer** with idle timeout set to at least 120 seconds
3. **Implement health checks** to ensure container availability
4. **Set up CloudWatch alarms** to monitor connection counts and response times
5. **Use AWS X-Ray** for tracing requests through your application
6. **Implement Amazon Managed Service for Prometheus** for metrics collection and monitoring

This approach provides the most reliable support for SSE connections while still leveraging AWS managed services and maintaining compatibility with the Model Context Protocol.

## Observability with AWS Services

### AWS X-Ray for Distributed Tracing

AWS X-Ray provides end-to-end tracing capabilities that help you analyze and debug distributed applications:

1. **Enable X-Ray in your application**:
   ```python
   # Install the X-Ray SDK
   pip install aws-xray-sdk

   # Add X-Ray middleware to your application
   from aws_xray_sdk.core import xray_recorder
   from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

   xray_recorder.configure(service='openapi-mcp-server')
   XRayMiddleware(app, xray_recorder)
   ```

2. **Configure X-Ray daemon** in your container:
   ```yaml
   # Add X-Ray daemon as a sidecar container
   - name: xray-daemon
     image: amazon/aws-xray-daemon
     ports:
       - containerPort: 2000
         protocol: UDP
   ```

3. **Set up IAM permissions** for X-Ray:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "xray:PutTraceSegments",
           "xray:PutTelemetryRecords"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### Amazon Managed Service for Prometheus

For comprehensive metrics collection and monitoring, integrate with Amazon Managed Service for Prometheus:

1. **Configure Prometheus in your application**:
   ```python
   # Set environment variables
   ENABLE_PROMETHEUS=true
   PROMETHEUS_PORT=9090
   ```

2. **Set up remote write to Amazon Managed Service for Prometheus**:
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s

   remote_write:
     - url: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345678-1234-1234-1234-123456789012/api/v1/remote_write
       sigv4:
         region: us-east-1
       queue_config:
         max_samples_per_send: 1000
         max_shards: 200

   scrape_configs:
     - job_name: 'openapi-mcp-server'
       static_configs:
         - targets: ['localhost:9090']
   ```

3. **Create an IAM role** with permissions for Amazon Managed Service for Prometheus:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "aps:RemoteWrite",
           "aps:GetSeries",
           "aps:GetLabels",
           "aps:GetMetricMetadata"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

4. **Visualize metrics** using Amazon Managed Grafana:
   - Create a Grafana workspace in the AWS console
   - Add Amazon Managed Service for Prometheus as a data source
   - Import or create dashboards for monitoring your OpenAPI MCP Server

This comprehensive observability setup provides both tracing and metrics monitoring for your OpenAPI MCP Server deployment.

## AWS Service Integration Documentation References

### Amazon Managed Service for Prometheus

For integrating with Amazon Managed Service for Prometheus, refer to:

- [Amazon Managed Service for Prometheus User Guide](https://docs.aws.amazon.com/prometheus/latest/userguide/what-is-Amazon-Managed-Service-Prometheus.html)
- [Getting started with Amazon Managed Service for Prometheus](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-getting-started.html)
- [Remote write to Amazon Managed Service for Prometheus](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-remote-write.html)
- [IAM policies for Amazon Managed Service for Prometheus](https://docs.aws.amazon.com/prometheus/latest/userguide/security_iam_service-with-iam.html)

### Amazon CloudWatch

For CloudWatch integration, refer to:

- [Amazon CloudWatch User Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [Using Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
- [Creating CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Logs for containers](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_GettingStarted.html)

### Amazon Managed Grafana

For visualization with Amazon Managed Grafana:

- [Amazon Managed Grafana User Guide](https://docs.aws.amazon.com/grafana/latest/userguide/what-is-Amazon-Managed-Service-Grafana.html)
- [Adding data sources to Amazon Managed Grafana](https://docs.aws.amazon.com/grafana/latest/userguide/AMG-data-sources.html)
- [Working with dashboards in Amazon Managed Grafana](https://docs.aws.amazon.com/grafana/latest/userguide/AMG-dashboards.html)

### AWS Application Load Balancer

For setting up an Application Load Balancer with SSE support:

- [What is an Application Load Balancer?](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [Creating an Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-application-load-balancer.html)
- [Target group settings for long-running connections](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-attributes)

### Amazon ECS

For deploying to Amazon ECS, refer to the official AWS documentation:
- [Amazon ECS Developer Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
- [Creating an Amazon ECS service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-service.html)

### Amazon EKS

For deploying to Amazon EKS, refer to:
- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [Getting started with Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html)
- [Deploying applications to Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/deploy-apps.html)

## Deploying to AWS AgentCore Runtime with AWS CDK

You can leverage this `openapi-mcp-sever` in your own CDK projects to MCP-fy your APIs.

The example below leverages git submodule functionality and creates an AgentCore Runtime MCP server using CDK, based on this repository.

First off, clone this repo as a submodule within your own repo

```
git submodule add https://github.com/awslabs/mcp.git mcp
```

Then create your runtime stack as in the example below.

```python
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_bedrockagentcore as bedrockagentcore,
    CfnOutput,
)
from cdk_nag import NagSuppressions
from constructs import Construct
import os
from typing import Protocol

class APIProps(Protocol):
    api: apigateway.RestApiBase
    user_pool: cognito.UserPool
    app_client: cognito.UserPoolClient
    cognito_domain: cognito.UserPoolDomain | None

class OpenApiMcpServerStack(Stack):
    """
    CDK Stack for deploying the OpenAPI MCP Server to AgentCore Runtime.
    This stack creates the necessary infrastructure to host the OpenAPI MCP server
    as a containerized service that can access external APIs through MCP protocol.
    """

    def __init__(self, scope: Construct, construct_id: str, api_stack: APIProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Store reference to ESG API stack for cross-stack references
        self.api_stack = api_stack

        # Build and push Docker image using CDK Docker Asset
        self.docker_image = ecr_assets.DockerImageAsset(
            self, "OpenApiMcpServerDockerImage",
            directory=os.path.join(os.path.dirname(__file__), "..", "mcp", "src", "openapi-mcp-server"),  # replace with the correct path to the submodule
            platform=ecr_assets.Platform.LINUX_ARM64
        )

        # Get account and region for IAM policies
        account_id = Stack.of(self).account
        region = Stack.of(self).region

        # Create IAM role for the AgentCore Runtime with proper permissions
        self.mcp_server_role = iam.Role(
            self, "OpenApiMcpServerRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "BedrockAgentCoreRuntimePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                            resources=[f"arn:aws:ecr:{region}:{account_id}:repository/*"]
                        ),
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                            resources=[f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"]
                        ),
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogGroups"],
                            resources=[f"arn:aws:logs:{region}:{account_id}:log-group:*"]
                        ),
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]
                        ),
                        iam.PolicyStatement(
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "bedrock-agentcore:GetWorkloadAccessToken",
                                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*"
                            ]
                        ),
                        # Additional permissions for Cognito authentication
                        iam.PolicyStatement(
                            actions=[
                                "cognito-idp:InitiateAuth",
                                "cognito-idp:RespondToAuthChallenge",
                                "cognito-idp:GetUser"
                            ],
                            resources=[
                                self.api_stack.user_pool.user_pool_arn,
                                f"{self.api_stack.user_pool.user_pool_arn}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Create the AgentCore Runtime for OpenAPI MCP Server with JWT authentication
        self.mcp_runtime = bedrockagentcore.CfnRuntime(
            self, "OpenApiMcpServerRuntime",
            agent_runtime_name="openapi_mcp_server_runtime",
            agent_runtime_artifact=bedrockagentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=bedrockagentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=self.docker_image.image_uri
                )
            ),
            network_configuration=bedrockagentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC"
            ),
            role_arn=self.mcp_server_role.role_arn,
            description="OpenAPI MCP Server runtime for connecting to external APIs through MCP protocol with Cognito JWT authentication",
            # Enable JWT authentication for inbound requests using Cognito
            authorizer_configuration=bedrockagentcore.CfnRuntime.AuthorizerConfigurationProperty(
                custom_jwt_authorizer=bedrockagentcore.CfnRuntime.CustomJWTAuthorizerConfigurationProperty(
                    discovery_url=f"{self.api_stack.user_pool.user_pool_provider_url}/.well-known/openid-configuration",
                    allowed_clients=[self.api_stack.app_client.user_pool_client_id]
                )
            ),
            protocol_configuration="MCP",
            environment_variables={
                "API_NAME": "your-api-name",
                "API_BASE_URL": self.api_stack.api.url,
                "API_SPEC_URL": f"{self.api_stack.api.url}openapi.json",  # make sure your api exposes a /openapi.json endpoint with the json for the spec
                "SERVER_TRANSPORT": "streamable-http",  # This is important to make sure it runs on AgentCore Runtime
                "LOG_LEVEL": "INFO",
                # Cognito authentication configuration - If you have a different AUTH, change this
                "AUTH_TYPE": "cognito",
                "AUTH_COGNITO_CLIENT_ID": self.api_stack.app_client.user_pool_client_id,
                "AUTH_COGNITO_USER_POOL_ID": self.api_stack.user_pool.user_pool_id,
                "AUTH_COGNITO_REGION": Stack.of(self).region,
                "AUTH_COGNITO_USERNAME": os.environ.get("COGNITO_USERNAME", ""),
                "AUTH_COGNITO_PASSWORD": os.environ.get("COGNITO_PASSWORD", ""),
                # Enhanced Cognito configuration for better reliability
                "AUTH_TOKEN_TTL": "3600",  # 1 hour token cache TTL
                "AUTH_COGNITO_DOMAIN": self.api_stack.cognito_domain.domain_name,  # Cognito domain for OAuth flows
                "ENABLE_PROMETHEUS": "false",
                "ENABLE_OPERATION_PROMPTS": "true",
                "OTEL_PYTHON_DISTRO": "aws_distro",  # Uses AWS Distro for OpenTelemetry
                "OTEL_PYTHON_CONFIGURATOR": "aws_configurator",  # Sets AWS configurator for ADOT SDK
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",  # Configures export protocol
            }
        )

        # Ensure the runtime waits for the role and its policies to be created
        self.mcp_runtime.node.add_dependency(self.mcp_server_role)

        # Output the runtime ARN and other useful information
        CfnOutput(
            self, "McpServerRuntimeArn",
            value=self.mcp_runtime.attr_agent_runtime_arn,
            description="ARN of the OpenAPI MCP Server AgentCore Runtime"
        )

        CfnOutput(
            self, "McpServerRuntimeName",
            value=self.mcp_runtime.agent_runtime_name,
            description="Name of the OpenAPI MCP Server AgentCore Runtime"
        )

        CfnOutput(
            self, "McpServerImageUri",
            value=self.docker_image.image_uri,
            description="URI of the OpenAPI MCP Server Docker image"
        )

        CfnOutput(
            self, "McpServerJwtDiscoveryUrl",
            value=f"https://cognito-idp.{Stack.of(self).region}.amazonaws.com/{self.api_stack.user_pool.user_pool_id}/.well-known/openid-configuration",
            description="JWT discovery URL for MCP server authentication"
        )

        # Store outputs as instance variables
        self.mcp_runtime_arn = self.mcp_runtime.attr_agent_runtime_arn
        self.image_uri = self.docker_image.image_uri
        self.api_base_url = self.api_stack.api.url

```