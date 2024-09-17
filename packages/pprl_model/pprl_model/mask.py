from enum import Enum
from typing import Literal, Union, Annotated

from pydantic import Field, conint, confloat, model_validator
from typing_extensions import Self

from pprl_model.common import ParentModel, BitVectorEntity, AttributeValueEntity


class HashStrategy(str, Enum):
    double_hash = "double_hash"
    triple_hash = "triple_hash"
    enhanced_double_hash = "enhanced_double_hash"
    random_hash = "random_hash"


class DoubleHash(ParentModel):
    name: Literal[HashStrategy.double_hash] = HashStrategy.double_hash


class TripleHash(ParentModel):
    name: Literal[HashStrategy.triple_hash] = HashStrategy.triple_hash


class EnhancedDoubleHash(ParentModel):
    name: Literal[HashStrategy.enhanced_double_hash] = HashStrategy.enhanced_double_hash


class RandomHash(ParentModel):
    name: Literal[HashStrategy.random_hash] = HashStrategy.random_hash


AnyHashStrategy = Union[DoubleHash, TripleHash, EnhancedDoubleHash, RandomHash]


class HashAlgorithm(str, Enum):
    md5 = "md5"
    sha1 = "sha1"
    sha256 = "sha256"
    sha512 = "sha512"


class HashFunction(ParentModel):
    algorithms: list[HashAlgorithm] = Field(min_length=1)
    key: str | None = None


class HashConfig(ParentModel):
    function: HashFunction
    strategy: AnyHashStrategy = Field(discriminator="name")


class FilterType(str, Enum):
    clk = "clk"
    rbf = "rbf"
    clkrbf = "clkrbf"


class CLKFilter(ParentModel):
    type: Literal[FilterType.clk] = FilterType.clk
    filter_size: conint(gt=0)
    hash_values: conint(gt=0)


class RBFFilter(ParentModel):
    type: Literal[FilterType.rbf] = FilterType.rbf
    hash_values: conint(gt=0)
    seed: int


class CLKRBFFilter(ParentModel):
    type: Literal[FilterType.clkrbf] = FilterType.clkrbf
    hash_values: conint(gt=0)


AnyFilter = Union[CLKFilter, RBFFilter, CLKRBFFilter]


class Hardener(str, Enum):
    balance = "balance"
    xor_fold = "xor_fold"
    permute = "permute"
    randomized_response = "randomized_response"
    rule_90 = "rule_90"
    rehash = "rehash"


class BalanceHardener(ParentModel):
    name: Literal[Hardener.balance] = Hardener.balance


class XORFoldHardener(ParentModel):
    name: Literal[Hardener.xor_fold] = Hardener.xor_fold


class PermuteHardener(ParentModel):
    name: Literal[Hardener.permute] = Hardener.permute
    seed: int


class RandomizedResponseHardener(ParentModel):
    name: Literal[Hardener.randomized_response] = Hardener.randomized_response
    probability: confloat(ge=0, le=1)
    seed: int


class Rule90Hardener(ParentModel):
    name: Literal[Hardener.rule_90] = Hardener.rule_90


class RehashHardener(ParentModel):
    name: Literal[Hardener.rehash] = Hardener.rehash
    window_size: conint(gt=0, le=32)
    window_step: conint(gt=0)
    samples: conint(gt=0)


AnyHardener = Union[
    BalanceHardener, PermuteHardener, RandomizedResponseHardener, XORFoldHardener, RehashHardener, Rule90Hardener,
]


class MaskConfig(ParentModel):
    token_size: conint(gt=1)
    hash: HashConfig
    prepend_attribute_name: Annotated[bool, Field(default=True)]
    filter: Annotated[AnyFilter, Field(discriminator="type")]
    padding: Annotated[str, Field(default="")]
    hardeners: Annotated[list[Annotated[AnyHardener, Field(..., discriminator="name")]], Field(default_factory=list)]


class AttributeSalt(ParentModel):
    value: str | None = None
    attribute: str | None = None

    @model_validator(mode="after")
    def validate_mutually_exclusive_attributes(self) -> Self:
        if self.value and self.attribute:
            raise ValueError("value and attribute cannot be set at the same time")

        if not self.value and not self.attribute:
            raise ValueError("neither value nor attribute is set")

        return self


