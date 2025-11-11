# AgentCore Runtime Outputs (corresponds to CDK CfnOutput)
output "agent_runtime_id" {
  description = "ID of the created agent runtime (corresponds to CDK AgentRuntimeId)"
  value       = aws_bedrockagentcore_agent_runtime.agent_runtime.agent_runtime_id
}

output "agent_runtime_arn" {
  description = "ARN of the created agent runtime (corresponds to CDK AgentRuntimeArn)"
  value       = aws_bedrockagentcore_agent_runtime.agent_runtime.agent_runtime_arn
}

output "agent_role_arn" {
  description = "ARN of the agent execution role (corresponds to CDK AgentRoleArn)"
  value       = aws_iam_role.agent_core_role.arn
}

# Additional useful outputs
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.basic_agent.repository_url
}

output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = aws_codebuild_project.agent_image_build.name
}

output "lambda_function_name" {
  description = "Name of the build trigger Lambda function"
  value       = aws_lambda_function.build_trigger.function_name
}

output "s3_source_bucket" {
  description = "Name of the S3 bucket for source code"
  value       = aws_s3_bucket.source_asset.bucket
}
