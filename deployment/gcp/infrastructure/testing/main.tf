###############################################################################
# Compute Engine instance
###############################################################################

# External IP
resource "google_compute_address" "vm_static_ip" {
  name = "${var.deployment_group_name}-${var.environment}-static-ip"
}

# Compute Instance
resource "google_compute_instance" "vm_instance" {
  name                = "${var.deployment_group_name}-${var.environment}"
  machine_type        = var.gce_instance_type
  can_ip_forward      = false
  deletion_protection = false
  enable_display      = false

  boot_disk {
    auto_delete = true
    device_name = "${var.deployment_group_name}-${var.environment}"

    initialize_params {
      image = "cos-cloud/cos-113-18244-85-49"
      size  = 100
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.vm_static_ip.address
    }
  }

  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  tags = ["https-server"]

  metadata_startup_script = file("${path.module}/startup.sh")
}

###############################################################################
# Cloud SQL PostgreSQL instance
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance
###############################################################################

resource "google_sql_database_instance" "postgres_instance" {
  name             = "${var.deployment_group_name}-${var.environment}-web-db"
  database_version = "POSTGRES_16"
  root_password    = random_password.postgres_password.result
  settings {
    tier            = var.db_tier
    disk_size       = 64
    disk_autoresize = true
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = google_compute_instance.vm_instance.name
        value = google_compute_address.vm_static_ip.address
      }
    }
  }

  # On newer versions of the provider, you must explicitly set deletion_protection=false (and run terraform apply to write the field to state) in order to destroy an instance. It is recommended to not set this field (or set it to true) until you're ready to destroy the instance and its databases.
  deletion_protection = false
}

###############################################################################
# Docker image repo
###############################################################################

resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = "${var.deployment_group_name}-${var.environment}"
  description   = "Docker image repository for ${var.deployment_group_name}-${var.environment}"
  format        = "DOCKER"
}
