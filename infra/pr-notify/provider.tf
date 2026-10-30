terraform {
  required_version = ">= 1.10" # use_lockfile del backend S3

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "pr-notify"
      ManagedBy = "terraform"
    }
  }
}
