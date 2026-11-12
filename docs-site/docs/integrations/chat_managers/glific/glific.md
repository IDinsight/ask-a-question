# ![glific logo](./glific_logo.png){ width="90" } <br/> Setup Instructions

Below is a tutorial for how to load our FAQ template flow into Glific and connect it to your own AAQ endpoint.

1. Go to "Flows"

    ![click flows](./tutorial/1_click_flows.png){ width="150" }

2. Click "Import flow"

    ![click import](./tutorial/2_click_import.png){ width="400" }

3. Select a `.json` file given under `chat_managers/glific/` in the [AAQ repo](https://github.com/IDinsight/ask-a-question/tree/main/chat_managers/glific)

    ![import flow](./tutorial/3_load_flow.png){ width="600" }

4. Open the imported flow

    ![open flow](./tutorial/4_open_flow.png){ width="600" }

5. Open the webhook card

    ![open webhook card](./tutorial/5_click_webhook.png){ width="600" }

6. Replace `<INSERT_AAQ_URL>` with your the URL to your AAQ instance

    ![replace URL](./tutorial/6_change_URL.png){ width="600" }

7. Go to headers and replace `<INSERT_AAQ_API_KEY>` value to your own AAQ API key.

    ![click headers](./tutorial/7_click_headers.png){ width="600" }
    ![replace API key](./tutorial/8_change_api_key.png){ width="600" }

8. Test the flow in the "Preview" emulator

    ![click preview](./tutorial/9_preview.png){ width="400" }
    ![start test](./tutorial/10_try.png){ width="400" }
