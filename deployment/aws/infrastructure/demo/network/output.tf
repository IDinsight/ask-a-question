output "vpc_id" {
  value       = aws_vpc.vpc.id
  description = "value for the vpc id"
}

output "interface_endpoints_sg_id" {
  value       = aws_security_group.interface_endpoints_sg.id
  description = "value for the interface endpoints security group id"
}

output "db_subnet_group_name" {
  value       = aws_db_subnet_group.default.name
  description = "value for the postgres database subnet group name"
}

output "private_subnets_cidr_blocks" {
  value       = aws_subnet.private[*].cidr_block
  description = "value for the private subnets cidr blocks"
}

output "public_subnets" {
  value       = aws_subnet.public
  description = "value for the public subnets"
}

output "private_subnets" {
  value       = aws_subnet.private
  description = "value for the private subnets"
}

output "private_subnets_ids" {
  value       = aws_subnet.private[*].id
  description = "value for the private subnets ids"
}

output "public_subnets_ids" {
  value       = aws_subnet.public[*].id
  description = "value for the public subnets ids"
}

output "cidr_block" {
  value       = aws_vpc.vpc.cidr_block
  description = "value for the vpc cidr block"
}

output "s3_vpc_endpoint_prefix_list" {
  value = aws_vpc_endpoint.s3.prefix_list_id
}
