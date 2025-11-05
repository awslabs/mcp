#!/bin/bash

set -e

echo "Building sample application..."
cd ../sample-app
npm install
npm run compile

echo "Installing CDK dependencies..."
cd ../cdk
npm install

echo "Building CDK application..."
npm run build

echo "Deploying CDK stack..."
npm run deploy

echo "Deployment complete!"