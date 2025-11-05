#!/bin/bash
set -e

# Build the sample app first
cd ../sample-app
mvn clean package

# Deploy with Terraform
cd ../terraform/lambda
terraform init
terraform apply -auto-approve