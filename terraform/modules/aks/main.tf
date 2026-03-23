# ============================================================
# MODULE: AKS — Azure Kubernetes Service
# ============================================================
# Cluster Kubernetes chính — chạy toàn bộ hệ thống:
#   namespace medical-data → target-app, Mosquitto, KEDA, NetworkPolicy
#   namespace aiops        → AI Agent, MLflow, Ollama
#   namespace monitoring   → Prometheus, Grafana, Loki
#
# Cấu hình mạng QUAN TRỌNG cho đồ án:
#   network_plugin = "azure"  → Azure CNI: Pod nhận IP thật từ subnet
#   network_policy = "azure"  → Bật K8s NetworkPolicy (Agent chặn DDoS)
# ============================================================

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "aks_name" {
  description = "Tên AKS cluster"
  type        = string
  default     = "aks-agentic-aiops"
}

variable "node_count" {
  description = "Số worker nodes (dev=1, prod=2)"
  type        = number
  default     = 2
}

variable "vm_size" {
  description = "VM size mỗi node (dev=Standard_B2s, prod=Standard_D2s_v3)"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "aks_subnet_id" {
  description = "Subnet ID từ module networking"
  type        = string
}

variable "acr_id" {
  description = "ACR resource ID từ module acr — để gán quyền AcrPull"
  type        = string
}

# --- Tạo AKS Cluster ---
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "aiops-cluster"

  default_node_pool {
    name           = "default"
    node_count     = var.node_count
    vm_size        = var.vm_size
    vnet_subnet_id = var.aks_subnet_id
  }

  # SystemAssigned = Azure tự tạo Managed Identity, không cần Service Principal
  identity {
    type = "SystemAssigned"
  }

  # --- Cấu hình mạng ---
  network_profile {
    network_plugin    = "azure"           # Azure CNI — Pod nhận IP thật
    network_policy    = "azure"           # Bật NetworkPolicy cho K8s
    load_balancer_sku = "standard"
    service_cidr      = "172.16.0.0/16"   # CIDR cho K8s Services (không trùng VNet 10.x)
    dns_service_ip    = "172.16.0.10"
  }
}

# --- Gán quyền AcrPull ---
# Nếu thiếu cái này: AKS sẽ không kéo được image từ ACR → Pod = ImagePullBackOff
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# --- Outputs ---
output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "kube_config" {
  description = "Kubeconfig raw — dùng: export KUBECONFIG=<path>"
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "cluster_id" {
  value = azurerm_kubernetes_cluster.aks.id
}
