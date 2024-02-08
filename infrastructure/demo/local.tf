# file for storing the locals -  values that will not change

data "aws_caller_identity" "current" {
}

locals {

  # Get AWS account ID from the AWS credentials provided - to be used when updating account-specific permissions
  aws_account_id          = data.aws_caller_identity.current.account_id
  aws_caller_identity_arn = data.aws_caller_identity.current.arn

  # handy name suffix concatenating the project name and environment
  name_prefix = "${var.project_name}-${var.environment}"

  required_tags = {
    Project     = var.project_name,
    Environment = var.environment,
    BillingCode = var.billing_code
    AccountID   = local.aws_account_id
    # We can add more tags here
  }
  tags = merge(var.resource_tags, local.required_tags)
}
