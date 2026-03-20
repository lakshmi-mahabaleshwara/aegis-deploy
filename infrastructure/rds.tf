# =============================================================================
# Amazon RDS — Identity Vault (PostgreSQL)
# =============================================================================
# Placed in a private subnet. Only accessible by EKS worker pods.
# =============================================================================

resource "aws_db_subnet_group" "vault" {
  name       = "${var.project_name}-vault-${var.environment}"
  subnet_ids = var.private_subnet_ids

  tags = {
    Component = "database"
  }
}

resource "aws_security_group" "vault" {
  name_prefix = "${var.project_name}-vault-"
  vpc_id      = var.vpc_id
  description = "Identity Vault — access restricted to EKS pods only"

  # Ingress: PostgreSQL from EKS security group only
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_primary_security_group_id]
    description     = "PostgreSQL from EKS cluster"
  }

  # No public egress needed for the vault
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound for updates"
  }

  tags = {
    Component = "database"
  }
}

resource "aws_db_instance" "vault" {
  identifier = "${var.project_name}-vault-${var.environment}"

  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  # Password managed via AWS Secrets Manager (see secrets.tf)
  manage_master_user_password = true

  # Network isolation
  db_subnet_group_name   = aws_db_subnet_group.vault.name
  vpc_security_group_ids = [aws_security_group.vault.id]
  publicly_accessible    = false

  # Storage
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  storage_type          = "gp3"

  # Backup & maintenance
  backup_retention_period = 7
  skip_final_snapshot     = var.environment == "qa"
  deletion_protection     = var.environment == "prod"

  tags = {
    Component = "database"
    Purpose   = "identity-vault"
  }
}
