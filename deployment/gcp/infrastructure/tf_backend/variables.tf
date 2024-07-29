variable "project_id" {
  type        = string
  description = "GCP project ID."
}
variable "deployment_group_name" {
  type = string

  validation {
    condition     = var.deployment_group_name != ""
    error_message = "You must provide your deployment group name in tf_backend.auto.tfvars."
  }

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.deployment_group_name))
    error_message = "Invalid deployment group name. Deployment group names must be all lowercase letters with non-consecutive hyphens, e.g. my-superset-project."
  }
}

variable "gcp_location" {
  type = string
  validation {
    condition     = var.gcp_location != ""
    error_message = "You must provide your GCP location in tf_backend.auto.tfvars."
  }
}
