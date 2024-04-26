# Github OICD provider
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:IDinsight/aaq-core:*"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = var.gh_role_name
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}
# This policy is used to grant the github actions role access to the web-task-role
# It also grants access to ECR and ECS
# This will allow github actions to deploy the application
data "aws_iam_policy_document" "gh_actions_policy_document" {

  statement {
    actions = ["sts:AssumeRole", "iam:GetRole", "iam:PassRole"]
    # Set the web-task-role as the resource
    resources = [aws_iam_role.web_task_role.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
    "ecr:UploadLayerPart"]
    resources = [aws_ecr_repository.web_ecr_repo.arn]
  }

  statement {
    effect = "Allow"
    actions = [
    "ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeTaskDefinition",
    "ecs:RegisterTaskDefinition"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
    "ecs:UpdateService"]
    resources = [
      aws_ecs_service.admin_app_service.id,
      aws_ecs_service.backend_service.id,
      aws_ecs_service.caddy_service.id,
      aws_ecs_service.litellm_proxy_service.id
    ]
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogStream"]
    resources = [
      aws_cloudwatch_log_group.backend.arn,
      aws_cloudwatch_log_group.admin_app.arn,
      aws_cloudwatch_log_group.caddy.arn,
      aws_cloudwatch_log_group.litellm_proxy.arn
    ]
  }
}

resource "aws_iam_policy" "github_actions_resource_policies" {
  name        = var.gh_action_name
  description = "Grant Github Actions access to assume the web-task-role"
  policy      = data.aws_iam_policy_document.gh_actions_policy_document.json
}

resource "aws_iam_role_policy_attachment" "github_actions" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_resource_policies.arn
}
