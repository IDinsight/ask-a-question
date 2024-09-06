# Voice Service

The Voice Service component provides voice interaction capabilities within the AAQ system. It supports both speech recognition (STT) and text-to-speech (TTS) functionalities through two primary methods:

1. **In-House Models:** Utilize in-house, dockerized models for STT and TTS to process speech data locally.
2. **External APIs:** Integrate with Google Cloud's Speech-to-Text and Text-to-Speech APIs for enhanced flexibility and accuracy.

This documentation will guide you through setting up, configuring, and using the Voice Service in various scenarios.

??? info "To Access the `/voice-search` endpoint In the question-answer service"
    You need to set the `TOGGLE_VOICE` environment variable in the `.core_backend.env` (cf. [Configuring AAQ](../../deployment/config-options.md#configuring-the-backend-core_backend))

---

??? note "To use the speech service for manual setup and testing, you must have `ffmpeg` installed on your system."
    for [MacOs](https://phoenixnap.com/kb/ffmpeg-mac) follow this guide.

    for [Windows](https://phoenixnap.com/kb/ffmpeg-windows) follow this guide.

    for [Linux](https://phoenixnap.com/kb/install-ffmpeg-ubuntu) follow this guide.

    Ensure `ffmpeg` is properly installed and accessible in your system's path.

??? note "Using a Combination of Internal and External Models"
    You have the flexibility to use both internal and external models simultaneously. Set the environment variables accordingly. If one of the environment variables is not set, the system will automatically default to the external model. For information on configuring and using external models, refer to our [External Apis](./external-apis.md) and [In-house Models](./in-house-models.md) guide.

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
