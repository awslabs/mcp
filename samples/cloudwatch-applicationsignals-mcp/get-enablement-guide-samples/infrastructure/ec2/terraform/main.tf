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

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_iam_role" "app_role" {
  name_prefix = "${var.app_name}-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_readonly" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "ssm_managed_instance" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "app_profile" {
  name_prefix = "${var.app_name}-profile-"
  role        = aws_iam_role.app_role.name
}

resource "aws_security_group" "app_sg" {
  name_prefix = "${var.app_name}-sg-"
  description = "Security group for ${var.app_name}"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Allow HTTPS for ECR, AWS APIs, and package repositories"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow HTTP for package repositories"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow DNS queries"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow DNS queries over TCP"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-sg"
  }
}

data "aws_caller_identity" "current" {}

locals {
  ecr_image_uri = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.image_name}:latest"

  user_data = <<-EOF
              #!/bin/bash
              set -e

              yum update -y
              yum install -y docker

              systemctl start docker
              systemctl enable docker
              usermod -a -G docker ec2-user

              echo "Waiting for Docker to be ready..."
              for i in {1..30}; do
                if docker info >/dev/null 2>&1; then
                  echo "Docker is ready"
                  break
                fi
                if [ $i -eq 30 ]; then
                  echo "Docker failed to become ready after 60 seconds"
                  exit 1
                fi
                echo "Waiting for Docker... ($i/30)"
                sleep 2
              done

              aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com

              docker pull ${local.ecr_image_uri}

              docker run -d --name ${var.app_name} \
                -p ${var.port}:${var.port} \
                -e PORT=${var.port} \
                -e AWS_REGION=${var.aws_region} \
                ${local.ecr_image_uri}

              echo "Waiting for application to be ready..."
              for i in {1..30}; do
                if curl -f http://localhost:${var.port}${var.health_check_path} >/dev/null 2>&1; then
                  echo "Application is healthy"
                  break
                fi
                if [ $i -eq 30 ]; then
                  echo "Application failed to become healthy after 60 seconds"
                  docker logs ${var.app_name}
                  exit 1
                fi
                echo "Waiting for application to be ready... ($i/30)"
                sleep 2
              done

              docker exec -d ${var.app_name} bash /app/generate-traffic.sh

              echo "Application deployed and traffic generation started"
              EOF
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t2.small"
  iam_instance_profile   = aws_iam_instance_profile.app_profile.name
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  subnet_id              = tolist(data.aws_subnets.default.ids)[0]
  ebs_optimized          = true
  monitoring             = true

  user_data = local.user_data

  root_block_device {
    encrypted = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tags = {
    Name     = var.app_name
    Language = var.language
  }
}
