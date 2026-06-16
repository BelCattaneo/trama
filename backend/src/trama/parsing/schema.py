from typing import Literal

from pydantic import BaseModel, ConfigDict


class ParseLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    product: str
    quantity: float
    unit: str | None = None
    raw_text: str | None = None
    page: int | None = None


class ParsePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    lines: list[ParseLine] = []
    warnings: list[str] = []
    supplier_cuit: str | None = None


class ConfirmLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    line_no: int | None
    product: str
    quantity: float
    unit: str | None
    raw_text: str | None
    page: int | None


CorrectionField = Literal["product", "quantity", "unit", "line_added", "line_removed"]


class ConfirmCorrection(BaseModel):
    model_config = ConfigDict(frozen=True)

    line_no: int | None
    field: CorrectionField
    original_value: str | None
    corrected_value: str | None
