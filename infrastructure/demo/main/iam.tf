data "aws_iam_policy_document" "agent_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "web_instance_role" {
  name               = var.web_ec2_instance_role_name
  assume_role_policy = data.aws_iam_policy_document.agent_assume_role.json
  tags               = merge({ Name = var.web_ec2_instance_role_name, Module = "Web" }, var.tags)
}

# This policy grants the EC2 instance permission to use SSM
resource "aws_iam_role_policy_attachment" "ssm_permissions" {
  role       = aws_iam_role.web_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# This policy grants the EC2 instance permission to use ECS
resource "aws_iam_role_policy_attachment" "ecs_agent_ec2" {
  role       = aws_iam_role.web_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role" "web_task_role" {
  name = var.web_ecs_task_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge({ Name = var.web_ecs_task_role_name, Module = "Web" }, var.tags)
}

data "aws_iam_policy_document" "web_ec2_role_policy" {
  # This statement grants permissions to the EC2 instance to access the following resources:
  # - Secrets Manager
  # - Service Discovery
  # - CloudWatch Logs
  # - ECR
  statement {
    actions = ["secretsmanager:GetSecretValue"]

    resources = [
      aws_secretsmanager_secret.rds_credentials.arn,
      aws_secretsmanager_secret.jwt_secret.arn,
      aws_secretsmanager_secret.content_access_secret.arn,
      aws_secretsmanager_secret.whatsapp_token_secret.arn,
      aws_secretsmanager_secret.open_ai_key_secret.arn,
      aws_secretsmanager_secret.question_answer_secret.arn,
      aws_secretsmanager_secret.whatsapp_verify_token_secret.arn,
    ]

  }

  statement {
    effect = "Allow"
    actions = [
      "servicediscovery:RegisterInstance",
      "servicediscovery:DeregisterInstance",
      "servicediscovery:DiscoverInstances",
      "servicediscovery:GetInstancesHealthStatus",
      "servicediscovery:GetOperation",
      "servicediscovery:ListInstances",
      "servicediscovery:ListNamespaces",
      "servicediscovery:ListServices",
      "servicediscovery:UpdateInstanceCustomHealthStatus",
      "servicediscovery:Get*",
    "servicediscovery:List*"]

    resources = [
      aws_service_discovery_service.backend.arn,
      aws_service_discovery_service.vectordb.arn,
      aws_service_discovery_service.backend.arn
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetRandomPassword",
    "secretsmanager:ListSecrets"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    "logs:DescribeLogStreams"]
    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    actions = ["ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage", ]

    effect    = "Allow"
    resources = [aws_ecr_repository.web_ecr_repo.arn]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecs:DescribeServices",
    "ecs:UpdateService"]
    resources = [aws_ecs_service.admin_app_service.id, aws_ecs_service.backend_service.id, aws_ecs_service.nginx_service.id]
  }

  statement {
    effect = "Allow"

    actions = [
    "ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "web_ec2_role_policy" {
  name   = "${var.web_ec2_instance_role_name}-policy"
  role   = aws_iam_role.web_task_role.id
  policy = data.aws_iam_policy_document.web_ec2_role_policy.json
}
