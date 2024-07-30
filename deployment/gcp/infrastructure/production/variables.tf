variable "deployment_group_name" {
  description = "value for the deployment group name"
  type        = string
}

variable "environment" {
  description = "value for the deployment environment"
  type        = string
}

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_location" {
  description = "GCP location"
  type        = string
}

variable "gcp_zone" {
  description = "value for the GCP zone"
  type        = string
}

variable "gce_instance_type" {
  description = "value for the GCE instance type"
  type        = string

}

variable "db_tier" {
  description = "Tier for the Cloud SQL instance. You can check available instances with `gcloud sql tiers list`."
  type        = string
}

variable "admin_username" {
  description = "Admin username for AAQ."
  type        = string
  sensitive   = true
}

variable "service_account_email" {
  description = "Service account email"
  type        = string
  sensitive   = true
}
