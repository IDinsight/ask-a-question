#!/bin/bash
set -e


# Function to add any cleanup actions
function cleanup() {
	echo "Cleanup."
}
trap cleanup EXIT
# Path to the certificates

CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
DUMMY_CERT_PATH="/etc/ssl/private/dummy.crt"
DUMMY_KEY_PATH="/etc/ssl/private/dummy.key"
NGINX_TEMP_CONF="/etc/nginx/conf.d/app.conf.template"
NGINX_CONF="/etc/nginx/conf.d/app.conf"
data_path="/etc/letsencrypt"

if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "Checking for existing certificates..."



# Check if the real certificate exists
if [[ ! -f "$CERT_PATH/fullchain.pem" || ! -f "$CERT_PATH/privkey.pem" ]]; then
  echo "Real certificates not found."

    # Check if the dummy certificates exist
    if [[ ! -f "$DUMMY_CERT_PATH" || ! -f "$DUMMY_KEY_PATH" ]]; then
    echo "Dummy certificates not found. Generating them..."

    mkdir -p "/etc/ssl/private"
    if [ ! -d "/etc/ssl/private/" ]; then
    echo "Directory /etc/ssl/private/ does not exist."
    fi
    chown nginx:nginx  /etc/ssl/private/
    chmod 600 -R /etc/ssl/private/
    # Generate a self-signed certificate
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout $DUMMY_KEY_PATH \
        -out $DUMMY_CERT_PATH \
        -subj "/CN=$DOMAIN"
    fi

     if [[ -f "$DUMMY_CERT_PATH" &&  -f "$DUMMY_KEY_PATH" ]]; then
        echo "Dummy Certificates obtained successfully."
        openssl x509 -in $DUMMY_CERT_PATH -text -noout
        openssl rsa -in $DUMMY_KEY_PATH -check
    else
        echo "Failed to obtain Dummy certificates."
        exit 1
    fi
    
  # Set up NGINX to use the dummy certificate
  echo "Configuring NGINX to use the dummy certificate."
  sed -i "s|ssl_certificate .*|ssl_certificate $DUMMY_CERT_PATH;|g" $NGINX_TEMP_CONF
  sed -i "s|ssl_certificate_key .*|ssl_certificate_key $DUMMY_KEY_PATH;|g" $NGINX_TEMP_CONF
else
  # Assuming real certificates are in place and NGINX is already configured to use them
  echo "Real certificates found. Using them."
fi

/reload_nginx.sh &


envsubst "\$DOMAIN" < $NGINX_TEMP_CONF > $NGINX_CONF



# Continue with the normal flow, such as starting the NGINX server
echo "Starting NGINX..."
nginx -g 'daemon off;'

exec "$@"