class StaticAttributeConfig(ParentModel):
    attribute_name: str
    salt: AttributeSalt | None = Field(default=None)


class WeightedAttributeConfig(ParentModel):
    attribute_name: str
    salt: AttributeSalt | None = Field(default=None)
    weight: confloat(gt=0)
    average_token_count: confloat(gt=0)


class BaseMaskRequest(ParentModel):
    config: MaskConfig
    attributes: Annotated[list[WeightedAttributeConfig] | list[StaticAttributeConfig], Field(default_factory=list)]

    def with_entities(self, entities: list[AttributeValueEntity]) -> "EntityMaskRequest":
        return EntityMaskRequest(
            config=self.config,
            attributes=self.attributes,
            entities=entities,
        )


class EntityMaskRequest(BaseMaskRequest):
    entities: Annotated[list[AttributeValueEntity], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_attribute_type(self) -> Self:
        if self.config.filter.type == FilterType.clk:
            # if no attribute configs are specified, return early
            if len(self.attributes) == 0:
                return self

            # check that all supplied attribute configs are static
            if all([isinstance(a, StaticAttributeConfig) for a in self.attributes]):
                return self

            raise ValueError(f"`{self.config.filter.type.value}` filters require static attribute configurations, but "
                             f"weighted ones were found")
        else:
            if len(self.attributes) == 0:
                raise ValueError(f"`{self.config.filter.type.value}` filters require weighted attribute "
                                 f"configurations, but none were found")

            # check that all supplied attribute configs are weighted
            if all([isinstance(a, WeightedAttributeConfig) for a in self.attributes]):
                return self

            raise ValueError(f"`{self.config.filter.type.value}` filters require weighted attribute configurations, "
                             f"but static ones were found")

    def _check_attribute_not_present_on_entities(self, attr_name: str) -> list[AttributeValueEntity]:
        return [e for e in self.entities if attr_name not in e.attributes]

    @model_validator(mode="after")
    def validate_configured_attributes_present_on_entities(self) -> Self:
        # if no attributes are configured, we can skip this
        if len(self.attributes) == 0:
            return self

        attribute_name_to_non_present_entity_id_dict: dict[str, list[str]] = {}

        for attr_conf in self.attributes:
            attr_name = attr_conf.attribute_name
            non_present_entities = self._check_attribute_not_present_on_entities(attr_name)

            # if attribute is present on all entities, continue
            if len(non_present_entities) == 0:
                continue

            # otherwise add it to the dict
            attribute_name_to_non_present_entity_id_dict[attr_name] = [e.id for e in non_present_entities]

        # throw an error if there are any attributes with configurations that are not present on some entities
        if len(attribute_name_to_non_present_entity_id_dict) != 0:
            entity_str = ",".join([
                f"`{attr_name}` on entities with ID `{'`, `'.join(entity_ids)}`"
                for attr_name, entity_ids in attribute_name_to_non_present_entity_id_dict.items()
            ])

            raise ValueError(f"some configured attributes are not present on entities: {entity_str}")

        return self

    @model_validator(mode="after")
    def validate_attribute_salt_present_on_all_entities(self) -> Self:
        # if no attributes are configured, we can skip this
        if len(self.attributes) == 0:
            return self

        attribute_name_to_non_present_entity_id_dict: dict[str, list[str]] = {}

        for attr_conf in self.attributes:
            salt = attr_conf.salt

            # if no salt is configured, skip this step
            if salt is None or salt.attribute is None:
                continue

            # retrieve the attribute name
            attr_name = salt.attribute
            non_present_entities = self._check_attribute_not_present_on_entities(attr_name)

            # if attribute is present on all entities, continue
            if len(non_present_entities) == 0:
                continue

            # otherwise add it to the dict
            attribute_name_to_non_present_entity_id_dict[attr_name] = [e.id for e in non_present_entities]

        # throw an error if there are any attributes that are not present on some entities
        if len(attribute_name_to_non_present_entity_id_dict) != 0:
            entity_str = ",".join([
                f"`{attr_name}` on entities with ID `{'`, `'.join(entity_ids)}`"
                for attr_name, entity_ids in attribute_name_to_non_present_entity_id_dict.items()
            ])

            raise ValueError(f"some configured attribute salts are not present on entities: {entity_str}")

        return self


class EntityMaskResponse(ParentModel):
    config: MaskConfig
    entities: list[BitVectorEntity]
