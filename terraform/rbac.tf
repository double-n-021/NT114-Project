# 1. Tạo "Chứng minh nhân dân" cho AI Agent
resource "kubernetes_service_account" "ai_agent_sa" {
  metadata {
    name      = "ai-agent-sa"
    namespace = "aiops"
  }
}

# 2. Định nghĩa danh sách các việc AI được làm (Role)
resource "kubernetes_cluster_role" "ai_agent_role" {
  metadata {
    name = "ai-agent-role"
  }

  rule {
    api_groups = ["", "apps", "autoscaling", "networking.k8s.io"]
    resources  = ["pods", "deployments", "services", "networkpolicies", "horizontalpodautoscalers"]
    verbs      = ["get", "list", "watch", "update", "patch"] # Không cho quyền 'delete' để an toàn
  }
}

# 3. Gán quyền cho AI Agent (Binding)
resource "kubernetes_cluster_role_binding" "ai_agent_binding" {
  metadata {
    name = "ai-agent-binding"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.ai_agent_role.metadata[0].name 
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.ai_agent_sa.metadata[0].name
    namespace = kubernetes_service_account.ai_agent_sa.metadata[0].namespace
  }
}