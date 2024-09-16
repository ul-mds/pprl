from pprl_model import VectorMatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity, EntityTransformRequest, \
    TransformConfig, EmptyValueHandling, GlobalTransformerConfig, \
    NormalizationTransformer, EntityMaskRequest, MaskConfig, HashConfig, HashFunction, RandomHash, HashAlgorithm, \
    CLKFilter, BaseTransformRequest, AttributeTransformerConfig, DateTimeTransformer, MatchMethod

import pprl_client
from pprl_client.lib import AttributeStats
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

    r = pprl_client.match(VectorMatchRequest(
        config=MatchConfig(
            measure=SimilarityMeasure.jaccard,
            threshold=0,
            method=MatchMethod.crosswise,
        ),
        domain=domain_vectors,
        range=range_vectors,
    ), base_url=pprl_base_url)

    assert len(r.matches) == len(domain_vectors) * len(range_vectors)


def test_transform(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]

    r = pprl_client.transform(EntityTransformRequest(
        config=TransformConfig(empty_value=EmptyValueHandling.error),
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


def test_split_into_wordlist(uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(10)]
    entity_0 = entities[0]

    attribute_name_to_wordlist_dict = pprl_client.lib.split_into_wordlist(entities)

    # check that all attribute names are present as keys
    assert set(attribute_name_to_wordlist_dict.keys()) == set(entity_0.attributes.keys())
    # check that each attribute name has values from all entities assigned to them
    assert all(
        [set(v) == set([e.attributes[k] for e in entities]) for k, v in attribute_name_to_wordlist_dict.items()]
    )


def test_tokenize_wordlist():
    expected = [
        {"_f", "fo", "oo", "ob", "ba", "ar", "r_"},
        {"_f", "fo", "oo", "ob", "ba", "az", "z_"},
    ]

    assert expected == pprl_client.lib.tokenize_wordlist(["foobar", "foobaz"], token_size=2, padding="_")


def test_compute_average_tokens_for_token_list():
    token_list = [set("012345"), set("012"), set("012345678")]
    expected = sum(len(x) for x in token_list) / len(token_list)

    assert expected == pprl_client.lib.compute_average_tokens_for_token_list(token_list)


def test_count_tokens_in_token_list():
    token_list = [
        {"_f", "fo", "oo", "ob", "ba", "ar", "r_"},
        {"_f", "fo", "oo", "ob", "ba", "az", "z_"},
    ]

    expected = {
        "_f": 2,
        "fo": 2,
        "oo": 2,
        "ob": 2,
        "ba": 2,
        "ar": 1,
        "az": 1,
        "r_": 1,
        "z_": 1
    }

    assert expected == pprl_client.lib.count_tokens_in_token_list(token_list)


def test_compute_attribute_stats(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]
    entity_0 = entities[0]

    attribute_name_to_attribute_stats_dict = pprl_client.lib.compute_attribute_stats(
        entities,
        BaseTransformRequest(
            config=TransformConfig(empty_value=EmptyValueHandling.skip),
            global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
        ),
        base_url=pprl_base_url
    )

    assert set(entity_0.attributes.keys()) == set(attribute_name_to_attribute_stats_dict.keys())
    assert all(v.ngram_entropy > 0 and v.average_tokens > 0 for v in attribute_name_to_attribute_stats_dict.values())


def _is_attribute_stat_pair_equal(d0: dict[str, AttributeStats], d1: dict[str, AttributeStats]):
    assert set(d0.keys()) == set(d1.keys())

    def _float_equals(f0: float, f1: float, epsilon: float = 0.000001) -> bool:
        return abs(f0 - f1) < epsilon

    for k, v0 in d0.items():
        v1 = d1[k]

        if not _float_equals(v0.average_tokens, v1.average_tokens):
            return False

        if not _float_equals(v0.ngram_entropy, v1.ngram_entropy):
            return False

    return True


def test_compute_attribute_stats_with_different_padding(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]
    computed_attribute_stats: list[dict[str, AttributeStats]] = []

    # choice of padding SHOULD NOT affect the generated weights
    for padding in ("_", "#"):
        computed_attribute_stats.append(pprl_client.lib.compute_attribute_stats(
            entities,
            BaseTransformRequest(
                config=TransformConfig(empty_value=EmptyValueHandling.skip),
                global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
            ),
            base_url=pprl_base_url,
            padding=padding
        ))

    d0, d1 = computed_attribute_stats
    assert _is_attribute_stat_pair_equal(d0, d1)


def test_compute_attribute_stats_with_different_token_sizes(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]
    computed_attribute_stats: list[dict[str, AttributeStats]] = []

    # choice of token size SHOULD affect the generated weights
    for token_size in (2, 3):
        computed_attribute_stats.append(pprl_client.lib.compute_attribute_stats(
            entities,
            BaseTransformRequest(
                config=TransformConfig(empty_value=EmptyValueHandling.skip),
                global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
            ),
            base_url=pprl_base_url,
            token_size=token_size
        ))

    d0, d1 = computed_attribute_stats
    assert not _is_attribute_stat_pair_equal(d0, d1)


def test_compute_attribute_stats_with_different_transform_config(pprl_base_url, uuid4_factory, faker):
    entities = [generate_person(uuid4_factory(), faker) for _ in range(100)]
    base_requests = [
        BaseTransformRequest(
            config=TransformConfig(empty_value=EmptyValueHandling.skip),
            global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
        ),
        BaseTransformRequest(
            config=TransformConfig(empty_value=EmptyValueHandling.skip),
            attribute_transformers=[
                AttributeTransformerConfig(
                    attribute_name="date_of_birth",
                    transformers=[
                        DateTimeTransformer(
                            input_format="%Y-%m-%d",
                            output_format="%d.%m.%Y"
                        )
                    ]
                )
            ]
        ),
    ]
    computed_attribute_stats: list[dict[str, AttributeStats]] = []

    # choice of token size SHOULD affect the generated weights
    for transform_base in base_requests:
        computed_attribute_stats.append(pprl_client.lib.compute_attribute_stats(
            entities,
            transform_base,
            base_url=pprl_base_url
        ))

    d0, d1 = computed_attribute_stats
    assert not _is_attribute_stat_pair_equal(d0, d1)
