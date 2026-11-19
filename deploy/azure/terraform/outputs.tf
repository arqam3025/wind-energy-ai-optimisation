output "api_url" {
  description = "Public HTTPS URL of the dispatch API (interactive docs at /docs)."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "dashboard_url" {
  description = "Public HTTPS URL of the dashboard."
  value       = "https://${azurerm_container_app.dashboard.ingress[0].fqdn}"
}

output "resource_group" {
  value = azurerm_resource_group.main.name
}
