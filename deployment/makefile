SHELL = /bin/sh

$(eval DEMO_ACCOUNT=XXXXXXXXXXX)
$(eval DOMAIN=XXXXXXXXXXX)
$(eval EMAIL=XXXXXXXXXXX)
$(eval NEXT_PUBLIC_BACKEND_URL=XXXXXXXXXXX/api)

login:
	@aws sso login --profile aaq_demo
image-backend-demo:
	@DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	docker build --platform linux/arm64 --rm --build-arg BOOTSTRAP_FILE="bootstrap_demo.sh" -t aaq-demo-backend:latest -f ../core_backend/Dockerfile.demo ../core_backend

	# Tag
	@docker tag aaq-demo-backend:latest $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:backend

	# Login to aws
	@aws ecr get-login-password \
    --region af-south-1 \
	--profile aaq_demo | \
	docker login \
    --username AWS \
    --password-stdin $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com

	# Push image to ECS repository
	@docker push $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:backend

create-backend-demo:
	# Configure ecs-cli options
	@ecs-cli configure --cluster aaq-demo-cluster \
	--default-launch-type EC2 \
	--region af-south-1 \
	--config-name aaq-demo-backend-config

	@DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	ecs-cli compose -f ../core_backend/deployment/docker-compose.yml \
	--aws-profile aaq_demo \
	--project-name backend-task \
	--cluster-config aaq-demo-backend-config \
	--task-role-arn arn:aws:iam::$(DEMO_ACCOUNT):role/aaq-demo-web-task-role \
	create

image-frontend-demo:
	@NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL} \
	docker build --platform linux/arm64 --rm -t aaq-demo-frontend:latest -f ../admin_app/Dockerfile ../admin_app

	# Tag
	@docker tag aaq-demo-frontend:latest $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:frontend

	# Login to aws
	@aws ecr get-login-password \
    --region af-south-1 \
	--profile aaq_demo | \
	docker login \
    --username AWS \
    --password-stdin $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com

	# Push image to ECS repository
	@docker push $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:frontend

create-frontend-demo:
	# Configure ecs-cli options
	@ecs-cli configure --cluster aaq-demo-cluster \
	--default-launch-type EC2 \
	--region af-south-1 \
	--config-name aaq-demo-frontend-config

	@NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL} \
	DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	ecs-cli compose -f ../admin_app/deployment/docker-compose.yml \
	--aws-profile aaq_demo \
	--project-name frontend-task \
	--cluster-config aaq-demo-frontend-config \
	--task-role-arn arn:aws:iam::$(DEMO_ACCOUNT):role/aaq-demo-web-task-role \
	create

image-nginx-demo:
	@DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	DOMAIN=${DOMAIN} \
	EMAIL=${EMAIL} \
	docker build --platform linux/arm64 --rm -t aaq-demo-nginx:latest -f ../nginx/Dockerfile.nginx nginx

	# Tag
	@docker tag aaq-demo-nginx:latest $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:nginx

	# Login to aws
	@aws ecr get-login-password \
	--region af-south-1 \
	--profile aaq_demo | \
	docker login \
	--username AWS \
	--password-stdin $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com

	# Push image to ECS repository
	@docker push $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:nginx

cretae-nginx-demo:
	# Configure ecs-cli options
	@ecs-cli configure --cluster aaq-demo-cluster \
	--default-launch-type EC2 \
	--region af-south-1 \
	--config-name aaq-demo-nginx-config

	@DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	DOMAIN=${DOMAIN} \
	EMAIL=${EMAIL} \
	ecs-cli compose -f ../nginx/docker-compose.yml \
	--aws-profile aaq_demo \
	--project-name nginx-task \
	--cluster-config aaq-demo-nginx-config \
	--task-role-arn arn:aws:iam::$(DEMO_ACCOUNT):role/aaq-demo-web-task-role \
	create

image-certbot-demo:
	@DEMO_ACCOUNT=${DEMO_ACCOUNT} \
	DOMAIN=${DOMAIN} \
	EMAIL=${EMAIL} \
	docker build --platform linux/arm64 --rm -t aaq-demo-certbot:latest -f ../nginx/Dockerfile.certbot nginx

	# Tag
	@docker tag aaq-demo-certbot:latest $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:certbot

	# Login to aws
	@aws ecr get-login-password \
	--region af-south-1 \
	--profile aaq_demo | \
	docker login \
	--username AWS \
	--password-stdin $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com

	# Push image to ECS repository
	@docker push $(DEMO_ACCOUNT).dkr.ecr.af-south-1.amazonaws.com/aaq-demo-ecr-repository:certbot
