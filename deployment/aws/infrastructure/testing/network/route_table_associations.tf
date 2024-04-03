resource "aws_route_table_association" "public" {
  # Associates a subnet with a route table. This association causes traffic originating from the subnet to be routed according to the routes in the route table.
  # This is the public route table association
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  # This is the private route table association
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
