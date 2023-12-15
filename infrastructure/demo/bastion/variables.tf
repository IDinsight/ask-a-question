variable "bastion_sg_name" {
  description = "value for the bastion security group name"
  type        = string
}

variable "bastion_instance_profile_name" {
  description = "value for the bastion instance profile name"
  type        = string

}

variable "bastion_server_name" {
  description = "value for the bastion server name"
  type        = string

}

variable "private_subnets" {
  description = "value for the private subnets"
  type        = list(any)

}

variable "interface_endpoints_sg_id" {
  description = "value for the interface endpoints security group id"
  type        = string

}

variable "bastion_ec2_instance_type" {
  description = "value for the bastion host ec2 instance type"
  type        = string
  default     = "t3.nano"
}

variable "tags" {
  description = "map of tags to be applied to all resources"
  type        = map(string)
  default     = {}

}

variable "vpc_id" {
  description = "value for the vpc id"
  type        = string

}

variable "web_db_sg_id" {
  description = "value for the web database security group id"
  type        = string

}

variable "web_db_endpoint" {
  description = "value for the web database endpoint"
  type        = string

}

variable "bastion_instance_role_name" {
  description = "value for the bastion instance role name"
  type        = string

}

