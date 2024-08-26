# Voice Service

The Voice Service component provides voice interaction capabilities within the AAQ system. It supports both speech recognition (ASR) and text-to-speech (TTS) functionalities through two primary methods:

1. **In-House Models:** Utilize in-house, dockerized models for ASR and TTS to process speech data locally.
2. **External APIs:** Integrate with Google Cloud's Speech-to-Text and Text-to-Speech APIs for enhanced flexibility and accuracy.

This documentation will guide you through setting up, configuring, and using the Voice Service in various scenarios.

## Key Features

- **Speech Recognition (ASR):** Convert spoken language into text.
- **Text-to-Speech (TTS):** Generate speech from text using high-quality voice models.
- **Flexible Integration:** Choose between in-house models and external APIs based on your requirements.

## Getting Started

To start using the Voice Service, follow the setup instructions in the following sections:

- [In-House Models](./in-house-models.md): Setting up and using the in-house ASR and TTS models.
- [External APIs](./external-apis.md): Integrating Google Cloud's STT and TTS services.
