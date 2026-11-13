# STATE AUDIT AI — Production Deployment Guide

This document outlines the configuration, environment variables, container packaging, and exact commands required to deploy State Audit AI into production.

---

## 1. Environment Variables Reference

### Backend Environment Variables (`backend/.env`)

All variables should be populated with production values. Do not commit actual credentials or secret keys to version control.

| Variable | Required in Prod | Example / Default | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **Yes** | `production` | Environment mode (`development`, `staging`, `production`). In production, API docs (`/docs`) are disabled and strict validation is enforced. |
| `PROJECT_NAME` | No | `STATE AUDIT AI` | Title used in logging, reports, and health disclosures. |
| `API_V1_STR` | No | `/api` | Base route prefix for backend REST endpoints. |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require` | PostgreSQL database connection string. |
| `SECRET_KEY` | **Yes** | `<32+ character random hex string>` | Cryptographic secret for signing JWT tokens. Fails at startup if missing, default, or < 32 characters. Generate with: `openssl rand -hex 32` |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Expiry duration for access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Expiry duration for refresh tokens. |
| `MAX_FAILED_LOGIN_ATTEMPTS` | No | `5` | Maximum failed password attempts before account lockout. |
| `LOCKOUT_DURATION_MINUTES` | No | `15` | Duration of temporary account lockouts. |
| `STORAGE_BACKEND` | **Yes** | `supabase` or `local` | Storage service provider. Use `supabase` for cloud object storage. |
| `STORAGE_DIR` | If local | `./storage` | Filesystem path used when `STORAGE_BACKEND=local`. |
| `MAX_UPLOAD_SIZE_BYTES` | No | `26214400` | Maximum allowed document upload payload size (25 MB). |
| `SUPABASE_URL` | If supabase | `https://your-project.supabase.co` | Project URL for Supabase Storage API. |
| `SUPABASE_SERVICE_ROLE_KEY` | If supabase | `your-service-role-key-here` | Service role key for private bucket streaming. Never share publicly. |
| `SUPABASE_STORAGE_BUCKET` | If supabase | `audit-documents` | Name of the private storage bucket. |
| `PUBLIC_BASE_URL` | **Yes** | `https://audit.karnataka.gov.in` | Canonical URL used for report verification links and QR codes. Fails at startup if missing in production. |
| `CORS_ORIGINS` | **Yes** | `["https://audit.karnataka.gov.in"]` | JSON array or comma-separated list of allowed origins. Fails at startup if missing in production. |
| `CSP_EXTRA` | No | `""` | Optional extra directives to append to the Content-Security-Policy header. |
| `DEFAULT_STATE` | No | `Karnataka` | Default governing jurisdiction. |
| `RATE_LIMIT_PER_MINUTE` | No | `600` | Global API rate limit ceiling. |
| `PORT` | No | `8000` | Port listened to by container or Uvicorn runner. |

---

### Frontend Environment Variables (`frontend/.env`)

These variables are embedded during the Vite build step (`npm run build`).

| Variable | Required in Prod | Example / Default | Description |
| :--- | :---: | :--- | :--- |
| `VITE_ENABLE_DEMO_LOGIN` | **Yes** | `false` | Must be `false` in production. Disables quick-login buttons, role switchers, and demo account listings. |
| `VITE_API_URL` | **Yes** | `/api` | Base API URL. Use `/api` if frontend is routed through a reverse proxy, or full origin (e.g. `https://api.audit.karnataka.gov.in/api`) if served cross-origin. |

---

## 2. Backend Container Packaging (Docker)

The backend includes a production-ready `Dockerfile` (Python 3.11 slim) with:
* System packages: `tesseract-ocr`, `tesseract-ocr-eng`, `libfreetype6`, `libjpeg62-turbo`, `libharfbuzz0b`, `libglib2.0-0`, `libgl1`.
* Automated startup entrypoint: runs `alembic upgrade head`, then executes `uvicorn app.main:app` on `${PORT:-8000}`.
* Non-root healthcheck verifying `/api/health`.

### Build Image
```bash
docker build -t state-audit-backend -f backend/Dockerfile ./backend
```

### Run Container
```bash
docker run -d \
  --name state_audit_backend \
  --restart always \
  -p 8000:8000 \
  --env-file backend/.env \
  -e PORT=8000 \
  state-audit-backend
```

### Health Verification
```bash
curl -f http://127.0.0.1:8000/api/health
```

---

## 3. Production User Account Provisioning

Before opening the platform to end users, deactivate all demo accounts and provision the primary production administrator:

```bash
# Deactivate all pre-seeded demo accounts (soft-deactivates, logs hash-chained audit trail)
python -m app.scripts.manage_users deactivate-demo-users

# Provision production administrator account (prompts for hidden password twice)
python -m app.scripts.manage_users create-admin admin@audit.karnataka.gov.in --full-name "Chief Auditor"

# Optional: Reset or update passwords securely without command-line exposure
python -m app.scripts.manage_users set-password user@audit.karnataka.gov.in
```

---

## 4. Frontend Production Build & Static Hosting

The frontend builds to optimized static assets in `frontend/dist/`.

### Build Frontend
```bash
cd frontend
npm ci

# Set production variables during build
export VITE_ENABLE_DEMO_LOGIN=false
export VITE_API_URL=/api
npm run build
```

### Nginx Reverse Proxy Configuration Example

```nginx
server {
    listen 443 ssl http2;
    server_name audit.karnataka.gov.in;

    ssl_certificate /etc/ssl/certs/audit.karnataka.gov.in.crt;
    ssl_certificate_key /etc/ssl/private/audit.karnataka.gov.in.key;

    # Frontend Single-Page App (SPA)
    location / {
        root /var/www/state_audit/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API & Public Verification
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /verify/ {
        proxy_pass http://127.0.0.1:8000/verify/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

