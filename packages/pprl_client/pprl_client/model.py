from typing import Any

from pydantic import BaseModel, Field, conint


class FakerGeneratorSpec(BaseModel):
    function_name: str
    attribute_name: str
    args: dict[str, Any] = Field(default_factory=dict)


def _default_faker_locale():
    return ["en_US"]


class FakerGeneratorConfig(BaseModel):
    seed: int
    count: conint(ge=0)
    locale: list[str] = Field(default_factory=_default_faker_locale)
    generators: list[FakerGeneratorSpec]


class GeckoGeneratorSpec(BaseModel):
    attribute_names: list[str]
    function_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class GeckoGeneratorConfig(BaseModel):
    seed: int
    count: conint(ge=0)
    generators: list[GeckoGeneratorSpec]
