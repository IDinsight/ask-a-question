terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "~> 5.36.0"
    }
  }
  backend "gcs" {}
}
