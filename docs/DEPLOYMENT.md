# Deployment Guide

This guide covers deploying RejseplanAPI on a Proxmox VM running Debian 12. The same steps apply to any Debian/Ubuntu host.

---

## Proxmox VM Setup

### Recommended specifications

| Resource | Minimum | Recommended |
|---|---|---|
| vCPU | 1 | 2 |
| RAM | 512 MB | 2 GB |
| Disk | 4 GB | 10 GB |
| OS | Debian 12 (Bookworm) | Debian 12 (Bookworm) |
| Network | 1 NIC, bridged | 1 NIC, bridged |

The backend is a lightweight async Python process. The SvelteKit frontend serves a pre-built static bundle via a Node.js process. Neither is CPU-intensive in steady state. 1 vCPU + 1 GB RAM is comfortable for a personal dashboard.

### Create the VM in Proxmox

1. Download the Debian 12 netinstall ISO from [https://www.debian.org/distrib/](https://www.debian.org/distrib/) and upload to Proxmox ISO storage.
2. Create VM: **Create VM** → set RAM/CPU as above → add a VirtIO disk (10 GB) → attach the ISO.
3. Boot and run through the Debian installer. Select: standard system utilities, SSH server. No GUI needed.
4. After first boot, note the VM's IP address (`ip addr`). Set a static IP or add a DHCP reservation in your router.

### Initial system setup

```bash
# Update and install prerequisites
apt-get update && apt-get upgrade -y
apt-get install -y curl git ca-certificates gnupg lsb-release

# Create a non-root user for running the application (optional but recommended)
useradd -m -s /bin/bash rejseplan
usermod -aG sudo rejseplan
su - rejseplan
```

---

## Docker and Docker Compose Installation

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (avoids sudo on every docker command)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker compose version
```

---

## First Deployment

```bash
# Clone the repository
git clone https://github.com/jonaslarsen0/dograllyblazorserver.git /opt/rejseplanapi
cd /opt/rejseplanapi

# Configure
cp .env.example .env
nano .env
```

At minimum, set these values in `.env`:

```dotenv
REJSEPLANEN_API_KEY=your_key_here
DEFAULT_STOP_IDS=8600020,8600254
TRAIN_ONLY=true
WALK_TIME_SECONDS=300
```

```bash
# Build images and start all services
docker compose up -d --build

# Verify all three containers are running and healthy
docker compose ps

# Watch the backend startup logs
docker compose logs -f backend
```

Expected output from `docker compose ps`:

```
NAME                    STATUS
rejseplanapi-backend-1  Up (healthy)
rejseplanapi-frontend-1 Up
rejseplanapi-nginx-1    Up
```

Open `http://<vm-ip>` in a browser. The dashboard should load within a few seconds.

### Persistent data

The delay log database is stored in a named Docker volume `delay_data`, mounted at `/app/data/delay_log.db` inside the backend container. This volume survives `docker compose down` and container rebuilds. Only `docker compose down -v` removes it.

```bash
# Find the volume on the host
docker volume inspect rejseplanapi_delay_data
```

---

## Updates

```bash
cd /opt/rejseplanapi
git pull
docker compose up -d --build
```

Docker Compose rebuilds only the images that have changed (layer cache). Typically this takes 30–60 seconds. The old containers are replaced with zero-downtime for static assets.

---

## SSL/HTTPS Setup

Pick one approach: **Traefik** (recommended for Proxmox homelabs with multiple services) or **nginx with Let's Encrypt** (simpler if this is your only service).

### Option A — Traefik reverse proxy (recommended)

If you already run Traefik on your Proxmox host, add labels to the `nginx` service so Traefik picks it up and issues a certificate automatically.

In `docker-compose.yml`, add a `labels` section to the `nginx` service:

```yaml
services:
  nginx:
    image: nginx:alpine
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.rejseplan.rule=Host(`rejseplan.yourdomain.com`)"
      - "traefik.http.routers.rejseplan.entrypoints=websecure"
      - "traefik.http.routers.rejseplan.tls.certresolver=letsencrypt"
      - "traefik.http.services.rejseplan.loadbalancer.server.port=80"
    networks:
      - rejseplan-net
      - traefik-net   # add Traefik's external network
```

Add the external network at the bottom of `docker-compose.yml`:

```yaml
networks:
  rejseplan-net:
    driver: bridge
  traefik-net:
    external: true
```

Remove the `ports:` mapping from the `nginx` service (Traefik handles that). Then update `.env`:

```dotenv
CORS_ORIGINS=https://rejseplan.yourdomain.com
```

Restart: `docker compose up -d`.

### Option B — nginx on the host with Certbot

Install nginx and certbot on the host VM (outside Docker), configure it as a proxy to the containerised nginx, and let Certbot manage the certificate.

```bash
# Install nginx and certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Change the Docker nginx to listen on a non-standard port (avoid conflict with host nginx)
# In docker-compose.yml, change: ports: - "8080:80"
docker compose up -d

# Create a host nginx config
sudo nano /etc/nginx/sites-available/rejseplan
```

```nginx
server {
    listen 80;
    server_name rejseplan.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rejseplan /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Obtain certificate (DNS must point to this VM's public IP)
sudo certbot --nginx -d rejseplan.yourdomain.com
```

Certbot modifies the nginx config to add HTTPS and sets up auto-renewal via a systemd timer.

Update `.env`:

```dotenv
CORS_ORIGINS=https://rejseplan.yourdomain.com
```

Restart backend: `docker compose restart backend`

---

## Systemd Service (optional)

If you want `docker compose` to start automatically on boot without Portainer or another orchestrator:

```bash
sudo nano /etc/systemd/system/rejseplanapi.service
```

```ini
[Unit]
Description=RejseplanAPI Docker Compose Stack
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/rejseplanapi
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable rejseplanapi
sudo systemctl start rejseplanapi
```

---

## Backup Strategy

### What needs backing up

| Data | Location | How |
|---|---|---|
| Delay log database | Docker volume `rejseplanapi_delay_data` | Copy from volume or container |
| Configuration | `.env` file on host | Include in host backup |
| Custom nginx config | `nginx/nginx.conf` | Covered by git |
| Application code | `/opt/rejseplanapi` | Covered by git |

The delay log is the only data generated at runtime that cannot be recreated from source code. Everything else is either in git or regenerated on `docker compose up --build`.

### Manual database backup

```bash
# Method 1: copy from the container (container can be running)
docker compose cp backend:/app/data/delay_log.db \
  /home/rejseplan/backups/delay_log_$(date +%Y%m%d).db

# Method 2: copy directly from the Docker volume
DB_PATH=$(docker volume inspect rejseplanapi_delay_data \
  --format '{{.Mountpoint}}')/delay_log.db
cp "$DB_PATH" /home/rejseplan/backups/delay_log_$(date +%Y%m%d).db
```

### Automated nightly backup with cron

```bash
# Create backup directory
mkdir -p /home/rejseplan/backups

# Add cron job
crontab -e
```

Add this line:

```cron
0 3 * * * docker compose -f /opt/rejseplanapi/docker-compose.yml cp backend:/app/data/delay_log.db /home/rejseplan/backups/delay_log_$(date +\%Y\%m\%d).db 2>&1 | logger -t rejseplan-backup
```

This runs at 03:00 every night. Backups accumulate; add a cleanup line to keep only the last 30 days:

```cron
5 3 * * * find /home/rejseplan/backups -name "delay_log_*.db" -mtime +30 -delete
```

### Restore from backup

```bash
# Stop backend (prevents writes during restore)
docker compose stop backend

# Copy backup into the volume via a temporary container
docker run --rm \
  -v rejseplanapi_delay_data:/data \
  -v /home/rejseplan/backups:/backup \
  alpine \
  cp /backup/delay_log_20260608.db /data/delay_log.db

# Restart backend
docker compose start backend
```

---

## Monitoring

### View live logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# With timestamps
docker compose logs -f --timestamps backend
```

### Check health

```bash
curl http://localhost/health
# {"status": "ok"}

# Or via Docker
docker compose ps
```

### Resource usage

```bash
docker stats
```

In steady state expect roughly: backend ~50–100 MB RAM, frontend ~30 MB RAM, nginx ~5 MB RAM.
