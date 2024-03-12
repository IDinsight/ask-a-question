# CI/CD of AAQ on AWS with GitHub Actions

After following the [infrastructure creation steps](infrastructure.md), you should now
have created 3 services in your AAQ ECS cluster.

1. backend
2. admin-app
3. nginx

This page will show you how the CI/CD pipelines work and how to configure your GitHub
Actions for CI/CD.

## Overview

The CI/CD pipelines are implemented using GitHub Actions workflows. There is one
workflow for each service.

The workflows expect you to maintain a separate branch for each deployment environment,
e.g. `development`, `staging`, `production`, etc.

The workflow will get triggered on
each deployment branch if any changes to the following files get merged:

- your AAQ application code (under `core_backend` or `admin_app`), or
- deployment code (`deployment/aws/...`)

## Setting up CI/CD workflows on GitHub Actions

1. To deploy AAQ via Github Actions, first [create a deployment
environment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#creating-an-environment)
in your copy/fork of the
AAQ repository, [aaq-core](https://github.com/IDinsight/aaq-core). The environment name
should be the same as the environment name used in your infrastructure configuration
(`infrastructure/<environment>/<environment>.auto.tfvars`).

2. In the new environment, create the following secrets that are specific to this
deployment environment:

| Name              | Example                                      | Description                                                                 |
|-------------------|----------------------------------------------|-----------------------------------------------------------------------------|
| AWS_ACCOUNT_ID    | `000000000000`                                | AWS account ID                                                              |
| AWS_REGION        | `af-south-1`                                  | AWS region                                                                  |
| BOOTSTRAP_FILE    | `bootstrap.sh`                               | Name of the bootstrap file at `deployment/aws/core_backend/`                                             |
| CLUSTER_NAME      | `aaq-demo-ecs-cluster`                        | ECS cluster name                                                            |
| DOMAIN            | `example.domain.com`                        | Domain name                                                                 |
| EMAIL             | `user@domain.com`                           | Email address                                                               |
| NEXT_PUBLIC_BACKEND_URL | `https://example.domain.com/api`             | Backend URL for the application                                       |
| PROJECT_NAME      | `aaq`                                          | Project name from Terraform (`infrastructure/demo/demo.auto.tfvars`)        |
| REPO              | `aaq-demo-ecr-repository`                       | Name of the ECR repository created using Terraform                          |
| ROLE              | `aaq-demo-github-actions-role`                  | Name of the GitHub Actions role for this environment created using Terraform |
| TASK_ROLE_ARN     | `arn:aws:iam::000000000000:role/aaq-demo-web-task-role` | ARN of the ECS task role created using Terraform                            |

!!! note
    See Github Actions' ["Using environments for
    deployment"](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
    page to learn more.
