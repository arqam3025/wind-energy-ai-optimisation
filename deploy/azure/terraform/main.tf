# WindGrid on Azure Container Apps: API + dashboard with public HTTPS endpoints, scale-to-zero.
#
# Created resources (all in one resource group):
#   - Log Analytics workspace (container logs, 30-day retention)
#   - Container Apps environment
#   - Container App "windgrid-api"        (port 8000, /health probes, 0..3 replicas)
#   - Container App "windgrid-dashboard"  (port 8501, 0..1 replica, sticky sessions)
#
# Images come from GitHub Container Registry (built and pushed by CI). State is kept in an
# Azure Storage backend created by deploy/azure/bootstrap.sh.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  use_oidc        = true
}

locals {
  tags = {
    project    = "windgrid"
    managed_by = "terraform"
    repository = "github.com/arqam3025/wind-energy-ai-optimisation"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.5
  tags                = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.name}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

resource "azurerm_container_app" "api" {
  name                         = "${var.name}-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = var.min_replicas
    max_replicas = 3

    container {
      name   = "api"
      image  = "${var.image_registry}/windgrid-api:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "MPLCONFIGDIR"
        value = "/tmp/matplotlib"
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }

    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = "20"
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

resource "azurerm_container_app" "dashboard" {
  name                         = "${var.name}-dashboard"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = var.min_replicas
    max_replicas = 1

    container {
      name   = "dashboard"
      image  = "${var.image_registry}/windgrid-dashboard:${var.image_tag}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "HOME"
        value = "/tmp"
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8501
        path      = "/_stcore/health"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8501
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
