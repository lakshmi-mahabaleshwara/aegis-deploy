# =============================================================================
# Aegis Deploy — Terraform Infrastructure
# =============================================================================
# Main configuration: provider, backend, and module composition.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in S3 (configure bucket before first apply)
  backend "s3" {
    bucket         = "aegis-terraform-state"
    key            = "aegis-deploy/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "aegis-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aegis-deploy"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
