# OpenShift Deployment Preparation — AI Complaint Triage

## 1. Local Verification Results

### FastAPI Service
- Service starts successfully with `uvicorn ai_triage.serve:app --host 0.0.0.0 --port 8000`
- Health endpoint returns `{"status": "ok"}`
- Predictions work end-to-end

### Model Artifacts
- `ai_triage/artifacts/category_model.joblib` (66,268 bytes)
- `ai_triage/artifacts/priority_model.joblib` (44,628 bytes)
- `ai_triage/artifacts/training_report.json` (2,153 bytes)
- All artifacts load without errors

### Prediction Tests (Live API)
```json
{"category":"Electrical","priority":"High","category_confidence":0.435,"priority_confidence":0.414,"abstain":true}
{"category":"Plumbing","priority":"Medium","category_confidence":0.777,"priority_confidence":0.507,"abstain":false}
```

---

## 2. Synthetic Dataset Analysis — Priority Classifier Weakness

### Issue
The priority classifier shows ~39% accuracy because the synthetic data generator injects priority signal as **generic appended phrases** that are identical across all categories. The model learns to detect these phrases rather than understanding the actual urgency of the complaint.

### Root Cause
In `ai_triage/dataset.py`, `_inject_priority_hint()` appends the same priority-specific phrases to every category:

- High: "This is an urgent safety issue.", "Emergency maintenance needed.", etc.
- Medium: "Prompt attention requested.", "Needs maintenance soon.", etc.
- Low: "Can be scheduled later.", "Minor inconvenience.", etc.

Because "Emergency maintenance needed" appears for Electrical, Plumbing, Furniture, and all other categories, the model cannot distinguish priority from category context. The signal is diluted across all classes.

### Evidence
Feature importance analysis shows the top priority features are:
- **High:** "maintenance needed", "emergency", "fix urgently"
- **Medium:** "soon", "prompt attention", "requested"
- **Low:** "inconvenience", "minor", "scheduled later"

These are all from the appended phrases, not from the actual complaint content.

### Impact
- Category classifier: 100% accuracy (strong signal from category-specific templates)
- Priority classifier: ~39% accuracy (weak, generic signal)
- Model returns `abstain=true` for clear cases due to low confidence

### Recommendation
Do not fabricate improved accuracy. For production use:
1. Replace synthetic priority data with **real labelled complaints** (even 200–300 real samples would dramatically improve priority accuracy)
2. OR make priority hints **category-aware** (e.g., "sparking" → High for Electrical, "leaking" → High for Plumbing, "cosmetic" → Low for Furniture)
3. OR use a **rule-based fallback** for priority (keyword matching) combined with ML for category

---

## 3. Existing Docker/Compose Configuration

### Current Stack
- **Local:** Django + PostgreSQL (docker-compose.local.yml)
- **Production:** Django + PostgreSQL + Redis + Traefik + Nginx (docker-compose.production.yml)
- **No existing AI/ML services** in Docker configuration
- **No existing OpenShift manifests** in the repository

### Production Django Container
- Base: `python:3.14-slim-bookworm`
- Multi-stage build with `uv` sync
- Runs gunicorn on port 5000
- Non-root user `django`
- No GPU dependencies

---

## 4. AI Inference Container Configuration

### New File: `compose/ai-triage/Dockerfile`
- Multi-stage build (builder + runtime)
- Base: `python:3.13-slim-bookworm`
- Installs: fastapi, uvicorn, scikit-learn, joblib
- Non-root user `ai`
- Health check on `/health`
- Exposes port 8000
- No GPU, no CUDA, no paid dependencies

### New File: `compose/ai-triage/requirements.txt`
```
fastapi==0.162.0
uvicorn[standard]==0.54.0
scikit-learn==1.9.1
joblib==1.6.0
```

### Container Resource Estimates
| Resource | Estimate | Rationale |
|----------|----------|-----------|
| CPU | 0.5–1 core | scikit-learn inference is lightweight; TF-IDF + Logistic Regression is fast on CPU |
| Memory | 256–512 MB | Models are ~66 KB + ~44 KB; FastAPI + scikit-learn overhead |
| Disk | 50 MB | Image layers + model artifacts |
| Port | 8000/TCP | Internal service only; not exposed externally |

---

## 5. OpenShift Project Review

### Existing Project: `sandbox-shared-models`
From earlier inspection:
- **3 models deployed:** Granite 3.1 8B FP8, NVIDIA Nemotron Nano 9B v2 FP8, Qwen3 8B FP8
- **Serving runtime:** RHAIIS NVIDIA GPU ServingRuntime for KServe v3.2.3
- **No CPU serving runtime** visible in the project
- **Status:** All models Started

### Implications for AI Triage Service
1. **No KServe CPU runtime configured** in `sandbox-shared-models`
2. **GPU ServingRuntime only** — cannot use for CPU-only inference
3. **Alternative:** Deploy as a **standard OpenShift Deployment** (not KServe/ModelMesh)
   - Plain container pod running uvicorn
   - Service type ClusterIP for internal access
   - No GPU resources requested

---

## 6. CPU-Only Deployment Feasibility

