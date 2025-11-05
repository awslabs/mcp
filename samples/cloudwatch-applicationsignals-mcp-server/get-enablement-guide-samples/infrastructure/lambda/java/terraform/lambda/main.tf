resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  architecture = var.architecture == "x86_64" ? "amd64" : "arm64"
  function_name = "${var.function_name}-${random_id.suffix.hex}"
  api_name = "ApiGateway-Lambda-java-terraform-${random_id.suffix.hex}"
}

module "hello-lambda-function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 2.24.0"

  architectures = compact([var.architecture])
  function_name = local.function_name
  handler       = "com.example.Handler::handleRequest"
  runtime       = var.runtime

  create_package         = false
  local_existing_package = "${path.module}/../../sample-app/target/lambda-sample-1.0.0.jar"

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

module "api-gateway" {
  source = "../api-gateway-proxy"

  name                = local.api_name
  function_name       = module.hello-lambda-function.lambda_function_name
  function_invoke_arn = module.hello-lambda-function.lambda_function_invoke_arn

}

resource "aws_iam_role_policy_attachment" "hello-lambda-cloudwatch" {
  role       = module.hello-lambda-function.lambda_function_name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

