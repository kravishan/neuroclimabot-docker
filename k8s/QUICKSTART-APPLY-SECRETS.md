# Quick Start: Apply Secrets to Fix Milvus Error

If you're seeing this Pydantic ValidationError:
```
ValidationError: 4 validation errors for MilvusConfig
HOST / PORT / USER / PASSWORD - Field required
```

Follow these steps to fix it immediately:

## Windows (PowerShell)

```powershell
# Navigate to your project directory
cd D:\Projects\docker\bot

# Apply the secrets file
kubectl apply -f k8s/base/secrets-ready.yaml

# Verify the secret was created
kubectl get secret neuroclima-secrets -n uoulu

# You should see output like:
# NAME                   TYPE     DATA   AGE
# neuroclima-secrets    Opaque   14     5s

# Restart the server to pick up the secrets
kubectl rollout restart deployment/neuroclima-server -n uoulu

# Wait a few seconds, then check the logs
kubectl logs -f -l component=server -n uoulu
```

## Linux/Mac (Bash)

```bash
# Navigate to your project directory
cd /path/to/neuroclimabot-docker

# Apply the secrets file
kubectl apply -f k8s/base/secrets-ready.yaml

# Verify the secret was created
kubectl get secret neuroclima-secrets -n uoulu

# Restart the server to pick up the secrets
kubectl rollout restart deployment/neuroclima-server -n uoulu

# Wait a few seconds, then check the logs
kubectl logs -f -l component=server -n uoulu
```

## What This Does

The `secrets-ready.yaml` file contains all required credentials with default values:
- **MILVUS_USER**: `root` (default Milvus username)
- **MILVUS_PASSWORD**: `Milvus` (default Milvus password)
- **REDIS_PASSWORD**: `redis-password-change-me` (update if needed)
- **MINIO_ACCESS_KEY**: `minioadmin` (default MinIO key)
- **MINIO_SECRET_KEY**: `minioadmin` (default MinIO secret)
- **SECRET_KEY**: A generated random key
- **ADMIN_USERNAME**: `admin` (update if needed)
- **ADMIN_PASSWORD**: `admin123` (update if needed)

## Verify It's Working

After applying secrets and restarting, you should see the server start successfully:

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Troubleshooting

### Secret already exists
If you get "AlreadyExists" error:
```bash
# Delete the old secret first
kubectl delete secret neuroclima-secrets -n uoulu

# Then apply the new one
kubectl apply -f k8s/base/secrets-ready.yaml
```

### Wrong credentials
If Milvus or other services use different credentials:
1. Edit `k8s/base/secrets-ready.yaml`
2. Update the values under `stringData:`
3. Apply again: `kubectl apply -f k8s/base/secrets-ready.yaml`
4. Restart: `kubectl rollout restart deployment/neuroclima-server -n uoulu`

## For Production

The `secrets-ready.yaml` file uses example/default credentials. For production:

1. Copy the template:
   ```bash
   cp k8s/base/secrets.yaml.template k8s/base/secrets.yaml
   ```

2. Edit with your actual credentials:
   ```bash
   nano k8s/base/secrets.yaml
   ```

3. Apply your custom secrets:
   ```bash
   kubectl apply -f k8s/base/secrets.yaml
   ```

4. **Important**: Never commit secrets files to git! They're already in `.gitignore`.
