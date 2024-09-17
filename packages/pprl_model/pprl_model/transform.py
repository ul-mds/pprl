from enum import Enum
from typing import Literal, Union, Annotated

from pydantic import Field, conint, model_validator
from typing_extensions import Self

from pprl_model.common import ParentModel, AttributeValueEntity


class EmptyValueHandling(str, Enum):
    ignore = "ignore"
    error = "error"
    skip = "skip"


class TransformConfig(ParentModel):
    empty_value: EmptyValueHandling


class Transformer(str, Enum):
    normalization = "normalization"
    date_time = "date_time"
    character_filter = "character_filter"
    mapping = "mapping"
    number = "number"
    phonetic_code = "phonetic_code"


class NormalizationTransformer(ParentModel):
    name: Literal[Transformer.normalization] = Transformer.normalization


class DateTimeTransformer(ParentModel):
    name: Literal[Transformer.date_time] = Transformer.date_time
    input_format: str
    output_format: str


class CharacterFilterTransformer(ParentModel):
    name: Literal[Transformer.character_filter] = Transformer.character_filter
    characters: str | None = None


class MappingTransformer(ParentModel):
    name: Literal[Transformer.mapping] = Transformer.mapping
    mapping: Annotated[dict[str, str], Field(min_length=1)]
    default_value: str | None = None
    inline: bool = False


class NumberTransformer(ParentModel):
    name: Literal[Transformer.number] = Transformer.number
    decimal_places: conint(ge=0)


class PhoneticCodeAlgorithm(str, Enum):
    soundex = "soundex"
    metaphone = "metaphone"
    refined_soundex = "refined_soundex"
    fuzzy_soundex = "fuzzy_soundex"
    cologne = "cologne"


class PhoneticCodeTransformer(ParentModel):
    name: Literal[Transformer.phonetic_code] = Transformer.phonetic_code
    algorithm: PhoneticCodeAlgorithm


AnyTransformer = Union[
    NormalizationTransformer, DateTimeTransformer, CharacterFilterTransformer, MappingTransformer,
    NumberTransformer, PhoneticCodeTransformer
]


class AttributeTransformerConfig(ParentModel):
    attribute_name: str
    transformers: Annotated[list[Annotated[AnyTransformer, Field(..., discriminator="name")]], Field(min_length=1)]


class GlobalTransformerConfig(ParentModel):
    before: Annotated[list[Annotated[AnyTransformer, Field(..., discriminator="name")]], Field(default_factory=list)]
    after: Annotated[list[Annotated[AnyTransformer, Field(..., discriminator="name")]], Field(default_factory=list)]


class BaseTransformRequest(ParentModel):
    config: TransformConfig
    attribute_transformers: Annotated[list[AttributeTransformerConfig], Field(default_factory=list)]
    global_transformers: Annotated[GlobalTransformerConfig, Field(default_factory=GlobalTransformerConfig)]

    @model_validator(mode="after")
    def validate_at_least_one_transformer(self) -> Self:
        if len(self.attribute_transformers) == 0 and (
                len(self.global_transformers.before) + len(self.global_transformers.after) == 0
        ):
            raise ValueError("attribute and global transformers are empty: must contain at least one")

        return self

    def with_entities(self, entities: list[AttributeValueEntity]) -> "EntityTransformRequest":
        return EntityTransformRequest(
            config=self.config,
            attribute_transformers=self.attribute_transformers,
            global_transformers=self.global_transformers,
            entities=entities,
        )


class EntityTransformRequest(BaseTransformRequest):
    entities: Annotated[list[AttributeValueEntity], Field(min_length=1)]


class EntityTransformResponse(ParentModel):
    config: TransformConfig
    entities: list[AttributeValueEntity]
