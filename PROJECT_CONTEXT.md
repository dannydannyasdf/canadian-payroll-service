# Canadian Payroll Service — Project Context

## 1. Project Overview & Business Goals

**What this is:** A web service on Debian Linux that automates Canadian payroll document generation for freelancers. It ingests pay-period data, accumulates year-to-date totals, and produces print-ready pay stubs plus year-end tax artifacts (CRA T4, Revenu Québec Relevé 1, and e-file XML).

**Who operates it:** **Gamma Personnel Inc.** (GP) — Danny Majerovich's payroll provider company, Montréal QC. GP acts as a **proxy payroll filer** for smaller client firms.

**Proxy payroll model (finalized):**
- **Client employers** (e.g. *Acme Productions Ltd.*) are the businesses GP runs payroll for.
- On **tax slips and e-files**, the employer name is `{ClientName}@{ProviderName}` → e.g. `Acme Productions Ltd.@Gamma Personnel Inc.`
- **Business number, payroll account, and address** on T4 / Relevé 1 / CRA XML always come from **GP's provider settings**, not from client employer DB fields.
- Pay stub payloads still send the **plain client name**; the `@Gamma Personnel Inc.` transform happens at tax-slip render time via `provider_config.py`.

**Primary users / flows:**
1. External client software (or the demo page) POSTs payroll → YTD updated → cumulative JSON + pay stub PDF returned.
2. Year-end: preview/download T4 and Relevé 1 PDFs and CRA/RQ e-file XML from stored YTD.
3. Optional explicit onboarding: register employers and employees before payroll runs.

**Product stance:** Current tax box mappings and PDF layouts are **preview / prep quality**. Production filing requires accountant review (QPP/QPIP splits, insurable/pensionable caps, federal vs provincial tax separation).

**Completed roadmap:**

| Phase | Delivered |
|-------|-----------|
| 1 | JSON (primary) + XML ingress → pay stub PDF |
| 2 | PostgreSQL, cumulative YTD JSON, YTD on PDF |
| 2.5 | Pay period history; duplicate period rejection (409) |
| 3 | Docker Compose + PostgreSQL |
| 3.5 | Mobile-friendly `/demo` page |
| 4 | NGINX → Kong → FastAPI; API keys; billing log |
| 5 | Multi-period pay stub archive PDF |
| 6 prep | Alembic migrations; T4/Relevé 1 box mapping; JSON preview endpoints |
| 6.1 | T4 PDF (official CRA form overlay when available) |
| 6.2 | Relevé 1 PDF |
| 6.3 | CRA T4 e-file XML (official XSD when present, else preview schema) |
| 6.4 | Revenu Québec Relevé 1 e-file XML (preview schema; QC employment province only) |

**Onboarding (implemented, separate from Phase 6 numbering):**
- Slices 1–2: Employer/employee registration API
- Slice 3: Optional `employer.id` / `employee.id` on pay stub; inactive → 403; demo dropdowns

---

## 2. Tech Stack & System Architecture

**Language & framework:** Python 3.13, **FastAPI**, **SQLAlchemy 2**, **Alembic**, **Pydantic v2**.

**Database:** **PostgreSQL 16** in Docker (production path). `DATABASE_URL` env var; SQLite fallback only for bare local dev.

**PDF generation:**
- **WeasyPrint** + **Jinja2** templates for pay stubs, HTML-fallback T4/Relevé 1, and pay-stub archives.
- **PyMuPDF** (`pymupdf`) for official CRA **t4-25e.pdf** overlay (`app/services/t4_official_form.py`). Asset at `app/assets/forms/t4-25e.pdf`.
- WeasyPrint fixed headers use **table layout** (not flex/absolute) for reliable multi-page rendering.

**XML:** **lxml** + **xmlschema** for ingress validation (`schemas/payroll.xsd`) and e-file egress validation.

**Edge stack (Docker):**

```
Client → NGINX (:8080 host, 2 MB body limit) → Kong (API keys, rate limits) → FastAPI (:8000 internal) → PostgreSQL
```

- Public routes (no API key): `/demo`, `/health`, `/images`, `/docs`, `/openapi.json`, `/redoc`
- Protected routes: `/payroll/*` requires header `apikey: <key>`
- Dev keys: `gamma-dev-api-key` (demo), `gamma-client-api-key` (simulated client)
- Billing: Kong passes `x-consumer-username`; app logs gross pay + ⅓ service fee per request

**Project root:** `~/Projects/canadian-payroll-service`

**Canonical folder layout:**

