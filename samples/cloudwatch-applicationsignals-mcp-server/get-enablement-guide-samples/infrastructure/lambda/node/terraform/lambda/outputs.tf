output "alb-url" {
  value = module.alb.alb_url
}

output "function_role_name" {
  value = module.hello-lambda-function.lambda_role_name
}
