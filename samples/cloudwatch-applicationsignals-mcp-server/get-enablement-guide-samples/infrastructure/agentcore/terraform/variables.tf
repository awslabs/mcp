variable "stack_name" {
  description = "Name of the stack (corresponds to CDK stack name)"
  type        = string
  default     = "AgentCoreRuntimeStack"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "agent_name" {
  description = "Name for the agent runtime (corresponds to CDK AgentName parameter)"
  type        = string
  default     = "BasicAgent"
}

variable "image_tag" {
  description = "Tag for the Docker image (corresponds to CDK ImageTag parameter)"
  type        = string
  default     = "latest"
}

variable "network_mode" {
  description = "Network mode for AgentCore resources (corresponds to CDK NetworkMode parameter)"
  type        = string
  default     = "PUBLIC"
  
  validation {
    condition     = contains(["PUBLIC", "PRIVATE"], var.network_mode)
    error_message = "Network mode must be either PUBLIC or PRIVATE."
  }
}
