#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
