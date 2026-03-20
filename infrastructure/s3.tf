# =============================================================================
# Amazon S3 — Raw Input and Clean Output Buckets
# =============================================================================

resource "aws_s3_bucket" "raw_images" {
  bucket = "${var.raw_bucket_name}-${var.environment}"

  tags = {
    Component = "storage"
    Purpose   = "raw-input"
  }
}

resource "aws_s3_bucket_versioning" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_images" {
  bucket                  = aws_s3_bucket.raw_images.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Clean Output Bucket ---

resource "aws_s3_bucket" "clean_images" {
  bucket = "${var.clean_bucket_name}-${var.environment}"

  tags = {
    Component = "storage"
    Purpose   = "clean-output"
  }
}

resource "aws_s3_bucket_versioning" "clean_images" {
  bucket = aws_s3_bucket.clean_images.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "clean_images" {
  bucket = aws_s3_bucket.clean_images.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "clean_images" {
  bucket                  = aws_s3_bucket.clean_images.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy — transition old raw data to Glacier after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id

  rule {
    id     = "archive-old-raw"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}
