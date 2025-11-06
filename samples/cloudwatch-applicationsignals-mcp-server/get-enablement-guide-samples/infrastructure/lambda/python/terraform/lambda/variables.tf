variable "function_name" {
  type        = string
  description = "Name of sample app function / ALB"
  default     = "awslabs-sample-python-terraform"
}

variable "runtime" {
  type        = string
  description = "Python runtime version used for sample Lambda Function"
  default     = "python3.12"
}

variable "architecture" {
  type        = string
  description = "Lambda function architecture, valid values are arm64 or x86_64"
  default     = "x86_64"
}