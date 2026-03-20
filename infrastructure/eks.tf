# =============================================================================
# Amazon EKS Cluster with GPU Node Group
# =============================================================================

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.eks_cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Cluster access
  cluster_endpoint_public_access  = var.environment == "qa" ? true : false
  cluster_endpoint_private_access = true

  # Managed node groups
  eks_managed_node_groups = {
    # System node group (non-GPU, for Argo controller, etc.)
    system = {
      instance_types = ["m5.large"]
      min_size       = 1
      max_size       = 3
      desired_size   = 1

      labels = {
        role = "system"
      }
    }

    # GPU node group (for MAP de-identification workers)
    gpu-workers = {
      instance_types = var.eks_gpu_instance_types
      capacity_type  = "SPOT"

      min_size     = var.eks_gpu_min_size
      max_size     = var.eks_gpu_max_size
      desired_size = var.eks_gpu_desired_size

      ami_type = "AL2_x86_64_GPU"

      labels = {
        role                = "gpu-worker"
        "nvidia.com/gpu"    = "true"
        "kubernetes.io/spot" = "true"
      }

      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  tags = {
    Component = "compute"
  }
}
