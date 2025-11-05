#!/bin/bash

# Build the Java Lambda function
cd ../sample-app
mvn clean package

# Deploy with CDK
cd ../cdk
npm install
npm run build
npm run deploy