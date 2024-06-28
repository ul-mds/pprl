from typing import Literal

from pydantic import BaseModel, ConfigDict


class ParentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttributeValueEntity(ParentModel):
    id: str
    attributes: dict[str, str]


class BitVectorEntity(ParentModel):
    id: str
    value: str


class HealthResponse(ParentModel):
    status: Literal["ok"] = "ok"
