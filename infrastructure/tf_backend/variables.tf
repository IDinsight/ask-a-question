variable "project_name" {
  type = string

  validation {
    condition     = var.project_name != "<fill-project-name>"
    error_message = "You must provide your project name in tf_backend.auto.tfvars."
  }

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.project_name))
    error_message = "Invalid project name. Project names must be all lowercase letters with non-consecutive hyphens, e.g. my-superset-project."
  }
}

variable "billing_code" {
  type = string

  validation {
    condition     = var.billing_code != "<Fill Billing Code>"
    error_message = "You must provide your billing code in tf_backend.auto.tfvars."
  }
}
