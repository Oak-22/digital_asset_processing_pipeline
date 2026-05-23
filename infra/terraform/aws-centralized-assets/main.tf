locals {
  # Tags are resource metadata for cloud inventory/filtering. They are
  # not resource prefixes or directory namespaces.
  common_tags = merge(
    {
      Project      = "creative-workflow-batch-transformation-pipeline"
      Architecture = "centralized-source-assets-local-analytic-outputs"
      ManagedBy    = "terraform"
      Environment  = var.environment
    },
    var.tags
  )
}

# The full Terraform resource address is:
#   aws_s3_bucket.source_assets
# `source_assets` is the local Terraform name for this bucket resource.
# Reusing the same local name across related resource types is a mental
# grouping convention, not a standalone group object.
resource "aws_s3_bucket" "source_assets" {
  # These are attributes of the S3 bucket resource itself.
  bucket        = var.bucket_name
  force_destroy = var.force_destroy

  tags = local.common_tags
}

# Separate Terraform resources can still configure the same conceptual
# bucket. They reference the bucket through attributes like `.id`.
resource "aws_s3_bucket_versioning" "source_assets" {
  bucket = aws_s3_bucket.source_assets.id

  versioning_configuration {
    status="Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source_assets" {
  bucket = aws_s3_bucket.source_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "source_assets" {
  bucket = aws_s3_bucket.source_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# These lifecycle rules operate by prefix convention inside one bucket.
# The prefixes (`raw/`, `xmp/`, `jpeg/`) are logical separations rather
# than separate buckets.
# Current-version transitions and noncurrent-version transitions are
# handled separately by S3 once versioning is enabled.
# This policy is currently archival/non-destructive: objects move to
# colder storage classes over time, but no expiration/deletion rules are
# declared here.
resource "aws_s3_bucket_lifecycle_configuration" "source_assets" {
  bucket = aws_s3_bucket.source_assets.id

  rule {
    id     = "raw-masters-lifecycle"
    status = "Enabled"

    filter {
      prefix = var.raw_prefix
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    # These rules apply only after an older object version becomes
    # noncurrent because a newer version replaced it at the same key.
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 180
      storage_class   = "GLACIER"
    }
  }

  rule {
    id     = "xmp-snapshots-lifecycle"
    status = "Enabled"

    filter {
      prefix = var.xmp_prefix
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
  }

  rule {
    id     = "jpeg-companions-lifecycle"
    status = "Enabled"

    filter {
      prefix = var.jpeg_prefix
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
