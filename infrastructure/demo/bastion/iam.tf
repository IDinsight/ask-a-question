data "aws_iam_policy_document" "agent_assume_role" {
  # https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html
  # https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_principal.html

  # The policy document that grants an entity permission to assume the role.

  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "bastion_instance_role" {
  # The role that the EC2 instance will assume

  name               = var.bastion_instance_role_name
  assume_role_policy = data.aws_iam_policy_document.agent_assume_role.json
  tags               = merge({ Name = var.bastion_instance_role_name, Module = "Bastion" }, var.tags)
}


resource "aws_iam_role_policy_attachment" "ssm_permissions_instance" {
  # This policy grants the EC2 instance permission to use SSM
  role       = aws_iam_role.bastion_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "bastion_instance_profile" {
  # This is the instance profile that will be attached to the EC2 instance
  # The instance profile is a container for the role
  # The instance profile is then attached to the EC2 instance

  name = var.bastion_instance_profile_name
  role = aws_iam_role.bastion_instance_role.name
}
