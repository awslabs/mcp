variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "config_file" {
  description = "Path to the Lambda configuration JSON file (relative to config/ directory)"
  type        = string
}
