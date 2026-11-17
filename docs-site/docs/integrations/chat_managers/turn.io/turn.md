# ![turn logo](./turn_logo.png){ width="100" } <br/> Setup Instructions

Below is an example of how to connect a [Turn.io Journey](https://whatsapp.turn.io/docs/build/journeys_overview) to AAQ endpoints.

1. On your [Turn.io](https://whatsapp.turn.io/app/) page, go to the Journey menu.

    ![Click Journey menu](./tutorial/01_Journeys.png){ width="200" }

2. Create New Journey.

    ![Click New Journey](./tutorial/02_New_journey.png){ width="400" }

2. Select "From Scratch" -> "Code".

    ![Select From Scratch and then Code](./tutorial/03_From_scratch_code.png){ width="250" }

3. Type in your journey title and click "Next".

    ![Type in your journey title and click "Next".](./tutorial/04_New_journey.png){ width=420 }

4. Copy and paste the contents of
   [chat_managers/turn.io/llm_response_flow_code_journey.txt](https://github.com/IDinsight/ask-a-question/blob/main/chat_managers/turn.io/llm_response_flow_code_journey.txt) in the AAQ repository into the
   Journey's code area.

    ![Copy and paste the journey code from chat_managers/turn.io/llm_response_flow_code_journey.txt into the code area](./tutorial/05_Paste_code.png)

5. Replace `<INSERT_AAQ_URL>` and `<INSERT_AAQ_API_KEY>` values to your own AAQ URL and
   API key.

    ![Replace `<INSERT_AAQ_URL>` and `<INSERT_AAQ_API_KEY>` values to your own AAQ URL and API key.](./tutorial/06_replace.png)

6. Test the bot in the emulator.

    ![Test in the emulator](./tutorial/07_emulate.png){ width="300"}
