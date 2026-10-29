terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    key          = "point-in-time-equity-risk/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "Terraform"
      Workload  = "synthetic-demonstration"
    }
  }
}
