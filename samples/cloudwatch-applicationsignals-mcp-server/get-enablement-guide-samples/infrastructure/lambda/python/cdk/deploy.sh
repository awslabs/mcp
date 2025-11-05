#!/bin/bash

# Build the Python Lambda function
cd ../sample-app
pip install -r requirements.txt -t .
zip -r function.zip . --exclude="*.pyc" "__pycache__/*"

# Deploy with CDK
cd ../cdk
npm install
npm run build
npm run deploy