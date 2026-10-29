variable "aws_region" {
  description = "AWS region used for the Terraform state bucket."
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Stable project prefix used for bootstrap resources."
  type        = string
  default     = "point-in-time-equity-risk"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deployment role."
  type        = string
  default     = "agalkova/point-in-time-equity-risk"
}

variable "github_environment" {
  description = "Protected GitHub environment used by the deployment workflow."
  type        = string
  default     = "production"
}
