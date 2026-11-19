variable "subscription_id" {
  description = "Azure subscription ID (set by the deploy workflow from the AZURE_SUBSCRIPTION_ID variable)."
  type        = string
}

variable "name" {
  description = "Short name used in every resource name."
  type        = string
  default     = "windgrid"
}

variable "location" {
  description = "Azure region. Azure for Students subscriptions allow only some regions; change it if a policy rejects this one."
  type        = string
  default     = "uksouth"
}

variable "image_registry" {
  description = "Container registry and owner that hold the CI-built images."
  type        = string
  default     = "ghcr.io/arqam3025"
}

variable "image_tag" {
  description = "Image tag to deploy (the deploy workflow passes the commit tag, sha-xxxxxxx)."
  type        = string
  default     = "latest"
}

variable "min_replicas" {
  description = "0 = scale to zero when idle (lowest cost; first request after idle takes a few seconds)."
  type        = number
  default     = 0

  validation {
    condition     = var.min_replicas >= 0 && var.min_replicas <= 1
    error_message = "min_replicas must be 0 or 1."
  }
}
