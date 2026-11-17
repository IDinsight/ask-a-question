# Voice Service

The Voice Service component provides voice interaction capabilities within the AAQ system. It supports both speech recognition (STT) and text-to-speech (TTS) functionalities through two primary methods:

1. **In-House Models:** Utilize in-house, dockerized models for STT and TTS to process speech data locally.
2. **External APIs:** Integrate with Google Cloud's Speech-to-Text and Text-to-Speech APIs for enhanced flexibility and accuracy.

This documentation will guide you through setting up, configuring, and using the Voice Service in various scenarios.

Note: To enable the `/voice-search` endpoint in the question-answer service, you need to set the `TOGGLE_VOICE` environment variable in `.core_backend.env` (cf. [Configuring AAQ](../../deployment/config-options.md#configuring-the-backend-core_backend))

??? note "To use the speech service for manual setup and testing, you must install `ffmpeg` on your system."
    - [Guide for MacOS](https://phoenixnap.com/kb/ffmpeg-mac)
    - [Guide for Windows](https://phoenixnap.com/kb/ffmpeg-windows)
    - [Guide for Linux](https://phoenixnap.com/kb/install-ffmpeg-ubuntu)

??? note "Using a combination of internal and external models"
    You have the flexibility to use both internal and external models simultaneously by setting the environment variables accordingly. If one of the environment variables is not set, the system will automatically default to the external model. For information on configuring and using external models, refer to our [External APIs](./external-apis.md) and [In-house Models](./in-house-models.md) guide.

<div class="grid cards" markdown>

- :octicons-gear-16:{ .lg .middle .red} __Using In-House Models__

    ---

    Follow the steps to set up and use the in-house STT and TTS models.

    [:octicons-arrow-right-24: More info](./in-house-models.md)

- :octicons-gear-16:{ .lg .middle .red} __Using External APIs__

    ---

    Learn how to integrate Google Cloud's Speech-to-Text and Text-to-Speech services.

    [:octicons-arrow-right-24: More info](./external-apis.md)

</div>
