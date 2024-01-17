

login:
	@export AWS_PROFILE=aaq_demo
	@aws sso login --profile aaq_demo

data-db-tunnel-demo:
	# Open a connection to the remote db via the bastion host
	# the target is the instance id of the bastion host
	@aws ssm start-session \
	--target i-XXXXXXXXXXXX \
	--profile aaq_demo \
	--region af-south-1 \
	--document-name AWS-StartPortForwardingSession \
	--parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'