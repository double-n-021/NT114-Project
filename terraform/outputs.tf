# ============================================================
# Outputs — hiển thị thông tin quan trọng sau terraform apply
# ============================================================

output "resource_group_name" {
  description = "Tên Resource Group đã tạo"
  value       = azurerm_resource_group.rg.name
}

output "aks_cluster_name" {
  description = "Tên AKS cluster — dùng: az aks get-credentials --name <this>"
  value       = module.aks.cluster_name
}

output "acr_login_server" {
  description = "ACR URL — dùng: docker push <this>/target-app:v1"
  value       = module.acr.login_server
}

output "kube_config" {
  description = "Kubeconfig để kết nối kubectl"
  value       = module.aks.kube_config
  sensitive   = true
}
