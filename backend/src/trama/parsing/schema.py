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
