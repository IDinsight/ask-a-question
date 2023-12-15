
resource "aws_vpc" "vpc" {
  # https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html#VPC_Sizing
  # https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html#vpc-sizing-ipv4
  # The smallest VPC you can create uses a /28 netmask (16 IP addresses), and the largest uses a /16 netmask (65,536 IP addresses).

  enable_dns_support   = true
  enable_dns_hostnames = true                # https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html#vpc-dns-updating
  cidr_block           = "${var.cidr_ip}/16" # 65k IP addresses
  tags                 = merge({ Name = "${var.vpc_name}", Module = "Network" }, var.tags)

}

resource "aws_flow_log" "vpc" {
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-logs-differences
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-logs-iam
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-logs-iam-example

  # The IAM role that's used to publish flow logs to CloudWatch Logs must have the following permissions:
  # logs:CreateLogGroup
  # logs:CreateLogStream
  # logs:PutLogEvents
  # logs:DescribeLogGroups
  # logs:DescribeLogStreams

  # VPC Flow Logs is a network traffic monitoring feature that enables you to capture information about the IP traffic going to and from network interfaces in your VPC (Virtual Private Cloud). 
  iam_role_arn             = aws_iam_role.vpc_flow_logs.arn
  log_destination          = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type             = "ALL"
  vpc_id                   = aws_vpc.vpc.id
  tags                     = merge({ Name = "${var.vpc_flow_log_name_prefix}-flow-logs", Module = "Network" }, var.tags)
  max_aggregation_interval = 60
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-cwl.html
  # The log group must use the following naming format: /aws/vpc/flow-log-id
  name = "${var.vpc_flow_log_name_prefix}-flow-logs-cloudwatch-logs"
  tags = merge({ Name = "${var.vpc_flow_log_name_prefix}-flow-logs", Module = "Network" }, var.tags)

}

resource "aws_iam_role" "vpc_flow_logs" {
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-cwl.html#flow-logs-iam
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-cwl.html#flow-logs-iam-example

  # The IAM role that's used to publish flow logs to CloudWatch Logs must have the following permissions:
  # logs:CreateLogGroup
  # logs:CreateLogStream
  # logs:PutLogEvents
  # logs:DescribeLogGroups
  # logs:DescribeLogStreams
  name = "${var.vpc_flow_log_name_prefix}-flow-logs-iam-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-cwl.html#flow-logs-iam
  # https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-cwl.html#flow-logs-iam-example


  name = "${var.vpc_flow_log_name_prefix}-flow-logs-iam-policy"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = aws_cloudwatch_log_group.vpc_flow_logs.arn
      },
    ]
  })
}
