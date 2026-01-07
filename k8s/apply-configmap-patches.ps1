# Apply ConfigMap patches to fix Milvus configuration
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Applying ConfigMap Patches" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Updating neuroclima-config with VM endpoints..." -ForegroundColor Yellow
kubectl patch configmap neuroclima-config -n uoulu --patch-file k8s/base/configmap-patch.yaml

Write-Host ""
Write-Host "2. Setting MINIO_SECURE=true in server-config..." -ForegroundColor Yellow
kubectl patch configmap server-config -n uoulu --patch-file k8s/base/server-config-patch.yaml

Write-Host ""
Write-Host "3. Setting SECURE=True in processor-config..." -ForegroundColor Yellow
kubectl patch configmap processor-config -n uoulu --patch-file k8s/base/processor-config-patch.yaml

Write-Host ""
Write-Host "4. Verifying the updated values..." -ForegroundColor Yellow
Write-Host ""
Write-Host "MILVUS_HOST:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MILVUS_HOST}'
Write-Host ""
Write-Host "MILVUS_PORT:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MILVUS_PORT}'
Write-Host ""
Write-Host "MINIO_ENDPOINT:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.MINIO_ENDPOINT}'
Write-Host ""
Write-Host "MINIO_SECURE:" -ForegroundColor Green
kubectl get configmap server-config -n uoulu -o jsonpath='{.data.MINIO_SECURE}'
Write-Host ""
Write-Host "OLLAMA_API_URL:" -ForegroundColor Green
kubectl get configmap neuroclima-config -n uoulu -o jsonpath='{.data.OLLAMA_API_URL}'
Write-Host ""

Write-Host ""
Write-Host "5. Restarting server deployment..." -ForegroundColor Yellow
kubectl rollout restart deployment/neuroclima-server -n uoulu

Write-Host ""
Write-Host "6. Waiting for pod to restart (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "7. Checking server logs..." -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
kubectl logs -l component=server -n uoulu --tail=50
