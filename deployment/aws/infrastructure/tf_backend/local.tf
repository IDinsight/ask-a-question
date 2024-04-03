# file for storing the locals -  values that will not change
data "aws_caller_identity" "current" {}
locals {
  # Get AWS account ID from the AWS credentials provided - to be used when updating account-specific permissions
  aws_account_id = data.aws_caller_identity.current.account_id
  required_tags = {
    Project     = var.project_name,
    BillingCode = var.billing_code,
    AccountID   = local.aws_account_id
    # We can add more tags here
  }
}
