resource "aws_ecs_cluster" "web_cluster" {
  name = var.web_ecs_cluster_name
  tags = merge({ Name = var.web_ecs_cluster_name, Module = "Web" }, var.tags)
}

# service discovery namespace
resource "aws_service_discovery_private_dns_namespace" "web" {
  name = "aaqdemo.local"
  vpc  = var.vpc_id
}

# backend service discovery service
resource "aws_service_discovery_service" "backend" {
  name = "backend"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.web.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "SRV"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

# backend service discovery service
resource "aws_service_discovery_service" "frontend" {
  name = "frontend"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.web.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "SRV"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

# vectordb service discovery service
resource "aws_service_discovery_service" "vectordb" {
  name = "vectordb"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.web.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "SRV"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}


# Nginx Service with EC2 Launch Type
resource "aws_ecs_service" "nginx_service" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an ECS service with EC2 launch type for the Nginx container
  # The ECS service will be used to route traffic to the Nginx container
  # The ECS service will be attached to the ECS cluster
  # This will be the entry point for the application
  name                               = "nginx-service"
  cluster                            = aws_ecs_cluster.web_cluster.id
  task_definition                    = aws_ecs_task_definition.nginx_task.arn
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200
  launch_type                        = "EC2"
  scheduling_strategy                = "REPLICA"
  desired_count                      = 1



  # workaround for https://github.com/hashicorp/terraform/issues/12634

  # we ignore task_definition changes as the revision changes on deploy
  # of a new version of the application
  # desired_count is ignored as it can change due to autoscaling policy
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}

resource "aws_ecs_task_definition" "nginx_task" {
  # The rest of the container definitions will be added when the application is deployed. It will be added to the task definition from docker-compose.yml using the ecs-cli compose service up command
  family             = "nginx-task"
  execution_role_arn = aws_iam_role.web_task_role.arn
  container_definitions = jsonencode([{
    name       = "nginx-container",
    image      = "nginx:latest",
    memory     = 512,
    cpu        = 256,
    entryPoint = ["/entrypoint.sh"],

    mountPoints = [
      {
        sourceVolume  = "nginx",
        containerPath = "/etc/nginx/conf.d",
        readOnly      = false,
      },
      {
        sourceVolume  = "nginx_cert",
        containerPath = "/var/www/certbot",
        readOnly      = false,
      },
      {
        sourceVolume  = "nginx_cert_conf",
        containerPath = "/etc/letsencrypt",
        readOnly      = false,
      }
    ],

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.nginx.name
        awslogs-stream-prefix = "ecs"
        awslogs-region        = var.aws_region
      }
    }
    },
    {
      name   = "certbot",
      image  = "certbot/certbot:latest",
      memory = 256,
      cpu    = 256,
      mountPoints = [
        {
          sourceVolume  = "nginx_cert_conf",
          containerPath = "/etc/letsencrypt",
          readOnly      = false,
        },
        {
          sourceVolume  = "nginx_cert",
          containerPath = "/var/www/certbot",
          readOnly      = false,
        },
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.nginx.name
          awslogs-stream-prefix = "ecs"
          awslogs-region        = var.aws_region
        }
      }
  }])

  volume {
    name      = "nginx"
    host_path = "/home/ssm-user/nginx"
  }

  volume {
    name      = "nginx_cert"
    host_path = "/home/ssm-user/certs/nginx/certbot/www"
  }

  volume {
    name      = "nginx_cert_conf"
    host_path = "/home/ssm-user/certs/nginx/certbot/conf"
  }

}

# Vectordb Service with EC2 Launch Type
resource "aws_ecs_service" "vectordb_service" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an ECS service with EC2 launch type for the vectordb container
  # The ECS service will be used to route traffic to the vectordb container
  # The ECS service will be attached to the ECS cluster
  name                               = "vectordb-service"
  cluster                            = aws_ecs_cluster.web_cluster.id
  task_definition                    = aws_ecs_task_definition.vectordb_task.arn
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200
  launch_type                        = "EC2"
  scheduling_strategy                = "REPLICA"
  desired_count                      = 1

  service_registries {
    registry_arn   = aws_service_discovery_service.vectordb.arn
    container_name = "vector-container"
    container_port = 6333
  }

  depends_on = [aws_ecs_cluster.web_cluster]

}

