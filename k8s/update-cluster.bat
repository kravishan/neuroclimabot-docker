@echo off
REM Quick Update Script for Kubernetes Cluster (Windows)
REM Run this after pulling latest changes from git

echo ========================================
echo Kubernetes Cluster Update Script
echo Phase 1: Security ^& Nginx Gateway
echo ========================================
echo.

REM Check if KUBECONFIG is set
if "%KUBECONFIG%"=="" (
    echo Warning: KUBECONFIG not set. Using default.
    echo Set it with: set KUBECONFIG=C:\path\to\kubeconfig.yaml
    echo.
)

set NAMESPACE=uoulu

echo Step 1: Updating ConfigMaps...
kubectl apply -f k8s/gateway/nginx-gateway.yaml --kubeconfig %KUBECONFIG%
kubectl apply -f k8s/client/nginx-config.yaml --kubeconfig %KUBECONFIG%
echo ConfigMaps updated
echo.

echo Step 2: Updating Deployments...
echo.

echo Updating Server deployment (Redis + Server)...
kubectl apply -f k8s/server/deployment.yaml --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-redis -n %NAMESPACE% --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-server -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo Updating Processor deployment (Unstructured + Processor)...
kubectl apply -f k8s/processor/deployment.yaml --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-unstructured -n %NAMESPACE% --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-processor -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo Updating Client deployment...
kubectl apply -f k8s/client/deployment.yaml --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-client -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo Updating Nginx Gateway...
kubectl apply -f k8s/gateway/nginx-gateway.yaml --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/nginx-gateway -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo Updating Monitoring (Grafana + Prometheus)...
kubectl apply -f k8s/monitoring/grafana-deployment.yaml --kubeconfig %KUBECONFIG%
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-grafana -n %NAMESPACE% --kubeconfig %KUBECONFIG%
kubectl rollout status deployment/neuroclima-prometheus -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo Step 3: Updating Ingress...
kubectl apply -f k8s/base/ingress-production.yaml --kubeconfig %KUBECONFIG%
echo Ingress updated
echo.

echo ========================================
echo Update Complete!
echo ========================================
echo.

echo Checking pod status...
kubectl get pods -n %NAMESPACE% --kubeconfig %KUBECONFIG%
echo.

echo All updates applied successfully!
echo.
echo Next steps:
echo 1. Test your application via ngrok URL
echo 2. Verify all routes work: /, /server/*, /processor/*
echo 3. Check logs if anything is not working:
echo    kubectl logs deployment/^<name^> -n %NAMESPACE% --kubeconfig %KUBECONFIG%

pause
