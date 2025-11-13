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

# Build script for Java Lambda function
# Uses Docker to build Lambda deployment package with Gradle
set -e

# Configuration
BUILD_DIR="build"
BUILDS_OUTPUT_DIR="../builds"
OUTPUT_ZIP="java-lambda.zip"
BUILD_IMAGE="lambda-java-builder:17"

echo "Building Java Lambda function with Docker and Gradle..."

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker first."
    exit 1
fi

# Build the Docker image if it doesn't exist
if ! docker image inspect "$BUILD_IMAGE" &> /dev/null; then
    echo "Building Docker image with build tools..."
    docker build -t "$BUILD_IMAGE" -f Dockerfile.build .
fi

# Create builds output directory
mkdir -p "$BUILDS_OUTPUT_DIR"

# Clean up any previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy source files to build directory
echo "Copying source files..."
cp -r src "$BUILD_DIR/"
cp build.gradle "$BUILD_DIR/"

# Build in Docker container
echo "Building package in Docker container..."
docker run --rm \
    -v "$(pwd)/$BUILD_DIR":/var/task \
    "$BUILD_IMAGE" \
    gradle clean buildZip

# Copy the built zip to builds directory
cp "$BUILD_DIR/build/distributions/"*.zip "$BUILDS_OUTPUT_DIR/$OUTPUT_ZIP"

# Clean up build directory
rm -rf "$BUILD_DIR"

echo "✓ Build complete: $BUILDS_OUTPUT_DIR/$OUTPUT_ZIP"