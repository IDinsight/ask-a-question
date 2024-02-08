variable "vpc_name" {
  description = "value for the vpc name"
  type        = string
  default     = ""

}
variable "vpc_flow_log_name_prefix" {
  description = "value for the vpc flow log name prefix"
  type        = string
  default     = ""

}
variable "public_subnet_name" {
  description = "value for the public subnet name"
  type        = string
  default     = ""

}
variable "private_subnet_name" {
  description = "value for the private subnet name"
  type        = string
  default     = ""

}
variable "db_subnet_group_name" {
  description = "value for the postgres database subnet group name"
  type        = string
  default     = ""

}
variable "elasticache_subnet_group_name" {
  description = "value for the elasticache subnet group name"
  type        = string
  default     = ""

}
variable "private_route_table_name" {
  description = "value for the private route table name"
  type        = string
  default     = ""

}
variable "public_route_table_name" {
  description = "value for the public route table name"
  type        = string
  default     = ""

}
variable "tags" {
  description = "map of tags to be applied to all resources"
  type        = map(string)
  default     = {}

}
variable "public_subnet_count" {
  description = "value for the public subnet count"
  type        = number
  default     = 2

}
variable "private_subnet_count" {
  description = "value for the private subnet count"
  type        = number
  default     = 2

}
variable "region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "af-south-1"

}

variable "cidr_ip" {
  description = "value for the cidr ip. CIDR (Classless Inter-Domain Routing) is a method used to allocate IP addresses and route IP packets"
  type        = string
  default     = "10.0.0.0"

}
variable "interface_endpoints_sg_name" {
  description = "value for the interface endpoints security group name"
  type        = string
  default     = ""

}

variable "bastion_sg_id" {
  description = "value for the bastion security group id"
  type        = string
  default     = ""

}

variable "web_ec2_sg_id" {
  description = "value for the web ec2 instance security group id"
  type        = string
  default     = ""

}
<<<<<<< HEAD
=======

variable "session_manager_prefs_name" {
  description = "value for the session manager preferences name"
  type        = string
  default     = ""

}
>>>>>>> main
