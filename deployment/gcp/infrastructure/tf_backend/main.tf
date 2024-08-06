terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.36.0"
    }
  }
  required_version = ">= 0.13"
}

resource "random_id" "bucket_prefix" {
  byte_length = 8
}

resource "google_storage_bucket" "terraform_state_bucket" {
  name          = "${var.deployment_group_name}-${random_id.bucket_prefix.hex}-bucket-tfstate"
  project       = var.project_id
  force_destroy = false
  location      = var.gcp_location
  storage_class = "STANDARD"
  versioning {
    enabled = true
  }
}
