## Verified Local State
- **Branch:** `feature/ai-complaint-triage`
- **Tests:** 53/53 passing (17 new AI triage + 36 existing complaints)
- **Django feature flag:** `AI_TRIAGE_ENABLED=False` by default
- **Container config:** `compose/ai-triage/Dockerfile` (CPU-only, multi-stage, non-root)
- **Artifacts bundled:** `ai_triage/artifacts/*.joblib` inside container image

## Prepared Manifests
- `compose/ai-triage/openshift.yaml` — Deployment + ClusterIP Service
- `compose/ai-triage/openshift-build.yaml` — ImageStream + BuildConfig

## Free Image Build & Registry Approach
Red Hat Developer Sandbox provides an integrated container registry at:
```
image-registry.openshift-image-registry.svc:5000
```

Build steps (requires `oc` CLI authenticated to the sandbox):
```bash
# 1. Create build config from binary Docker build
oc new-build --name=ai-triage-service --binary --dockerfile=compose/ai-triage/Dockerfile -n sandbox-shared-models

# 2. Push source and build
oc start-build ai-triage-service --from-dir=. --follow -n sandbox-shared-models

# 3. Create service account for internal pull if needed
oc policy add-role-to-group system:image-puller system:serviceaccounts:sandbox-shared-models -n sandbox-shared-models

# 4. Deploy
oc apply -f compose/ai-triage/openshift.yaml -n sandbox-shared-models
```

Django integration (only after AI service is verified reachable):
```bash
# In SmartCampus Django pod/deployment, set:
# AI_TRIAGE_ENABLED=True
# AI_TRIAGE_API_URL=http://ai-triage-service:8000
```

## Resource Limits
- CPU request: 250m / limit: 500m
- Memory request: 256Mi / limit: 512Mi
- No persistent storage required (artifacts baked into image)
- No GPU required

## Genuine Blockers (cannot proceed without user action)
1. **`oc` CLI unavailable** — cannot verify cluster access, permissions, or execute deployment commands
2. **Builder strategy unverified** — sandbox must allow Docker build strategy in `BuildConfig`; if restricted, an alternative registry or CI path is needed
3. **Project write permissions unknown** — cannot create resources in `sandbox-shared-models` without verified access
4. **No CPU ServingRuntime confirmed** — dashboard showed only GPU ServingRuntimes; our Deployment approach avoids model-serving platforms entirely, but this should be confirmed

## What Was Prepared
- Deployment manifest with CPU-only resource limits and security context
- Service manifest (ClusterIP, internal only)
- Build config manifest using Docker strategy
- Container Dockerfile updated to package artifacts and run as non-root
- Deployment instructions documented

## What Remains Pending
- Actual `oc` login and resource creation
- Verification of service health endpoint
- Django feature flag activation after AI service is reachable
- Monitoring/logging configuration (optional)

## Recommendation
If you have `oc` access from another terminal or can install it, run the build/deploy commands above. If the sandbox restricts Docker build strategy, use the local Podman/Docker daemon to build and push to the internal registry, then create the Deployment/Service directly.

Do not proceed with paid services or external registries.
