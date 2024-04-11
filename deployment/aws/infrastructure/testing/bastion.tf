module "bastion_host" {
  source                          = "./bastion"
  bastion_sg_name                 = "${var.project_name}-${var.environment}-db-bastion-sg"
  bastion_instance_profile_name   = "${var.project_name}-${var.environment}-db-bastion-instance-profile"
  bastion_instance_role_name      = "${var.project_name}-${var.environment}-db-bastion-instance-role"
  bastion_server_name             = "${var.project_name}-${var.environment}-db-bastion-host"
  private_subnets                 = module.vpc.private_subnets
  interface_endpoints_sg_id       = module.vpc.interface_endpoints_sg_id
  bastion_ec2_instance_type       = var.bastion_ec2_instance_type
  tags                            = local.required_tags
  vpc_id                          = module.vpc.vpc_id
  web_db_sg_id                    = module.main.web_db_sg_id
  web_db_endpoint                 = module.main.web_db_endpoint
  s3_vpc_endpoint_prefix_list_ids = module.vpc.s3_vpc_endpoint_prefix_list
}
