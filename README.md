# Email System

Self-hosted email platform with one unified Python backend process running SMTP, IMAP, and the REST API together, plus Celery, PostgreSQL, Redis, Nginx, SpamAssassin, ClamAV, and a Next.js 14 frontend.

## Prerequisites

- Docker and Docker Compose
- A domain name that you control
- Open ports 25, 80, 443, 587, and 993
- DNS access for MX, SPF, DKIM, and DMARC records

## Setup

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in all secrets and hostnames.
3. Generate DKIM keys:

```bash
bash infra/dkim/generate_keys.sh yourdomain.com
```

4. Start the stack:

```bash
docker compose up -d
```

5. Run migrations:

```bash
docker compose exec backend alembic upgrade head
```

6. Seed the initial admin and default domain:

```bash
docker compose exec backend python seed.py
```

7. Obtain TLS certificates:

```bash
docker compose exec nginx certbot --nginx -d mail.yourdomain.com
```

## DNS Records

Create the following records for your domain:

- MX: `10 mail.yourdomain.com.`
- A: `mail.yourdomain.com. -> YOUR_SERVER_IP`
- SPF: `v=spf1 ip4:YOUR_SERVER_IP mx ~all`
- DKIM: `mail._domainkey.yourdomain.com. TXT v=DKIM1; k=rsa; p=<pubkey>`
- DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com; pct=100`

## Validation

- Test deliverability at mail-tester.com and aim for 10/10.
- Verify login, SMTP submission, IMAP access, and outbound DKIM signing.

## Architecture

- The `backend` container hosts FastAPI, SMTP on 25/587, IMAP on 993, and the REST API on 8000 in one Python process.
- Celery runs in the `celery-worker` container and uses Redis for retries and scheduled cleanup.
- PostgreSQL stores users, domains, mailboxes, aliases, audit logs, and refresh sessions.
- Mail data lives on the shared `maildata` volume so SMTP and IMAP see the same Maildir state.

## Upgrade Notes

- Update container images in `docker-compose.yml` and `docker-compose.prod.yml`.
- Rotate JWT secrets, DKIM keys, and TLS certificates on a schedule.
- Re-run migrations after schema changes.
