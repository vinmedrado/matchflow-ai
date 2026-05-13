from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class ErrorPayload(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[ErrorPayload] = None
