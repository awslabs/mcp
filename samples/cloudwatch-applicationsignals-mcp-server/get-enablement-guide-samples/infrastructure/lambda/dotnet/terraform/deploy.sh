#!/bin/bash
set -e

# Store the original directory
ORIG_DIR=$(pwd)

# Build the sample app first
cd ../sample-app
dotnet publish -c Release -o bin/Release/net8.0/publish
cd bin/Release/net8.0/publish
zip -r function.zip .

# Deploy with Terraform
cd "$ORIG_DIR/lambda"
terraform init
terraform apply -auto-approve