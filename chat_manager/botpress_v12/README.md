# Botpress v12

## Installation and Setup

### Via Docker

To install through Docker (recommended): Follow the official Botpress v12 docs [here](https://hub.docker.com/r/botpress/server).

1.  Get the image

        docker pull botpress/server

2.  Run the image

        docker run -d --name=botpress -p 3000:3000 botpress/server

⚠️ If you're having issues with image type on MacOS, you can also try running the image through the Docker UI instead of commandline. This fixed the issue for me.

### Via executables

To install for Mac/Windows/Linux: Follow the official docs [here](https://v12.botpress.com/) to set up Botpress v12 locally as per your OS.

## Running Botpress

1. Go to `localhost://3000`
2. Make an account and login
3. Go to "Create Bot" and then "Import Existing" (you can set Bot ID to anything you want)
4. Load the `.tgz` file given in this repo
5. Edit the "API Call" cards to reflect the AAQ endpoint URL that you have running

   a. Click on the card

   b. Click on "Edit skill"

   c. Change the base of the URL at the top

6. Test the bot in the emulator
