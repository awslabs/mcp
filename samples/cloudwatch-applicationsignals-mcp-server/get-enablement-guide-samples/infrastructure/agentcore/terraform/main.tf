terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Get current AWS region and account
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ECR Repository (corresponds to CDK ecr.Repository)
resource "aws_ecr_repository" "basic_agent" {
  name                 = "${lower(var.stack_name)}-basic-agent"
  image_tag_mutability = "MUTABLE"
  
  force_delete = true
  
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.stack_name}-basic-agent"
  }
}

# S3 Asset equivalent - Create S3 bucket and upload source code
resource "aws_s3_bucket" "source_asset" {
  bucket_prefix = "${lower(var.stack_name)}-source-asset-"
  
  tags = {
    Name = "${var.stack_name}-source-asset"
  }
}

resource "aws_s3_bucket_versioning" "source_asset" {
  bucket = aws_s3_bucket.source_asset.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Archive source code
data "archive_file" "agent_code" {
  type        = "zip"
  source_dir  = "${path.module}/agent-code"
  output_path = "${path.module}/agent-code.zip"
}

# Upload source code to S3
resource "aws_s3_object" "agent_code" {
  bucket = aws_s3_bucket.source_asset.id
  key    = "agent-code.zip"
  source = data.archive_file.agent_code.output_path
  etag   = data.archive_file.agent_code.output_md5

  tags = {
    Name = "${var.stack_name}-agent-code"
  }
}

# CodeBuild IAM Role (corresponds to CDK codebuild_role)
resource "aws_iam_role" "codebuild_role" {
  name = "${var.stack_name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.stack_name}-codebuild-role"
  }
}

