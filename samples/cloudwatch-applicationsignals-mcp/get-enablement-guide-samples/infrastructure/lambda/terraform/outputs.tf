# Lambda function outputs
output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.function.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.function.arn
}

output "invoke_command" {
  description = "Command to manually invoke the Lambda function"
  value       = "aws lambda invoke --function-name ${aws_lambda_function.function.function_name} --invocation-type Event /dev/stdout"
}
