resource "aws_subnet" "public" {
  # The subnet is a range of IP addresses in your VPC. You can launch AWS resources into a specified subnet.
  # Use a public subnet for resources that must be connected to the internet
  count                   = var.public_subnet_count
  vpc_id                  = aws_vpc.vpc.id
  tags                    = merge({ Name = "${var.public_subnet_name}-${count.index + 1}", Type = "public", Module = "Network" }, var.tags)
  availability_zone       = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  cidr_block              = cidrsubnet(aws_vpc.vpc.cidr_block, 8, count.index)
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  # Use a private subnet for resources that won't be connected to the internet
  count                   = var.private_subnet_count
  vpc_id                  = aws_vpc.vpc.id
  tags                    = merge({ Name = "${var.private_subnet_name}-${count.index + 1}", Type = "private", Module = "Network" }, var.tags)
  availability_zone       = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  cidr_block              = cidrsubnet(aws_vpc.vpc.cidr_block, 8, count.index + var.public_subnet_count)
  map_public_ip_on_launch = true
}
