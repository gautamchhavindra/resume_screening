"""FastAPI layer exposing the resume screening pipeline over REST."""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import load_config
from models import JobDescriptionRequest, JobStatusResponse, ScreenResponse
from pipeline import run_screening

logger = logging.getLogger(__name__)

config = load_config()

app = FastAPI(title="Resume Screening API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/resumes", StaticFiles(directory=config.resume_folder), name="resumes")

# In-memory job store. Fine for a single-process deployment; swap for a real
# store (Redis, DB) if this needs to run behind multiple workers.
_JOBS: dict[str, ScreenResponse] = {}


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """No-op when RECRUITMENT_API_KEY isn't set (default, matches the no-auth
    assumption in the README); enforced once it is."""
    if config.recruitment_api_key and x_api_key != config.recruitment_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")


@app.post("/screen", response_model=ScreenResponse, dependencies=[Depends(require_api_key)])
def screen(jd: JobDescriptionRequest) -> ScreenResponse:
    job_id = str(uuid.uuid4())
    try:
        results = run_screening(jd, config)
    except ValueError as exc:
        # e.g. DEEPSEEK_API_KEY missing from .env — a config problem, not a client error
        logger.error("Screening pipeline misconfigured: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    response = ScreenResponse(jobId=job_id, results=results)
    _JOBS[job_id] = response
    return response


@app.get(
    "/screen/{job_id}/results",
    response_model=JobStatusResponse,
    dependencies=[Depends(require_api_key)],
)
def get_results(job_id: str) -> JobStatusResponse:
    response = _JOBS.get(job_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(jobId=job_id, status="completed", results=response.results)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
