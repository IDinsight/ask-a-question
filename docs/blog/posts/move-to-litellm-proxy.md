---
authors:
  - Amir
category:
  - Architecture

date: 2024-04-05
---
# Model calls made flexible

Instead of being handled directly in our code, our model calls are now routed through a [LiteLLM Proxy](https://litellm.vercel.app/docs/simple_proxy) server, which lets use change models on the fly, have retries and fallbacks, budget tracking, and more.

<!-- more -->
