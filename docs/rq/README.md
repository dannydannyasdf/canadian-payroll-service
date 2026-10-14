# Revenu Québec reference documents

Official RQ guides for RL-slip software developers and transmitters. Place the PDFs in this folder locally (they are gitignored).

| File | Purpose |
|------|---------|
| `tp-1015-f-v-2026-01.pdf` | **Formulas to Calculate Source Deductions and Contributions** — Québec provincial income tax, QPP, QPIP |
| `IN-412-V(2025-10).pdf` | **RL slip PDF requirements** — authorization number (FS######), 2D barcode, layout, copy instructions |
| `IN-800-V(2025-10).pdf` | **XML e-file requirements** — certification process, `Transmission` structure, data rules, NoReleve modulus-7 |

## Related project assets

| Path | Role |
|------|------|
| `schemas/rq/` | Official XSD package (`Transmission.xsd` is the validation root) |
| `schemas/rq/read-me.txt` | XML examples and namespace notes |
| `app/tax/rq/provincial.py` | TP-1015.F-V Option 1 Québec provincial income tax calculator |
| `app/services/rq_efile_service.py` | Official + preview XML generation |
| `app/services/releve1_official_form.py` | RL-1 PDF overlay on official blank form |
| `app/rq_releve_number.py` | Modulus-7 check digit for `NoReleve` (IN-800 Schedule 1) |

## Key identifiers (Gamma Personnel)

| Concept | Env var | Notes |
|---------|---------|-------|
| Employer file ID (`NoId` in XML) | `PAYROLL_RQ_EMPLOYER_ID` | 10-digit RQ identification — **not** the NEQ |
| NEQ (optional on `T` summary) | `PAYROLL_RQ_NEQ` | Québec enterprise number |
| Preparer number | `PAYROLL_RQ_PREPARATEUR_NO` | `NP######` for `<Preparateur><No>` |
| Certification number | `PAYROLL_RQ_CERTIFICATION_NO` | `RQ-##-##-###` in `<NoCertification>` |
| RL-slip sequence base | `PAYROLL_RQ_RELEVE_SEQ_BASE` | 8-digit start of series assigned by RQ; check digit computed automatically |

## Still outstanding for production filing

- RQ certification test-case submission (IN-800 §3) for a real certification number
- PDF authorization number overlay (`FS######`, IN-412 §3.14)
- 2D barcode on RL-1 copy 1 for paper filing (IN-412 §3.16, SW-162-T)
- RLZ-1.S employer summary form for paper / Mon Dossier paths
