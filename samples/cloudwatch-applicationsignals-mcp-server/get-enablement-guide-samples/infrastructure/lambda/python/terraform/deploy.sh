#!/bin/bash
set -e

# Build the sample app first
cd ../sample-app
pip install -r requirements.txt -t .
zip -r function.zip . --exclude="*.pyc" "__pycache__/*"

# Deploy with Terraform
cd ../terraform/lambda
terraform init
terraform apply -auto-approve