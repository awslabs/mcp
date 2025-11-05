#!/bin/bash

# Get the current directory (should be cdk)
CDK_DIR=$(pwd)

# Build the .NET Lambda function
cd ../sample-app
dotnet publish -c Release -o bin/Release/net8.0/publish
cd bin/Release/net8.0/publish
zip -r function.zip .

# Go back to CDK directory
cd "$CDK_DIR"

# Deploy with CDK
npm install
npm run build
npm run deploy