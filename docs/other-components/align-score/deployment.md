# Deploying and Using AlignScore

The authors of the AlignScore paper have made
[their code](https://github.com/yuh-zha/AlignScore) available on Github.
We wrap their code (1) in a FastAPI application and expose APIs that can be called by AAQ.
The FastAPI application can be deployed using a Docker container.
{ .annotate }

1.  Actually, we wrap [a fork](https://github.com/IDinsight/AlignScore) of their code


## Configure AAQ to use AlignScore

You can use AlignScore instead of the default LLM-based content validation by setting
`ALIGN_SCORE_METHOD` to `AlignScore` in the `.env` file (1) in the `deployment/` folder.
{.annotate}

1.  If you don't a .env file, make sure you have deployed the app as per instruction in
[Quick Setup]("../../deployment/quick-setup.md")

```
ALIGN_SCORE_METHOD=AlignScore
```
### Other configuration

You can also change the threshold score below which the LLM response is considered not
consistent with the provided context.
```
ALIGN_SCORE_THRESHOLD=0.7
```

See [Testing](./testing.md) on how to decide on this threshold.

## Deploying the service

Follow the deployment instructions in [Quick Setup]("../../deployment/quick-setup.md").

On **Step 6:** _Run docker-compose_, run the following command instead:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
    --profile alignScore -p aaq-stack up -d --build
```

### Dev setup

If you are using the [Dev setup](../../develop/setup.md), you can start the container
manually using:

```bash
cd optional_components/alignScore
docker build -t alignscore-base . # (1)
docker run -p 5001:5001 --name align-score-local --detach 'alignscore-base'
```

1.  This step can take long time and even longer if you have a slow internet connection.
So if you have already generated the image previously, you can skip this step. Alternatively,
you can pull from ECR using
```
docker pull \
    public.ecr.aws/j3r7b4k0/alignscore-base:latest
```

## Also see

1. [Quick Setup]("../../deployment/quick-setup.md")
2. [Configuring AAQ]("../../deployment/config-options.md")
