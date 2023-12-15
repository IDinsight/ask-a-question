output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "interface_endpoints_sg_id" {
  value = aws_security_group.interface_endpoints_sg.id
}

output "db_subnet_group_name" {
  value = aws_db_subnet_group.default.name
}

output "private_subnets_cidr_blocks" {
  value = aws_subnet.private[*].cidr_block
}

output "public_subnets" {
  value = aws_subnet.public
}

output "private_subnets" {
  value = aws_subnet.private
}

output "private_subnets_ids" {
  value = aws_subnet.private[*].id
}

output "public_subnets_ids" {
  value = aws_subnet.public[*].id
}

output "cidr_block" {
  value = aws_vpc.vpc.cidr_block
}
