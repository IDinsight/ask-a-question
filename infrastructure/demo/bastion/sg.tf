resource "aws_security_group" "bastion_sg" {
  # This is the security group for the bastion host
  # It allows egress to the interface endpoints security group
  # It allows egress to the web database security group
  vpc_id = var.vpc_id
  name   = var.bastion_sg_name
  tags   = merge({ Name = var.bastion_sg_name, Module = "Bastion" }, var.tags)
}

resource "aws_security_group_rule" "bastion_sg_interface_endpoints_egress" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = var.interface_endpoints_sg_id
  security_group_id        = aws_security_group.bastion_sg.id
}

<<<<<<< HEAD
=======
resource "aws_security_group_rule" "bastion_sg_s3_prefix_list_egress" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.bastion_sg.id
  prefix_list_ids   = [var.s3_vpc_endpoint_prefix_list_ids, ]
}


>>>>>>> main

# The following rule allows the bastion host to connect to the application database
resource "aws_security_group_rule" "bastion_to_web_db_egress" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.bastion_sg.id
  source_security_group_id = var.web_db_sg_id
}
