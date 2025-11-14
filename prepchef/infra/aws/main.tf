terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "prepchef-terraform-state"
    key            = "aws/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "prepchef-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type = string
}

variable "db_subnet_group_name" {
  type = string
}

variable "db_security_group_ids" {
  type = list(string)
}

variable "app_bucket_name" {
  type = string
}

variable "lambda_function_name" {
  type    = string
  default = "app-function"
}

variable "lambda_handler" {
  type    = string
  default = "index.handler"
}

variable "lambda_runtime" {
  type    = string
  default = "python3.11"
}

variable "lambda_code_key" {
  type = string
}

variable "cloudfront_price_class" {
  type    = string
  default = "PriceClass_All"
}

locals {
  static_dir   = "${path.module}/../../dist"
  static_files = try(fileset(local.static_dir, "**"), [])
  mime_types = {
    css          = "text/css"
    html         = "text/html"
    ico          = "image/x-icon"
    js           = "application/javascript"
    json         = "application/json"
    map          = "application/json"
    png          = "image/png"
    svg          = "image/svg+xml"
    txt          = "text/plain"
    webmanifest  = "application/manifest+json"
  }
}

# S3 bucket for static assets and Lambda code
resource "aws_s3_bucket" "app" {
  bucket = var.app_bucket_name
}

resource "aws_s3_object" "static_site" {
  for_each = { for file in local.static_files : file => file }

  bucket       = aws_s3_bucket.app.id
  key          = each.value
  source       = "${local.static_dir}/${each.value}"
  etag         = filemd5("${local.static_dir}/${each.value}")
  content_type = lookup(
    local.mime_types,
    lower(element(split(".", each.value), length(split(".", each.value)) - 1)),
    "application/octet-stream"
  )
}

# Lambda execution role
resource "aws_iam_role" "lambda" {
  name = "${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda function
resource "aws_lambda_function" "app" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda.arn
  handler       = var.lambda_handler
  runtime       = var.lambda_runtime
  s3_bucket     = aws_s3_bucket.app.id
  s3_key        = var.lambda_code_key
}

# Secrets Manager for DB credentials
resource "aws_secretsmanager_secret" "db" {
  name = "${var.environment}/db"
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}

# RDS Postgres instance
resource "aws_db_instance" "postgres" {
  identifier             = "${var.environment}-postgres"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15.2"
  instance_class         = var.db_instance_class
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.db_security_group_ids
  name                   = var.db_name
  username               = var.db_username
  password               = var.db_password
  skip_final_snapshot    = true
}

# CloudFront distribution fronting the S3 bucket
resource "aws_cloudfront_distribution" "cdn" {
  origin {
    domain_name = aws_s3_bucket.app.bucket_regional_domain_name
    origin_id   = "s3-app"
  }

  enabled             = true
  default_root_object = "index.html"

  default_cache_behavior {
    target_origin_id       = "s3-app"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  price_class = var.cloudfront_price_class

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  web_acl_id = aws_wafv2_web_acl.cdn.arn
}

# WAF to protect CloudFront
resource "aws_wafv2_web_acl" "cdn" {
  provider = aws.us_east_1

  name  = "${var.environment}-waf"
  scope = "CLOUDFRONT"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.environment}-waf"
    sampled_requests_enabled   = true
  }
}

