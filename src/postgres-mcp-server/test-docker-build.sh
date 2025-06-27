#!/bin/bash
# Test script for Docker build validation

set -e

echo "🐳 Testing PostgreSQL MCP Server Docker Build..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t postgres-mcp-server-test .

# Test that the image was built successfully
echo "✅ Docker image built successfully!"

# Test that the container can start and show help
echo "🚀 Testing container startup..."
docker run --rm postgres-mcp-server-test python3 -m awslabs.postgres_mcp_server.server --help | head -5

echo "🎉 Docker build test completed successfully!"
echo ""
echo "To run the container with proper configuration:"
echo "docker run -p 8000:8000 \\"
echo "  -v ~/.aws:/aws-config:ro \\"
echo "  -e AWS_CONFIG_FILE=/aws-config/config \\"
echo "  -e AWS_SHARED_CREDENTIALS_FILE=/aws-config/credentials \\"
echo "  -e AWS_PROFILE=your-profile-name \\"
echo "  postgres-mcp-server-test \\"
echo "  python3 -m awslabs.postgres_mcp_server.server \\"
echo "  --resource_arn <Your Resource ARN> \\"
echo "  --secret_arn <Your Secret ARN> \\"
echo "  --database \"your-database\" \\"
echo "  --region \"us-west-2\" \\"
echo "  --readonly \"true\""
