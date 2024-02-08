# This file creates the VPC endpoints for SSM, EC2 Messages, and SSM Messages.
# The SSM endpoints are used to connect to the EC2 instances using SSM Session Manager.
# The EC2 Messages and SSM Messages endpoints are used to connect to the EC2 instances using SSM Run Command.
# The SSM endpoints are created in the private subnets.
# The SSM endpoints are created with the security group that allows traffic from the bastion host.
# The SSM endpoints are created with private DNS enabled.
# The SSM endpoints are created with the SSM Session Manager preferences document. This document sets the maximum session duration to 12 hours and the idle session timeout to 1 hour.
resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.vpc.id
  service_name        = "com.amazonaws.${var.region}.ssm"
  tags                = merge({ Module = "Network" }, var.tags)
  subnet_ids          = aws_subnet.private[*].id
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.interface_endpoints_sg.id]
}

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id              = aws_vpc.vpc.id
  service_name        = "com.amazonaws.${var.region}.ec2messages"
  tags                = merge({ Module = "Network" }, var.tags)
  subnet_ids          = aws_subnet.private[*].id
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.interface_endpoints_sg.id]
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id              = aws_vpc.vpc.id
  service_name        = "com.amazonaws.${var.region}.ssmmessages"
  tags                = merge({ Module = "Network" }, var.tags)
  subnet_ids          = aws_subnet.private[*].id
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.interface_endpoints_sg.id]
}

resource "aws_ssm_document" "session_manager_prefs" {
  name            = var.session_manager_prefs_name
  document_type   = "Session"
  document_format = "JSON"

  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Document to hold regional settings for Session Manager"
    sessionType   = "Standard_Stream"
    inputs = {

      maxSessionDuration = 720,
      idleSessionTimeout = 60

    }
  })
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.vpc.id
  service_name = "com.amazonaws.${var.region}.s3"
  tags         = merge({ Module = "Network" }, var.tags)
  route_table_ids = [
    aws_route_table.private.id,
    aws_route_table.public.id
  ]
}

resource "aws_vpc_endpoint_policy" "vpc_endpoint_s3_access" {
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action = [
          "*"
        ],
        Resource = [
          "arn:aws:s3:::amazonlinux.${var.region}.amazonaws.com",
          "arn:aws:s3:::amazonlinux.${var.region}.amazonaws.com/*",
          "arn:aws:s3:::amazonlinux-2-repos-${var.region}",
          "arn:aws:s3:::amazonlinux-2-repos-${var.region}/*"
        ]
      },
  ] })
}
