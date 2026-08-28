"""End-to-end orchestration: parse -> rank -> shortlist -> LLM score -> results."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from config import AppConfig, load_config
from embedding_ranker import RankedResume, get_embedding_provider, rank_resumes, select_shortlist
from llm_scorer import build_scoring_chain, get_llm, score_resume
from location_matcher import resolve_cluster
from models import JobDescriptionRequest, ScreenResultItem
from resume_parser import parse_resume_folder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_screening(jd: JobDescriptionRequest, config: AppConfig | None = None) -> list[ScreenResultItem]:
    config = config or load_config()
    jd_text = jd.to_text()

    t0 = time.perf_counter()
    resumes = parse_resume_folder(config.resume_folder)
    t1 = time.perf_counter()
    logger.info("Stage 1 (parse): %d resume(s) in %.2fs", len(resumes), t1 - t0)

    if not resumes:
        logger.warning("No parsable resumes found in %s", config.resume_folder)
        return []

    jd_cluster = resolve_cluster(jd.location)
    if jd_cluster:
        before_count = len(resumes)
        resumes = [r for r in resumes if resolve_cluster(r.location) == jd_cluster]
        logger.info(
            "Location filter: %d of %d resume(s) match '%s' cluster (JD location=%r)",
            len(resumes),
            before_count,
            jd_cluster,
            jd.location,
        )
        if not resumes:
            return []

    provider = get_embedding_provider(config)
    ranked = rank_resumes(jd_text, resumes, provider)
    t2 = time.perf_counter()
    logger.info("Stage 2 (embed+rank): %d resume(s) in %.2fs", len(ranked), t2 - t1)

    shortlist = select_shortlist(ranked, config.top_percent, config.min_candidates)
    logger.info(
        "Stage 3 (shortlist): %d of %d resume(s) selected (top %.0f%%)",
        len(shortlist),
        len(ranked),
        config.top_percent,
    )

    llm = get_llm(config)
    chain = build_scoring_chain(llm)

    def score_one(ranked_resume: RankedResume) -> ScreenResultItem:
        resume = ranked_resume.resume
        score = score_resume(chain, resume.text, jd_text)
        return ScreenResultItem(
            candidateName=resume.candidate_name,
            location=resume.location,
            skills=resume.skills,
            resumeLink=f"/resumes/{resume.filename}",
            similarityScore=round(ranked_resume.similarity, 4),
            llmScore=score.overall_score,
            recommendation=score.recommendation,
        )

    # LLM calls are independent, I/O-bound network requests — run them
    # concurrently instead of one-at-a-time so total latency is roughly one
    # call's worth, not len(shortlist) calls' worth.
    with ThreadPoolExecutor(max_workers=min(len(shortlist), 8)) as executor:
        results = list(executor.map(score_one, shortlist))
    t3 = time.perf_counter()
    logger.info("Stage 4 (LLM scoring): %d resume(s) in %.2fs", len(shortlist), t3 - t2)

    results.sort(key=lambda r: r.llmScore, reverse=True)
    logger.info("Pipeline complete in %.2fs total", t3 - t0)
    return results


if __name__ == "__main__":
    sample_jd = JobDescriptionRequest(
        location="Remote",
        skills="Python, FastAPI, machine learning",
        other_details="3+ years experience, bachelor's degree preferred",
    )
    for item in run_screening(sample_jd):
        print(item.model_dump_json(indent=2))
