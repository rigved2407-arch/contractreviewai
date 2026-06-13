# Security Guide — Contract Review AI & M&A Due Diligence AI

## Overview

Both tools handle **legally privileged, confidential documents** (contracts, financials, M&A data). This guide covers the security architecture, configuration, and operational best practices.

---

## 1. Encryption-at-Rest (AES-256)

### Document Files
All uploaded documents can be encrypted on disk using **AES-256 via Fernet** (symmetric encryption).

Enable it:
```bash
ENCRYPT_DOCUMENTS=true
ENCRYPTION_KEY=<generate a strong key>
```

Generate a key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**How it works:**
- On upload: file is encrypted before writing to disk
- On read: file is decrypted to a temporary location for processing, then cleaned up
- Key derivation uses PBKDF2 with 600,000 iterations

### Database
The SQLite/PostgreSQL database itself is **not encrypted** at the application layer (TDE is handled at the filesystem/storage layer in production). For sensitive content in the database:
- Set `ENCRYPT_DOCUMENTS=true` — extracted text in the DB will be the parsed plaintext
- For production, use **encrypted volumes** (AWS EBS encryption, Azure Disk Encryption, LUKS)

---

## 2. Authentication

### API Key Auth
Enable API key authentication for all API endpoints:

```bash
AUTH_ENABLED=true
API_KEY=your-secure-api-key-here
```

All `/api/*` requests must include the header:
```
X-API-Key: your-secure-api-key-here
```

**Exempt paths** (no auth required):
- `/` — landing page
- `/dashboard`, `/contracts/new`, `/billing` — web UI pages
- `/web/*` — HTMX form submissions
- `/static/*` — static assets
- `/api/health` — health check

### Web UI Auth
For production, place the app behind a **reverse proxy** (nginx/Caddy) with:
- **Basic Auth** or **OAuth2 Proxy** (e.g., Google OAuth, Azure AD)
- **mTLS** for firm-to-app communication
- **VPN** for internal deployments

---

## 3. Audit Logging

All API requests are logged to the `audit_logs` table automatically:

| Field | Description |
|-------|-------------|
| `method` | HTTP method (GET, POST, etc.) |
| `path` | API endpoint accessed |
| `query_params` | Query string parameters |
| `status_code` | HTTP response code |
| `duration_ms` | Request duration |
| `ip_address` | Client IP |
| `user_agent` | Client user agent |
| `created_at` | Timestamp |

Disable if not needed:
```bash
AUDIT_ENABLED=false
```

---

## 4. Data Retention & Auto-Delete

```bash
DATA_RETENTION_DAYS=365
AUTO_DELETE_EXPIRED=false   # Enable to auto-clean
```

When enabled, contracts, documents, and audit logs older than `DATA_RETENTION_DAYS` are deleted.

Trigger cleanup:
```bash
curl -X POST http://localhost:8000/api/admin/retention/cleanup
```

---

## 5. LLM Data Privacy

### OpenAI API (Default)
By default, **OpenAI does NOT train on API data** (since March 2023). To verify:
1. Go to https://platform.openai.com/account/org-settings
2. Confirm "Improve the model for everyone" is **disabled**

Additional protections:
```bash
LLM_DATA_LOGGING=false         # Don't log prompts/responses (default)
LLM_REDACT_PII=false           # Enable to redact PII before sending to LLM
```

### Azure OpenAI (Recommended for Enterprise)
Use Azure OpenAI for data residency guarantees:
```bash
LLM_USE_AZURE=true
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_KEY=your-azure-key
```

**Benefits:**
- Data stays within Azure boundary (no data leaves your region)
- Azure AD authentication
- HIPAA, SOC 2, ISO 27001 compliance
- SLA guarantees

### On-Premise LLM (Maximum Security)
For air-gapped deployments, use open-source models:
- **Llama 3.1** (70B or 8B) via Ollama or vLLM
- **Mistral Large** via self-hosted API
- **Mixtral 8x22B** via Hugging Face TGI

Update the clause extractor and analyzer to use a local endpoint instead of OpenAI.

---

## 6. Network Security

### Production Deployment Architecture

```
[Client]
    | HTTPS (TLS 1.3)
    v
[Reverse Proxy: nginx/Caddy]
    | TLS termination, rate limiting, WAF
    v
[Application Container (FastAPI)]
    | Internal network (not exposed)
    v
[OpenAI API]  (outbound HTTPS only)
```

### TLS Certificate
Use **Let's Encrypt** (free) or your firm's CA-signed certificate.

### Firewall Rules
- Allow: 443 (HTTPS) from client IPs
- Allow: outbound to `api.openai.com` (or Azure OpenAI endpoint)
- Deny: all other inbound traffic

---

## 7. Data Residency & Compliance

### India (DPDP Act 2023)
```bash
DPDP_COMPLIANCE=true
DATA_RESIDENCY=india
```

Requirements:
- Host on **AWS Mumbai (ap-south-1)** or **Azure Central India**
- Use **Azure OpenAI** (Mumbai region) or **self-hosted LLM** (data never leaves India)
- Enable encryption-at-rest
- Set data retention per DPDP principles (delete when purpose is served)
- Consent mechanism for data processing (add to Terms of Service)

### GDPR (Europe)
- Host on **AWS Frankfurt** or **Azure West Europe**
- Use Azure OpenAI (Europe regions)
- Data Processing Agreement (DPA) with OpenAI/Azure
- Right to erasure — implement via the delete endpoint + retention cleanup

### USA (CCPA, NY Shield)
- Host on **AWS us-east-1** or **Azure East US**
- Standard encryption + audit logging satisfies most requirements

---

## 8. Docker Security

```dockerfile
# Run as non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Read-only root filesystem
docker run --read-only --tmpfs /tmp ...
```

In `docker-compose.yml`:
```yaml
services:
  app:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

---

## 9. Secrets Management

**Never** commit secrets to git. Use:

| Environment | Secret Storage |
|-------------|---------------|
| Local dev | `.env` file (in `.gitignore`) |
| Docker | Docker secrets or env_file |
| AWS | AWS Secrets Manager |
| Azure | Azure Key Vault |
| Kubernetes | Kubernetes Secrets + Sealed Secrets |

---

## 10. Security Checklist

### Pre-Production
- [ ] Enable encryption-at-rest (`ENCRYPT_DOCUMENTS=true`)
- [ ] Generate strong `ENCRYPTION_KEY`
- [ ] Enable authentication (`AUTH_ENABLED=true`)
- [ ] Set strong `API_KEY`
- [ ] Enable audit logging
- [ ] Set data retention policy
- [ ] Configure CORS to specific origins (not `*`)
- [ ] Use HTTPS (TLS 1.3)
- [ ] Run as non-root user in container
- [ ] Drop all unnecessary container capabilities
- [ ] Set up rate limiting on reverse proxy
- [ ] Configure WAF rules
- [ ] Verify OpenAI API data usage settings

### Ongoing
- [ ] Rotate API keys every 90 days
- [ ] Rotate encryption key annually (re-encrypt documents)
- [ ] Review audit logs weekly
- [ ] Run data retention cleanup monthly
- [ ] Penetration test annually
- [ ] Review LLM provider compliance certifications

---

## Quick Security Setup

```bash
# 1. Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Generate API key (32+ random chars)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Set in .env
ENCRYPTION_KEY=<from step 1>
ENCRYPT_DOCUMENTS=true
AUTH_ENABLED=true
API_KEY=<from step 2>
AUDIT_ENABLED=true
DATA_RETENTION_DAYS=365

# 4. Deploy behind HTTPS reverse proxy
```
