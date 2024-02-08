resource "aws_db_subnet_group" "default" {
  name       = var.db_subnet_group_name
  subnet_ids = aws_subnet.private[*].id
  tags       = merge({ Name = var.db_subnet_group_name, Module = "Network" }, var.tags)
}

