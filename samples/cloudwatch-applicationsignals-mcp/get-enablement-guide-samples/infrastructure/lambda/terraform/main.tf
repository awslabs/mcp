terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Read single config file
locals {
  config = jsondecode(file("${path.module}/config/${var.config_file}"))
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${local.config.functionName}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach S3 read-only access
resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# Lambda function
resource "aws_lambda_function" "function" {
  filename         = "${path.module}/${local.config.artifactPath}"
  function_name    = local.config.functionName
  role            = aws_iam_role.lambda_role.arn
  handler         = local.config.handler
  runtime         = local.config.runtime
  timeout         = local.config.timeout
  memory_size     = local.config.memorySize
  source_code_hash = filebase64sha256("${path.module}/${local.config.artifactPath}")

  environment {
    variables = local.config.environment
  }
}

# API Gateway HTTP API
resource "aws_apigatewayv2_api" "api" {
  name          = "${local.config.functionName}-api"
  protocol_type = "HTTP"
}

# API Gateway integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.function.invoke_arn
  payload_format_version = "2.0"
}

# API Gateway route - catch all
resource "aws_apigatewayv2_route" "route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "stage" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