resource "aws_ecs_task_definition" "vectordb_task" {
  # The rest of the container definitions will be added when the application is deployed. It will be added to the task definition from docker-compose.yml using the ecs-cli compose service up command
  family             = "vectordb-task"
  execution_role_arn = aws_iam_role.web_task_role.arn
  container_definitions = jsonencode([{
    name   = "vector-container",
    image  = "qdrant/qdrant:v1.5.1",
    memory = 512,
    cpu    = 256,

    mountPoints = [
      {
        "sourceVolume" : "quadrand-volume",
        "readOnly" : false
        "containerPath" : "/qdrant/storage"
      }
    ]
    portMappings = [
      {
        "containerPort" : 6333,
        "hostPort" : 6333,
        "protocol" : "tcp"
      }
    ]
    environment = [
      {
        "name" : "QDRANT__TELEMETRY_DISABLED",
        "value" : "true"
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.vectordb.name
        awslogs-stream-prefix = "ecs"
        awslogs-region        = var.aws_region
      }
    }
    restart = "always"
  }])

  volume {
    name = "quadrand-volume"
  }

}

# Frontend Service with EC2 Launch Type
resource "aws_ecs_service" "frontend_service" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an ECS service with EC2 launch type for the Frontend container
  # The ECS service will be used to route traffic to the Frontend container
  # The ECS service will be attached to the ECS cluster
  name                               = "frontend-service"
  cluster                            = aws_ecs_cluster.web_cluster.id
  task_definition                    = aws_ecs_task_definition.frontend_task.arn
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200
  launch_type                        = "EC2"
  scheduling_strategy                = "REPLICA"
  desired_count                      = 1

  service_registries {
    registry_arn   = aws_service_discovery_service.frontend.arn
    container_name = "frontend-container"
    container_port = 3000
  }


  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

}

resource "aws_ecs_task_definition" "frontend_task" {
  # The rest of the container definitions will be added when the application is deployed. It will be added to the task definition from docker-compose.yml using the ecs-cli compose service up command
  family             = "frontend-task"
  execution_role_arn = aws_iam_role.web_task_role.arn
  container_definitions = jsonencode([{
    name   = "frontend-container",
    image  = "frontend:latest",
    memory = 512,
    cpu    = 256,



    portMappings = [
      {
        "containerPort" : 3000,
        "hostPort" : 3000,
        "protocol" : "tcp"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.frontend.name
        awslogs-stream-prefix = "ecs"
        awslogs-region        = var.aws_region
      }
    }
  }])

}

# Backend Service with EC2 Launch Type
resource "aws_ecs_service" "backend_service" {
  # This is a resource, which means it will create a resource in AWS
  # This resource will create an ECS service with EC2 launch type for the Backend container
  # The ECS service will be used to route traffic to the Backend container
  # The ECS service will be attached to the ECS cluster
  name                               = "backend-service"
  cluster                            = aws_ecs_cluster.web_cluster.id
  task_definition                    = aws_ecs_task_definition.backend_task.arn
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200
  launch_type                        = "EC2"
  scheduling_strategy                = "REPLICA"
  desired_count                      = 1

  service_registries {
    registry_arn   = aws_service_discovery_service.backend.arn
    container_name = "backend-container"
    container_port = 8000
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}

resource "aws_ecs_task_definition" "backend_task" {
  # The rest of the container definitions will be added when the application is deployed. It will be added to the task definition from docker-compose.yml using the ecs-cli compose service up command
  family             = "backend-task"
  execution_role_arn = aws_iam_role.web_task_role.arn
  container_definitions = jsonencode([{
    name   = "backend-container",
    image  = "backend:latest",
    memory = 512,
    cpu    = 256,

    portMappings = [
      {
        "containerPort" : 8000,
        "hostPort" : 8000,
        "protocol" : "tcp"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-stream-prefix = "ecs"
        awslogs-region        = var.aws_region
      }
    }
  }])





}

resource "aws_cloudwatch_log_group" "frontend" {
  name = "/ecs/frontend-task-demo"

  tags = {
    Name        = "frontend-task-deno"
    Environment = "demo"
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name = "/ecs/backend-task-demo"

  tags = {
    Name        = "backend-task-demo"
    Environment = "demo"
  }
}

resource "aws_cloudwatch_log_group" "vectordb" {
  name = "/ecs/vectordb-task-demo"

  tags = {
    Name        = "vectordb-task-demo"
    Environment = "demo"
  }
}

resource "aws_cloudwatch_log_group" "nginx" {
  name = "/ecs/nginx-task-demo"

  tags = {
    Name        = "nginx-task-demo"
    Environment = "demo"
  }
}
