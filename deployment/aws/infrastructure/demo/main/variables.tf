variable "rds_db_instance_identifier" {
  description = "value for the rds db instance identifier"
  type        = string
  default     = ""
}

variable "rds_db_instance_class" {
  description = "value for the rds db instance class"
  type        = string
  default     = ""
}

variable "rds_db_name" {
  description = "value for the rds db name"
  type        = string
  default     = ""
}

variable "rds_master_username" {
  description = "value for the rds master username"
  type        = string
  default     = ""
}

variable "rds_master_password" {
  description = "value for the rds master password"
  type        = string
  default     = ""
}

variable "db_subnet_group_name" {
  description = "value for the postgres database subnet group name"
  type        = string
  default     = ""
}

variable "rds_credentials_secret_name" {
  description = "value for the rds credentials secret name"
  type        = string
  default     = ""
}

variable "db_sg_name" {
  description = "value for the db security group name"
  type        = string
  default     = ""
}

variable "bastion_sg_id" {
  description = "value for the bastion security group id"
  type        = string
  default     = ""
}

variable "ecr_repo_name" {
  description = "value for the ecr repository name"
  type        = string
  default     = ""
}

variable "web_ecs_cluster_name" {
  description = "value for the wweb ecs cluster name"
  type        = string
  default     = ""
}

variable "web_task_role" {
  description = "value for the web task role"
  type        = string
  default     = ""
}

variable "web_task_execution_role" {
  description = "value for the web task execution role"
  type        = string
  default     = ""
}

variable "private_subnets" {
  description = "value for the private subnets"
  type        = list(any)
  default     = []
}

variable "cidr_block" {
  description = "value for the cidr block"
  type        = string
  default     = ""
}

variable "tags" {
  description = "map of tags to be applied to all resources"
  type        = map(string)
  default     = {}
}

variable "region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "af-south-1"
}

variable "web_ecs_task_role_name" {
  description = "value for the web ecs task role name"
  type        = string
  default     = ""
}

variable "web_ec2_instance_role_name" {
  description = "value for the web ec2 instance role name"
  type        = string
  default     = ""
}

variable "web_instance_profile_name" {
  description = "value for the web instance profile name"
  type        = string
  default     = ""
}

variable "web_ec2_server_name" {
  description = "value for the web ec2 server name"
  type        = string
  default     = ""
}

variable "web_asg_name" {
  description = "value for the web asg name"
  type        = string
  default     = ""
}

variable "web_ec2_instance_type" {
  description = "value for the web ec2 instance type"
  type        = string
  default     = ""
}

variable "public_subnets" {
  description = "value for the public subnets"
  type        = list(any)
  default     = []
}

variable "web_ec2_sg_name" {
  description = "value for the web ec2 instance security group name"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "value for the vpc id"
  type        = string
  default     = ""
}

variable "ec2_sg_ingress_ports" {
  type        = list(number)
  default     = [80, 443, 53]
  description = "value for the ec2 security group ingress ports"
}

variable "ec2_sg_egress_ports" {
  type        = list(number)
  default     = [80, 443, 53]
  description = "value for the ec2 security group egress ports"
}

variable "interface_endpoints_sg_id" {
  description = "value for the interface endpoints security group id"
  type        = string
  default     = ""
}

variable "jwt_secret_secret_name" {
  description = "value for the jwt secret secret name"
  type        = string
  default     = ""
}

variable "content_access_secret_name" {
  description = "value for the content access secret name"
  type        = string
  default     = ""
}

variable "whatsapp_token_secret_name" {
  description = "value for the whatsapp token secret name"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "af-south-1"
}

variable "account_id" {
  description = "AWS account id"
  type        = string
  default     = ""
}

variable "open_ai_key_secret_name" {
  type        = string
  description = "value for the open ai key secret name"
}

variable "question_answer_secret_name" {
  type        = string
  description = "value for the question answer secret name"
}

variable "whatsapp_verify_token_secret_name" {
  type        = string
  description = "value for the whatsapp verify token secret name"
}

variable "private_dns_namespace_name" {
  type        = string
  description = "value for the private dns namespace name"
}

variable "environment" {
  type        = string
  description = "value for the environment"
}

variable "project_name" {
  type        = string
  description = "value for the project name"
}

variable "gh_action_name" {
  type        = string
  description = "value for the github action name"
}

variable "gh_role_name" {
  type        = string
  description = "value for the github role name"
}
