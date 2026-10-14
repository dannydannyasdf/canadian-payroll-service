# Canadian Payroll Service

Web service for Canadian payroll: pay-period ingestion, year-to-date totals, pay stub PDFs, and year-end CRA T4 / Revenu Québec Relevé 1 previews plus e-file XML. Operated as **proxy payroll** by **Gamma Personnel Inc.** for client employers.

For architecture, API contracts, tax rules, and environment variables, see **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)** (source of truth for contributors and agents).

## Quick start

From the project root:

```bash
docker compose up --build -d
```

On startup the app runs Alembic migrations against PostgreSQL.

| URL | Purpose |
|-----|---------|
| http://localhost:8080/demo | Interactive demo |
| http://localhost:8080/docs | OpenAPI (Swagger) |
| http://localhost:8080/health | Health check |

Default host port is **8080**. Override with `NGINX_PORT=80 docker compose up --build -d`.

### API access

Traffic flows **NGINX → Kong → FastAPI**. Routes under `/payroll/*` require:

```http
apikey: gamma-dev-api-key
```

(Dev default from `DEMO_API_KEY` in `docker-compose.yml`.)

Public routes (no key): `/demo`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/images`.

### Optional: direct app (debug)

Bypass Kong/nginx on port 8000:

```bash
docker compose --profile dev up --build -d
```

## Development

**Stack:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, WeasyPrint, lxml/xmlschema.

**Tests** (with dependencies installed, e.g. in a venv):

```bash
pip install -r requirements.txt pytest
pytest
```

**Samples:** `samples/` — example payroll JSON/XML and tax-slip payloads.

**Schemas:** `schemas/payroll.xsd` (ingress), `schemas/cra/` and `schemas/rq/` (e-file validation when XSD packages are present).

## Main capabilities

- `POST /payroll/pay-stub` — JSON payroll → cumulative YTD + pay stub PDF
- Employer/employee onboarding under `/payroll/employers`
- T4 and Relevé 1 PDF/XML per employee; bulk CRA/RQ filing XML by tax year
- `POST /payroll/calculate-deductions` — federal (T4127) and CPP/EI/QPIP estimates

Tax slip employer identity on filings uses `{ClientName}@{ProviderName}` with Gamma Personnel’s BN and address; see `app/services/provider_config.py`.

## Repository layout

```
app/           FastAPI application, services, templates, tax logic
alembic/       Database migrations
schemas/       XSD validation
samples/       Example payloads
kong/          Kong declarative config
nginx/         Reverse proxy
docs/CRA/      CRA reference notes
docs/rq/       Revenu Québec reference notes
```

## License / filing disclaimer

Box mappings and PDF layouts are **preview / prep quality**. Professional review is required before production filing with CRA or Revenu Québec.
