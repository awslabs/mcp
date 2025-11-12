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
  validation {
    condition     = var.port > 0 && var.port <= 65535
    error_message = "Port must be between 1 and 65535."
  }
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
