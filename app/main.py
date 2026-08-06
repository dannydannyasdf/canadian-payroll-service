from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import demo, payroll

PROJECT_DIR = Path(__file__).resolve().parent.parent


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
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(demo.router, tags=["demo"])
app.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
app.mount("/images", StaticFiles(directory=PROJECT_DIR / "Images"), name="images")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
