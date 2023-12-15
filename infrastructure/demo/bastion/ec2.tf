
data "aws_ami" "amazon_linux_2" {
  # This is a data source, which means it will not create any resources
  # It will fetch the data from AWS and make it available to use in the code
  # This data source will fetch the latest Amazon Linux 2 AMI for the region specified


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
    values = ["*x86_64*"]
  }
  most_recent = true

}

resource "aws_instance" "bastion" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an EC2 instance
  # The EC2 instance will be created in the VPC and subnet specified
  ami                  = data.aws_ami.amazon_linux_2.id
  instance_type        = var.bastion_ec2_instance_type
  iam_instance_profile = aws_iam_instance_profile.bastion_instance_profile.name
  user_data = base64encode(
    templatefile(
      "${path.module}/bootstrap.tpl",
      {
        web_db_endpoint = var.web_db_endpoint
      }
    )
  )
  vpc_security_group_ids      = [aws_security_group.bastion_sg.id]
  associate_public_ip_address = false # This is set to false because we do not want the bastion host to have a public IP address
  subnet_id                   = var.private_subnets[0].id
  tags                        = merge({ Name = var.bastion_server_name, Module = "Bastion" }, var.tags)

  lifecycle {
    ignore_changes = [
      ami
    ]
  }
}
