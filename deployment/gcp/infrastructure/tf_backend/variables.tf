variable "project_id" {
  type = string
  description = "GCP project ID. Set through export TF_VAR_gcp_project_id=<project_id> or in tf_backend.auto.tfvars."
}
variable "project_name" {
  type = string

  validation {
    condition     = var.project_name != ""
    error_message = "You must provide your project name in tf_backend.auto.tfvars."
  }

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.project_name))
    error_message = "Invalid project name. Project names must be all lowercase letters with non-consecutive hyphens, e.g. my-superset-project."
  }
}

variable "gcp_region" {
  type = string
  validation {
    condition     = var.gcp_region != ""
    error_message = "You must provide your GCP region in tf_backend.auto.tfvars."
  }
}
