from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import demo, onboarding, payroll

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
    version="0.4.7",
    lifespan=lifespan,
)

FAVICON_PATH = PROJECT_DIR / "Images" / "GammaHeadsOrange.png"

app.include_router(demo.router, tags=["demo"])
app.include_router(onboarding.router, prefix="/payroll", tags=["onboarding"])
app.include_router(payroll.router, prefix="/payroll", tags=["payroll"])


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/png")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/images", StaticFiles(directory=PROJECT_DIR / "Images"), name="images")