```
canadian-payroll-service/
├── app/
│   ├── main.py                 # FastAPI app, routers, lifespan → alembic upgrade
│   ├── config.py               # DATABASE_URL
│   ├── database.py             # SQLAlchemy engine/session
│   ├── db_models.py            # employers, employees, pay_periods, ytd_totals, billing_events
│   ├── sin.py                  # SIN validation (Luhn, no leading 0/8)
│   ├── exceptions.py
│   ├── models/                 # Pydantic: payroll, cumulative, tax_slip, onboarding, employee
│   ├── routes/
│   │   ├── payroll.py          # Pay stub, stubs archive, tax slips, CRA e-file
│   │   ├── onboarding.py       # Employer/employee CRUD
│   │   └── demo.py             # GET /demo
│   ├── services/
│   │   ├── provider_config.py  # ★ GP proxy settings — single source for filing identity
│   │   ├── ytd_service.py      # Pay period + YTD accumulation
│   │   ├── pdf_generator.py    # WeasyPrint renderers
│   │   ├── t4_official_form.py # PyMuPDF CRA form overlay
│   │   ├── tax_slip_service.py # T4/Relevé 1 preview from YTD
│   │   ├── cra_efile_service.py
│   │   ├── rq_efile_service.py # Relevé 1 e-file (Slice 4)
│   │   ├── onboarding_service.py
│   │   ├── stub_archive_service.py
│   │   ├── billing_service.py
│   │   └── xml_validator.py
│   ├── tax/box_mapping.py      # YTD → T4 boxes & Relevé 1 boxes
│   ├── templates/              # Jinja2 HTML for PDFs + demo.html
│   └── assets/forms/           # t4-25e.pdf
├── alembic/versions/           # 001 baseline, 002 tax metadata, 003 onboarding status
├── schemas/
│   ├── payroll.xsd             # Ingress contract
│   ├── cra/                    # Official CRA XSD subset + t4_efile_preview.xsd
│   └── rq/                     # releve1_efile_preview.xsd (+ official RQ XSDs later)
├── samples/                    # sample_payroll.json/xml, tax slip expected outputs
├── kong/kong.yml
├── nginx/nginx.conf
├── docker-compose.yml
├── Images/                     # Client + provider logos (env-configurable paths)
└── requirements.txt
```

**Key API surface:**

| Endpoint | Purpose |
|----------|---------|
| `POST /payroll/pay-stub` | JSON payroll → YTD + PDF (primary) |
| `POST /payroll/pay-stub/xml` | XML payroll → same response shape |
| `GET /payroll/employees/{id}/stubs?taxYear=` | All pay periods → one PDF |
| `GET /payroll/employees/{id}/t4[|/pdf|/xml]?taxYear=` | T4 JSON / PDF / CRA XML |
| `GET /payroll/employees/{id}/releve1[|/pdf|/xml]?taxYear=` | Relevé 1 JSON / PDF / RQ XML |
| `GET /payroll/tax-filing/cra?taxYear=` | Bulk CRA T4 e-file |
| `GET /payroll/tax-filing/cra/schema-status` | CRA XSD inventory |
| `GET /payroll/tax-filing/rq?taxYear=` | Bulk Relevé 1 e-file (QC employees only) |
| `GET /payroll/tax-filing/rq/schema-status` | RQ XSD inventory |
| `POST/GET/PATCH /payroll/employers[/{id}]` | Client employer onboarding |
| `POST/GET/PATCH /payroll/employers/{id}/employees[/{employee_id}]` | Employee onboarding |
| `GET /payroll/employees?employerId=` | List employees (optional filter) |
| `GET /demo` | Interactive demo (uses `DEMO_API_KEY`) |

**Tax box mappings (simplified YTD → boxes):**
- **T4:** 14 gross, 16 CPP (box 17 for QC/QPP), 18 EI, 22 income tax, 24/26 = gross
- **Relevé 1:** A gross, B CPP/QPP, C EI, E income tax, G/I = gross

**Branding on every PDF page:**
- **Left:** client logo (`PAYROLL_CLIENT_LOGO_PATH`)
- **Right:** GP logo + "Gamma Personnel Inc." + Danny Majerovich + Montréal address

---

## 3. Core Rules & Constraints

### Business & data rules

