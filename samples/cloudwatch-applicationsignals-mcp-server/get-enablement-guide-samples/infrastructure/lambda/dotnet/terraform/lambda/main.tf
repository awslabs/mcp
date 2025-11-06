provider "aws" {
  region = "us-west-2"
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  architecture = var.architecture == "x86_64" ? "amd64" : "arm64"
  function_name = "${var.function_name}-${random_id.suffix.hex}"
  alb_name = "dotnet-tf-alb-${random_id.suffix.hex}"
}

module "hello-lambda-function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.14.0"

  architectures = compact([var.architecture])
  function_name = local.function_name
  handler       = "LambdaSample::LambdaSample.Function::FunctionHandler"
  runtime       = var.runtime

  create_package         = false
  local_existing_package = "${path.module}/../../sample-app/bin/Release/net8.0/publish/function.zip"

  memory_size = 512
  timeout     = 30

  environment_variables = {
  }



  attach_policy_statements = true
  policy_statements = {
    s3 = {
      effect = "Allow"
      actions = [
        "s3:ListAllMyBuckets"
      ]
      resources = [
        "*"
      ]
    }
  }
}

module "alb" {
  source = "../alb-proxy"

  name         = local.alb_name
  function_arn = module.hello-lambda-function.lambda_function_arn
}

resource "aws_iam_role_policy_attachment" "hello-lambda-cloudwatch" {
  role       = module.hello-lambda-function.lambda_function_name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

