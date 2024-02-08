variable "project_name" {
  description = "value for the project name"
  type        = string
}

variable "environment" {
  description = "value for the environment"
  type        = string
}

variable "billing_code" {
  description = "value for the billing code"
  type        = string
}

variable "resource_tags" {
  description = "map of tags to be applied to all resources"
  type        = map(string)
  default     = {}

}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "af-south-1"

}

variable "demo_profile" {
  description = "AWS profile to use for development"
  type        = string
  default     = "aaq"
}

variable "ec2_instance_type" {
  description = "value for the ec2 instance type"
  type        = string
  default     = "t4g.medium"
}

variable "bastion_ec2_instance_type" {
  description = "value for the bastion host ec2 instance type"
  type        = string
  default     = "t3.nano"
}

variable "rds_db_instance_class" {
  description = "value for the rds db instance class"
  type        = string
  default     = "db.t4g.small"
}
