#!/bin/bash
echo ECS_CLUSTER=${cluster_name} >> /etc/ecs/ecs.config

# We need to create the ssm-user manually because AWS only creates it the first time we log in to Session Manager
# This is needed so the cron jobs can start running right away
adduser -m ssm-user
tee /etc/sudoers.d/ssm-agent-users <<'EOF'
ssm-user ALL=(ALL) NOPASSWD:ALL
EOF
chmod 440 /etc/sudoers.d/ssm-agent-users

echo " " >> /var/spool/cron/ssm-user
echo "# Clean docker files once a week" >> /var/spool/cron/ssm-user
echo "0 0 * * 0 /usr/bin/docker system prune -f" >> /var/spool/cron/ssm-user
echo " " >> /var/spool/cron/ssm-user

mkdir /home/ssm-user/nginx
mkdir /home/ssm-user/certs


sudo chmod 755 -R /home/ssm-user/nginx
<<<<<<< HEAD
sudo chmod 755 -R /home/ssm-user/certs
=======
sudo chmod 755 -R /home/ssm-user/certs
>>>>>>> main
