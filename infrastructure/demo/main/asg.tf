resource "aws_autoscaling_group" "web_instance_asg" {
  name                = var.web_asg_name
  vpc_zone_identifier = var.public_subnets

  launch_template {
    id      = aws_launch_template.web_server.id
    version = "$Latest"
  }

  desired_capacity  = 1
  min_size          = 0
  max_size          = 1
  health_check_type = "EC2"
}
