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

variable "enable_https" {
  description = "Enable HTTPS for the load balancer. Requires ssl_certificate_arn to be provided. Set to false to use HTTP only (not recommended for production)."
  type        = bool
  default     = false
}

variable "ssl_certificate_arn" {
  description = "ARN of the SSL certificate to use for HTTPS. Required when enable_https is true. Use AWS Certificate Manager (ACM) to create a certificate. Leave empty to use HTTP only."
  type        = string
  default     = null
  validation {
    condition     = var.enable_https == false || (var.enable_https == true && var.ssl_certificate_arn != null && var.ssl_certificate_arn != "")
    error_message = "ssl_certificate_arn must be provided when enable_https is true. Create a certificate in AWS Certificate Manager (ACM) first."
  }
}
