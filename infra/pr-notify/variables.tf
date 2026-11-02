variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "repos" {
  description = "Repos (nombre, sin org) cuyos PRs se avisan. Vacío = todos los de la org."
  type        = list(string)
  default     = ["platform-api", "conectamos-platform", "brain", "brightcell-api", "zoe-integration", "os"]
}
