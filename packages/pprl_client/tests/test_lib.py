from pprl_model import MatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity, EntityTransformRequest, \
    EntityTransformConfig, EmptyValueHandling, GlobalTransformerConfig, \
    NormalizationTransformer, EntityMaskRequest, MaskConfig, HashConfig, HashFunction, RandomHash, HashAlgorithm, \
    CLKFilter

import pprl_client
from tests.helpers import generate_person


def test_match(pprl_base_url, base64_factory, uuid4_factory):
    domain_vectors = [BitVectorEntity(
        id=uuid4_factory(),
        value=base64_factory(),
    ) for _ in range(10)]

    range_vectors = [BitVectorEntity(
        id=uuid4_factory(),
        value=base64_factory(),
    ) for _ in range(10)]

    r = pprl_client.match(MatchRequest(
        config=MatchConfig(
            measure=SimilarityMeasure.jaccard,
            threshold=0,
        ),
        domain=domain_vectors,
        range=range_vectors,
    ), base_url=pprl_base_url)

    assert len(r.matches) == len(domain_vectors) * len(range_vectors)


def test_transform(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]

    r = pprl_client.transform(EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.error),
        entities=entities,
        global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
    ), base_url=pprl_base_url)

    input_ids = [ent.id for ent in entities]
    output_ids = [ent.id for ent in r.entities]

    assert len(r.entities) == len(input_ids)
    assert all(input_id in output_ids for input_id in input_ids)


def test_mask(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]

    r = pprl_client.mask(EntityMaskRequest(
        config=MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(
                    algorithms=[HashAlgorithm.sha1],
                    key="s3cr3t_k3y"
                ),
                strategy=RandomHash()
            ),
            filter=CLKFilter(hash_values=5, filter_size=1024)
        ),
        entities=entities
    ), base_url=pprl_base_url)

    input_ids = [ent.id for ent in entities]
    output_ids = [ent.id for ent in r.entities]

    assert len(r.entities) == len(input_ids)
    assert all(input_id in output_ids for input_id in input_ids)
