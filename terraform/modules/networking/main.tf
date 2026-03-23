# ============================================================
# MODULE: NETWORKING — VNet + Subnet cho AKS
# ============================================================
# Tạo mạng ảo (Virtual Network) riêng biệt cho AKS cluster.
# Subnet snet-aks sẽ được gán cho node pool của AKS.
#
# Tại sao cần VNet riêng?
#   - Cách ly traffic giữa AKS và các service khác trên Azure
#   - Cho phép dùng Azure CNI → mỗi Pod nhận IP thật trong subnet
#   - Hỗ trợ NetworkPolicy (cần cho Agent chặn DDoS traffic)
# ============================================================

variable "resource_group_name" {
  description = "Tên Resource Group chứa VNet"
  type        = string
}

variable "location" {
  description = "Azure region (southeastasia cho VN)"
  type        = string
}

# --- Tạo Virtual Network ---
# Address space 10.0.0.0/16 = 65,536 IPs — đủ rộng cho cluster + mở rộng sau
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-aiops"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = var.resource_group_name
}

# --- Tạo Subnet cho AKS ---
# 10.0.1.0/24 = 256 IPs — đủ cho 2 nodes × ~30 pods/node (Azure CNI)
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# --- Outputs trả về cho root module ---
output "vnet_id" {
  value = azurerm_virtual_network.vnet.id
}

output "aks_subnet_id" {
  description = "Subnet ID — module AKS dùng để gán node pool vào đây"
  value       = azurerm_subnet.aks.id
}
