from enum import Enum

from pydantic import confloat, Field

from pprl_model.common import ParentModel, BitVectorEntity


class SimilarityMeasure(str, Enum):
    dice = "dice"
    cosine = "cosine"
    jaccard = "jaccard"


class MatchConfig(ParentModel):
    measure: SimilarityMeasure
    threshold: confloat(ge=0, le=1)


class MatchRequest(ParentModel):
    config: MatchConfig
    domain: list[BitVectorEntity] = Field(min_length=1)
    range: list[BitVectorEntity] = Field(min_length=1)


class Match(ParentModel):
    domain: BitVectorEntity
    range: BitVectorEntity
    similarity: float


class MatchResponse(ParentModel):
    config: MatchConfig
    matches: list[Match]
