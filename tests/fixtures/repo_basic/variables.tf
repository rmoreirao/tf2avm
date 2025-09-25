variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-vnet-demo"
}

variable "location" {
  description = "Azure location"
  type        = string
  default     = "West Europe"
}

variable "vnet_name" {
  description = "Name of the virtual network"
  type        = string
  default     = "vnet-demo"
}

variable "address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {
    Environment = "Demo"
    Project     = "VNet-Demo"
  }
}