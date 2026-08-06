from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import payroll


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Canadian Payroll Service",
    description=(
        "Generates pay stubs and tax documents. "
        "Accepts JSON (primary) or XML, returns cumulative YTD JSON plus PDF."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(payroll.router, prefix="/payroll", tags=["payroll"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
