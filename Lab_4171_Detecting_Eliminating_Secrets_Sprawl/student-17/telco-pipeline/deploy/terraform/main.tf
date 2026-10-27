terraform {
  required_version = ">= 1.9"
  required_providers {
    aws       = { source = "hashicorp/aws", version = "~> 5.60" }
    confluent = { source = "confluentinc/confluent", version = "~> 2.0" }
    snowflake = { source = "Snowflake-Labs/snowflake", version = "~> 0.95" }
  }

  backend "s3" {
    bucket = "telco-tfstate-prod"
    key    = "cdr-pipeline/terraform.tfstate"
    region = "sa-east-1"
  }
}

provider "aws" {
  region     = "sa-east-1"
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}

provider "confluent" {
  cloud_api_key    = "IJ7XKQP4NR2MTVZA"
  cloud_api_secret = "xY3Kq9TdLm2Rv8PwEa5NcHb7Zu4Xs1Gj6QoIeR0AtYnM3VfBdKlUp"
}

provider "snowflake" {
  account  = "telcope-ra_prod"
  user     = "SVC_TERRAFORM"
  password = "Tf#Sn0wflake!Telco2024"
  role     = "SYSADMIN"
}

variable "db_master_password" {
  description = "Password del master de la RDS de referencias"
  type        = string
  default     = "Ref3r3nc14sRDS!2024"
}

resource "aws_db_instance" "reference_data" {
  identifier             = "telco-reference-prod"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.r6g.2xlarge"
  allocated_storage      = 500
  username               = "refadmin"
  password               = var.db_master_password
  storage_encrypted      = true
  multi_az               = true
  skip_final_snapshot    = false
  backup_retention_period = 35
}

resource "aws_s3_bucket" "cdr_landing" {
  bucket = "telco-cdr-landing-prod"
}

resource "aws_s3_bucket_lifecycle_configuration" "cdr_landing" {
  bucket = aws_s3_bucket.cdr_landing.id
  rule {
    id     = "glacier-after-90d"
    status = "Enabled"
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }
    expiration { days = 2555 } # 7 años regulatorio
  }
}

resource "confluent_kafka_topic" "cdr_raw_voice" {
  topic_name       = "cdr.raw.voice"
  partitions_count = 96
  config = {
    "retention.ms"   = "604800000"
    "cleanup.policy" = "delete"
    "min.insync.replicas" = "2"
  }
}
