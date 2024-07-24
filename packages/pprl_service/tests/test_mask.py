import copy
import datetime
import itertools
import re
import uuid
from typing import TypeVar, Callable

import pytest
from faker import Faker
from pprl_core import bits
from pprl_model import AttributeValueEntity, WeightedAttributeConfig, MaskConfig, StaticAttributeConfig, \
    EntityMaskRequest, FilterType, HashConfig, HashFunction, HashAlgorithm, DoubleHash, CLKFilter, EntityMaskResponse, \
    CLKRBFFilter, RBFFilter, BitVectorEntity, EnhancedDoubleHash, TripleHash, RandomHash, BalanceHardener, \
    XORFoldHardener, PermuteHardener, Rule90Hardener, RandomizedResponseHardener, RehashHardener, AnyHardener, \
    Hardener, AttributeSalt
from starlette import status
from starlette.testclient import TestClient

fake = Faker()
fake.seed_instance(727)


def _generate_person():
    return AttributeValueEntity(
        id=str(uuid.uuid4()),
        attributes={
            "firstName": fake.unique.first_name(),
            "lastName": fake.unique.last_name(),
            "dateOfBirth": fake.unique.date_of_birth(tzinfo=datetime.timezone.utc, minimum_age=18, maximum_age=120)
            .strftime("%Y-%m-%d"),
            "gender": fake.random_element(["m", "f"])
        }
    )


_entities = [_generate_person() for _ in range(100)]

_weighted_attributes = [
    WeightedAttributeConfig(
        attribute_name="firstName",
        weight=4,
        average_token_count=10,
    ),
    WeightedAttributeConfig(
        attribute_name="lastName",
        weight=4,
        average_token_count=8,
    ),
    WeightedAttributeConfig(
        attribute_name="gender",
        weight=1,
        average_token_count=2,
    ),
    WeightedAttributeConfig(
        attribute_name="dateOfBirth",
        weight=3,
        average_token_count=10,
    ),
]

_T = TypeVar("_T")


def _stack(*values: _T, depth=2, include_fn: Callable[[list[_T]], bool] | None = None) -> list[list[_T]]:
    def _always_include(_x: list[_T]) -> bool:
        return True

    if include_fn is None:
        include_fn = _always_include

    stacked_values = [[v] for v in values]

    for i in range(2, depth + 1):
        stacked_values += [list(tpl) for tpl in itertools.product(values, repeat=i)]

    return [s for s in stacked_values if include_fn(s)]


def _assert_matching_entity_ids(mask_req: EntityMaskRequest, mask_resp: EntityMaskResponse):
    orig_ids = set([e.id for e in mask_req.entities])
    resp_ids = set([e.id for e in mask_resp.entities])

    assert orig_ids == resp_ids


def _assert_bit_vectors_not_empty(mask_resp: EntityMaskResponse):
    bits_set = [bits.from_base64(e.value).any() for e in mask_resp.entities]
    assert all(bits_set)


def _construct_request_for(
        mask_config: MaskConfig,
        attributes: list[WeightedAttributeConfig] | list[StaticAttributeConfig] | None = None
) -> EntityMaskRequest:
    if attributes is None:
        if mask_config.filter.type != FilterType.clk:
            attributes = _weighted_attributes
        else:
            attributes = []

    return EntityMaskRequest(config=mask_config, entities=_entities, attributes=attributes)


def _retrieve_bit_vectors_from_request(test_client: TestClient, mask_req: EntityMaskRequest):
    r = test_client.post("/mask", json=mask_req.model_dump())
    assert r.status_code == status.HTTP_200_OK

    mask_resp = EntityMaskResponse(**r.json())

    _assert_matching_entity_ids(mask_req, mask_resp)
    _assert_bit_vectors_not_empty(mask_resp)

    return mask_resp.entities


