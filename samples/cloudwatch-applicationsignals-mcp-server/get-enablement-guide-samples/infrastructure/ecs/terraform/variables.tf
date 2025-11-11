variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "image_name" {
  description = "Name of the ECR repository/image"
  type        = string
}

variable "language" {
  description = "Programming language of the application"
  type        = string
}

variable "port" {
  description = "Port number the application listens on"
  type        = number
}


variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "service_name" {
  description = "Name of the ECS service"
  type        = string
}
