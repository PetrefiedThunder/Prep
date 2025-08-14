terraform {
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
  required_version = ">= 1.5.0"
}
provider "aws" { region = var.region }

variable "region" { type = string, default = "us-west-2" }

# TODO: RDS, ECS/Lambda, S3, CloudFront, WAF, Secrets Manager
