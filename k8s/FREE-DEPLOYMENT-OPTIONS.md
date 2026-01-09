# Free Deployment Options for NeuroClima (No Domain Required)

This guide covers **100% FREE** ways to deploy your Kubernetes application without a domain name or paid services.

---

## 🎯 Recommended Options (Ranked)

| Option | Ease | Security | Production Ready | Notes |
|--------|------|----------|------------------|-------|
| **Cloudflare Tunnel** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Best free option |
| **NodePort** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Simplest setup |
| **ngrok** (current) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Good for dev/testing |
| **Tailscale** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Best for private access |

---

## Option 1: NodePort (Simplest - Recommended)

### What is it?
Exposes your service on a **static port** (30000-32767) on each cluster node's IP address.

### Pros:
✅ **100% Free** - Built into Kubernetes
✅ **Static Port** - Unlike ngrok, port never changes
✅ **No External Dependencies** - No third-party services
✅ **Simple Setup** - Just change service type

### Cons:
❌ **Must use HTTP** (not HTTPS) unless you add SSL yourself
❌ **High port numbers** (30000+) - may be blocked by some firewalls
❌ **No custom domain** - Must use IP address

### Setup Instructions:

#### Step 1: Apply NodePort Services

```powershell
cd D:\Projects\docker\bot\k8s
$env:KUBECONFIG = ".\kubeconfig.yaml"

# Apply NodePort services
kubectl apply -f client\service-nodeport.yaml
kubectl apply -f server\service-nodeport.yaml
```

#### Step 2: Get Your Node IP

```powershell
# Get node external IP
kubectl get nodes -o wide

# Example output:
# NAME              STATUS   ROLES    EXTERNAL-IP      INTERNAL-IP
# pool-abc-xyz      Ready    <none>   164.92.123.45    10.114.0.2
```

#### Step 3: Access Your Application

```
Frontend: http://164.92.123.45:30080
Backend API: http://164.92.123.45:30800
```

#### Step 4: Update Client Environment Variables

Your client needs to know the backend URL. Update your client deployment:

```yaml
env:
- name: REACT_APP_API_URL
  value: "http://164.92.123.45:30800/api"  # Your node IP
```

### Security Considerations:

```powershell
# Allow ports in DigitalOcean firewall
# Go to: DigitalOcean Dashboard → Networking → Firewalls
# Add Inbound Rules:
# - Port 30080 (HTTP - Client)
# - Port 30800 (HTTP - API)
# - Source: All IPv4, All IPv6
```

---

## Option 2: Cloudflare Tunnel (Best Free Alternative)

### What is it?
Free alternative to ngrok with better features and reliability. Creates a secure tunnel from Cloudflare to your cluster.

### Pros:
✅ **100% Free** - No cost, no credit card
✅ **HTTPS Included** - Free SSL certificates
✅ **Reliable** - Better uptime than ngrok free tier
✅ **Custom Subdomain** - Get yourapp.trycloudflare.com for free
✅ **No Port Forwarding** - Works through NAT/firewalls
✅ **DDoS Protection** - Cloudflare's global network

### Cons:
❌ **Still a tunnel** - Extra hop (like ngrok)
❌ **Random subdomain** - Changes on restart (unless you use Cloudflare account)

### Setup Instructions:

#### Step 1: Install Cloudflare Tunnel in Kubernetes

```powershell
# Download cloudflared
kubectl run cloudflared --image=cloudflare/cloudflared:latest \
  --namespace=uoulu \
  --command -- cloudflared tunnel --url http://neuroclima-client:80
```

Or use this deployment file:

```yaml
# cloudflare-tunnel.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflare-tunnel
  namespace: uoulu
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudflare-tunnel
  template:
    metadata:
      labels:
        app: cloudflare-tunnel
    spec:
      containers:
      - name: cloudflared
        image: cloudflare/cloudflared:latest
        args:
        - tunnel
        - --url
        - http://neuroclima-client:80
        - --no-autoupdate
```

Apply it:
```powershell
kubectl apply -f cloudflare-tunnel.yaml
```

#### Step 2: Get Your Tunnel URL

```powershell
kubectl logs deployment/cloudflare-tunnel -n uoulu

# Look for output like:
# Your quick tunnel has been created! Visit it at:
# https://random-name.trycloudflare.com
```

#### Step 3: Use the URL

Access your app at: `https://random-name.trycloudflare.com`

### Upgrade to Permanent Cloudflare Tunnel (Still Free!)

