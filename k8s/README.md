# Kubernetes 部署指南

本目录包含 CC Switch 的 Kubernetes 部署配置。

## 前置要求

- Kubernetes 集群（1.24+）
- kubectl 配置
- 持久化存储类（StorageClass）
- Ingress Controller（如 Nginx Ingress）
- cert-manager（可选，用于 TLS 证书）

## 部署步骤

### 1. 创建命名空间

```bash
kubectl apply -f namespace.yaml
```

### 2. 创建密钥

复制 `secrets.yaml.example` 为 `secrets.yaml` 并填写实际值：

```bash
cp secrets.yaml.example secrets.yaml
# 编辑 secrets.yaml，填写实际的密钥值
kubectl apply -f secrets.yaml
```

**重要**：不要将 `secrets.yaml` 提交到 Git！

### 3. 创建持久化存储

```bash
kubectl apply -f pvc.yaml
```

### 4. 部署 Redis

```bash
kubectl apply -f redis-deployment.yaml
```

### 5. 部署后端

```bash
kubectl apply -f backend-deployment.yaml
```

### 6. 部署前端

```bash
kubectl apply -f frontend-deployment.yaml
```

### 7. 配置 Ingress

编辑 `ingress.yaml`，将 `your-domain.com` 替换为实际域名：

```bash
# 编辑 ingress.yaml
kubectl apply -f ingress.yaml
```

### 8. 验证部署

```bash
# 检查所有 Pod 状态
kubectl get pods -n cc-switch

# 检查服务
kubectl get svc -n cc-switch

# 检查 HPA
kubectl get hpa -n cc-switch

# 查看后端日志
kubectl logs -f deployment/backend -n cc-switch

# 查看前端日志
kubectl logs -f deployment/frontend -n cc-switch
```

## 自动扩缩容

系统配置了 HorizontalPodAutoscaler (HPA)：

- **后端**：3-10 个副本，基于 CPU（70%）和内存（80%）
- **前端**：2-5 个副本，基于 CPU（70%）和内存（80%）

查看扩缩容状态：

```bash
kubectl describe hpa backend-hpa -n cc-switch
kubectl describe hpa frontend-hpa -n cc-switch
```

## 健康检查

所有服务都配置了健康检查：

- **Liveness Probe**：检测容器是否存活，失败时重启容器
- **Readiness Probe**：检测容器是否就绪，失败时从服务中移除

## 滚动更新

部署使用滚动更新策略：

- `maxSurge: 1`：最多允许 1 个额外 Pod
- `maxUnavailable: 0`：更新时不允许不可用

手动触发滚动更新：

```bash
kubectl rollout restart deployment/backend -n cc-switch
kubectl rollout restart deployment/frontend -n cc-switch
```

## 资源限制

### 后端
- 请求：256Mi 内存，250m CPU
- 限制：1Gi 内存，1000m CPU

### 前端
- 请求：64Mi 内存，100m CPU
- 限制：256Mi 内存，500m CPU

### Redis
- 请求：128Mi 内存，100m CPU
- 限制：512Mi 内存，500m CPU

## 监控和日志

### 查看日志

```bash
# 后端日志
kubectl logs -f deployment/backend -n cc-switch

# 前端日志
kubectl logs -f deployment/frontend -n cc-switch

# Redis 日志
kubectl logs -f deployment/redis -n cc-switch
```

### 查看指标

如果启用了 OpenTelemetry，可以通过配置的 OTLP 端点查看指标。

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n cc-switch

# 查看事件
kubectl get events -n cc-switch --sort-by='.lastTimestamp'
```

### 健康检查失败

检查健康检查端点：

```bash
# 后端健康检查
kubectl exec -it deployment/backend -n cc-switch -- curl http://localhost:8000/health

# 前端健康检查
kubectl exec -it deployment/frontend -n cc-switch -- curl http://localhost:80/
```

### 存储问题

```bash
# 检查 PVC 状态
kubectl get pvc -n cc-switch

# 查看 PVC 详情
kubectl describe pvc backend-data -n cc-switch
```

## 清理

删除所有资源：

```bash
kubectl delete namespace cc-switch
```

**注意**：这将删除所有数据，包括持久化存储！

## 自定义配置

### 修改副本数

编辑对应的 deployment 文件，修改 `spec.replicas`。

### 修改资源限制

编辑对应的 deployment 文件，修改 `resources` 部分。

### 修改 HPA 配置

编辑对应的 HPA 文件，修改 `minReplicas`、`maxReplicas` 和 `metrics`。


