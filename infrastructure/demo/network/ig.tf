
resource "aws_internet_gateway" "default" {
  # The internet gateway is a logical entity that provides a target in your VPC. 
  # It represents the Amazon VPC side of a connection to the public internet.

  vpc_id = aws_vpc.vpc.id
  tags   = merge({ Module = "Network" }, var.tags)
}
