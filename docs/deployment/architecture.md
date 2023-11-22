## Architecture

We use docker-compose to orchestrate containers.

<p align="center">
  <img src="../images/architecture-docker.png" alt="Architecture"/>
</p>

A reverse proxy manages all incoming traffic to the service. The vector database and SQL database are only accessed by the core app.

<p align="center">
  <img src="../images/architecture-traffic.png" alt="Flow"/>
</p>
