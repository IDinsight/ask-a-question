# Setup new infrastructure

## Set up terraform backend

0. You may have to authenticate to gcloud

   ```shell
   gcloud config set project $GCP_PROJECT_ID
   gcloud auth application-default login
   ```

1. Run `export TF_VAR_gcp_project_id=your-gcp-project-id-12345"`
2. Run `terraform init` and `terraform apply` against main.tf
3. Note down the bucket name.
4. Update `backend.conf` in each environment (e.g. testing, production, ...)