def _assert_bit_vectors_unique_across_requests(test_client: TestClient, mask_reqs: list[EntityMaskRequest]):
    bit_vectors: list[BitVectorEntity] = []

    for mask_req in mask_reqs:
        bit_vectors += _retrieve_bit_vectors_from_request(test_client, mask_req)

    unique_values = set([e.value for e in bit_vectors])
    assert len(bit_vectors) == len(unique_values)


@pytest.mark.parametrize("filter_type", [
    CLKFilter(filter_size=2 ** 10, hash_values=5),
    RBFFilter(hash_values=5, seed=727),
    CLKRBFFilter(hash_values=5)
], ids=["clk", "rbf", "clkrbf"])
def test_mask_filter_types(test_client, filter_type):
    _ = _retrieve_bit_vectors_from_request(test_client, _construct_request_for(
        MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_"
        )
    ))


@pytest.mark.parametrize(
    "filter_type,token_sizes",
    [
        (CLKFilter(filter_size=2 ** 10, hash_values=5), (2, 3, 4)),
        (RBFFilter(hash_values=5, seed=727), (2, 3, 4)),
        (CLKRBFFilter(hash_values=5), (2, 3, 4)),
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_token_size(test_client, filter_type, token_sizes):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=q,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_"
        )) for q in token_sizes
    ])


@pytest.mark.parametrize(
    "filter_type,padding_chars",
    [
        (CLKFilter(filter_size=2 ** 10, hash_values=5), ("_", "#")),
        (RBFFilter(hash_values=5, seed=727), ("_", "#")),
        (CLKRBFFilter(hash_values=5), ("_", "#")),
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_padding(test_client, filter_type, padding_chars):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding=padding
        )) for padding in padding_chars
    ])


_hash_strategies = [DoubleHash(), EnhancedDoubleHash(), TripleHash(), RandomHash()]


@pytest.mark.parametrize(
    "filter_type,hash_strategies",
    [
        (CLKFilter(filter_size=2 ** 10, hash_values=5), _hash_strategies),
        (RBFFilter(hash_values=5, seed=727), _hash_strategies),
        (CLKRBFFilter(hash_values=5), _hash_strategies),
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_hash_strategies(test_client, filter_type, hash_strategies):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=hash_strategy
            ),
            filter=filter_type,
            padding="_"
        )) for hash_strategy in hash_strategies
    ])


def test_different_vectors_for_clk_with_different_filter_sizes(test_client):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=CLKFilter(filter_size=m, hash_values=5),
            padding="_"
        )) for m in (2 ** 10, 2 ** 11, 2 ** 12)
    ])


@pytest.mark.parametrize(
    "filter_types",
    [
        [CLKFilter(filter_size=2 ** 10, hash_values=5), CLKFilter(filter_size=2 ** 10, hash_values=3)],
        [RBFFilter(hash_values=5, seed=727), RBFFilter(hash_values=3, seed=727)],
        [CLKRBFFilter(hash_values=5), CLKRBFFilter(hash_values=3)]
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_hash_values(test_client, filter_types):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_"
        )) for filter_type in filter_types
    ])


@pytest.mark.parametrize(
    "filter_type",
    [
        CLKFilter(filter_size=2 ** 10, hash_values=5),
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_prepend_attribute_names_on_and_off(test_client, filter_type):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            prepend_attribute_name=p,
            padding="_"
        )) for p in (True, False)
    ])


def test_different_vectors_for_rbf_with_different_seeds(test_client):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=RBFFilter(hash_values=5, seed=seed),
            padding="_"
        )) for seed in (727, 727 * 2, 727 * 3)
    ])


_hash_algorithms = _stack(
    HashAlgorithm.md5, HashAlgorithm.sha1, HashAlgorithm.sha256, HashAlgorithm.sha512,
    depth=3
)


@pytest.mark.parametrize(
    "filter_type,hash_algorithms",
    [
        (CLKFilter(filter_size=2 ** 10, hash_values=5), _hash_algorithms),
        (RBFFilter(hash_values=5, seed=727), _hash_algorithms),
        (CLKRBFFilter(hash_values=5), _hash_algorithms),
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_hash_algorithms(test_client, filter_type, hash_algorithms):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=hash_algorithm_lst),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_"
        )) for hash_algorithm_lst in hash_algorithms
    ])


