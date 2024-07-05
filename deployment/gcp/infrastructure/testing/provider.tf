provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_location
  zone    = var.gcp_zone
}
