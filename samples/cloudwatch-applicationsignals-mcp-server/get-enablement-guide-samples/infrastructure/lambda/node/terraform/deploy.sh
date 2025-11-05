#!/bin/bash
set -e

# Build the sample app first
cd ../sample-app
npm install
npm run compile

# Deploy with Terraform
cd ../terraform/lambda
terraform init
terraform apply -auto-approve