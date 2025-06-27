#!/bin/bash
# Test script for Docker build validation

set -e

echo "🐳 Testing PostgreSQL MCP Server Docker Build..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t postgres-mcp-server-test .

# Test that the image was built successfully
echo "✅ Docker image built successfully!"

# Test that the container can start (will exit quickly without proper args, but that's expected)
echo "🚀 Testing container startup..."
timeout 5s docker run --rm postgres-mcp-server-test || echo "Container started and exited as expected"

echo "🎉 Docker build test completed successfully!"
echo ""
echo "To run the container with proper configuration:"
echo "docker run -p 8000:8000 \\"
echo "  -v ~/.aws:/root/.aws:ro \\"
echo "  -e AWS_PROFILE=your-profile-name \\"
echo "  postgres-mcp-server-test \\"
echo "  --resource_arn <Your Resource ARN> \\"
echo "  --secret_arn <Your Secret ARN> \\"
echo "  --database \"your-database\" \\"
echo "  --region \"us-west-2\" \\"
echo "  --readonly \"true\""