- **Sensitive data:** Names, addresses, salaries, SINs — treat as PII; never log or commit secrets.
- **SIN:** Format `XXX-XXX-XXX`; Luhn checksum; must not start with 0 or 8. Sample SIN: `130-692-544`.
- **Sample client employer:** `Acme Productions Ltd.` (plain name in pay payloads).
- **Net pay:** Must equal `grossPay − cpp − ei − incomeTax`; API rejects mismatch.
- **Duplicate pay periods:** Same employee + period start + period end → **409 Conflict**, no YTD change.
- **Employment province** (T4 box 10, RQ eligibility): `employee.employmentProvince` → `employee.address.province` → `PAYROLL_DEFAULT_EMPLOYMENT_PROVINCE` (**ON**). Do **not** use GP's Montréal QC address as the employment province default.
- **QC employees:** T4 uses box **17** (QPP) instead of box **16** (CPP). Relevé 1 e-file applies only to **QC** employment province.
- **E-file report type:** Original (`O`) only for now; Amended (`A`) / Cancel (`C`) are future work.
- **Accountant disclaimer:** Box mappings are intentionally simplified previews — do not present as filing-ready without professional review.

### Proxy payroll / provider config

- All filing identity logic lives in **`app/services/provider_config.py`**. Extend here, don't scatter GP BN/address across services.
- **`filing_employer_display_name(client)`** → `{client}@{PROVIDER_NAME}`.
- **`build_filing_employer_summary(client_name)`** → GP BN, payroll account, Montréal address for tax slips.
- Client employer DB columns (`business_number`, etc.) are **not** used for T4/Relevé 1/CRA XML employer blocks.

### Environment variables (defaults)

```
PAYROLL_PROVIDER_NAME=Gamma Personnel Inc.
PAYROLL_PROVIDER_CONTACT_NAME=Danny Majerovich
PAYROLL_PROVIDER_ADDRESS_* → Montréal QC address
PAYROLL_CRA_PAYROLL_ACCOUNT=10668 8385 RP0001   # spaced on PDF; stripped for XML
PAYROLL_CRA_TRANSMITTER_BN9 → derived from payroll account (106688385)
PAYROLL_DEFAULT_EMPLOYMENT_PROVINCE=ON
PAYROLL_RQ_EMPLOYER_ID=1234567890              # GP's Revenu Québec dossier ID
PAYROLL_CLIENT_LOGO_PATH / PAYROLL_PROVIDER_LOGO_PATH
DEMO_API_KEY=gamma-dev-api-key
DATABASE_URL=postgresql+psycopg://payroll:payroll@db:5432/payroll
```

### Onboarding rules (finalized decisions)

- **No `externalReference`** — defer until CRM integration.
- **Soft-delete only** — set `status: inactive`; never hard-delete employers/employees.
- **Employer rename locked** after the first pay stub (`nameLocked: true`; PATCH name → 409).
- **Employers first**, then nested employees under `/payroll/employers/{id}/employees`.
- **Backward compatible:** pay stub without IDs still get-or-creates by name/SIN.
- **With IDs:** name/SIN must match registered record; employee must belong to employer.
- **Inactive employer/employee** on pay stub → **403**.
- **ID/name/SIN mismatch** → **422**.
- **`filingDisplayName`** on employer responses shows the `@`-suffix preview name.
- **`employmentProvince`** on employees — capture at registration; flows into T4/Relevé 1.

### Coding & operational standards

- **JSON is the primary ingress format;** XML is a supported alternate (`/payroll/pay-stub/xml`).
- **JSON API uses camelCase** aliases (`taxYear`, `employerId`, `employmentProvince`, `payStubPdfBase64`).
- **Schema validation at boundaries:** ingress against `payroll.xsd`; e-file exports against official XSD when bundled, else internal preview XSD.
- **Migrations:** Alembic only (no `create_all()`); `init_db()` runs `alembic upgrade head` on startup.
- **After code/dependency changes:** `docker compose up --build -d` from project root.
- **Public access:** `http://localhost:8080` (NGINX); app is not exposed directly except optional `app-direct` dev profile on :8000.
- **Minimize diff scope** — match existing patterns (service layer, Pydantic models, Jinja templates).
- **Do not commit** unless explicitly asked.
- **`.cursorignore`** excludes bulk CRA XSD noise; keep T4 filing subset indexed. Official CRA schema source URL belongs in module docstrings only, not API responses.

### What NOT to build or revert to

- **No Java / Spring Boot / JAXB** — Python monolith was chosen deliberately (WeasyPrint is Python-native).
- **No XSL-FO / Apache FOP.**
- **No Bitcoin / crypto remittance** — not part of this codebase.
- **Do not put client BN/payroll account on tax slips** — always GP's via `provider_config`.
- **Do not hard-delete onboarding records.**
