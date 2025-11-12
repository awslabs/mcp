output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.app.id
}

output "instance_private_ip" {
  description = "EC2 Instance Private IP"
  value       = aws_instance.app.private_ip
}

output "health_check_url" {
  description = "Health check endpoint URL"
  value       = "http://${aws_instance.app.private_ip}:${var.port}${var.health_check_path}"
}

output "buckets_api_url" {
  description = "Buckets API endpoint URL"
  value       = "http://${aws_instance.app.private_ip}:${var.port}/api/buckets"
}

output "ecr_image_uri" {
  description = "ECR image URI used"
  value       = local.ecr_image_uri
}

output "language" {
  description = "Application language"
  value       = var.language
}
