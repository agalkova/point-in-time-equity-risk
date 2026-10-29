variable "aws_region" {
  description = "AWS region for the workload."
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Stable prefix for all workload resources."
  type        = string
  default     = "point-in-time-equity-risk"
}

variable "image_tag" {
  description = "Immutable container tag, normally the Git commit SHA."
  type        = string
  default     = "bootstrap"
}

variable "git_commit_sha" {
  description = "Full Git commit represented by the deployed image."
  type        = string
  default     = "unknown"
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression for the synthetic proof run."
  type        = string
  default     = "cron(15 23 ? * MON-FRI *)"
}

variable "schedule_state" {
  description = "Set to ENABLED only after the image has been pushed and smoke-tested."
  type        = string
  default     = "DISABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.schedule_state)
    error_message = "schedule_state must be ENABLED or DISABLED."
  }
}

variable "artifact_prefix" {
  description = "S3 prefix for immutable runs and the latest status pointer."
  type        = string
  default     = "synthetic"
}

variable "alert_email" {
  description = "Optional email for CloudWatch and budget alerts. Confirmation is required by AWS."
  type        = string
  default     = ""
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget for the demonstration environment."
  type        = number
  default     = 10
}

variable "enable_status_site" {
  description = "Publish a read-only CloudFront page backed by the private artifact bucket."
  type        = bool
  default     = true
}

variable "allow_destroy_artifacts" {
  description = "Allow Terraform to remove a non-empty artifact bucket. Keep false outside disposable demos."
  type        = bool
  default     = false
}
