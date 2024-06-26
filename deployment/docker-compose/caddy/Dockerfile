# Start from the official Caddy image
FROM caddy:2.7.6

ARG DOMAIN
ENV DOMAIN=${DOMAIN}

# Copy the Caddyfile into the image
COPY ./Caddyfile /etc/caddy/Caddyfile

# Set the working directory
WORKDIR /srv

# The official Caddy image already sets the CMD to run Caddy, so no need to repeat that here unless you need to customize it
