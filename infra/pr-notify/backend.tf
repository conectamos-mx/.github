# State en el mismo bucket que brain y jupiter (cuenta AI). Un solo stack para
# toda la org: no hay dev/prod, porque cada aviso saldría dos veces.
terraform {
  backend "s3" {
    bucket       = "conectamos-tfstate-ai"
    key          = "pr-notify/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