With a free Cloudflare account, you get:
- ✅ Persistent subdomain (doesn't change)
- ✅ Custom subdomain: `myapp.yourusername.workers.dev`
- ✅ More control over routing

Setup:
1. Create free Cloudflare account at https://dash.cloudflare.com
2. Follow: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/

---

## Option 3: Continue with ngrok (Current Setup)

Since you're already using ngrok, you can keep it with some improvements:

### Pros:
✅ **Already Working** - No changes needed
✅ **Easy to Use** - Simple setup
✅ **HTTPS Included** - Free SSL

### Cons:
❌ **Random URL** - Changes on restart
❌ **Rate Limits** - Free tier restrictions
❌ **Connection Limits** - Limited concurrent connections

### How to Get Static ngrok URL (Free):

1. Create free ngrok account: https://dashboard.ngrok.com/signup
2. Get your authtoken
3. Create a Kubernetes secret:

```powershell
kubectl create secret generic ngrok-auth \
  --from-literal=authtoken=YOUR_AUTHTOKEN_HERE \
  -n uoulu
```

4. Update ngrok deployment to use reserved domain (if you have ngrok free static domain)

---

## Option 4: Tailscale (Best for Private Access)

### What is it?
Creates a private VPN network between your devices and your cluster. Your app is only accessible to you.

### Pros:
✅ **100% Free** - Up to 20 devices
✅ **Ultra Secure** - Private network, not public internet
✅ **HTTPS Support** - MagicDNS with automatic HTTPS
✅ **Fast** - Direct peer-to-peer connections

### Cons:
❌ **Private Only** - Can't share with general public
❌ **Requires Installation** - Must install Tailscale on client devices
❌ **More Complex** - Steeper learning curve

### When to Use:
- Internal company tools
- Admin dashboards
- Private APIs
- Development/staging environments

### Setup:
Follow: https://tailscale.com/kb/1185/kubernetes/

---

## Comparison: Which Should You Choose?

### For Public Access (Anyone can use your app):

**Development/Testing:**
```
ngrok or Cloudflare Tunnel
→ Easy setup, HTTPS included, good enough for testing
```

**Production (Free):**
```
NodePort + No-IP/DuckDNS
→ NodePort for access + Free dynamic DNS for friendly URL
```

### For Private Access (Only you and team):

```
Tailscale
→ Most secure, best performance, private network
```

### For Semi-Production (Limited users, free):

```
Cloudflare Tunnel (with account)
→ Persistent URL, HTTPS, DDoS protection, unlimited bandwidth
```

---

## Recommended Setup for You

Based on your situation, I recommend:

### Phase 1: Immediate (Use NodePort)

**Why:** Simplest, most reliable, completely free, no external dependencies

```powershell
# Apply the NodePort services I created
kubectl apply -f client\service-nodeport.yaml
kubectl apply -f server\service-nodeport.yaml

# Get your node IP
kubectl get nodes -o wide

# Access at: http://<node-ip>:30080
```

### Phase 2: Add Free Dynamic DNS (Optional)

Instead of `http://164.92.123.45:30080`, get a free domain:

**Free Dynamic DNS Providers:**
- **Duck DNS** - https://www.duckdns.org (Recommended)
- **No-IP** - https://www.noip.com/free
- **FreeDNS** - https://freedns.afraid.org

Setup:
1. Sign up for Duck DNS
2. Create subdomain: `neuroclimabot.duckdns.org`
3. Point it to your node IP: `164.92.123.45`
4. Access at: `http://neuroclimabot.duckdns.org:30080`

### Phase 3: Future (When Ready for Production)

When you're ready to invest in proper production setup:
1. Buy domain ($10/year)
2. Use DigitalOcean LoadBalancer ($12/month)
3. Set up NGINX Ingress + Let's Encrypt SSL
4. Result: `https://neuroclimabot.com`

---

## Quick Start Commands

### Deploy with NodePort (Recommended):

```powershell
cd D:\Projects\docker\bot\k8s
$env:KUBECONFIG = ".\kubeconfig.yaml"

# Apply NodePort services
kubectl apply -f client\service-nodeport.yaml
kubectl apply -f server\service-nodeport.yaml

# Get node IP
kubectl get nodes -o wide

# Check services
kubectl get svc -n uoulu

# Access your app at:
# http://<NODE-IP>:30080
```

### Deploy with Cloudflare Tunnel:

```powershell
# Quick tunnel (random URL)
kubectl run cloudflared --image=cloudflare/cloudflared:latest `
  --namespace=uoulu `
  -- cloudflared tunnel --url http://neuroclima-client:80

# Get the URL from logs
kubectl logs cloudflared -n uoulu -f
```

---

## Summary

| Your Needs | Best Option | Command |
|------------|-------------|---------|
| **Quick testing** | ngrok (current) | Already set up |
| **Reliable free access** | NodePort | `kubectl apply -f client/service-nodeport.yaml` |
| **Public HTTPS free** | Cloudflare Tunnel | `kubectl run cloudflared...` |
| **Private secure access** | Tailscale | See Tailscale docs |
| **Friendly URL (free)** | NodePort + DuckDNS | NodePort + sign up at duckdns.org |

**My recommendation: Start with NodePort**, it's the most straightforward free option that doesn't depend on external services.
