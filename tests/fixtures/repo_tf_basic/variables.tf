# General Variables
variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-webapp-demo"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Environment = "Demo"
    Project     = "WebApp"
    ManagedBy   = "Terraform"
  }
}

# App Service Variables
variable "app_service_plan_name" {
  description = "Name of the App Service Plan"
  type        = string
  default     = "asp-webapp-demo"
}

variable "app_service_plan_sku" {
  description = "SKU for the App Service Plan"
  type        = string
  default     = "B1"
}

variable "web_app_name" {
  description = "Name of the Web App (ReactJS)"
  type        = string
  default     = "webapp-frontend-demo"
}

variable "api_app_name" {
  description = "Name of the API App (.NET)"
  type        = string
  default     = "webapp-api-demo"
}

# Key Vault Variables
variable "key_vault_name" {
  description = "Name of the Key Vault"
  type        = string
  default     = "kv-webapp-demo"
}

# Cosmos DB Variables
variable "cosmos_db_account_name" {
  description = "Name of the Cosmos DB account"
  type        = string
  default     = "cosmos-webapp-demo"
}

variable "cosmos_db_database_name" {
  description = "Name of the Cosmos DB database"
  type        = string
  default     = "webapp-db"
}

variable "cosmos_db_container_name" {
  description = "Name of the Cosmos DB container"
  type        = string
  default     = "webapp-container"
}

# Monitoring Variables
variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace"
  type        = string
  default     = "law-webapp-demo"
}

variable "application_insights_name" {
  description = "Name of the Application Insights instance"
  type        = string
  default     = "ai-webapp-demo"
}