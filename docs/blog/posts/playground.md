---
authors:
  - Sid
category:
  - Admin App
  - LLM Response
  - Embeddings Search
date: 2024-04-16
---
# Check out the new Playground

Admin app now has a new Playground page where you can test out the FAQ matching and LLM response endpoints!

<!-- more -->

Here's a screenshot:

![Playground](../images/playground.png){: .blog-img }

## Why did we build this?

Content managers can now test out how the retrieval APIs will perform when new content is added - without
leaving the Admin App.

By clicking on `<json>` at the bottom, they can also see the raw JSON response sent back
by the server. This include debugging information that may be useful in understanding behaviour.

![Playground JSON](../images/playground-json.png){: .blog-img }
