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

variable "kms_key_id" {
  description = "The ARN of the KMS Key to use when encrypting log data. If not provided, uses the default AWS managed key for CloudWatch Logs."
  type        = string
  default     = null
}

variable "log_retention_in_days" {
  description = "Number of days to retain log events in the CloudWatch log group. Must be at least 365 days (1 year) for security compliance."
  type        = number
  default     = 365
  validation {
    condition     = var.log_retention_in_days >= 365
    error_message = "Log retention must be at least 365 days (1 year) for security compliance."
  }
}
