resource "random_password" "web_db" {
  # A random password is generated for the RDS instance.
  # This password is then stored in AWS Secrets Manager.
  length  = 16
  special = false
}

resource "random_password" "secrets" {
  # A random password is generated for the JWT secret.
  # This password is then stored in AWS Secrets Manager.
  length  = 16
  special = true
  count   = 5 # 3 passwords are generated
}



resource "aws_secretsmanager_secret" "rds_credentials" {
  # AWS Secrets Manager is used to store the RDS credentials.
  # The secret is then used by the application to connect to the database.

  name                    = var.rds_credentials_secret_name
  tags                    = merge({ Name = var.rds_credentials_secret_name, Module = "Web" }, var.tags)
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "rds_credentials" {
  # The secret version is created for the RDS credentials.
  # The secret version is then used by the application to connect to the database.

  secret_id = aws_secretsmanager_secret.rds_credentials.id
  secret_string = jsonencode({
    username = aws_db_instance.web_db.username,
    password = random_password.web_db.result,
    engine   = aws_db_instance.web_db.engine,
    host     = aws_db_instance.web_db.address,
    dbname   = aws_db_instance.web_db.db_name,
    port     = aws_db_instance.web_db.port,
  })
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  # AWS Secrets Manager is used to store the JWT secret.
  # The secret is then used by the application to generate JWT tokens.

  name                    = var.jwt_secret_secret_name
  tags                    = merge({ Name = var.jwt_secret_secret_name, Module = "Web" }, var.tags)
  recovery_window_in_days = 0

}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  # The secret version is created for the JWT secret.
  # The secret version is then used by the application to generate JWT tokens.
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = random_password.secrets[0].result
}

# secret for access content
resource "aws_secretsmanager_secret" "content_access_secret" {
  # AWS Secrets Manager is used to store the access secret.

  name                    = var.content_access_secret_name
  tags                    = merge({ Name = var.content_access_secret_name, Module = "Web" }, var.tags)
  recovery_window_in_days = 0

}

resource "aws_secretsmanager_secret_version" "content_access_secret" {
  # The secret version is created for the access secret.
  secret_id = aws_secretsmanager_secret.content_access_secret.id
  secret_string = jsonencode({
    full_access_password = random_password.secrets[1].result,
    read_only_password   = random_password.secrets[2].result,
  })
}

# whatsapp token secret
resource "aws_secretsmanager_secret" "whatsapp_token_secret" {
  # AWS Secrets Manager is used to store the whatsapp token secret.

  name                    = var.whatsapp_token_secret_name
  tags                    = merge({ Name = var.whatsapp_token_secret_name, Module = "Web" }, var.tags)
  recovery_window_in_days = 0

}

resource "aws_secretsmanager_secret_version" "whatsapp_token_secret" {
  # The secret version is created for the whatsapp token secret.
  # The value will be added manually to the secret version.
  secret_id = aws_secretsmanager_secret.whatsapp_token_secret.id
  secret_string = jsonencode({
    verify_token = random_password.secrets[3].result,
    token        = random_password.secrets[4].result,
  })


}
