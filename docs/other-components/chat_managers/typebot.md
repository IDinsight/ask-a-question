# Typebot

Below is an example of how to get Typebot running and connected to AAQ endpoints using a provided demo bot.

## Deployment

**Step 1:** Navigate to `chat_managers/typebot/deployment/`

**Step 2:** Copy `template.env` to `.env` and edit it to set the variables

**Step 3:** Run docker compose

    docker compose -p typebot-stack up -d --build

You can now access Typebot at `https://[DOMAIN]/`

**Step 4:** Shutdown containers

    docker compose -p typebot-stack down

## Using Typebot

1. Go to the URL where the app is running
2. Make an account and login
3. Go to "Create a typebot" and then "Import a file"
4. Load the `.json` file given under `chat_managers/typebot/` in this repo
5. Edit the "API Call" cards to reflect the AAQ endpoint URL that you have running

    a. Click on the card

    b. Change the base of the URL at the top

    c. Add the bearer token in the Headers section.

6. Test the bot in the emulator
