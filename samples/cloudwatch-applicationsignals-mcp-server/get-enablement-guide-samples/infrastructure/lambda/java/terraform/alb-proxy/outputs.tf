output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "URL of the load balancer"
  value       = "http://${aws_lb.main.dns_name}"
}