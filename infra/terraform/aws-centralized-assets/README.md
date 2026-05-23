# AWS Centralized Assets Terraform

This Terraform root module provisions a realistic baseline for the
architecture recorded in ADR 0001:

- one centralized S3 bucket for source assets
- separate logical prefixes for RAW masters, XMP sidecars, and optional
  rendered JPEG companions
- local scripts and analytic outputs remain outside the bucket

## What It Creates

- one S3 bucket
- bucket versioning
- bucket-wide server-side encryption
- bucket public-access blocking
- lifecycle rules for:
  - RAW masters
  - XMP sidecars
  - JPEG companions

## Prefix Convention

The design uses one bucket with separate prefixes rather than separate
buckets by default:

- `raw/`
- `xmp/`
- `jpeg/`

These prefixes are conventions for source-asset separation. S3 does not
enforce folder semantics itself, but the outputs from this module make
those canonical URIs explicit.

## Usage

```bash
cd infra/terraform/aws-centralized-assets
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Notes

- This module does not upload any assets.
- It provisions the storage boundary only.
- The Stage 1 verifier/extractor can later target the bucket and these
  prefixes directly.
