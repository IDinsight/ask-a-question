<pre align="center" style="text-align:center; font-size: 1vw; background:none;">
    __            __        ______
    /""\          /""\      /    " \
    /    \        /    \    // ____  \
    /' /\  \      /' /\  \  /  /    )  )
  //  __'  \    //  __'  \(: (____/ //
 /   /  \\  \  /   /  \\  \\         \
 (___/    \___)(___/    \___)\"____/\__\
ASK-A-QUESTION
</pre>

<p align="center" style="text-align:center">
<a href="https://idinsight.github.io/aaq-core/">Developer Docs</a> |
<a href="#features">Features</a> |
<a href="#usage">Usage</a> |
<a href="#architecture">Architecture</a> |
<a href="#funders-and-partners">Funders and Partners</a>
</p>

**[Ask-a-question](https://idinsight.github.io/aaq-core/) lets your users ask questions and receive answers from your content repository in their preferred language**

## :woman_cartwheeling: Features

#### **:question: LLM-powered search**

Match your questions to content in the database using embeddings from LLMs.

#### **:robot: LLM responses**

Craft a custom reponse to the question using LLM chat and the content in your database

#### **:speech_balloon: Deploy on whatsapp**

Easily deploy using WhatsApp Business API

#### **:books: Manage content**

Use the Admin App to add, edit, and delete content in the database

## :construction: Upcoming

#### **:earth_africa: Support for low resourced language**

Ask questions in local languages. Languages currently on the roadmap

- [ ] Xhosa
- [ ] Zulu
- [ ] Hindi
- [ ] Igbo

#### **:speech_balloon: Conversation capability**

Refine or clarify your question through conversation

#### :video_camera: Multimedia content

Respond with not just text but voice, images, and videos as well.

#### :rotating_light: Message Triaging

Identify urgent or important messages. Handle them differently.

#### :woman_technologist: Engineering dashboard

Monitor uptime, response rates, throughput HTTP reponse codes and more

#### :woman_office_worker: Content manager dashboard

See which content is the most sought after, the kinds of questions that receive poor feedback, identify missing content, and more

> [!NOTE]
> Looking for other features? Please raise an issue with `[FEATURE REQUEST]` before the title.

## Usage

There are two major endpoints for Question-Answering:

- Embeddings search: Finds the most similar content in the database using cosine similarity between embeddings.
- LLM response: Crafts a custom response using LLM chat using the most similar content.

See [docs](https://idinsight.github.io/aaq-core/) or SwaggerUI at `https://<DOMAIN>/api/docs` or `https://<DOMAIN>/docs` for more details and other API endpoints.

### :question: Embeddings search

```
curl -X 'POST' \
  'https://[DOMAIN]/api/embeddings-search' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "how are you?",
  "query_metadata": {}
}'
```

### :robot: LLM response

```
curl -X 'POST' \
  'https://[DOMAIN]/api/llm-response' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "this is my question",
  "query_metadata": {}
}'
```

### :books: Manage content

You can access the admin console at

```
https://[DOMAIN]/
```

## Architecture

We use docker-compose to orchestrate containers.

<p align="center">
  <img src="docs/images/architecture-docker.png" alt="Architecture"/>
</p>

A reverse proxy manages all incoming traffic to the service. The vector database and SQL database are only accessed by the core app.

<p align="center">
  <img src="docs/images/architecture-traffic.png" alt="Flow"/>
</p>

## Documentation

See [here](https://idinsight.github.io/aaq-core/) for full documentation.

## Funders and Partners

<img src="docs/images/google_org.png" alt="google_dot_org" width=200/>
