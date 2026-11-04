"""Helpers shared by the route modules."""

from typing import Any, TypeVar

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db import Base

RowT = TypeVar("RowT", bound=Base)
ModelT = TypeVar("ModelT", bound=BaseModel)


def get_or_404(session: Session, model: type[RowT], row_id: Any, name: str) -> RowT:
    row = session.get(model, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return row


def validate_or_422(model: type[ModelT], data: dict[str, Any]) -> ModelT:
    """Validate data assembled in a route (not the raw body) with the same 422 shape."""
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
