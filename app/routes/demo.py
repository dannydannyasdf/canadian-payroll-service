import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _load_sample(name: str) -> dict:
    return json.loads((SAMPLES_DIR / name).read_text())


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/demo")


@router.get("/demo", response_class=HTMLResponse)
def demo_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "demo.html",
        {
            "week1_json": json.dumps(_load_sample("sample_payroll.json")),
            "week2_json": json.dumps(_load_sample("sample_payroll_week2.json")),
        },
    )
