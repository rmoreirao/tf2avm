resource "azurerm_virtual_network" "vnet1" {
  name                = "vnet1"
  resource_group_name = "rg-demo"
  location            = "westeurope"
  address_space       = ["10.0.0.0/16"]
}
