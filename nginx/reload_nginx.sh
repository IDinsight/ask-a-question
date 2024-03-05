#!/bin/bash

DOMAIN=$DOMAIN
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
CERT_KEY_PATH="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
CERT_PATH_FOLDER="/etc/letsencrypt/live/$DOMAIN"
NGINX_CONF="/etc/nginx/conf.d/app.conf"



watch_certificate_changes(){
# Check if the domain folder has been changed
while inotifywait -e modify,create,delete,move "$CERT_PATH_FOLDER"; do
  # Reload NGINX configuration
  if [ -f $CERT_PATH ]; then
    echo "Certificates found. Reloading NGINX."
    sed -i "s|ssl_certificate .*|ssl_certificate $CERT_PATH;|g" $NGINX_CONF
    sed -i "s|ssl_certificate_key .*|ssl_certificate_key $CERT_KEY_PATH;|g" $NGINX_CONF
    nginx -t
    nginx -s reload
    echo "NGINX has been reloaded."
  else
    echo "Certificates not found. Skipping reload."
  fi

done
}

if [ -d "$CERT_PATH_FOLDER" ]; then
    echo "Certificates folder already exist for $DOMAIN, skipping creation."
    watch_certificate_changes
else
    echo "No certificates folder found for $DOMAIN, Creating the folder..."
    mkdir -p "$CERT_PATH_FOLDER"
    watch_certificate_changes
fi