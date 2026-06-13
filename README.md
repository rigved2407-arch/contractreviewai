# Contract Review AI

AI-powered contract analysis and redlining built for **Indian law firms**. Trained on Indian statutes — Companies Act 2013, Contract Act 1872, DPDP Act 2023, GST Act 2017, Income Tax Act 1961, and more.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key (or Groq, Azure OpenAI)

### Setup

1. Clone and enter the directory:
```bash
git clone <repo> && cd contract-review-ai
```

2. Copy the env file and add your API key:
```bash
cp .env.example .env
# Edit .env - set OPENAI_API_KEY and optionally generate ENCRYPTION_KEY & API_KEY
```

3. Start the services:
```bash
docker-compose up --build
```

4. Open http://localhost:3000

### Usage
1. Click "Upload Contract" and select a PDF or DOCX
2. Wait for parsing to complete
3. Click "Run AI Analysis" to extract clauses and assess risk under Indian law
4. Review flagged clauses with India-specific risk reasons and statute references
5. Download the redlined DOCX with suggested changes

## Features

### India-Specific Legal Analysis
- **Non-Compete**: Flags void clauses under Section 27, Indian Contract Act 1872
- **Indemnification**: Reviews against Sections 124-125, Indian Contract Act
- **Data Protection**: Checks compliance with DPDP Act 2023 (penalties up to INR 250 Cr)
- **GST Compliance**: Verifies CGST/SGST/IGST Act 2017 compliance
- **TDS Withholding**: Confirms Section 194C/194J compliance
- **Arbitration**: Validates Arbitration and Conciliation Act 1996 requirements
- **Limitation of Liability**: Reviews against Indian market standards (100% cap)
- **Force Majeure**: Checks Section 56 (Doctrine of Frustration) alignment
- **SHA/SSA clauses**: ROFR, Tag-Along, Drag-Along, Anti-dilution, Board Composition
- **Employment contracts**: Notice periods, restrictive covenants, POSH compliance

### Compliance Dashboard
- Real-time compliance scoring against 8 Indian regulatory frameworks
- Visual indicators showing which statutes are addressed in the contract

### Smart Playbooks
- Create custom playbooks with preferred positions for each clause type
- Use India-market standard templates as starting point
- Playbook rules automatically adjust risk scoring

### Security
- AES-256 encryption at rest (document storage)
- API key authentication
- Comprehensive audit logging
- DPDP Act 2023 compliant
- Data residency: India (AWS Mumbai / Azure Central India)
- On-premise deployment available

## Architecture

```
[Client Browser]
    |
[Next.js Frontend] ──rewrites── [FastAPI Backend]
    :3000                        :8000
                                      |
                              [OpenAI/Groq/Azure OpenAI API]
```

- **Backend**: FastAPI (Python), SQLAlchemy, OpenAI SDK
- **Frontend**: Next.js 14 (React), Tailwind CSS, HTMX (admin)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Document Processing**: PyMuPDF (PDF), python-docx (DOCX)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/contracts/upload | Upload a contract |
| GET | /api/contracts | List all contracts |
| GET | /api/contracts/:id | Get contract details |
| GET | /api/contracts/:id/redline | Download redlined DOCX |
| DELETE | /api/contracts/:id | Delete a contract |
| POST | /api/analysis/:id | Run AI analysis |
| GET | /api/playbooks | List playbooks |
| POST | /api/playbooks | Create a playbook |
| GET | /api/billing/plans | List pricing plans |
| GET | /api/health | Health check |

## Pricing for Indian Law Firms

| Tier | Price | Volume | Best For |
|------|-------|--------|----------|
| Starter | ₹30,000/mo | 200 contracts | Solo practitioners |
| Professional | ₹75,000/mo | 1,000 contracts | Mid-size firms |
| Enterprise | ₹2,50,000/mo | 5,000 contracts | Top-tier firms |

Pay-per-use also available at ₹500/contract.

## Deployment

### Production Requirements
- HTTPS reverse proxy (nginx/Caddy with Let's Encrypt)
- PostgreSQL database
- AWS Mumbai (ap-south-1) or Azure Central India hosting
- Environment variables configured via secrets manager

### Configuration
See `.env.example` for all configuration options.

## Security Checklist

- [ ] Enable `ENCRYPT_DOCUMENTS=true` with strong `ENCRYPTION_KEY`
- [ ] Enable `AUTH_ENABLED=true` with strong `API_KEY`
- [ ] Set `CORS_ORIGINS` to your domain(s)
- [ ] Deploy behind HTTPS reverse proxy
- [ ] Use non-root user in containers
- [ ] Enable audit logging
- [ ] Set data retention policy
- [ ] Verify OpenAI API data usage settings
