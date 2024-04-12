---
authors:
  - Carlos
category:
  - Database
  - API
date: 2024-03-19
---
# Namaste Multilingual support


We are excited to announce a significant enhancement to our web application: **multilingual content management**. This update is sets stone to one of our key features which is to enable multlilingual model support. This update will make managing contents in different languages easier. 

<!-- more -->

Multilingual content support changes the way contents are managed. Now contents can have many languages version, up to the number of languages supported. 


## Why this change?

While Qdrant served us well as a dedicated vector database, integrating it with our existing PostgreSQL setup introduced complexity and maintenance overhead. Operating Qdrant alongside PostgreSQL meant managing two distinct database systems with their own infrastructure, architecture, and requirements. Integrating both databases into our codebase required additional integration layers, complicating our codebase.

As we already were using Postgresql, pgvector caught our attention with [this article](https://supabase.com/blog/increase-performance-pgvector-hnsw) as a promising solution that integrates vector database capabilities directly into our existing database. Here's why we decided to go for pgvector:
- **Simplified Architecture**: By adopting pgvector, we significantly reduced the complexity of our data infrastructure. Vector and relational data now reside within the same database, eliminating the need for separate systems.
- **Improved Response Time**: Direct integration with PostgreSQL enhances performance by eliminating the overhead of communicating between separate databases.

Moving to pgvector not only benefits our team in terms of reduced complexity and better resource utilization but also lays the groundwork for future innovations such as the multilingual support which should be coming soon.
