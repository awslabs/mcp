terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "aws" {
}

# Data source to get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Data source to get default VPC
data "aws_vpc" "default" {
  default = true
}

# Data source to get default VPC subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Data source to get subnet details
data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

# Get private and public subnets
locals {
  # Prefer private subnets for security, fallback to public if no private subnets available
  private_subnet_ids = [
    for subnet in data.aws_subnet.default :
    subnet.id if !subnet.map_public_ip_on_launch
  ]

  public_subnet_ids = [
    for subnet in data.aws_subnet.default :
    subnet.id if subnet.map_public_ip_on_launch
  ]

  # Use private subnets for ECS tasks (more secure), public subnets as fallback
  ecs_subnet_ids = length(local.private_subnet_ids) > 0 ? local.private_subnet_ids : local.public_subnet_ids

  # Determine if we need public IP based on subnet type (only if using public subnets as fallback)
  assign_public_ip = length(local.private_subnet_ids) == 0

  ecr_image_uri = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.image_name}:latest"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app_log_group" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = var.kms_key_id

  tags = {
    Name        = "${var.app_name}-log-group"
    Application = var.app_name
    Language    = var.language
  }
}

# CloudWatch Log Group for curl sidecar
resource "aws_cloudwatch_log_group" "curl_log_group" {
  name              = "/ecs/${var.app_name}-curl"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = var.kms_key_id

  tags = {
    Name        = "${var.app_name}-curl-log-group"
    Application = var.app_name
    Language    = var.language
  }
}

# IAM Task Execution Role
resource "aws_iam_role" "task_execution_role" {
  name = "${var.app_name}-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-task-execution-role"
    Application = var.app_name
  }
}

# Attach the AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "task_execution_role_policy" {
  role       = aws_iam_role.task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Task Role
resource "aws_iam_role" "task_role" {
  name = "${var.app_name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-task-role"
    Application = var.app_name
  }
}

# Attach S3 policy for the application functionality
resource "aws_iam_role_policy_attachment" "task_role_s3_policy" {
  role       = aws_iam_role.task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      kms_key_id = var.kms_key_id

      log_configuration {
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs_exec_logs.name
        cloud_watch_encryption_enabled = true
      }
      logging = "OVERRIDE"
    }
  }

  tags = {
    Name        = "${var.app_name}-cluster"
    Application = var.app_name
    Language    = var.language
  }
}

# CloudWatch Log Group for ECS Exec
resource "aws_cloudwatch_log_group" "ecs_exec_logs" {
  name              = "/aws/ecs/exec/${var.app_name}-cluster"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = var.kms_key_id

  tags = {
    Name        = "${var.app_name}-ecs-exec-log-group"
    Application = var.app_name
    Language    = var.language
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution_role.arn
  task_role_arn           = aws_iam_role.task_role.arn

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([
    {
      name                = "application"
      image               = local.ecr_image_uri
      essential           = true
      memory              = 512
      readonlyRootFilesystem = true

      environment = [
        {
          name  = "PORT"
          value = tostring(var.port)
        }
      ]

      portMappings = [
        {
          containerPort = var.port
          protocol      = "tcp"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "tmp"
          containerPath = "/tmp"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app_log_group.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "app"
        }
      }
    },
    {
      name      = "curl-sidecar"
      image     = "curlimages/curl:8.1.2"
      essential = false
      memory    = 128

      command = [
        "sh", "-c",
        "echo 'Starting curl sidecar...'; sleep 30; while true; do echo \"$(date): Curling localhost:${var.port}/api/buckets\"; curl -f localhost:${var.port}/api/buckets || echo 'Curl failed'; sleep 60; done"
      ]

      dependsOn = [
        {
          containerName = "application"
          condition     = "START"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.curl_log_group.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "curl"
        }
      }
    }
  ])

  tags = {
    Name        = "${var.app_name}-task-definition"
    Application = var.app_name
    Language    = var.language
  }
}

# Security Group for ECS Service
resource "aws_security_group" "ecs_service" {
  name_prefix = "${var.app_name}-ecs-"
  description = "Security group for ECS service - allows limited outbound access for ECS operations"
  vpc_id      = data.aws_vpc.default.id

  # HTTPS for ECR image pulls and AWS API calls
  egress {
    description = "HTTPS for ECR and AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP for package downloads (if needed)
  egress {
    description = "HTTP for package downloads"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS resolution
  egress {
    description = "DNS UDP"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS resolution TCP (for large queries)
  egress {
    description = "DNS TCP"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-ecs-sg"
    Application = var.app_name
  }
}

# ECS Service (without load balancer)
resource "aws_ecs_service" "app" {
  name            = var.app_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_service.id]
    subnets         = local.ecs_subnet_ids
    assign_public_ip = local.assign_public_ip
  }

  tags = {
    Name        = "${var.app_name}-service"
    Application = var.app_name
    Language    = var.language
  }
}
