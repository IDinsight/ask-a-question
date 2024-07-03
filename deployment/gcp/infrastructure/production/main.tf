###############################################################################
# Compute Engine instance
###############################################################################

# External IP
resource "google_compute_address" "vm_static_ip" {
  name   = "${var.project_name}-${var.environment}-static-ip"
}

# Firewall rule to allow incoming HTTPS traffic
# resource "google_compute_firewall" "allow_https" {
#   name    = "${var.project_name}-${var.environment}-allow-https"
#   network = "default"

#   allow {
#     protocol = "tcp"
#     ports    = ["443"]
#   }

#   source_ranges = ["0.0.0.0/0"]

#   target_tags = ["https-server"]
# }

# Compute Instance
resource "google_compute_instance" "vm_instance" {
  name         = "${var.project_name}-${var.environment}"
  machine_type = var.gce_instance_type
  boot_disk {
    initialize_params {
        image = "cos-cloud/cos-113-18244-85-49"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.vm_static_ip.address
    }
  }

  tags = ["https-server"]

  metadata_startup_script = file("${path.module}/startup.sh")
}

###############################################################################
# Cloud SQL PostgreSQL instance
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance
###############################################################################

resource "google_sql_database_instance" "postgres_instance" {
    name             = "${var.project_name}-${var.environment}-web-db"
    database_version = "POSTGRES_16"
    root_password = random_password.postgres_password.result
    settings {
        tier = var.db_tier
        disk_size = 64
        disk_autoresize = true
        ip_configuration {
            ipv4_enabled    = true
            authorized_networks {
                name  = google_compute_instance.vm_instance.name
                value = google_compute_address.vm_static_ip.address
            }
        }
    }

    # On newer versions of the provider, you must explicitly set deletion_protection=false (and run terraform apply to write the field to state) in order to destroy an instance. It is recommended to not set this field (or set it to true) until you're ready to destroy the instance and its databases.
    # deletion_protection = true
}

###############################################################################
# Docker image repo
###############################################################################

resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = "${var.project_name}-${var.environment}"
  description   = "Docker image repository for ${var.project_name}-${var.environment}"
  format        = "DOCKER"
}
