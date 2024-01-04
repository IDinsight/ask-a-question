
data "aws_ami" "amazon_linux_2" {

  owners = ["amazon"]

  filter {
    name   = "owner-alias"
    values = ["amazon"]
  }

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm*"]
  }

  filter {
    name   = "name"
    values = ["*arm64*"]
  }
  most_recent = true

}

resource "aws_eip" "web_eip" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an Elastic IP
  # The Elastic IP will be attached to the EC2 instance
  vpc      = true
  instance = aws_instance.web_instance.id
  tags     = merge({ Name = var.web_ec2_server_name, Module = "Web" }, var.tags)

}


resource "aws_instance" "web_instance" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an EC2 instance
  # The EC2 instance will be created in the VPC
  instance_type          = var.web_ec2_instance_type
  ami                    = data.aws_ami.amazon_linux_2.id
  iam_instance_profile   = aws_iam_instance_profile.web_instance_profile.id
  vpc_security_group_ids = [aws_security_group.web_ec2_sg.id]

  user_data = base64encode(
    templatefile(
      "${path.module}/bootstrap.tpl",
      {
        cluster_name = aws_ecs_cluster.web_cluster.name
      }
    )
  )
  subnet_id = var.public_subnets[0].id
  tags      = merge({ Name = var.web_instance_profile_name, Module = "Web" }, var.tags)
}

resource "aws_iam_instance_profile" "web_instance_profile" {
  # This is the instance profile that will be attached to the EC2 instance
  # The instance profile is a container for the role
  # The instance profile is then attached to the EC2 instance

  name = var.web_instance_profile_name
  role = aws_iam_role.web_instance_role.name
}
