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
  name               = "github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}


data "aws_iam_policy_document" "gh_actions_policy_document_frontend" {
  statement {
    actions = ["sts:AssumeRole", "iam:GetRole", "iam:PassRole"]
    # Set the web-task-role as the resource
    resources = [aws_iam_role.web_task_role.arn]
  }



  statement {
    effect = "Allow"

    actions = [
      "ecr:CompleteLayerUpload",
      "ecr:GetAuthorizationToken",
      "ecr:UploadLayerPart",
      "ecr:InitiateLayerUpload",
      "ecr:BatchCheckLayerAvailability",
    "ecr:PutImage"]
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
    resources = [aws_ecs_service.admin_app_service.id, aws_ecs_service.backend_service.id, aws_ecs_service.nginx_service.id]
  }
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogStream"]
    resources = ["*"]
  }

}



resource "aws_iam_policy" "github_actions_resource_policies_frontend" {
  name        = "github-actions-role-policy"
  description = "Grant Github Actions access to assume the web-task-role"
  policy      = data.aws_iam_policy_document.gh_actions_policy_document_frontend.json
}
