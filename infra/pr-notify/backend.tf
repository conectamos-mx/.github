# Cuenta prod (114743615563). Un solo stack para toda la org: no hay dev/prod,
# porque cada aviso saldría dos veces.
terraform {
  backend "s3" {
    bucket       = "conectamos-tfstate-prod"
    key          = "pr-notify/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
