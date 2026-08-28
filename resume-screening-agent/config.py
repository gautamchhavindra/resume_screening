"""Load pipeline configuration from config.yaml + environment (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_CONFIG_PATH = _BASE_DIR / "config.yaml"


@dataclass
class AppConfig:
    resume_folder: str
    embedding_provider: str
    local_embedding_model: str
    openai_embedding_model: str
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_temperature: float
    top_percent: float
    min_candidates: int
    cors_origins: list[str]
    log_level: str
    deepseek_api_key: str | None
    openai_api_key: str | None
    anthropic_api_key: str | None
    llm_api_key: str | None
    recruitment_api_key: str | None


def load_config(config_path: str | Path | None = None) -> AppConfig:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    resume_folder = raw.get("resume_folder", "SampleResumes")
    if not os.path.isabs(resume_folder):
        resume_folder = str((_BASE_DIR / resume_folder).resolve())

    embedding = raw.get("embedding", {})
    llm = raw.get("llm", {})
    shortlist = raw.get("shortlist", {})
    api = raw.get("api", {})
    logging_cfg = raw.get("logging", {})

    return AppConfig(
        resume_folder=resume_folder,
        embedding_provider=embedding.get("provider", "local"),
        local_embedding_model=embedding.get("local_model", "all-MiniLM-L6-v2"),
        openai_embedding_model=embedding.get("openai_model", "text-embedding-3-small"),
        llm_provider=llm.get("provider", "deepseek"),
        llm_model=llm.get("model", "deepseek-chat"),
        llm_base_url=llm.get("base_url", "https://api.deepseek.com"),
        llm_temperature=float(llm.get("temperature", 0.2)),
        top_percent=float(shortlist.get("top_percent", 10)),
        min_candidates=int(shortlist.get("min_candidates", 1)),
        cors_origins=api.get("cors_origins", ["*"]),
        log_level=logging_cfg.get("level", "INFO"),
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        llm_api_key=os.environ.get("LLM_API_KEY"),
        recruitment_api_key=os.environ.get("RECRUITMENT_API_KEY"),
    )
