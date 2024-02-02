# AAQ Infrastructure
The infrastructure as code (IaC) is done using Terraform. The Module is organized into environments. Each environment will have its own code.

## Login to AWS

- [First time setup] Set up your AWS config file (`~/.aws/config`) to work with the different environments and AWS SSO. Make sure your config file contains the following entries:

```
[profile aaq]
sso_start_url = <your AWS SSO start URL>
sso_region = <your AWS SSO region>
sso_account_id = <your AWS account ID>
sso_role_name = <your AWS SSO role name, e.g. AdministratorAccess>
region = <your AWS infratructure region>

```

- Run `export AWS_PROFILE=aaq`
- Run `make login`
## Running in a new AWS Account
To be able to run the code in a new AWS Account, first you will need to initialize the code and create an S3 bucket where you will store the terraform state.
Steps:
 1. Login to AWS using `make login`
 2. `cd tf_backend`
 3. Review and edit the values in `tf_backend/tf_backend.auto.tfvars`.
 4. `terraform init`
 5. `terraform plan`
 6. `terraform apply`

 This will create the S3 bucket that will store the states of terraform.