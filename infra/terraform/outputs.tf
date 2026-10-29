output "ecr_repository_url" {
  value = aws_ecr_repository.workload.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.synthetic.arn
}

output "artifact_bucket" {
  value = aws_s3_bucket.artifacts.id
}

output "artifact_prefix" {
  value = var.artifact_prefix
}

output "subnet_ids" {
  value = aws_subnet.public[*].id
}

output "security_group_id" {
  value = aws_security_group.task.id
}

output "status_url" {
  value = var.enable_status_site ? "https://${aws_cloudfront_distribution.status[0].domain_name}" : null
}
