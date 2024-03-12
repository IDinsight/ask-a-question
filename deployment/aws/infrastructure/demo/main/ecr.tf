resource "aws_ecr_repository" "web_ecr_repo" {
  name         = var.ecr_repo_name
  force_delete = true
  tags         = merge({ Name = var.ecr_repo_name, Module = "Web" }, var.tags)
}
