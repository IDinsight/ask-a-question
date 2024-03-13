resource "aws_route" "public" {
  # A route is the rule, or set of rules, that is used to determine where network traffic is directed.
  # This is the public route. It directs traffic from the subnet to the internet gateway.
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.default.id
}
