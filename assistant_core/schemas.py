from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1)
    kind: Literal["explicit", "inferred"]
    evidence_quote: str = Field(description="Exact quote from the job supporting this item")


class JobAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    requirements: list[Requirement]
    tasks: list[str]
    missing_information: list[str]
    budget: str | None
    deadline: str | None


def validate_analysis(raw: str, job_text: str) -> JobAnalysis:
    analysis = JobAnalysis.model_validate_json(raw)
    for requirement in analysis.requirements:
        quote = requirement.evidence_quote.strip()
        if not quote or quote not in job_text:
            raise ValueError("A requirement has a missing or untraceable evidence quote.")
    return analysis
