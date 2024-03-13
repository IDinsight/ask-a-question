# Configuring AAQ

There are compulsory configs you must set like secrets and API keys. These are all set
in the .env files as shown in Steps 3 and 4 in [Quick Setup]("./setup.md").

## Other parameters

In addition to these, you can modify a bunch of other parameters by either:

- Setting environment variables in the `.env` file; or
- Updating the config directly in the config files under `core_backend/app/configs/`.

??? Note "Environment variables take precedence over the config file."
    You'll see in the config files that we get parameters from the environment and if
    not found, we fall back on defaults provided. So any environment variables set
    will override any defaults you have set in the config file.


### Application parameters

You can find parameters than control the behaviour of the app at

```bash
core_backend/app/configs/
```

For a number of optional
components like the WhatsApp connector or offline models, you will need to update the
parameters in this file.

See instructions for setting these in the documentation for the specific optional component.

### Updating LLM prompts

You may wish to customize the prompts for your specific context. These are all found
in

```bash
core_backend/app/configs/llm_prompts.py
```
