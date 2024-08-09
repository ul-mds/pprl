import binascii

import pprl_core
from bitarray import bitarray
from fastapi import APIRouter, HTTPException
from pprl_core.similarity import SimilarityFn
from pprl_model import SimilarityMeasure, VectorMatchRequest, VectorMatchResponse, Match
from starlette import status

router = APIRouter()

_similarity_mapping: dict[SimilarityMeasure, SimilarityFn] = {
    SimilarityMeasure.cosine: pprl_core.similarity.cosine,
    SimilarityMeasure.dice: pprl_core.similarity.dice,
    SimilarityMeasure.jaccard: pprl_core.similarity.jaccard,
}


def _construct_bitarray_lookup_dict(match_req: VectorMatchRequest) -> dict[str, bitarray]:
    bitarray_lookup_dict: dict[str, bitarray] = {}
    failed_b64decode_entity_ids: set[str] = set()

    for bitarray_entity in match_req.domain + match_req.range:
        try:
            bitarray_lookup_dict[bitarray_entity.value] = pprl_core.bits.from_base64(bitarray_entity.value)
        except (ValueError, binascii.Error):
            # from_base64 will throw a ValueError if invalid b64 is found
            failed_b64decode_entity_ids.add(bitarray_entity.id)

    if len(failed_b64decode_entity_ids) != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid Base64 encoded bit vectors on entities with IDs {', '.join(failed_b64decode_entity_ids)}"
        )

    return bitarray_lookup_dict


@router.post("/")
async def perform_matching(match_req: VectorMatchRequest) -> VectorMatchResponse:
    sim_measure = match_req.config.measure
    sim_fn = _similarity_mapping.get(sim_measure)

    if sim_fn is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented similarity measure `{sim_measure.name}`"
        )

    bitarray_lookup = _construct_bitarray_lookup_dict(match_req)
    matches: list[Match] = []

    for domain_entity in match_req.domain:
        for range_entity in match_req.range:
            domain_ba = bitarray_lookup[domain_entity.value]
            range_ba = bitarray_lookup[range_entity.value]

            similarity = sim_fn(domain_ba, range_ba)

            if similarity >= match_req.config.threshold:
                matches.append(Match(
                    domain=domain_entity,
                    range=range_entity,
                    similarity=similarity,
                ))

    return VectorMatchResponse(
        config=match_req.config,
        matches=matches,
    )
