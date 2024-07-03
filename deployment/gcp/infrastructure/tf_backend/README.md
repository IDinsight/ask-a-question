<!-- 0. Run
   ```shell
   gcloud config set project $GCP_PROJECT_ID
   gcloud auth application-default login
   ``` -->

0. Run `export TF_VAR_gcp_project_id=your-gcp-project-id-12345"`
1. Run Terraform init and terraform apply against main.tf
2. Note down the bucket name.
3. Update backend.tf in each environment.
