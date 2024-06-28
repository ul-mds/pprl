from pprl_model import MatchConfig, SimilarityMeasure, MatchRequest, MatchResponse, Match
from starlette import status


def test_match(test_client, bit_vector_entity_factory):
    exact_match_entity = bit_vector_entity_factory()
    config = MatchConfig(
        measure=SimilarityMeasure.jaccard,
        threshold=1,
    )
    match_request = MatchRequest(
        config=config,
        domain=[exact_match_entity, bit_vector_entity_factory()],
        range=[exact_match_entity, bit_vector_entity_factory()],
    )

    r = test_client.post("/match", json=match_request.model_dump())
    assert r.status_code == status.HTTP_200_OK

    match_response = MatchResponse(**r.json())

    assert match_response.config == config
    assert match_response.matches == [
        Match(
            domain=exact_match_entity,
            range=exact_match_entity,
            similarity=1
        )
    ]


def test_match_404_on_invalid_base64(test_client, bit_vector_entity_factory):
    valid_entity, invalid_entity = bit_vector_entity_factory(), bit_vector_entity_factory()
    invalid_entity.value = "=A="  # invalid character for b64

    match_request = MatchRequest(
        config=MatchConfig(
            measure=SimilarityMeasure.jaccard,
            threshold=1,
        ),
        domain=[valid_entity],
        range=[invalid_entity],
    )

    r = test_client.post("/match", json=match_request.model_dump())
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert r.json()["detail"] == f"invalid Base64 encoded bit vectors on entities with IDs {invalid_entity.id}"