def _filter_hardeners(hardeners: list[AnyHardener]) -> bool:
    if len(hardeners) == 1:
        return True

    # sanity check
    assert len(hardeners) == 2
    h0, h1 = hardeners

    # rand_resp -> rand_resp will yield the same result as a single rand_resp
    if h0.name == h1.name == Hardener.randomized_response:
        return False

    # balance -> xor causes all bits to be set
    if h0.name == Hardener.balance and h1.name == Hardener.xor_fold:
        return False

    # xor -> rule_90 has the same result as rule_90 -> xor
    if h0.name == Hardener.xor_fold and h1.name == Hardener.rule_90:
        return False

    return True


_hardeners = _stack(
    BalanceHardener(), XORFoldHardener(), PermuteHardener(seed=727), Rule90Hardener(),
    RandomizedResponseHardener(probability=.5, seed=727), RehashHardener(window_size=8, window_step=8, samples=3),
    depth=2,
    include_fn=_filter_hardeners
)


@pytest.mark.parametrize(
    "filter_type,hardeners",
    [
        (CLKFilter(filter_size=2 ** 10, hash_values=5), _hardeners),
        (RBFFilter(hash_values=5, seed=727), _hardeners),
        (CLKRBFFilter(hash_values=5), _hardeners),
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_hardeners(test_client, filter_type, hardeners):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_",
            hardeners=hardener_lst
        )) for hardener_lst in hardeners
    ])


@pytest.mark.parametrize(
    "filter_type",
    [
        CLKFilter(filter_size=2 ** 10, hash_values=5),
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_randomized_response_seeds(test_client, filter_type):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_",
            hardeners=[RandomizedResponseHardener(seed=seed, probability=.5)],
        )) for seed in (727, 727 * 2, 727 * 3)
    ])


@pytest.mark.parametrize(
    "filter_type",
    [
        CLKFilter(filter_size=2 ** 10, hash_values=5),
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_randomized_response_probabilities(test_client, filter_type):
    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_",
            hardeners=[RandomizedResponseHardener(seed=727, probability=probability)],
        )) for probability in (.25, .5, .75)
    ])


@pytest.mark.parametrize(
    "filter_type",
    [
        CLKFilter(filter_size=2 ** 10, hash_values=5),
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_different_vectors_with_different_rehash_parameters(test_client, filter_type):
    rehash_params = [
        (8, 8, 3),
        (16, 8, 3),
        (8, 16, 3),
        (8, 8, 5)
    ]

    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=filter_type,
            padding="_",
            hardeners=[RehashHardener(window_size=rehash_args[0], window_step=rehash_args[1], samples=rehash_args[2])],
        )) for rehash_args in rehash_params
    ])


def test_different_vectors_for_clk_with_different_salts(test_client):
    attr_confs = [
        StaticAttributeConfig(
            attribute_name="firstName",
            salt=AttributeSalt(value="foo")
        ),
        StaticAttributeConfig(
            attribute_name="lastName",
            salt=AttributeSalt(value="foo")
        ),
        StaticAttributeConfig(
            attribute_name="firstName",
            salt=AttributeSalt(attribute="dateOfBirth")
        ),
        StaticAttributeConfig(
            attribute_name="lastName",
            salt=AttributeSalt(attribute="dateOfBirth")
        )
    ]

    _assert_bit_vectors_unique_across_requests(test_client, [
        _construct_request_for(MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                strategy=DoubleHash()
            ),
            filter=CLKFilter(filter_size=2 ** 10, hash_values=5),
            padding="_",
        ), [attr_conf]) for attr_conf in attr_confs
    ])


