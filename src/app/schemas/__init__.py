"""
A package that holds response schemas and models.
"""

__all__ = [
    "RESPONSES",
    "ErrorMessage",
    "SuccessMessage",
    "Judge",
    "Assembly",
    "JudgeEvaluation",
    "database_schema",
]
__author__ = "AI GBBS"

from .endpoints import JudgeEvaluation
from .models import Assembly, Judge
from .responses import RESPONSES, ErrorMessage, SuccessMessage

database_schema = {
    "Judge Table": Judge.model_json_schema(),
    "Assembly Table": Assembly.model_json_schema(),
}
