# General Deployment files
Each apllication has its own older with Dockerfile and docker_compose file. The makefile is used to push image to ecr and create a new task definition.
IF the docker_compose does not change, the task definition revision number will remain the same. To run ecs-cli, you will need to add the aws profile to (~/.aws/credentials) since it does not work with SSO