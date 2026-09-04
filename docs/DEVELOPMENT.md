# Development

Do not run the public SMTP listener on a Windows workstation. Use the Arch
host for Postfix/Caddy. Unit tests can run anywhere Python 3.11+ is available.

## Backend tests

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The open-relay test is mandatory. If `victim@gmail.com` would be accepted as
an inbound recipient, the suite must fail.

## API (dev)

```bash
export MAILGATE_ETC=./tmp-etc
export MAILGATE_DATA_DIR=./tmp-data
export MAILGATE_SECRETS_DIR=./tmp-etc/secrets
export MAILGATE_CONFIG=./tmp-etc/config.yml
# copy config.example.yml, switch database.url to sqlite
uvicorn mailgate.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Point the browser at `http://localhost:3000` and either proxy `/api` to
`:8000` or open the static export behind Caddy as in production.

```bash
npm run build   # writes frontend/out (static export)
```

## Layout

```text
backend/mailgate/    FastAPI, CLI, Postfix generator, policy
backend/tests/       pytest
frontend/            Next.js 14 + Tailwind
cli/                 thin wrapper
installer/           sudoers, helpers, nftables
postfix/             main.cf snippet
caddy/               Caddyfile template
systemd/             api + worker units
docs/
```
