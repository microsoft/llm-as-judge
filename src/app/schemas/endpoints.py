"""
This module contains the Pydantic models for the endpoints of the mailing service.
"""

from typing import Literal

from pydantic import BaseModel


class JudgeEvaluation(BaseModel):
    id: str
    prompt: str
    method: Literal["assembly", "super"]
