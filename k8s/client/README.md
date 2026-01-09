# Client Deployment - Runtime Environment Variable Injection

## Problem

Vite (the frontend build tool) bundles `VITE_*` environment variables **at build time**, not runtime. This means:

- ❌ Changing `env:` in `deployment.yaml` doesn't affect the running app
- ❌ The Docker image has hardcoded URLs in the JavaScript bundle
- ❌ URLs like `http://localhost:8000/api` are baked into the code

## Solutions

### Solution 1: Runtime URL Replacement (No Rebuild Required) ✅

Use `runtime-env.yaml` which:
1. Uses an **initContainer** to copy static files to a shared volume
2. Runs `sed` to replace hardcoded URLs with relative paths (`/api`, `/processor`)
3. Serves the modified files with nginx

**Pros:**
- ✅ No Docker image rebuild needed
- ✅ Works with existing images
- ✅ Fast deployment

**Cons:**
- ⚠️ Slightly slower startup (init container runs first)
- ⚠️ Modifies JavaScript files at runtime

**Deploy:**
```powershell
kubectl --kubeconfig ../kubeconfig.yaml apply -f nginx-config.yaml
kubectl --kubeconfig ../kubeconfig.yaml apply -f runtime-env.yaml
```

### Solution 2: Rebuild Client Image (Proper Fix)

Rebuild the Docker image with correct environment variables.

1. Update client source `.env` or build args:
   ```env
   VITE_API_BASE_URL=/api
   VITE_API_DOCUMENT_URL=/processor
   VITE_TRANSLATE_API_URL=/processor
   VITE_STP_SERVICE_URL=/processor
   ```

2. Rebuild and push:
   ```bash
   cd client/
   docker build -t docker.io/raviyah/neuroclima-client:latest .
   docker push docker.io/raviyah/neuroclima-client:latest
   ```

3. Deploy:
   ```powershell
   kubectl --kubeconfig ../kubeconfig.yaml apply -f deployment.yaml
   kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment neuroclima-client -n uoulu
   ```

**Pros:**
- ✅ Clean solution
- ✅ Faster startup
- ✅ No runtime modifications

**Cons:**
- ❌ Requires rebuilding Docker image
- ❌ Requires access to source code

## Current Configuration

The `deployment.yaml` sets environment variables:
```yaml
env:
- name: VITE_API_BASE_URL
  value: "/api"
- name: VITE_API_DOCUMENT_URL
  value: "/processor"
```

**Note:** These only work if the client code is built to read them at runtime OR if you rebuild the image with these values.

## Recommended Approach

1. **Short-term:** Use `runtime-env.yaml` (Solution 1)
2. **Long-term:** Rebuild the client image (Solution 2)

## Testing

After deployment, check:

1. **Port-forward to test:**
   ```powershell
   kubectl --kubeconfig ../kubeconfig.yaml port-forward svc/neuroclima-client 8080:80 -n uoulu
   ```

2. **Open browser devtools (F12)** → Network tab
3. **Load http://localhost:8080**
4. **Check API calls** - should go to `/api`, not `http://localhost:8000/api`

## Troubleshooting

### Check if URLs were replaced:

```powershell
# Exec into the pod
kubectl --kubeconfig ../kubeconfig.yaml exec -it -n uoulu deployment/neuroclima-client -- sh

# Check if JavaScript files have relative URLs
grep -r "localhost:8000" /usr/share/nginx/html/assets/ || echo "No localhost URLs found (good!)"
grep -r '"/api"' /usr/share/nginx/html/assets/ && echo "Relative URLs found (good!)"
```

### Check init container logs:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml logs -n uoulu -l component=client -c inject-runtime-env
```

### Restart client:

```powershell
kubectl --kubeconfig ../kubeconfig.yaml rollout restart deployment neuroclima-client -n uoulu
```
