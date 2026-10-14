from typing import List

from pydantic import BaseModel, Field


class IncidentAnalysis(BaseModel):
    severity: str
    summary: str
    root_cause: str
    possible_causes: List[str]
    recommended_actions: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
