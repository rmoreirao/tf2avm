output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "virtual_network_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.main.id
}

output "virtual_network_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.main.name
}

output "subnet_ids" {
  description = "IDs of the subnets"
  value = {
    web = azurerm_subnet.web.id
    app = azurerm_subnet.app.id
  }
}

output "network_security_group_id" {
  description = "ID of the network security group"
  value       = azurerm_network_security_group.web.id
}