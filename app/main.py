from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import __version__
from .redhat_client import RedHatAPIError
from .schemas import FilterMode, QueryParams, SearchResponse
from .service import find_rhsa_for_month

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="RHEL Vulnerability Scanner",
    description=(
        "RHEL のメジャー/マイナーバージョンと対象月を指定して、"
        "その月に初回リリースされた RHSA を Red Hat Security Data API から取得し JSON で返します。"
    ),
    version=__version__,
)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/", response_class=HTMLResponse, tags=["ui"])
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"version": __version__})


@app.get("/api/rhsa", response_model=SearchResponse, tags=["rhsa"])
async def search_rhsa(
    major: int = Query(..., ge=5, le=99, description="RHEL major version, e.g. 8"),
    month: str = Query(..., description="Target month YYYY-MM"),
    minor: Optional[int] = Query(None, ge=0, le=99, description="RHEL minor version"),
    mode: Optional[FilterMode] = Query(None, description="Filter mode"),
) -> SearchResponse:
    try:
        params = QueryParams(major=major, minor=minor, month=month, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return await find_rhsa_for_month(params)
    except RedHatAPIError as exc:
        logger.exception("Red Hat API error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.exception_handler(ValueError)
async def _value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
