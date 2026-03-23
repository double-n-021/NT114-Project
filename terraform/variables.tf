variable "resource_group_name" {
  description = "Azure Resource Group name"
  type        = string
  default     = "rg-aiops-qos"
}

variable "location" {
  description = "Azure region (southeastasia = gần VN nhất)"
  type        = string
  default     = "southeastasia"
}

variable "environment" {
  description = "Environment name (dev/prod)"
  type        = string
  default     = "dev"
}

variable "aks_name" {
  description = "Tên AKS cluster"
  type        = string
  default     = "aks-agentic-aiops"
}

variable "aks_node_count" {
  description = "Số worker nodes (dev=1, prod=2)"
  type        = number
  default     = 2
}

variable "aks_vm_size" {
  description = "VM size cho mỗi AKS node"
  type        = string
  default     = "Standard_B2s"
}

variable "acr_name" {
  description = "Tên ACR — phải unique toàn cầu, chỉ chữ + số"
  type        = string
  default     = "nt1142352132523521037"
}
