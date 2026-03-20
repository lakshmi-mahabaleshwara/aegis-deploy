# =============================================================================
# Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (qa, prod)"
  type        = string
  default     = "qa"
  validation {
    condition     = contains(["qa", "prod"], var.environment)
    error_message = "Environment must be 'qa' or 'prod'."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "aegis-deploy"
}

# --- EKS ---
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.29"
}

variable "eks_gpu_instance_types" {
  description = "GPU instance types for the EKS node group"
  type        = list(string)
  default     = ["g4dn.xlarge", "g4dn.2xlarge"]
}

variable "eks_gpu_min_size" {
  description = "Minimum number of GPU nodes"
  type        = number
  default     = 0
}

variable "eks_gpu_max_size" {
  description = "Maximum number of GPU nodes"
  type        = number
  default     = 4
}

variable "eks_gpu_desired_size" {
  description = "Desired number of GPU nodes"
  type        = number
  default     = 0
}

# --- S3 ---
variable "raw_bucket_name" {
  description = "S3 bucket for raw input images"
  type        = string
  default     = "aegis-raw-images"
}

variable "clean_bucket_name" {
  description = "S3 bucket for de-identified output images"
  type        = string
  default     = "aegis-clean-images"
}

# --- RDS ---
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Database name for the Identity Vault"
  type        = string
  default     = "aegis_vault"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "aegis"
}

# --- Networking ---
variable "vpc_id" {
  description = "VPC ID for EKS and RDS placement"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EKS nodes and RDS"
  type        = list(string)
}
