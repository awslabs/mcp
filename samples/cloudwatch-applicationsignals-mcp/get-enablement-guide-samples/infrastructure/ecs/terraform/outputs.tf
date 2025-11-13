output "cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "ECS Service Name"
  value       = aws_ecs_service.app.name
}

output "ecr_image_uri" {
  description = "ECR image URI used"
  value       = local.ecr_image_uri
}

output "language" {
  description = "Application language"
  value       = var.language
}
