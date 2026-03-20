# =============================================================================
# AWS Secrets Manager — Token Salt & DB Credentials
# =============================================================================

resource "aws_secretsmanager_secret" "token_salt" {
  name        = "${var.project_name}/${var.environment}/token-salt"
  description = "Aegis de-identification token salt for deterministic hashing"

  tags = {
    Component = "security"
  }
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/${var.environment}/db-credentials"
  description = "Identity Vault database credentials"

  tags = {
    Component = "security"
  }
}

# Note: Secret values should be set manually or via CI/CD — never in Terraform code.
# Use: aws secretsmanager put-secret-value --secret-id <arn> --secret-string '...'
