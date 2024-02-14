---
authors:
  - Sid
category:
  - Architecture
  - Reverse proxy
  - API
date: 2024-02-09
---
# Nginx out, Caddy in

By swapping out Nginx for Caddy, we substantially simplified the deployment steps
and the architecture - which means fewer docker containers to run and manage.

<!-- more -->

Previously, we were using Nginx and then manually running a script to issue certificates
from Let's Encrypt. We were also running a [container](https://hub.docker.com/r/certbot/certbot/)
to refresh Let’s Encrypt certificates. And then sharing volumes between this container and
the nginx container. [This article](https://pentacent.medium.com/nginx-and-lets-encrypt-with-docker-in-less-than-5-minutes-b4b8a60d3a71) from
2018 shows you the setup. It was a bit of a mess.

The other issue was that this process wouldn't work when running locally - for example when
you are developing. Your domain would be `localhost` and Let's Encrypt can't issue
certificates for it. So we had to come up with a different process for local dev
where we were issuing self-signed certs.

## Welcome Caddy

Oscar, our Google.org AI advisor's first advice when he saw our architecture was to switch
to Caddy. Here are the benefits:

1. It requests and refresh certs from Let's Encrypt.
2. If your domain is localhost, it knows to issue its own certificate.
3. A much smaller and simpler config file.
4. You can use environment variables.

So now our local setup process is the same as prod and requires one fewer containers. Amazing!
