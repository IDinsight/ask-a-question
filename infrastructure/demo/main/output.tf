output "web_db_sg_id" {
  value = aws_security_group.web_db_sg.id
}

output "web_db_endpoint" {
  value = aws_db_instance.web_db.endpoint
}

output "web_ec2_sg_id" {
  value = aws_security_group.web_ec2_sg.id
}
