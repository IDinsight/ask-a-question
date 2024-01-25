#!/bin/bash
set -e


# Function to add any cleanup actions
function cleanup() {
	echo "Cleanup."
}
trap cleanup EXIT
# Define the domain and email for registration

email="$EMAIL"
domains=("$DOMAIN")
staging=0 # Set to 1 if you're testing your setup to avoid hitting request limits
rsa_key_size=4096

# Define webroot directory and mount path
WEBROOT_DIR="/var/www/certbot"
CERTBOT_EC2_PATH="/mnt/home/ssm-user/certs/nginx/certbot/www"

# Certbot command to obtain a certificate
function obtain_certificate {
    echo "### Requesting Let's Encrypt certificate for $domains ..."
    #Join $domains to -d args
    domain_args=""
    for domain in "${domains[@]}"; do
        domain_args="$domain_args -d $domain"
    done

    # Select appropriate email arg
    case "$email" in
    "") email_arg="--register-unsafely-without-email" ;;
    *) email_arg="--email $email" ;;
    esac

    # Enable staging mode if needed
    if [ $staging != "0" ]; then staging_arg="--staging"; fi

    certbot certonly --webroot -w "$WEBROOT_DIR" \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --non-interactive \
    --force-renewal 
}

echo "Checking for existing certificates..."

# Path to the live certificates from Certbot
CERT_PATH_FOLDER="/etc/letsencrypt/live/$DOMAIN"
FULLCERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
CERT_KEY_PATH="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/cert.pem"

# Path to nginx configuration file
NGINX_CONF="/etc/nginx/conf.d/app.conf"

# Check for existing certificates for the domain
while true; do
if [[ -f "$FULLCERT_PATH" ]]; then
    echo "Certificates already exist for $DOMAIN, checking if they need to be renewed..."
    start_date=$(openssl x509 -startdate -noout -in "$CERT_PATH" | cut -d= -f2)
    start_date_epoch=$(date -j -f '%b %d %T %Y %Z' "$start_date" +%s)
    current_epoch=$(date +%s)

    # Calculate the difference in seconds
    diff_epoch=$((current_epoch - start_date_epoch))

    # Check if 1 week (604800 seconds) have passed
    if [ $diff_epoch -ge 604800 ]; then
    echo "It's been more than 1 week since the cert was created."
    echo "Renewing the certificate..."
    certbot renew
    
    else
    hours_left=$(( (604800 - diff_epoch) / 3600 ))
    seconds_left=$(( hours_left * 3600 ))
    echo "The cert was created less than 1 week ago. Wait for $hours_left hours."
    fi
else
    echo "No certificates found for $DOMAIN, obtaining one..."
    obtain_certificate
    seconds_left=604800
    
    if [[ -d "$CERT_PATH_FOLDER" ]]; then
        echo "Certificates obtained successfully."
    else
        echo "Failed to obtain certificates."
        exit 1
    fi

fi

sleep $seconds_left  

done


exec "$@"