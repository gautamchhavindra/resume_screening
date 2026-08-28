"""LangChain-based nuanced LLM scoring for shortlisted resumes — provider-agnostic."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import AppConfig

logger = logging.getLogger(__name__)


class DimensionScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    justification: str = Field(..., description="One or two sentence justification")


class ResumeScoreResult(BaseModel):
    soft_skills: DimensionScore
    project_relevance: DimensionScore
    culture_fit: DimensionScore
    overall_score: int = Field(..., ge=0, le=100, description="Overall weighted score 0-100")
    recommendation: str = Field(..., description="Short overall hiring recommendation")


_SYSTEM_PROMPT = """You are an expert technical recruiter screening a candidate resume \
against a job description. Evaluate the candidate on three dimensions, inferring signal \
from the language and achievements described rather than just keyword matching:

1. soft_skills: communication, leadership, collaboration
2. project_relevance: how closely past projects map to the JD's actual needs
3. culture_fit: working style, team context, values alignment where evidenced

Score each dimension 0-100 with a short justification, give an overall_score (0-100), \
and a short overall recommendation. Respond ONLY with data matching the required schema."""


def get_llm(config: AppConfig) -> BaseChatModel:
    """Build the LangChain chat model for config.yaml's `llm.provider`/`llm.model`.

    Model-agnostic by design: switch providers by changing `llm.provider` +
    `llm.model` in config.yaml (and setting the matching API key env var) —
    no other code needs to change.
    """
    provider = config.llm_provider.lower()

    if provider == "deepseek":
        if not config.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set (check your .env file)")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm_model,
            base_url=config.llm_base_url or "https://api.deepseek.com",
            api_key=config.deepseek_api_key,
            temperature=config.llm_temperature,
        )

    if provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set (check your .env file)")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm_model,
            api_key=config.openai_api_key,
            temperature=config.llm_temperature,
        )

    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set (check your .env file)")
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.llm_model,
            api_key=config.anthropic_api_key,
            temperature=config.llm_temperature,
        )

    if provider == "openai_compatible":
        # Any other OpenAI-compatible endpoint: Groq, Together, local Ollama/vLLM, etc.
        if not config.llm_api_key:
            raise ValueError("LLM_API_KEY is not set (check your .env file)")
        if not config.llm_base_url:
            raise ValueError("llm.base_url must be set in config.yaml for provider 'openai_compatible'")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm_model,
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            temperature=config.llm_temperature,
        )

    raise ValueError(
        f"Unknown llm.provider {config.llm_provider!r} in config.yaml — expected one of: "
        "deepseek, openai, anthropic, openai_compatible"
    )


def build_scoring_chain(llm: BaseChatModel):
    """Chain that forces ResumeScoreResult-shaped JSON via tool-calling structured output."""
    structured_llm = llm.with_structured_output(ResumeScoreResult, method="function_calling")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("user", "Job Description:\n{jd_text}\n\nCandidate Resume:\n{resume_text}"),
        ]
    )
    return prompt | structured_llm


_FALLBACK_RESULT = ResumeScoreResult(
    soft_skills=DimensionScore(score=0, justification="Scoring failed."),
    project_relevance=DimensionScore(score=0, justification="Scoring failed."),
    culture_fit=DimensionScore(score=0, justification="Scoring failed."),
    overall_score=0,
    recommendation="Could not be scored due to an LLM error; review manually.",
)


def score_resume(chain, resume_text: str, jd_text: str) -> ResumeScoreResult:
    try:
        result = chain.invoke({"resume_text": resume_text, "jd_text": jd_text})
        if isinstance(result, ResumeScoreResult):
            return result
        return ResumeScoreResult.model_validate(result)
    except Exception as exc:
        logger.error("LLM scoring failed: %s", exc)
        return _FALLBACK_RESULT
