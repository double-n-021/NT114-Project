# ============================================================
# Terraform Root Module — Azure Infrastructure
# ============================================================
# Entry point gọi 3 modules theo thứ tự dependency:
#   1. Resource Group (tạo trước — mọi resource đều nằm trong RG)
#   2. modules/networking → VNet + Subnet
#   3. modules/acr        → Container Registry
#   4. modules/aks        → AKS cluster (nhận subnet_id + acr_id từ trên)
#
# Usage:
#   cd terraform/
#   terraform init
#   terraform plan -var-file=environments/dev/terraform.tfvars
#   terraform apply -var-file=environments/dev/terraform.tfvars
#   terraform destroy -var-file=environments/dev/terraform.tfvars
# ============================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ============================================================
# 1. Resource Group — container logic cho toàn bộ Azure resources
# ============================================================
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# ============================================================
# 2. Networking — VNet + Subnet (tạo trước AKS)
# ============================================================
module "networking" {
  source              = "./modules/networking"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

# ============================================================
# 3. ACR — Container Registry (tạo trước AKS để gán quyền pull)
# ============================================================
module "acr" {
  source              = "./modules/acr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  acr_name            = var.acr_name
}

# ============================================================
# 4. AKS — Kubernetes Cluster (phụ thuộc networking + acr)
# ============================================================
module "aks" {
  source              = "./modules/aks"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  aks_name            = var.aks_name
  node_count          = var.aks_node_count
  vm_size             = var.aks_vm_size
  aks_subnet_id       = module.networking.aks_subnet_id   # output từ networking
  acr_id              = module.acr.acr_id                 # output từ acr
}
