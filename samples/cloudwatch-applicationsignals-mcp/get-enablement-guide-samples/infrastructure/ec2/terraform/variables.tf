variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "image_name" {
  description = "ECR image name"
  type        = string
}

variable "language" {
  description = "Programming language of the application"
  type        = string
}

variable "port" {
  description = "Application port"
  type        = number
}

variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
