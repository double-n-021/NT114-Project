# ============================================================
# MODULE: ACR — Azure Container Registry
# ============================================================
# Lưu trữ Docker images cho target-app và aiops-agent.
# CI/CD pipeline (GitHub Actions) sẽ build → push image vào ACR.
# AKS cluster pull image từ ACR khi kubectl apply deployment.
#
# SKU "Standard":
#   - 100 GB storage — đủ cho đồ án
#   - Rẻ (~$5/tháng vs Premium ~$50/tháng)
# ============================================================

variable "resource_group_name" {
  description = "Tên Resource Group chứa ACR"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "acr_name" {
  description = "Tên ACR — phải unique toàn cầu, chỉ chữ + số, không gạch ngang"
  type        = string
}

# --- Tạo Container Registry ---
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
}

# --- Outputs ---
output "acr_id" {
  description = "ACR resource ID — module AKS dùng để gán quyền AcrPull"
  value       = azurerm_container_registry.acr.id
}

output "login_server" {
  description = "ACR login URL, vd: nt114acr.azurecr.io — CI/CD dùng để push image"
  value       = azurerm_container_registry.acr.login_server
}
