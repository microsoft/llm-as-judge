"""
A package that manages the response bodies.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_301_MOVED_PERMANENTLY,
    HTTP_302_FOUND,
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_418_IM_A_TEAPOT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)


@dataclass
class SuccessMessage:
    """
    The base message body for HTTP responses
    """

    title: Optional[str]
    message: Optional[str]
    content: Optional[Union[Dict[str, Union[str, List]], List[Dict[str, Union[str, List]]]]]


@dataclass
class ErrorMessage:
    """
    The base message body for HTTP responses
    """

    success: bool
    type: Optional[str]
    title: Optional[str]
    detail: Optional[Union[Dict[str, Union[str, List]], List[Dict[str, Union[str, List]]]]]


RESPONSES = {
    HTTP_200_OK: {"model": SuccessMessage},
    HTTP_201_CREATED: {"model": SuccessMessage},
    HTTP_202_ACCEPTED: {"model": SuccessMessage},
    HTTP_302_FOUND: {"model": SuccessMessage},
    HTTP_301_MOVED_PERMANENTLY: {"model": ErrorMessage},
    HTTP_307_TEMPORARY_REDIRECT: {"model": ErrorMessage},
    HTTP_400_BAD_REQUEST: {"model": ErrorMessage},
    HTTP_401_UNAUTHORIZED: {"model": ErrorMessage},
    HTTP_403_FORBIDDEN: {"model": ErrorMessage},
    HTTP_418_IM_A_TEAPOT: {"model": ErrorMessage},
    HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorMessage},
}