@pytest.mark.parametrize(
    "filter_type,attribute_salts",
    [
        (RBFFilter(hash_values=5, seed=727), [AttributeSalt(value="foo"), AttributeSalt(attribute="dateOfBirth")]),
        (CLKRBFFilter(hash_values=5), [AttributeSalt(value="foo"), AttributeSalt(attribute="dateOfBirth")]),
    ],
    ids=["rbf", "clkrbf"]
)
def test_different_vectors_for_rbf_and_clkrbf_with_different_salts(test_client, filter_type, attribute_salts):
    def _patch_weighted_attribute_configs_with_salt(attribute_salt: AttributeSalt):
        attr_confs_list: list[list[WeightedAttributeConfig]] = []

        for i, _ in enumerate(_weighted_attributes):
            attr_confs = copy.deepcopy(_weighted_attributes)
            attr_confs[i].salt = attribute_salt
            attr_confs_list.append(attr_confs)

        return attr_confs_list

    for attr_salt in attribute_salts:
        _assert_bit_vectors_unique_across_requests(test_client, [
            _construct_request_for(MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                    strategy=DoubleHash()
                ),
                filter=filter_type,
                padding="_",
            ), attr_confs) for attr_confs in _patch_weighted_attribute_configs_with_salt(attr_salt)
        ])


@pytest.mark.parametrize(
    "filter_type",
    [
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["rbf", "clkrbf"]
)
def test_different_vectors_for_rbf_and_clkrbf_with_different_weights(test_client, filter_type):
    def _patch_weighted_attribute_configs_with_weight(weight_factor: float):
        attr_confs_list: list[list[WeightedAttributeConfig]] = []

        for i, _ in enumerate(_weighted_attributes):
            attr_confs = copy.deepcopy(_weighted_attributes)
            attr_confs[i].weight *= weight_factor
            attr_confs_list.append(attr_confs)

        return attr_confs_list

    for factor in (.5, 2):
        _assert_bit_vectors_unique_across_requests(test_client, [
            _construct_request_for(MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                    strategy=DoubleHash()
                ),
                filter=filter_type,
                padding="_",
            ), attr_confs) for attr_confs in _patch_weighted_attribute_configs_with_weight(factor)
        ])


@pytest.mark.parametrize(
    "filter_type",
    [
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["rbf", "clkrbf"]
)
def test_different_vectors_for_rbf_and_clkrbf_with_different_average_token_counts(test_client, filter_type):
    def _patch_weighted_attribute_configs_with_average_token_count(token_factor: float):
        attr_confs_list: list[list[WeightedAttributeConfig]] = []

        for i, _ in enumerate(_weighted_attributes):
            attr_confs = copy.deepcopy(_weighted_attributes)
            attr_confs[i].average_token_count *= token_factor
            attr_confs_list.append(attr_confs)

        return attr_confs_list

    for factor in (.5, 2):
        _assert_bit_vectors_unique_across_requests(test_client, [
            _construct_request_for(MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha1]),
                    strategy=DoubleHash()
                ),
                filter=filter_type,
                padding="_",
            ), attr_confs) for attr_confs in _patch_weighted_attribute_configs_with_average_token_count(factor)
        ])


# see https://github.com/ul-mds/pprl/issues/1
# when an entity has an attribute value whose length is below the specified token size and no padding is specified,
# then no tokens are inserted. this should raise a 400 at minimum.
@pytest.mark.parametrize(
    "filter_type",
    [
        CLKFilter(filter_size=512, hash_values=5),
        RBFFilter(hash_values=5, seed=727),
        CLKRBFFilter(hash_values=5)
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_clk_with_empty_string_and_no_padding(test_client, filter_type):
    req = _construct_request_for(MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(
                algorithms=[HashAlgorithm.sha1],
                key="s3cr3t"
            ),
            strategy=RandomHash()
        ),
        filter=filter_type
    ))

    r = test_client.post("/mask", json=req.model_dump())

    error_regex = (r"value for `gender` on entity with ID `[0-9a-f-]+` did not produce any tokens - decrease the "
                   r"token size or add sufficient padding")

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert re.match(error_regex, str(r.json()["detail"])) is not None
