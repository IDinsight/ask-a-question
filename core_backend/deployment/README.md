# Backend Deployment

To ensure the application initializes correctly, certain variables must be declared. These variables were originally located within a config file and an .env file. For the application to access these variables on startup, the bootstrap_demo.sh script is employed.

The variables come from two different sources:

 - Some variables are securely stored in the AWS Secret Manager. This is where sensitive information, such as API keys, database passwords, and other confidential data, is held.
 - Other variables are declared directly in GitHub Actions. These might include less sensitive configurations that are required for the CI/CD process.

By separating these variables accordingly — sensitive data in AWS Secret Manager and other configurations in GitHub Actions — we maintain both security and functionality during startup and within the continuous integration and delivery workflows.

The variables in the AWS Secret Manager can either be in form of text or json. When stored in json, this means that there are multiple values under on Secret. The values are accessed using their key.

## Creating a Secret.
All secrets stored in AWS Secret manager are created and managed using Terraform. The secrets can be located under `main/credentials.md` in the infrastructure code.
To add a generated secret, below are the steps:
 - Add the value of `random_password.secrets.count` by X depending on how many secrets need to be genereated
 - Create an `aws_secretsmanager_secret` and `aws_secretsmanager_secret_version`. The value of the `aws_secretsmanager_secret_version.secret_string` is where the generated secret will be stored. To add the value of the generated secret, reference the `random_password.secrets` and value of the index. If there are 2 secrets to be generated, the index startes from 0, if the secret is the first one, the value will be `random_password.secrets[0].result`. If you are adding to already existing count, get the last decled index and add 1. So if the last secret was `random_password.secrets[4].result`, the new one will be `random_password.secrets[5].result`
 - If the secret is to be manually added, the `secret_string` should have a place holder string. Terraform will not allow an empty string. In the `aws_secretsmanager_secret_version`, we will also have to ignore changes to the string. This is because when yyou manually change the string, terraform will detect the change and without ignoring the change it will overwrite the secret with the place holder
 - Once the secret is added, it also needs to be added to the `bootstrap_{env}.sh` file if it is needed on startup.