# Deployment Guide for OpenAPI MCP Server

This document provides guidance on deploying the OpenAPI MCP Server in various environments, with a focus on AWS deployment options and considerations for the Server-Sent Events (SSE) transport.

## Building and Deploying with Docker

The project includes a Dockerfile that sets up the environment for running the OpenAPI MCP Server.

### Building the Docker Image

Navigate to the project directory and build the Docker image:

```bash
# Navigate to the project directory
cd /Users/patilag/Projects/mcp/src/openapi-mcp-server

# Build the Docker image
docker build -t openapi-mcp-server:latest .
```

### Running the Container Locally

Once the image is built, you can run it locally:

```bash
# Run with default settings (Petstore API)
docker run -p 8000:8000 openapi-mcp-server:latest

# Run with custom API configuration
docker run -p 8000:8000 \
  -e API_NAME=myapi \
  -e API_BASE_URL=https://api.example.com \
  -e API_SPEC_URL=https://api.example.com/openapi.json \
  -e SERVER_TRANSPORT=sse \
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
-e USE_PROMETHEUS=true \
-e PROMETHEUS_PORT=9090
```

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

This approach provides the most reliable support for SSE connections while still leveraging AWS managed services and maintaining compatibility with the Model Context Protocol.

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
