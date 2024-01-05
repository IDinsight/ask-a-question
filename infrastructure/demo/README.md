## AAQ Demo Environment Infrastructure
The code into 3 main module:

** 1. Bastion **
This is what will be used to access db locally. To open the tunnel, run `make data-db-tunnel-demo` from the infrastructure folder.
If you have pgAdmin installed, you will create a connection with host as localhost and credentials of the db will be found in the secret manager.
If you do not have pgAdmin installed, you can run it in docker using the following:
`docker pull dpage/pgadmin4
docker run -p 80:80 \
    -e 'PGADMIN_DEFAULT_EMAIL=user@domain.com' \
    -e 'PGADMIN_DEFAULT_PASSWORD=SuperSecret' \
    -d dpage/pgadmin4` 

    When using pgAdmin or docker, the host will be `host.docker.internal` if localhost does not work.

** 2. Main **
This is where all the infrastructure for the Application be stored. The application is running on ECS with EC2 launch type. The loadbalancing is done using Nginx and certificate generation and maintainance will be handled by Certbot.
The docker images wll stored in ECR.

** 3. Network **
This module will have the code of the VPC and its components. The other modules will only have Security groups resources. The rest will be place here.


### How To Run

1. Follow the setup and authentication steps outlined in the README in the root directory of this repo.
2. Run `terraform init -backend-config=backend.conf` to initialize the Terraform backend and install the providers.
3. Run `terraform plan` to view the plan.
4. Run `terraform apply` to deploy the terraform configuration.