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
<a href="https://idinsight.github.io/aaq-core/">Docs</a> |
<a href="#features">Features</a> |
<a href="#usage">Usage</a> |
<a href="#architecture">Architecture</a> |
<a href="#partners">Partners</a>
</p>

**[Ask-a-question](https://idinsight.github.io/aaq-core/) allows your beneficiaries or staff to ask question in natural language in their preferred language and receive answers from your content repository**

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

#### **:speech_balloon: conversation capability**

Refine or clarify your question through conversation

#### :video_camera: multimedia content

Respond with not just text but images and videos as well.

#### :rotating_light: urgency detection

Identify and handle urgent messages.

#### :woman_technologist: engineering dashboard

Monitor uptime, response rates, throughput HTTP reponse codes and more

#### :woman_office_worker: content manager dashboard

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
  'http://0.0.0.0:8000/embeddings-search' \
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
  'http://0.0.0.0:8000/llm-response' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "this is my question",
  "query_metadata": {}
}'
```

## Architecture

<p align="center">
  <img src="/images/architecture-docker.png" alt="Architecture"/>
</p>

## Documentation

See [here](https://idinsight.github.io/aaq-core/) for full documentation.
