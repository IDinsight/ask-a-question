# Setting up the WhatsApp integration

The WhatsApp connector allows you to send and receive messages using the WhatsApp Business API.

The WhatsApp server sends post requests to our FastAPI app. Our App processes these messages and replies to the user. Right now, we respond to the incoming message with the best matching document chunk from our database [To change in the future].

### Step 1. Core App Deployment
To set up the WhatsApp integration, while deploying the Core App, you need to do the following:
1. Create/Login to your Meta/Facebook project
2. Once you are in the project, go to "WhatsApp" -> "API Setup"
3. Copy the "Temporary access token" and paste it in the `WHATSAPP_TOKEN` field in the `.env` file in the deployments folder in the aaq-core repo
    - You can skip the previous steps if you already have access to the `WHATSAPP_TOKEN`.
4. In the `.env` file, set the `WHATSAPP_VERIFY_TOKEN` according to any string of your choice. This will be used to verify the WhatsApp webhook in the next step.

These are all the necessary steps to set up the Core App for WhatsApp integration at the app deployment stage. You can go ahead and deploy the app.

### Step 2. WhatsApp Webhook Setup
Once you have deployed the Core App, you need to set up the webhook for the WhatsApp integration. To do this, follow these steps:
1. Login to your Meta project
2. Navigate to the "WhatsApp" -> "Webhook" page
3. Click on "Edit Subscription"
4. In the pop-up, fill in the core-backend app's URL in the "Callback URL" field. The URL should be of the form: `<your-core-backend-app-url>/webhook`. Then fill the "Verify token" field with the value of the `WHATSAPP_VERIFY_TOKEN` that you set in the `.env` file in the Core App deployment step. Finally, click on "Verify and Save"
5. Next, navigate to "WhatsApp" -> "Configuration"
6. On the page, next to "Callback URL", click on the "Edit" button and similar to the previous step, fill in the "Callback URL" and the "Verify token" field.

Once you have gone through all of the above steps, you will have successfully set up a connection between WhatsApp and your app!
