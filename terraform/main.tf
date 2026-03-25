terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.5.1"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.23.0"
    }
  }
}

# Cấu hình cụm Kind Cluster giả lập AKS
resource "kind_cluster" "aiops_local" {
  name           = "agentic-aiops-cluster"
  node_image     = "kindest/node:v1.27.3"
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    # Cấu hình Node chính (Control Plane)
    node {
      role = "control-plane"
      
      # Map cổng 80 từ máy bạn vào K8s để Ingress hoạt động
      extra_port_mappings {
        container_port = 80
        host_port      = 8881
      }
      # Map cổng 1883 cho MQTT Broker
      extra_port_mappings {
        container_port = 31883
        host_port      = 1883
      }
    }
  }
}

# Kết nối Terraform với cụm K8s vừa tạo
provider "kubernetes" {
  host                   = kind_cluster.aiops_local.endpoint
  client_certificate     = kind_cluster.aiops_local.client_certificate
  client_key             = kind_cluster.aiops_local.client_key
  cluster_ca_certificate = kind_cluster.aiops_local.cluster_ca_certificate
}