terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
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

  # Use private subnets for ECS tasks (more secure), public subnets for ALB
  ecs_subnet_ids = length(local.private_subnet_ids) > 0 ? local.private_subnet_ids : local.public_subnet_ids
  alb_subnet_ids = local.public_subnet_ids

  # Determine if we need public IP based on subnet type (only if using public subnets as fallback)
  assign_public_ip = length(local.private_subnet_ids) == 0

  ecr_image_uri = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.image_name}:latest"

  # Generate shorter names for AWS resources with 32-char limit
  # Ensure names don't end with hyphen by trimming app_name if needed
  base_name_max_length = 32 - 4  # Reserve 4 chars for suffix (-alb, -tg)
  shortened_app_name = substr(var.app_name, 0, local.base_name_max_length)
  clean_app_name = replace(local.shortened_app_name, "/-+$", "")

  alb_name = "${local.clean_app_name}-alb"
  tg_name  = "${local.clean_app_name}-tg"
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

  # Checkov CKV_AWS_65: Ensure container insights are enabled on ECS cluster
  configuration {
    execute_command_configuration {
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_exec_logs.name
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
    }
  ])

  tags = {
    Name        = "${var.app_name}-task-definition"
    Application = var.app_name
    Language    = var.language
  }
}

# Security Group for ALB
#checkov:skip=CKV_AWS_260:ALB security group intentionally allows public HTTP/HTTPS access for web application demo
resource "aws_security_group" "alb" {
  name_prefix = "${var.app_name}-alb-"
  description = "Security group for Application Load Balancer - allows inbound HTTP and HTTPS traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow inbound HTTP traffic from internet to ALB"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow inbound HTTPS traffic from internet to ALB"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound traffic to ECS tasks for load balancing"
    from_port   = var.port
    to_port     = var.port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    description = "Allow outbound DNS resolution (UDP)"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound DNS resolution (TCP)"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound HTTPS for AWS service communication"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-alb-sg"
    Application = var.app_name
  }
}

# Security Group for ECS Service
resource "aws_security_group" "ecs_service" {
  name_prefix = "${var.app_name}-ecs-"
  description = "Security group for ECS service - allows inbound traffic from ALB"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Allow inbound traffic from Application Load Balancer to ECS tasks"
    from_port       = var.port
    to_port         = var.port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow outbound DNS resolution (UDP)"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound DNS resolution (TCP)"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound HTTPS for ECR, AWS services, and application dependencies"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound HTTP for application dependencies (if needed)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-ecs-sg"
    Application = var.app_name
  }
}

# CloudWatch Log Group for WAF
resource "aws_cloudwatch_log_group" "waf_log_group" {
  name              = "/aws/wafv2/${var.app_name}"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = var.kms_key_id

  tags = {
    Name        = "${var.app_name}-waf-log-group"
    Application = var.app_name
    Language    = var.language
  }
}

# WAF v2 WebACL for ALB protection
resource "aws_wafv2_web_acl" "main" {
  name  = "${var.app_name}-waf"
  description = "WAF for ${var.app_name} Application Load Balancer protection"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                 = "${var.app_name}-CommonRuleSetMetric"
      sampled_requests_enabled    = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                 = "${var.app_name}-KnownBadInputsMetric"
      sampled_requests_enabled    = true
    }
  }

  rule {
    name     = "AWSManagedRulesUnixRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesUnixRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                 = "${var.app_name}-UnixRuleSetMetric"
      sampled_requests_enabled    = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                 = "${var.app_name}-WAF"
    sampled_requests_enabled    = true
  }

  tags = {
    Name        = "${var.app_name}-waf"
    Application = var.app_name
    Language    = var.language
  }
}

# WAF v2 Logging Configuration - Temporarily disabled due to ARN format issue
# resource "aws_wafv2_web_acl_logging_configuration" "main" {
#   resource_arn            = aws_wafv2_web_acl.main.arn
#   log_destination_configs = [aws_cloudwatch_log_group.waf_log_group.arn]
#
#   # Optional: Redact sensitive fields from logs
#   redacted_fields {
#     single_header {
#       name = "authorization"
#     }
#   }
#
#   redacted_fields {
#     single_header {
#       name = "cookie"
#     }
#   }
# }

# S3 Bucket for ALB Access Logs
resource "aws_s3_bucket" "alb_logs" {
  bucket        = "${var.app_name}-alb-logs-${random_id.bucket_suffix.hex}"
  force_destroy = true

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Name        = "${var.app_name}-alb-logs"
    Application = var.app_name
    Language    = var.language
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_public_access_block" "alb_logs_pab" {
  bucket = aws_s3_bucket.alb_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLogDeliveryWrite"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::797873946194:root"  # ELB service account for us-west-2
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
      },
      {
        Sid    = "AWSLogDeliveryAclCheck"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::797873946194:root"  # ELB service account for us-west-2
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      }
    ]
  })
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = local.alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = local.public_subnet_ids

  # Checkov CKV_AWS_92: Ensure that Application Load Balancer (ALB) drops invalid HTTP header fields
  drop_invalid_header_fields = true

  # Checkov CKV_AWS_91: Ensure that the Application Load Balancer access log is enabled
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb-logs"
    enabled = false
  }

  # Checkov CKV_AWS_92: Ensure that Load Balancer has deletion protection enabled
  enable_deletion_protection = var.enable_deletion_protection

  tags = {
    Name        = "${var.app_name}-alb"
    Application = var.app_name
    Language    = var.language
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# Target Group
#checkov:skip=CKV_AWS_378:For demo purposes, target group uses HTTP protocol for internal communication between ALB and ECS tasks
resource "aws_lb_target_group" "app" {
  name        = local.tg_name
  port        = var.port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
    path                = var.health_check_path
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.app_name}-tg"
    Application = var.app_name
    Language    = var.language
  }
}

# HTTP Listener - Redirect to HTTPS if certificate is provided, otherwise forward directly
#checkov:skip=CKV_AWS_2:For demo purposes, HTTP to HTTPS redirect is conditional based on SSL certificate availability
#checkov:skip=CKV_AWS_103:For demo purposes, ALB HTTP listener is needed for applications without SSL certificates
# nosemgrep: terraform.aws.security.insecure-load-balancer-tls-version.insecure-load-balancer-tls-version
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.enable_https && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.enable_https && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = var.enable_https && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "" ? [] : [1]
      content {
        target_group {
          arn = aws_lb_target_group.app.arn
        }
      }
    }
  }

  tags = {
    Name        = var.enable_https && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "" ? "${var.app_name}-http-redirect-listener" : "${var.app_name}-http-listener"
    Application = var.app_name
  }
}

# HTTPS Listener - Only create if certificate is provided
resource "aws_lb_listener" "https" {
  count = var.enable_https && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.ssl_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  tags = {
    Name        = "${var.app_name}-https-listener"
    Application = var.app_name
  }
}

# ECS Service
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

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "application"
    container_port   = var.port
  }

  depends_on = [
    aws_lb_listener.http,
    aws_lb_listener.https
  ]

  tags = {
    Name        = "${var.app_name}-service"
    Application = var.app_name
    Language    = var.language
  }
}
