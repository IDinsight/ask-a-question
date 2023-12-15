resource "aws_security_group" "web_ec2_sg" {
  # This is the security group for the web ec2 instance

  vpc_id = var.vpc_id
  name   = var.web_ec2_sg_name
  tags   = merge({ Name = var.web_ec2_sg_name, Module = "Web" }, var.tags)
}

resource "aws_security_group_rule" "web_ec2_sg_ingress" {
  # This is the security group rule for the web ec2 instance
  # The security group rule allows ingress traffic on the ports specified in the variable ec2_sg_ingress_ports

  count             = length(var.ec2_sg_ingress_ports)
  type              = "ingress"
  from_port         = var.ec2_sg_ingress_ports[count.index]
  to_port           = var.ec2_sg_ingress_ports[count.index]
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web_ec2_sg.id
}

resource "aws_security_group_rule" "web_ec2_sg_egress" {
  # This is the security group rule for the web ec2 instance
  # The security group rule allows egress traffic on the ports specified in the variable ec2_sg_egress_ports
  count             = length(var.ec2_sg_egress_ports)
  type              = "egress"
  from_port         = var.ec2_sg_egress_ports[count.index]
  to_port           = var.ec2_sg_egress_ports[count.index]
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web_ec2_sg.id
}

resource "aws_security_group_rule" "web_ec2_sg_interface_endpoints_sg_egress" {
  # This is the security group rule for the web ec2 instance
  # The rule allows egress traffic to the interface endpoints security group on port 443
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web_ec2_sg.id
  source_security_group_id = var.interface_endpoints_sg_id
}

resource "aws_security_group" "web_db_sg" {
  # This is the security group for the web db instance
  # The security group allows ingress traffic from the bastion security group and the web ec2 security group on port 5432
  vpc_id = var.vpc_id
  name   = var.db_sg_name
  tags   = merge({ Name = var.db_sg_name, Module = "Web" }, var.tags)
}

resource "aws_security_group_rule" "bastion_to_web_db_ingress" {
  # This is the security group rule for the web db instance
  # The security group rule allows ingress traffic from the bastion security group on port 5432
  # This allows the db to be accessed from the bastion host
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web_db_sg.id
  source_security_group_id = var.bastion_sg_id
}

resource "aws_security_group_rule" "ec2_to_web_db_ingress" {
  # This is the security group rule for the web db instance
  # The security group rule allows ingress traffic from the web ec2 security group on port 5432
  # This allows the db to be accessed from the web ec2 instance
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web_db_sg.id
  source_security_group_id = aws_security_group.web_ec2_sg.id
}

resource "aws_security_group_rule" "ec2_to_web_db_egress" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web_ec2_sg.id
  source_security_group_id = aws_security_group.web_db_sg.id
}
