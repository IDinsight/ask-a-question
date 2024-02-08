

login:
<<<<<<< HEAD
	@export AWS_PROFILE=aaq_demo
	@aws sso login --profile aaq_demo
=======
	
	@aws sso login --profile <Profile>
>>>>>>> main

data-db-tunnel-demo:
	# Open a connection to the remote db via the bastion host
	# the target is the instance id of the bastion host
	@aws ssm start-session \
<<<<<<< HEAD
	--target i-XXXXXXXXXXXX \
	--profile aaq_demo \
	--region af-south-1 \
=======
	--target i-XXXXXXXXXXXXXXXXX \
	--profile <Profile Name> \
	--region <Region> \
>>>>>>> main
	--document-name AWS-StartPortForwardingSession \
	--parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'