# CodeBuild IAM Policy (corresponds to CDK inline policies)
resource "aws_iam_role_policy" "codebuild_policy" {
  name = "CodeBuildPolicy"
  role = aws_iam_role.codebuild_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/*",
          "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/*:*"
        ]
      },
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [aws_ecr_repository.basic_agent.arn, "*"]
      },
      {
        Sid    = "S3SourceAccess"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.source_asset.arn}/*"
      }
    ]
  })
}

# CodeBuild Project (corresponds to CDK codebuild.Project)
resource "aws_codebuild_project" "agent_image_build" {
  name         = "${var.stack_name}-basic-agent-build"
  description  = "Build basic agent Docker image for ${var.stack_name}"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_LARGE"
    image                      = "aws/codebuild/amazonlinux2-aarch64-standard:3.0"
    type                       = "ARM_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode            = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = data.aws_region.current.id
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.basic_agent.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = var.image_tag
    }

    environment_variable {
      name  = "STACK_NAME"
      value = var.stack_name
    }
  }

  source {
    type     = "S3"
    location = "${aws_s3_bucket.source_asset.bucket}/${aws_s3_object.agent_code.key}"
    buildspec = jsonencode({
      version = "0.2"
      phases = {
        pre_build = {
          commands = [
            "echo Logging in to Amazon ECR...",
            "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
          ]
        }
        build = {
          commands = [
            "echo Build started on `date`",
            "echo Building the Docker image for basic agent ARM64...",
            "docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .",
            "docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG"
          ]
        }
        post_build = {
          commands = [
            "echo Build completed on `date`",
            "echo Pushing the Docker image...",
            "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG",
            "echo ARM64 Docker image pushed successfully"
          ]
        }
      }
    })
  }

  tags = {
    Name = "${var.stack_name}-basic-agent-build"
  }
}

# Lambda IAM Role for Build Trigger
resource "aws_iam_role" "build_trigger_role" {
  name = "${var.stack_name}-build-trigger-role"

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

  tags = {
    Name = "${var.stack_name}-build-trigger-role"
  }
}

# Lambda IAM Policy
resource "aws_iam_role_policy_attachment" "build_trigger_basic" {
  role       = aws_iam_role.build_trigger_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "build_trigger_policy" {
  name = "BuildTriggerPolicy"
  role = aws_iam_role.build_trigger_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "codebuild:StartBuild",
          "codebuild:BatchGetBuilds"
        ]
        Resource = aws_codebuild_project.agent_image_build.arn
      }
    ]
  })
}

# Lambda Function for Build Trigger (corresponds to CDK lambda function)
resource "aws_lambda_function" "build_trigger" {
  filename         = "${path.module}/build_trigger_lambda.zip"
  function_name    = "${var.stack_name}-build-trigger"
  role            = aws_iam_role.build_trigger_role.arn
  handler         = "lambda_function.handler"
  source_code_hash = data.archive_file.build_trigger_lambda.output_base64sha256
  runtime         = "python3.9"
  timeout         = 900

  environment {
    variables = {
      PROJECT_NAME = aws_codebuild_project.agent_image_build.name
    }
  }

  tags = {
    Name = "${var.stack_name}-build-trigger"
  }
}

# Archive Lambda function code
data "archive_file" "build_trigger_lambda" {
  type        = "zip"
  output_path = "${path.module}/build_trigger_lambda.zip"
  
  source {
    content = templatefile("${path.module}/lambda_function.py", {
      # Template variables if needed
    })
    filename = "lambda_function.py"
  }
}

# AgentCore IAM Role (equivalent to CDK AgentCoreRole)
resource "aws_iam_role" "agent_core_role" {
  name = "${var.stack_name}-agentcore-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.stack_name}-agentcore-role"
  }
}

# AgentCore IAM Policy (equivalent to CDK AgentCoreRole policy)
resource "aws_iam_role_policy" "agent_core_policy" {
  name = "AgentCorePolicy"
  role = aws_iam_role.agent_core_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRImageAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = "arn:aws:ecr:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:repository/*"
      },
      {
        Sid    = "ECRTokenAccess"
        Effect = "Allow"
        Action = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogStreams",
          "logs:CreateLogGroup",
          "logs:DescribeLogGroups",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
      },
      {
        Sid    = "XRayPermissions"
        Effect = "Allow"
        Action = [
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "bedrock-agentcore"
          }
        }
      },
      {
        Sid    = "GetAgentAccessToken"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetWorkloadAccessToken",
          "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
          "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
        ]
        Resource = [
          "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:workload-identity-directory/default",
          "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:workload-identity-directory/default/workload-identity/*"
        ]
      },
      {
        Sid    = "BedrockModelInvocation"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:*"
        ]
      }
    ]
  })
}

# Custom Resource to trigger build (using null_resource as approximation)
resource "null_resource" "trigger_build" {
  depends_on = [
    aws_lambda_function.build_trigger,
    aws_s3_object.agent_code
  ]

  triggers = {
    source_code_hash = data.archive_file.agent_code.output_md5
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Starting Docker image build..."
      
      # Create payload file
      echo '{"ProjectName":"${aws_codebuild_project.agent_image_build.name}"}' > payload.json
      
      # Invoke Lambda function - simplified version that just triggers the build
      aws lambda invoke \
        --function-name ${aws_lambda_function.build_trigger.function_name} \
        --cli-read-timeout 900 \
        --cli-connect-timeout 60 \
        --cli-binary-format raw-in-base64-out \
        --payload file://payload.json \
        response.json
      
      # For now, just check if Lambda was invoked successfully
      if [ $? -eq 0 ]; then
        echo "Lambda function invoked successfully"
        echo "Build process initiated - checking results in validation step"
      else
        echo "Failed to invoke Lambda function"
        rm -f payload.json response.json
        exit 1
      fi
      
      rm -f payload.json response.json
      echo "Docker image build trigger completed"
    EOT
  }
}

# Validation resource to ensure image exists before creating AgentCore Runtime
resource "null_resource" "validate_image" {
  depends_on = [null_resource.trigger_build]

  triggers = {
    image_uri = "${aws_ecr_repository.basic_agent.repository_url}:${var.image_tag}"
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Validating Docker image exists in ECR..."
      
      # Check if the image exists in ECR
      aws ecr describe-images \
        --repository-name ${aws_ecr_repository.basic_agent.name} \
        --image-ids imageTag=${var.image_tag} \
        --region ${data.aws_region.current.id}
      
      if [ $? -eq 0 ]; then
        echo "Docker image ${var.image_tag} found in repository ${aws_ecr_repository.basic_agent.name}"
      else
        echo "Docker image ${var.image_tag} not found in repository ${aws_ecr_repository.basic_agent.name}"
        exit 1
      fi
    EOT
  }
}

# BedrockAgentCore Runtime (corresponds to CDK bedrockagentcore.CfnRuntime)
resource "aws_bedrockagentcore_agent_runtime" "agent_runtime" {
  agent_runtime_name = "${replace(var.stack_name, "-", "_")}_${var.agent_name}"
  description        = "Basic agent runtime for ${var.stack_name}"
  role_arn          = aws_iam_role.agent_core_role.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.basic_agent.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = {
    AWS_DEFAULT_REGION = data.aws_region.current.id
  }

  depends_on = [null_resource.validate_image]

  tags = {
    Name = "${var.stack_name}-agent-runtime"
  }
}
