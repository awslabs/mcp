output "cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "ECS Service Name"
  value       = aws_ecs_service.app.name
}

output "load_balancer_dns" {
  description = "Application Load Balancer DNS Name"
  value       = aws_lb.main.dns_name
}

output "health_check_url" {
  description = "Health Check Endpoint URL"
  value       = "http://${aws_lb.main.dns_name}:${var.port}${var.health_check_path}"
}

output "buckets_api_url" {
  description = "Buckets API Endpoint URL"
  value       = "http://${aws_lb.main.dns_name}:${var.port}/api/buckets"
}

output "ecr_image_uri" {
  description = "ECR image URI used"
  value       = local.ecr_image_uri
}

output "language" {
  description = "Application language"
  value       = var.language
}
