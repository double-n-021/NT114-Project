resource "kubernetes_namespace" "medical_data" {
  metadata {
    name = "medical-data"
  }
}

resource "kubernetes_namespace" "aiops" {
  metadata {
    name = "aiops"
  }
}

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }
}

resource "kubernetes_namespace" "keda_system" {
  metadata {
    name = "keda-system"
  }
}