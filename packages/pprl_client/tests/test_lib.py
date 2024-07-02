from faker import Faker
from pprl_model import MatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity, AttributeValueEntity, \
    EntityTransformRequest, EntityTransformConfig, EmptyValueHandling, GlobalTransformerConfig, \
    NormalizationTransformer, EntityMaskRequest, MaskConfig, HashConfig, HashFunction, RandomHash, HashAlgorithm, \
    CLKFilter

import pprl_client


def _generate_person(person_id: str, faker: Faker):
    return AttributeValueEntity(
        id=person_id,
        attributes={
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "date_of_birth": faker.date_of_birth(minimum_age=18, maximum_age=120).strftime("%Y-%m-%d"),
            "gender": faker.random_element(["male", "female"])
        }
    )


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
    entities = [_generate_person(uuid4_factory(), faker) for _ in range(100)]

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
    entities = [_generate_person(uuid4_factory(), faker) for _ in range(100)]

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
