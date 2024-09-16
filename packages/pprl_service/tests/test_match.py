from pprl_model import MatchConfig, SimilarityMeasure, VectorMatchRequest, VectorMatchResponse, Match, \
    MatchMethod
from starlette import status


def test_match_crosswise(test_client, bit_vector_entity_factory):
    exact_match_entity = bit_vector_entity_factory()
    config = MatchConfig(
        measure=SimilarityMeasure.jaccard,
        threshold=1,
        method=MatchMethod.crosswise,
    )
    match_request = VectorMatchRequest(
        config=config,
        domain=[exact_match_entity, bit_vector_entity_factory()],
        range=[exact_match_entity, bit_vector_entity_factory()],
    )

    r = test_client.post("/match", json=match_request.model_dump())
    assert r.status_code == status.HTTP_200_OK

    match_response = VectorMatchResponse(**r.json())

    assert match_response.config == config
    assert match_response.matches == [
        Match(
            domain=exact_match_entity,
            range=exact_match_entity,
            similarity=1
        )
    ]


def test_match_pairwise(test_client, bit_vector_entity_factory):
    exact_match_entity = bit_vector_entity_factory()
    config = MatchConfig(
        measure=SimilarityMeasure.jaccard,
        threshold=1,
        method=MatchMethod.pairwise,
    )
    match_request = VectorMatchRequest(
        config=config,
        domain=[exact_match_entity, bit_vector_entity_factory()],
        range=[exact_match_entity, bit_vector_entity_factory()],
    )

    r = test_client.post("/match", json=match_request.model_dump())
    assert r.status_code == status.HTTP_200_OK

    match_response = VectorMatchResponse(**r.json())

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

    match_request = VectorMatchRequest(
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


def test_match_404_on_pairwise_unmatched_list_lengths(test_client, bit_vector_entity_factory):
    match_request = VectorMatchRequest(
        config=MatchConfig(
            measure=SimilarityMeasure.jaccard,
            threshold=1,
            method=MatchMethod.pairwise,
        ),
        domain=[bit_vector_entity_factory()] * 2,
        range=[bit_vector_entity_factory()] * 1,
    )

    r = test_client.post("/match", json=match_request.model_dump())
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert r.json()["detail"] == ("length of domain and range lists do not match: domain has length of 2, "
                                  "range has length of 1")
