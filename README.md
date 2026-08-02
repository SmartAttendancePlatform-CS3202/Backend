# Smart Attendance Platform — Backend

PID 12 / Group 24 — Smart Attendance and Classroom Access Platform with
Face Verification and Geofenced Check-In.

Three FastAPI microservices sharing one Python package (`libs/shared-core`)
for auth/RBAC/config/schemas, deployed on a multi-node **K3s Kubernetes Cluster** with **NGINX Ingress** and automated **GitHub Actions CI/CD**.

```
backend/
├── .github/workflows/       # CI workflows (test + Docker push) & K3s CD deployment workflow
├── k8s/                     # Kubernetes Manifests (Namespace, ConfigMap, Deployments, Services, Ingress)
├── libs/shared-core/        # Shared auth (JWT + RBAC), config, DB client, Pydantic schemas
└── services/
    ├── scheduling-service/  # Courses, offerings, timetables
    ├── attendance-service/  # Sessions, check-ins, geofence orchestration, reports
    └── ai-vision-service/   # Face embedding + matching (internal-only)
```

---

## 🏗️ Architecture & Kubernetes Deployment

The project is deployed to a 2-node **K3s Kubernetes Cluster** hosted on Azure VMs with **NGINX Ingress Controller**:

- **Namespace**: `smart-attendance`
- **Ingress Controller**: Path-based routing via NGINX Ingress
  - `/scheduling/*` ➔ `scheduling-service:8000`
  - `/attendance/*` ➔ `attendance-service:8000`
  - `/vision/*` ➔ `ai-vision-service:8000`
- **Deployments & Scaling**: Each service runs with 2 replicas, resource CPU/Memory requests & limits, and Kubernetes readiness/liveness health probes (`/docs`).

---

## 🛠️ Local Development (Docker Compose)

Requires Docker and Docker Compose.

```bash
cp .env.example services/scheduling-service/.env
cp .env.example services/attendance-service/.env
cp .env.example services/ai-vision-service/.env

make up
```

This starts all three services with live-reload:
- `scheduling-service` ➔ http://localhost:8001
- `attendance-service` ➔ http://localhost:8002
- `ai-vision-service` ➔ http://localhost:8003

Each has interactive API docs at `/docs` once running.

Run tests: `make test`. Apply migrations: `make migrate`. Tear down: `make down`.

---

## 🚀 Continuous Deployment (GitHub Actions to K3s)

Every push to `main` triggers:
1. Automated unit & integration tests (`pytest`).
2. Docker multi-stage image build and push to **Docker Hub**.
3. Automated deployment to the **Azure K3s Kubernetes Cluster** via `.github/workflows/deploy.yml` applying the `k8s/` manifests and executing zero-downtime `rollout restart`.

---

## 🗝️ Required GitHub Repository Secrets

Configure the following secrets in GitHub Repository Settings:
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Your Docker Hub Access Token
- `KUBECONFIG`: Content of your K3s cluster kubeconfig (`/etc/rancher/k3s/k3s.yaml` with Master VM Public IP)
