resource "aws_cloudwatch_log_group" "workload" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.project_name}-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${var.project_name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "task" {
  statement {
    sid = "ArtifactBucketMetadata"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]
    resources = [aws_s3_bucket.artifacts.arn]
  }

  statement {
    sid = "SyntheticArtifacts"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = ["${aws_s3_bucket.artifacts.arn}/${var.artifact_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "${var.project_name}-artifact-publication"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}

resource "aws_ecs_cluster" "main" {
  name = var.project_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "synthetic" {
  family                   = "${var.project_name}-synthetic"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "synthetic-pipeline"
    image     = "${aws_ecr_repository.workload.repository_url}:${var.image_tag}"
    essential = true
    environment = [
      { name = "ARTIFACT_BUCKET", value = aws_s3_bucket.artifacts.id },
      { name = "ARTIFACT_PREFIX", value = var.artifact_prefix },
      { name = "GIT_COMMIT_SHA", value = var.git_commit_sha },
      { name = "IMAGE_URI", value = "${aws_ecr_repository.workload.repository_url}:${var.image_tag}" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.workload.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "synthetic"
      }
    }
    readonlyRootFilesystem = true
    linuxParameters = {
      initProcessEnabled = true
    }
    mountPoints = [{
      sourceVolume  = "output"
      containerPath = "/app/output"
      readOnly      = false
    }]
  }])

  volume {
    name = "output"
  }
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.project_name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.synthetic.arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.task.arn,
      aws_iam_role.task_execution.arn
    ]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${var.project_name}-run-task"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

resource "aws_scheduler_schedule" "synthetic" {
  name                = "${var.project_name}-synthetic"
  description         = "Runs the public synthetic risk-pipeline proof on weekdays"
  schedule_expression = var.schedule_expression
  state               = var.schedule_state

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.synthetic.arn
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        assign_public_ip = true
        security_groups  = [aws_security_group.task.id]
        subnets          = aws_subnet.public[*].id
      }
    }

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 1
    }
  }
}
