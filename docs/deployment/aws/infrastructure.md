# Creating infrastructure for AAQ on AWS


Create your own fork or a copy of the [AAQ repository](https://github.com/IDinsight/aaq-core) to follow along.

## 1. Install requirements

1. Install [Terraform](https://developer.hashicorp.com/terraform/install).
2. Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

## 2. Login to AWS

1. (First time setup) Set up your AWS config file (`~/.aws/config`) to work with the different environments and AWS SSO. Make sure your config file contains the following entries:

    ```bash
    [profile <Profile Name>]
    sso_start_url = <your AWS SSO start URL>
    sso_region = <your AWS SSO region>
    sso_account_id = <your AWS account ID>
    sso_role_name = <your AWS SSO role name, e.g. AdministratorAccess>
    region = <your AWS infratructure region>
    ```
2. Log in to AWS
    ```bash
    aws sso login --profile <Profile Name>
    ```
3. Run the following (Terraform relies on `AWS_PROFILE` environment variable)
    ```bash
    export AWS_PROFILE=<Profile Name>
    ```

## 3. Create Terraform backend infrastructure

To be able to run the code in a new AWS Account, first you will need to initialize the
code and create an S3 bucket where you will store the terraform state. This code is
housed in `infrastructure/tf_backend`.

 1. Make sure you've performed the [login steps](#2-login-to-aws) above.
 3. Review and edit the values in `infrastructure/tf_backend/tf_backend.auto.tfvars`.
 4. Navigate to `infrastructure/tf_backend`. Run the following in order:
    ```bash
    terraform init
    terraform plan
    ```
 5. Review the plan, and apply the changes by running the following.
    ```
    terraform apply
    ```

 This will create the S3 bucket that will store the states of terraform.


## 4. Create AAQ infrastructure

The infractructure code for an example environment `demo` is housed in
`infrastructure/demo`.

!!! note "Create infrastructure for new deployment environments"
    If you wish to have multiple deployment environments, you can copy the `demo`
    folder as `infrastructure/<environment>/`, for example, `infrastructure/production/`.
    Rename `demo.auto.tfvars` file to `<environment>.auto.tfvars`. Then, follow the steps
    below but replace `demo` with your own environment name.

### Overview

There are three main modules.

1. `bastion`: The Bastion Host serves as an intermediary server that allows secure access to the
   DB (an RDS instance). This will allow developers to connect to the DB even outside
   the VPC that the RDS instance resides in.
2. `main`: This is where all the infrastructure code for backend (`core_backend`) and
   frontend (`admin-app`) is stored. The application will run on ECS with an EC2 launch type. The
   load-balancing is done using Nginx, and certificate generation and maintainance will
   be handled by Certbot. The docker images will be stored in ECR.
3. `network`: This module has the code for the VPC and its components. The other modules will only have Security Groups resources. The rest are placed here.

### Creating AAQ infrastructure

1. Navigate to `infrastructure/demo` folder.
    ```bash
    cd infrastructure/demo
    ```
1. Configure your deployment environment.
    1. Update the contents of `backend.conf` to match the resource names created in
       [step 3](#3-create-terraform-backend-infrastructure).
    1. Review and update the contents of the `demo.auto.tfvars` file. This file contains environment-specific variable
        values which Terraform automatically loads during resource creation.
1. Make sure you've performed the [login steps](#2-login-to-aws) above.
2. Initialize the Terraform backend and install the providers.
    ```bash
    terraform init -backend-config=backend.conf
    ```
4. Run `terraform plan` to view the plan.
5. Run `terraform apply` to deploy the terraform configuration.

### Preparing your infrastructure for deployment

#### Attach Elastic IP to your domain
When the infrastructure is created, a new Elastic IP is created. If you have your own
domain, make sure to associate it with this IP address.

#### Store API keys in AWS Secrets Manager
For example, if you rely on OpenAI models, you must update the OpenAI API key in AWS AWS Secrets Manager.

## Additional guides

### Connecting to your DB locally
1. Open a connection to the AAQ database
    ```bash
    aws ssm start-session \
        --target <Instance ID> \
        --profile <Profile Name> \
        --region <Region> \
        --document-name AWS-StartPortForwardingSession \
        --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'
    ```
    `<Instance ID>` is the EC2 instance ID of the Bastion Host.

    If the command hangs at `Starting session with SessionId:... `, make sure port
    5432 is available.

2. Retrieve the DB connection credentials from AWS Secrets Manager.
3. Connect to the DB via the tunnel created above:
    1. With pgAdmin: create a connection with the host as `localhost` and enter the credentials
    2. With docker:
        ```
        docker pull dpage/pgadmin4
        docker run -p 80:80 \
            -e 'PGADMIN_DEFAULT_EMAIL=user@domain.com' \
            -e 'PGADMIN_DEFAULT_PASSWORD=SuperSecret' \
            -d dpage/pgadmin4
        ```
    When using pgAdmin or docker, the host will be `host.docker.internal` if localhost does not work.

### Adding a new secret

All secrets stored in AWS Secrets Manager are created and managed using Terraform. The
secrets are defined under `infrastructure/<environment>/main/credentials.tf`.

To add a new secret,

1. Create an `aws_secretsmanager_secret` and `aws_secretsmanager_secret_version` for
   your secret.
    1. If this will be a generated secret,
        1. Increase the value of `random_password.secrets.count` by X depending on how many secrets need to be genereated
        1. The value of the `aws_secretsmanager_secret_version.secret_string` is where the generated secret will be stored. To add the value of the generated secret, reference the `random_password.secrets` and value of the index. If there are 2 secrets to be generated, the index startes from 0, if the secret is the first one, the value will be `random_password.secrets[0].result`. If you are adding to already existing count, get the last decled index and add 1. So if the last secret was `random_password.secrets[4].result`, the new one will be `random_password.secrets[5].result`
    1. If you want to create a placeholder secret to be manually set later (e.g. external API key), the
        `secret_string` should have a place holder string. Terraform will not allow an empty
        string. In the `aws_secretsmanager_secret_version`, we will also have to ignore
        changes to the string. This is because when you manually change the string, terraform
        will detect the change and without ignoring the change it will overwrite the secret
       with the place holder
1. Add the secret to the `infrastructure/<environment>/main/iam.tf` permissions to allow the `ecs_task_role` to get the value.
1. If the secret is needed at backend startup, it also needs to be added to the
   `deployment/aws/core_backend/bootstrap.sh` file.
