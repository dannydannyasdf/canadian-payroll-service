from fastapi import FastAPI

from app.routes import payroll

app = FastAPI(
    title="Canadian Payroll Service",
    description="Generates pay stubs and tax documents from XML payroll payloads.",
    version="0.1.0",
)

app.include_router(payroll.router, prefix="/payroll", tags=["payroll"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
