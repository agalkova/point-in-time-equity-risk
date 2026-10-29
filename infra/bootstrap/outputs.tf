output "github_deploy_role_arn" {
  description = "Store this value as the GitHub variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}

output "terraform_state_bucket" {
  description = "Store this value as the GitHub variable TF_STATE_BUCKET."
  value       = aws_s3_bucket.terraform_state.id
}

output "aws_region" {
  description = "Store this value as the GitHub variable AWS_REGION."
  value       = var.aws_region
}
