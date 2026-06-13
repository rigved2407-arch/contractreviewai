# Production Deployment Guide — Contract Review AI

This guide covers **secrets management, PostgreSQL setup, and production hardening** for law firm deployments.

---

## 1. Secrets Management (Critical)

### The Problem

API keys (OpenAI, encryption, JWT) currently live in a plain `.env` file. For law firm deployments this is unacceptable — any compromise of the host or container leaks every key.

### Solution: Three options (choose one)

#### Option A: Docker Secrets (Recommended — simplest)

1. Create a `secrets.env` file with your secrets (keep this file out of git):
```bash
# secrets.env — KEEP OUT OF VERSION CONTROL
OPENAI_API_KEY=sk-...
ENCRYPTION_KEY=<from 'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'>
API_KEY=<from 'python -c "import secrets; print(secrets.token_urlsafe(48))"'>
JWT_SECRET=<from 'python -c "import secrets; print(secrets.token_urlsafe(32))"'>
SMTP_PASSWORD=...
```

2. Deploy with Docker secrets:
```bash
# Convert secrets.env to individual Docker secret files
mkdir -p .secrets
while IFS='=' read -r key value; do
  echo "$value" > ".secrets/$key"
done < secrets.env

# Deploy with compose override
docker-compose -f docker-compose.yml -f deploy/docker-compose.secrets.yml up -d

# Clean up
rm -rf .secrets
```

The app reads secrets from `/run/secrets/<NAME>` automatically — no code changes needed.

#### Option B: AWS Secrets Manager

Use the included script to sync secrets from AWS to Docker:

```bash
# IAM role must have secretsmanager:GetSecretValue
aws secretsmanager create-secret \
  --name contract-review-ai/production \
  --secret-string file://secrets.env

# On each deploy, sync secrets
python deploy/scripts/aws-secrets.py \
  --secret-id contract-review-ai/production \
  --region ap-south-1
```

This writes secrets to `.secrets/` which map to Docker secrets.

#### Option C: Azure Key Vault

```bash
az keyvault secret set \
  --vault-name contract-review-ai-kv \
  --name production-secrets \
  --file secrets.env

python deploy/scripts/azure-secrets.py \
  --vault-url https://contract-review-ai-kv.vault.azure.net \
  --secret-name production-secrets
```

---

## 2. Production Docker Deployment

### Prerequisites
- Docker Engine 24+ with Compose plugin
- PostgreSQL 16 (included in docker-compose)
- HTTPS reverse proxy (nginx/Caddy recommended)
- Domain name pointed to your server

### Step-by-step

```bash
# 1. Clone on your server
git clone <repo> /opt/contract-review-ai
cd /opt/contract-review-ai

# 2. Set up secrets (Option A from above)
mkdir -p .secrets
# ... populate .secrets/ with your values ...

# 3. Deploy with secrets
docker-compose \
  -f docker-compose.yml \
  -f deploy/docker-compose.secrets.yml \
  up -d

# 4. Verify
curl http://localhost:8000/api/health
# {"status":"ok","version":"1.0.0","environment":"production"}

# 5. Set up reverse proxy (nginx example below)
```

### Nginx Reverse Proxy (TLS termination)

```nginx
server {
    listen 443 ssl;
    server_name contracts.yourfirm.com;

    ssl_certificate /etc/letsencrypt/live/contracts.yourfirm.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/contracts.yourfirm.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 3. Security Checklist

- [ ] **Secrets**: No `.env` file on production servers. Use Docker secrets or cloud vault.
- [ ] **Database**: PostgreSQL (not SQLite). Enabled in `docker-compose.yml` by default.
- [ ] **TLS**: HTTPS with Let's Encrypt or firm certificate. TLS 1.3 only.
- [ ] **Encryption at rest**: Set `ENCRYPT_DOCUMENTS=true` with strong key in Docker secret.
- [ ] **API auth**: Set `AUTH_ENABLED=true` with `API_KEY` in Docker secret.
- [ ] **CORS**: Restrict `CORS_ORIGINS` to your firm's domain only.
- [ ] **Audit**: Keep `AUDIT_ENABLED=true` (default).
- [ ] **Data retention**: Set `DATA_RETENTION_DAYS=365` or as per firm policy.
- [ ] **Container security**: Containers run as non-root, all capabilities dropped (done in Dockerfile).
- [ ] **Rate limiting**: Add `nginx rate limiting` or `cloudflare WAF` in front.

---

## 4. Backup & Recovery

```bash
# Backup PostgreSQL
docker exec contract-review-ai_db_1 pg_dump -U cra contract_review > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker exec -i contract-review-ai_db_1 psql -U cra contract_review

# Backup uploaded documents
docker run --rm -v app_data:/data -v $(pwd):/backup alpine tar czf /backup/documents_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 5. Monitoring & Alerts

The app exposes:
- `GET /api/health` — health check (use with Docker HEALTHCHECK or load balancer)
- Structured JSON logging to stdout (collect with your log shipper)
- Optional Sentry integration — set `SENTRY_DSN` in secrets

---

## 6. On-Premise Deployment

For firms that require air-gapped deployment:

1. Use a self-hosted LLM (Llama 3.1 70B, Mistral Large) via Ollama or vLLM
2. Set `OPENAI_BASE_URL=http://ollama:11434/v1` and `OPENAI_MODEL=llama3.1:70b`
3. No external API calls = fully air-gapped
4. All data stays within firm's network

See `SECURITY.md` for on-premise LLM configuration.
