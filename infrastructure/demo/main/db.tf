data "aws_rds_engine_version" "postgres" {
  # The latest version of Postgres is used for the RDS instance.
  engine             = "postgres"
  preferred_versions = ["15.3"]
}

resource "aws_db_instance" "web_db" {
  # The RDS instance is created.
  # The RDS instance is created in the private subnet.
  # The RDS instance is not publicly accessible.
  # The RDS instance is encrypted.
  identifier                 = var.rds_db_instance_identifier
  allocated_storage          = 60
  port                       = 5432
  instance_class             = var.rds_db_instance_class
  storage_type               = "gp2"
  backup_retention_period    = 7
  db_name                    = var.rds_db_name
  engine                     = "postgres"
  engine_version             = data.aws_rds_engine_version.postgres.version
  storage_encrypted          = true
  db_subnet_group_name       = var.db_subnet_group_name
  vpc_security_group_ids     = [aws_security_group.web_db_sg.id]
  tags                       = merge({ Name = var.rds_db_instance_identifier, Module = "Web" }, var.tags)
  username                   = var.rds_master_username
  password                   = random_password.web_db.result
  skip_final_snapshot        = true
  auto_minor_version_upgrade = false

}
