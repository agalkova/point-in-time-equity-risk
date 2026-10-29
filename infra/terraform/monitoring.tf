resource "aws_cloudwatch_log_metric_filter" "failures" {
  name           = "${var.project_name}-failures"
  pattern        = "{ $.level = \"ERROR\" }"
  log_group_name = aws_cloudwatch_log_group.workload.name

  metric_transformation {
    name      = "SyntheticPipelineFailures"
    namespace = "PointInTimeEquityRisk"
    value     = "1"
  }
}

resource "aws_sns_topic" "alerts" {
  count = var.alert_email != "" ? 1 : 0
  name  = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "failures" {
  alarm_name          = "${var.project_name}-scheduled-run-failed"
  alarm_description   = "The synthetic Fargate pipeline emitted a structured ERROR event."
  namespace           = "PointInTimeEquityRisk"
  metric_name         = "SyntheticPipelineFailures"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
}

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = var.alert_email != "" ? [var.alert_email] : []
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 80
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = [notification.value]
    }
  }
}

resource "aws_cloudfront_origin_access_control" "status" {
  count = var.enable_status_site ? 1 : 0

  name                              = "${var.project_name}-status"
  description                       = "Private S3 access for the public synthetic status page"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "status" {
  count = var.enable_status_site ? 1 : 0

  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.artifacts.bucket_regional_domain_name
    origin_id                = "artifact-bucket"
    origin_access_control_id = aws_cloudfront_origin_access_control.status[0].id
  }

  default_cache_behavior {
    target_origin_id       = "artifact-bucket"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    min_ttl                = 0
    default_ttl            = 60
    max_ttl                = 300

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "status_bucket" {
  count = var.enable_status_site ? 1 : 0

  statement {
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.artifacts.arn}/index.html",
      "${aws_s3_bucket.artifacts.arn}/${var.artifact_prefix}/status/*"
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.status[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "status" {
  count = var.enable_status_site ? 1 : 0

  bucket = aws_s3_bucket.artifacts.id
  policy = data.aws_iam_policy_document.status_bucket[0].json
}
