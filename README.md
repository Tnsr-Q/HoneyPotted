# HoneyPotted

HoneyPotted is an active honeypot platform for detecting, verifying, and analyzing automated traffic and malicious bot behavior.

## What is implemented

- HTTP/API service layer in `api/` for request handling, authentication, middleware, scheduling, and integrations
- Core honeypot modules in `honeypot/` for:
  - challenge generation and validation
  - fingerprint collection and classification workflows
  - verification APIs
  - sandbox execution support
- Real-time operational dashboard in `web/` with WebSocket-driven updates
- Database bootstrap and migrations (`honeypot/migrations/`)
- Environment-driven configuration (`.env.example`, `config/production.py`)
- Containerized deployment support (`docker/`)

## Repository layout

- `main.py` — application entry point
- `api/` — backend API, auth, middleware, scheduler, integrations, WebSocket server
- `honeypot/` — challenge, fingerprinting, verification, sandbox, migrations
- `web/` — dashboard templates and static assets
- `docker/` — Dockerfile and compose configuration
- `requirements.txt` — Python dependencies

## Running locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure environment:
   ```bash
   cp .env.example .env
   ```
3. Initialize core components:
   ```bash
   python main.py --init-only
   ```
4. Start the service:
   ```bash
   python main.py
   ```

Default local URL: `http://localhost:5000`

## API and runtime surface

- REST endpoints under `/api/*`
- WebSocket stream at `/events`
- JWT-based authentication for protected routes

## Development

Run tests:

```bash
pytest
```

## License

See `LICENSE`.
