# CRA reference documents

Official CRA guides for payroll deduction calculations. Place PDFs in this folder locally (they are gitignored via `*.pdf`).

| File | Purpose |
|------|---------|
| `t4127-jul-26e.pdf` | **Payroll Deductions Formulas** (123rd ed., effective July 1, 2026) — federal and provincial/territorial income tax, CPP, EI |

## Related project assets

| Path | Role |
|------|------|
| `app/tax/t4127/` | T4127 Option 1 federal tax calculator (July 2026 rates) |
| `app/services/payroll_deductions_service.py` | Service wrapper |
| `POST /payroll/calculate-deductions` | API endpoint for federal income tax |

## Official CRA sources

- [T4127-JUL landing page](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jul.html)
- [Rates CSV (Table 8.1)](https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4127-jul/rates-income-thresholds-constants-26e.csv)
- [Other amounts CSV (Table 8.2)](https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4127-jul/other-rates-amounts-26e.csv)
- [Payroll Deductions Online Calculator (PDOC)](https://www.canada.ca/en/revenue-agency/services/e-services/digital-services-businesses/payroll-deductions-online-calculator.html) — use to validate implementation

## What is implemented

- **Federal income tax** — T4127 Option 1, Steps 1–3 and Step 6 (federal `T1 / P`)
- **Québec employees** — QPP/QPIP federal credits (`K2Q`) and 16.5% federal abatement
- **Claim codes** — federal TD1 codes 0–10 (default code 1 = maximum BPAF)

## Not yet implemented

- Provincial/territorial tax (`T2`) for non-Québec provinces
- Québec **provincial** income tax (Revenu Québec — separate from T4127)
- CPP, EI, and QPIP contribution calculation (inputs accepted; not derived)
- Option 2 cumulative averaging
- Bonuses and non-periodic payments (`TB` formula)
- Dynamic BPAF based on net income (`NI`)
