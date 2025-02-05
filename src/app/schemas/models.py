"""
This module defines the data models for the application using Pydantic.

Classes:
    Judge: Represents a Judge with an id, model, url, and metaprompt.
    Assemble: Represents an Assemble with an id, list of judges, and roles.
"""

import json
from typing import List

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Judge(BaseModel):
    """
    Represents a Judge with an id, model, url, and metaprompt.

    Attributes:
        id (str): The unique identifier for the judge.
        model (HttpUrl): The model name of the judge.
        metaprompt (str): The metaprompt for the judge.
    """

    id: str = Field(..., description="Judge ID")
    name: str = Field(..., description="Judge Name", max_length=16)
    model: HttpUrl = Field(..., description="Model URL")
    metaprompt: str = Field(..., description="Judge System Prompt", max_length=60)

    @field_validator("model")
    def model_must_be_azure_url(cls, v):
        if not v.startswith("https://"):
            raise ValueError("model must be a URL from Azure Open AI")
        return v

    @field_validator("metaprompt")
    def metaprompt_must_be_json_serializable(cls, v):
        try:
            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("metaprompt must be JSON serializable")
        if not ("text" in v and "json" in v):
            raise ValueError("metaprompt must contain the format (text, json)")
        return v


class Assembly(BaseModel):
    """
    Represents an Assemble with an id, list of judges, and roles.

    Attributes:
        id (int): The unique identifier for the assemble.
        judges (List[Judge]): A list of Judge objects.
        roles (List[str]): A list of roles.
    """

    id: str = Field(..., description="Judge Assembly ID")
    judges: List[Judge] = Field(..., description="Judges Assemblies")
    roles: List[str] = Field(..., description="Judge Roles ID")

    @field_validator("roles")
    def roles_must_not_exceed_length(cls, v):
        for role in v:
            if len(role) > 60:
                raise ValueError("each role must have at most 60 characters")
        return v
