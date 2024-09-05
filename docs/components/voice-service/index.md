# Voice Service

The Voice Service component provides voice interaction capabilities within the AAQ system. It supports both speech recognition (ASR) and text-to-speech (TTS) functionalities through two primary methods:

1. **In-House Models:** Utilize in-house, dockerized models for ASR and TTS to process speech data locally.
2. **External APIs:** Integrate with Google Cloud's Speech-to-Text and Text-to-Speech APIs for enhanced flexibility and accuracy.

This documentation will guide you through setting up, configuring, and using the Voice Service in various scenarios.

---
**Note**

To use the external speech APIs (Google Cloud's Speech-to-Text and Text-to-Speech), you will need to set up a Google Cloud account and obtain the necessary credentials file to authenticate with Google Cloud. This is essential for accessing and using their services. Alternatively, you can use the
in-house models if you prefer not to integrate with external APIs.

---

<div class="grid cards" markdown>

- :octicons-gear-16:{ .lg .middle .red} __How to use In-House Models__

    ---

    Follow the steps to set up and use the In-house STT and TTS models.

    [:octicons-arrow-right-24: More info](./in-house-models.md)

- :octicons-gear-16:{ .lg .middle .red} __How to use External APIs__

    ---

    Learn how to integrate Google Cloud's Speech-to-Text and Text-to-Speech services.

    [:octicons-arrow-right-24: More info](./external-apis.md)

</div>
