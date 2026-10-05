from typing import Any

from pydantic import BaseModel, Field


class VehicleAction(BaseModel):
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class AIResponse(BaseModel):
    reply: str
    actions: list[VehicleAction] = Field(default_factory=list)
    allowed: bool = True