variable "name" {
  type        = string
  description = "Name of ALB to create"
}

variable "function_arn" {
  type        = string
  description = "ARN of function to proxy to"
}