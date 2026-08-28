"""Pydantic request/response schemas for the resume screening API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobDescriptionRequest(BaseModel):
    location: str = ""
    skills: str | list[str] = ""
    other_details: str = ""

    def to_text(self) -> str:
        skills_text = self.skills if isinstance(self.skills, str) else ", ".join(self.skills)
        parts = []
        if self.location:
            parts.append(f"Location: {self.location}")
        if skills_text:
            parts.append(f"Required skills: {skills_text}")
        if self.other_details:
            parts.append(f"Other details: {self.other_details}")
        return "\n".join(parts)


class ScreenResultItem(BaseModel):
    candidateName: str
    location: str
    skills: str
    resumeLink: str
    similarityScore: float
    llmScore: int
    recommendation: str


class ScreenResponse(BaseModel):
    jobId: str
    results: list[ScreenResultItem]


class JobStatusResponse(BaseModel):
    jobId: str
    status: str
    results: list[ScreenResultItem] = Field(default_factory=list)
