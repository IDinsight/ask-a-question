# AAQ Infrastructure
The infrastructure as code (IaC) is done using Terraform. The Module is organized into environments. Each environment will have its own code.

## Login to AWS
- [First time setup] Set up your AWS config file (`~/.aws/config`) to work with the different environments and AWS SSO. Make sure your config file contains the following entries:

```
[profile aaq_demo]
sso_start_url = https://idinsight.awsapps.com/start
sso_region = ap-south-1
sso_account_id = 039685995141
sso_role_name = AdministratorAccess
region = ap-south-1

```

## Running in a new AWC Account
To be able to run the code in a new AWS Account, first you will need to initialize the code and create an S3 bucket where you will store the terraform state.
Steps:
 - Login to AWS using `make login`
 - `cd tf_backend`
 - `terraform init`
 - `terraform plan`
 - `terraform apply`

 This will create the S3 bucket that will store the states of terraform.