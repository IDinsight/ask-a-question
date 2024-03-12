resource "aws_security_group" "interface_endpoints_sg" {
  vpc_id = aws_vpc.vpc.id
  name   = var.interface_endpoints_sg_name
  tags   = merge({ Name = var.interface_endpoints_sg_name, Module = "Network" }, var.tags)
}

resource "aws_security_group_rule" "bastion_to_vpce_ingress" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.interface_endpoints_sg.id
  source_security_group_id = var.bastion_sg_id
}

resource "aws_security_group_rule" "web_to_vpce_ingress" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.interface_endpoints_sg.id
  source_security_group_id = var.web_ec2_sg_id
}
