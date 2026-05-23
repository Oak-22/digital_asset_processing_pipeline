output "bucket_name" {
  description = "Centralized source-assets bucket name."
  value       = aws_s3_bucket.source_assets.bucket
}

# Outputs publish useful post-provision values for humans or for
# downstream Terraform/config consumers.
output "bucket_arn" {
  description = "ARN of the centralized source-assets bucket."
  value       = aws_s3_bucket.source_assets.arn
}

output "bucket_uri" {
  description = "S3 URI of the centralized source-assets bucket."
  value       = "s3://${aws_s3_bucket.source_assets.bucket}"
}

output "raw_prefix_uri" {
  description = "Canonical S3 URI for RAW masters."
  value       = "s3://${aws_s3_bucket.source_assets.bucket}/${var.raw_prefix}"
}

output "xmp_prefix_uri" {
  description = "Canonical S3 URI for XMP sidecars or metadata snapshots."
  value       = "s3://${aws_s3_bucket.source_assets.bucket}/${var.xmp_prefix}"
}

output "jpeg_prefix_uri" {
  description = "Canonical S3 URI for optional JPEG companions."
  value       = "s3://${aws_s3_bucket.source_assets.bucket}/${var.jpeg_prefix}"
}
