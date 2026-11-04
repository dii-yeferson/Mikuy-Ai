"""Contratos del pipeline. La interpretación interna nunca se devuelve al cliente."""

from typing import Literal

from pydantic import Field

from .schemas import Strict


class FoodAmount(Strict):
    food: str = Field(max_length=100)
    quantity: float = Field(gt=0, le=100000, allow_inf_nan=False)
    unit: Literal["g", "kg", "ml", "l", "unid", "porcion"]
    preparation: str = Field(default="", max_length=60)
    evidence_span: str = Field(max_length=250)


class QueryIntent(Strict):
    topic: Literal["nutrition", "clinical", "cooking", "budget", "general"]
    rewritten_question: str = Field(min_length=2, max_length=2000)
    search_terms: list[str] = Field(default_factory=list, max_length=8)
    depth: Literal["brief", "detailed"] = "brief"
    needs_current: bool = False
    clarification: str = Field(default="", max_length=300)
    calculation: Literal["none", "nutrition", "budget", "arithmetic"] = "none"
    expression: str = Field(default="", max_length=150)
    amounts: list[FoodAmount] = Field(default_factory=list, max_length=10)


class SupportedClaim(Strict):
    statement: str = Field(max_length=600)
    source_id: str = Field(max_length=100)
    excerpt: str = Field(default="", max_length=1600)


class AnswerDraft(Strict):
    answer: str = Field(min_length=2, max_length=9000)
    sources: list[str] = Field(default_factory=list, max_length=8)
    evidence_level: Literal["cited", "general", "insufficient"] = "general"
    claims: list[SupportedClaim] = Field(default_factory=list, max_length=12)


class AnswerReview(Strict):
    accepted: bool
    issues: list[str] = Field(default_factory=list, max_length=8)
