## AAQ Demo Environment Infrastructure
<<<<<<< HEAD
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
=======
The codebase is organized into three main modules:

#### 1. Bastion
- This is what will be used to access db locally. To open the tunnel, run `make data-db-tunnel-demo` from the infrastructure folder.
If the command hangs at `Starting session with SessionId:... `, make sure port 5432 is available.

- If you have pgAdmin installed, you can create a connection with the host as localhost. You can find the DB credentials in AWS Secrets Manager.
If you do not have pgAdmin installed, you can run it in docker using the following:

```
docker pull dpage/pgadmin4
docker run -p 80:80 \
    -e 'PGADMIN_DEFAULT_EMAIL=user@domain.com' \
    -e 'PGADMIN_DEFAULT_PASSWORD=SuperSecret' \
    -d dpage/pgadmin4
 ```

When using pgAdmin or docker, the host will be `host.docker.internal` if localhost does not work.

#### 2. Main
This is where all the infrastructure for the Application be stored. The application is running on ECS with EC2 launch type. The loadbalancing is done using Nginx and certificate generation and maintainance will be handled by Certbot.
The docker images will be stored in ECR.

#### 3. Network
This module will have the code of the VPC and its components. The other modules will only have Security Groups resources. The rest will be placed here.
>>>>>>> main


### How To Run

<<<<<<< HEAD
1. Follow the setup and authentication steps outlined in the README in the root directory of this repo.
2. Run `terraform init -backend-config=backend.conf` to initialize the Terraform backend and install the providers.
3. Run `terraform plan` to view the plan.
4. Run `terraform apply` to deploy the terraform configuration.

## Attaching IP to the Domain
When the infrastructure is created, a new Elastic IP is created. The IP needs to be associated with the domain. This is done in the Main IDinsight AWS Account. Go to route 53, Host zones. Look for the record and edit the IP.
=======
1. Follow the setup and authentication steps outlined in the README in `infrastructure/README.md`.
2. Run `terraform init -backend-config=backend.conf` to initialize the Terraform backend and install the providers.
3. To ensure your infrastructure is set up correctly, you should review the contents of the `{env}.auto.tfvars` file thoroughly. This file contains environment-specific variable values which Terraform automatically loads during operations
4. Run `terraform plan` to view the plan.
5. Run `terraform apply` to deploy the terraform configuration.

### Attaching IP to the Domain
When the infrastructure is created, a new Elastic IP is created. If you have your own domain, make sure to associate it with this IP address
>>>>>>> main
