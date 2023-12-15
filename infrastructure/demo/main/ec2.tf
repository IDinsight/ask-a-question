
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
  vpc  = true
  tags = merge({ Name = var.web_ec2_server_name, Module = "Web" }, var.tags)

}


resource "aws_iam_instance_profile" "web_instance_profile" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an IAM instance profile
  # The IAM instance profile will be attached to the EC2 instance
  name = var.web_instance_profile_name
  role = aws_iam_role.web_instance_role.name
}

resource "aws_launch_template" "web_server" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create a launch template
  # The launch template will be used by the autoscaling group to create EC2 instances
  image_id               = data.aws_ami.amazon_linux_2.id
  instance_type          = var.web_ec2_instance_type
  vpc_security_group_ids = [aws_security_group.web_ec2_sg.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.web_instance_profile.name
  }

  user_data = base64encode(
    templatefile(
      "${path.module}/bootstrap.tpl",
      {
        cluster_name = aws_ecs_cluster.web_cluster.name
      }
    )
  )
  tag_specifications {
    resource_type = "instance"
    tags          = merge({ Name = var.web_ec2_server_name, Module = "Web" }, var.tags)
  }
  lifecycle {
    ignore_changes = [
      image_id
    ]
  }
}