### Option A: Plain OpenShift Deployment (Recommended)
- Deploy `ai-triage` as a standard `Deployment` + `Service` (ClusterIP)
- CPU-only, no GPU required
- No KServe/ModelMesh dependency
- Django calls via internal service DNS: `http://ai-triage-service:8000/predict`

**Pros:**
- Works with current `sandbox-shared-models` configuration
- No GPU resources needed
- Lightweight (~50 MB image, 256 MB RAM)

**Cons:**
- No built-in model serving features (autoscaling, canary, etc.)
- Manual rollout strategy

### Option B: Add CPU ServingRuntime to `sandbox-shared-models`
- Requires cluster admin permissions to install CPU runtime
- Uncertain if available in free Developer Sandbox
- **Not recommended** without verifying CPU runtime availability

---

## 7. Required Resources and Permissions

### Compute
| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| AI Triage Service | 0.5–1 core | 256–512 MB | 50 MB |
| Django (existing) | unchanged | unchanged | unchanged |
| PostgreSQL (existing) | unchanged | unchanged | unchanged |

### Network
- **Internal only:** `ai-triage` service accessible via ClusterIP
- **Django → AI Triage:** Pod-to-pod via service DNS
- **No external exposure** required

### Permissions Needed
| Permission | Required For | Current Status |
|------------|--------------|----------------|
| Create Deployment | Deploy AI triage pod | Unknown — need to verify |
| Create Service (ClusterIP) | Internal DNS | Unknown — need to verify |
| Create ConfigMap | Feature flag settings | Unknown — need to verify |
| Create Secret | `AI_TRIAGE_API_URL` (optional) | Not needed if env vars used |
| View models in `sandbox-shared-models` | Inspection only | Already confirmed accessible |

### Storage
- **No persistent storage required** for AI inference (models baked into container)
- If PVC needed for model updates: ~100 MB

---

## 8. Deployment Plan

### Phase 1: Prepare Container Image
1. Ensure `ai_triage/artifacts/` is in the repository (already done)
2. Add `compose/ai-triage/Dockerfile` and `requirements.txt` (already done)
3. Build and test locally:
   ```bash
   docker build -t ai-triage:latest -f compose/ai-triage/Dockerfile .
   docker run --rm -p 8000:8000 ai-triage:latest
   ```
4. Push to container registry (if available in sandbox)

### Phase 2: Deploy to OpenShift (Pending Approval)
1. Create new project or use existing `sandbox-shared-models`
2. Apply resources:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ai-triage
     labels:
       app: ai-triage
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: ai-triage
     template:
       metadata:
         labels:
           app: ai-triage
       spec:
         containers:
         - name: ai-triage
           image: ai-triage:latest
           ports:
           - containerPort: 8000
           resources:
             requests:
               cpu: "0.5"
               memory: "256Mi"
             limits:
               cpu: "1"
               memory: "512Mi"
           env:
           - name: AI_TRIAGE_ENABLED
             value: "true"
           livenessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 10
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: ai-triage-service
     labels:
       app: ai-triage
   spec:
     type: ClusterIP
     ports:
     - port: 8000
       targetPort: 8000
       protocol: TCP
     selector:
       app: ai-triage
   ```

3. Update Django settings:
   - `AI_TRIAGE_ENABLED=True`
   - `AI_TRIAGE_API_URL=http://ai-triage-service:8000`

### Phase 3: Verify
1. Test `/health` endpoint from Django pod
2. Test `/predict` with sample complaints
3. Verify existing complaint workflows unchanged
4. Monitor resource usage

---

## 9. Remaining Blockers

### Critical
1. **Priority classifier accuracy (~39%)** — weak due to synthetic data design
   - **Fix:** Use category-aware priority hints or real labelled data
   - **Do not deploy priority predictions** until accuracy is acceptable
   - **Fallback:** Deploy category-only predictions first; add priority later

2. **No `oc` CLI available** — cannot verify OpenShift permissions or resource quotas
   - **Fix:** Use web UI or install `oc` in the environment

3. **Unknown sandbox CPU quota** — earlier docs cited ~3 cores/14 GB RAM (unverified)
   - **Fix:** Check Developer Sandbox console for current quota

### Non-Critical
4. **No container registry** — need to push image somewhere OpenShift can pull it
   - Options: Docker Hub (public), Quay.io, or OpenShift internal registry

5. **No persistent model update strategy** — currently models are baked into image
   - Acceptable for initial deployment; add ConfigMap/PVC later if needed

---

## 10. Recommended Next Steps

1. **Immediate:** Address priority classifier weakness before deployment
   - Option A: Category-aware priority hints (quick fix)
   - Option B: Rule-based priority fallback (fastest to implement)
   - Option C: Collect 200+ real labelled complaints (best long-term)

2. **Pending approval:** Deploy container to OpenShift as plain Deployment

3. **Post-deployment:** Add monitoring, logging, and fallback behavior

---

## Files Created/Modified in This Phase

### Created
- `compose/ai-triage/Dockerfile`
- `compose/ai-triage/requirements.txt`

### Verified (No Changes)
- `ai_triage/serve.py` — FastAPI service verified working
- `ai_triage/artifacts/` — Model artifacts verified loading
- Existing Docker/Compose configs — reviewed, not modified
