import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

# SQLite by default for local dev; set DATABASE_URL for PostgreSQL in production.
# Example: postgresql+psycopg://payroll:payroll@localhost:5432/payroll
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_DIR / 'payroll.db'}",
)
