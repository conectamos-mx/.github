output "webhook_url" {
  description = "Payload URL del webhook de la org conectamos-mx"
  value       = aws_lambda_function_url.pr_notify.function_url
}
