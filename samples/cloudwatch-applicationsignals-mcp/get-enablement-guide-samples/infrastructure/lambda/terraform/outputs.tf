# Lambda function outputs
output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.function.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.function.arn
}

# API Gateway outputs
output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = aws_apigatewayv2_stage.stage.invoke_url
}

output "api_gateway_endpoints" {
  description = "API Gateway endpoints"
  value = {
    health_url  = "${aws_apigatewayv2_stage.stage.invoke_url}health"
    buckets_url = "${aws_apigatewayv2_stage.stage.invoke_url}api/buckets"
  }
}
