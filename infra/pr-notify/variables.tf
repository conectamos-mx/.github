variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "repos" {
  description = "Repos (nombre, sin org) cuyos PRs se avisan. Vacío = todos los de la org."
  type        = list(string)
  default     = ["platform-api", "conectamos-platform", "brain", "brightcell-api", "zoe-integration", "os"]
}

variable "deploy_services" {
  description = <<-EOT
    Repos cuyos deploys se avisan, con lo que el evento workflow_run no trae:
    nombre del servicio y URL por entorno (Production = rama main). Un repo que
    no está acá no se avisa. El canal sale de deploy-notify/SLACK_WEBHOOKS.
  EOT
  type = map(object({
    service  = string
    workflow = optional(string, ".github/workflows/deploy.yml")
    prod_url = optional(string, "N/A")
    dev_url  = optional(string, "N/A")
  }))
  default = {
    "platform-api"          = { service = "platform-api", prod_url = "https://platform-api.conectamos.ai", dev_url = "https://platform-api-dev.conectamos.ai" }
    "conectamos-platform"   = { service = "conectamos-platform", prod_url = "https://platform.conectamos.ai", dev_url = "https://platform-dev.conectamos.ai" }
    "brain"                 = { service = "gustavo-integration", prod_url = "https://gustavo.conectamos.ai", dev_url = "https://gustavo-dev.conectamos.ai" }
    "jupiter"               = { service = "llm-gateway", prod_url = "https://jupiter.conectamos.ai" }
    "conectamos-dashboards" = { service = "conectamos-dashboards", prod_url = "https://dashboard.conectamos.ai", dev_url = "https://dashboard-dev.conectamos.ai" }
  }
}
