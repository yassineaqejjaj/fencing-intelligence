# Security

## Reporting

Report vulnerabilities privately to the repository maintainers. Do not open a public issue that includes exploit detail, session tokens, or private video.

## Controls in this application

- Passwords are hashed with Argon2. Sessions are random tokens stored as SHA-256 hashes in an httpOnly cookie.
- Unsafe methods require the `X-CSRF-Token` header to match the readable `fi_csrf` cookie.
- Login attempts are rate limited in Redis. If Redis is unavailable, the limiter fails closed.
- Video uploads are rate limited per user (`UPLOAD_RATE_LIMIT`, default 20/hour) in addition to the size cap.
- Guardian consent protects minors: videos of athletes under 18 without a recorded guardian consent are forced private, and research-training use is refused with `guardian_consent_required`.
- Without SMTP, password-reset and invitation emails are dropped with a server-side error log; invitations return the token to the inviting administrator so onboarding never fails silently.
- Authorization is enforced in the API. A resource from another organization returns 404.
- Video playback uses signed URLs that expire. Buckets are not public.
- Uploads are size limited and checked for a known video container header before storage.
- Audit logs store action names and resource ids. They do not store passwords, tokens, or video bytes.
- Account export and deletion are available under Privacy. Deletion anonymizes the user and can delete uploaded objects.
- Athlete video is excluded from research use unless a consent record grants `research_training`.
- `ENVIRONMENT=production` refuses the development secret and the development object-storage credentials.

## Deployment expectations

Put the web and API behind HTTPS. Set `COOKIE_SECURE=true`, `TRUST_PROXY=true` only behind a proxy you control, and a unique `SECRET_KEY` of at least 32 characters. Do not publish Postgres, Redis, or object storage to the public internet. Restrict `CORS_ORIGINS` to the public web origin. The Caddy example ships HSTS and baseline hardening headers; configure SMTP (`SMTP_HOST`, or invitations and password resets cannot be delivered). See `docs/DEPLOYMENT.md` and `docs/BACKUP.md`.
