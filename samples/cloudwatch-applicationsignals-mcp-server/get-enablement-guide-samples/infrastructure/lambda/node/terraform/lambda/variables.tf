variable "function_name" {
  type        = string
  description = "Name of sample app function / ALB"
  default     = "awslabs-sample-nodejs-terraform"
}

variable "runtime" {
  type        = string
  description = "NodeJS runtime version used for sample Lambda Function"
  default     = "nodejs20.x"
}

variable "architecture" {
  type        = string
  description = "Lambda function architecture, valid values are arm64 or x86_64"
  default     = "x86_64"
}
