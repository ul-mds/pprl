from enum import Enum
from typing import Annotated

from pydantic import confloat, Field

from pprl_model.common import ParentModel, BitVectorEntity


class MatchMethod(str, Enum):
    crosswise = "crosswise"
    pairwise = "pairwise"


class SimilarityMeasure(str, Enum):
    dice = "dice"
    cosine = "cosine"
    jaccard = "jaccard"


class MatchConfig(ParentModel):
    measure: SimilarityMeasure
    threshold: confloat(ge=0, le=1)
    method: MatchMethod = MatchMethod.crosswise


class BaseMatchRequest(ParentModel):
    config: MatchConfig

    def with_vectors(self, domain_lst: list[BitVectorEntity], range_lst: list[BitVectorEntity]) -> "VectorMatchRequest":
        return VectorMatchRequest(
            config=self.config,
            domain=domain_lst,
            range=range_lst,
        )


class VectorMatchRequest(BaseMatchRequest):
    domain: Annotated[list[BitVectorEntity], Field(min_length=1)]
    range: Annotated[list[BitVectorEntity], Field(min_length=1)]


class Match(ParentModel):
    domain: BitVectorEntity
    range: BitVectorEntity
    similarity: float


class VectorMatchResponse(ParentModel):
    config: MatchConfig
    matches: list[Match]
