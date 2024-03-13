resource "aws_route_table" "public" {
  # A route table contains a set of rules, called routes, that are used to determine where network traffic is directed.
  # A route table must be associated with one or more subnets in the VPC.
  # A subnet can only be associated with one route table at a time, but you can associate multiple subnets with the same route table.
  # The route table directs traffic from the subnet to the internet gateway or other peered VPCs, NAT gateways, NAT instances, VPC endpoints, or network interface.
  # This is the public route table
  vpc_id = aws_vpc.vpc.id
  tags   = merge({ Name = var.public_route_table_name, Module = "Network" }, var.tags)
}

resource "aws_route_table" "private" {
  # This is the private route table
  vpc_id = aws_vpc.vpc.id
  tags   = merge({ Name = var.private_route_table_name, Module = "Network" }, var.tags)

}
