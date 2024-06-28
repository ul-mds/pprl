import hashlib
import hmac
import math
import random
from typing import TypeVar, Callable

from bitarray import bitarray
from fastapi import APIRouter, HTTPException
from pprl_core import harden, bits, common
from pprl_model import AttributeValueEntity, HashAlgorithm, HashFunction, MaskConfig, BalanceHardener, \
    XORFoldHardener, PermuteHardener, RandomizedResponseHardener, Rule90Hardener, RehashHardener, Hardener, \
    StaticAttributeConfig, WeightedAttributeConfig, AnyHashStrategy, HashStrategy, EntityMaskRequest, \
    EntityMaskResponse, BitVectorEntity, FilterType
from pydantic import BaseModel
from starlette import status

router = APIRouter()

HashFn = Callable[[bytes], bytes]
HmacFn = Callable[[bytes, bytes], bytes]

_alg_to_hash_dict: dict[HashAlgorithm, HashFn] = {
    HashAlgorithm.md5: lambda b: hashlib.md5(b).digest(),
    HashAlgorithm.sha1: lambda b: hashlib.sha1(b).digest(),
    HashAlgorithm.sha256: lambda b: hashlib.sha256(b).digest(),
    HashAlgorithm.sha512: lambda b: hashlib.sha512(b).digest()
}

_alg_to_hmac_dict: dict[HashAlgorithm, HmacFn] = {
    HashAlgorithm.md5: lambda key, b: hmac.digest(key, b, hashlib.md5),
    HashAlgorithm.sha1: lambda key, b: hmac.digest(key, b, hashlib.sha1),
    HashAlgorithm.sha256: lambda key, b: hmac.digest(key, b, hashlib.sha256),
    HashAlgorithm.sha512: lambda key, b: hmac.digest(key, b, hashlib.sha512),
}


def _resolve_hash_function(hash_fn: HashFunction) -> HashFn:
    hash_fn_chain = [_alg_to_hash_dict.get(alg) for alg in hash_fn.algorithms]

    if any([fn is None for fn in hash_fn_chain]):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented hash function in `{'`, `'.join(hash_fn.algorithms)}`"
        )

    def _hash(b: bytes):
        digest = b

        for fn in hash_fn_chain:
            digest = fn(digest)

        return digest

    return _hash


def _resolve_hmac_function(hash_fn: HashFunction) -> HashFn:
    hmac_key = hash_fn.key.encode()
    hmac_fn_chain = [_alg_to_hmac_dict.get(alg) for alg in hash_fn.algorithms]

    if any([fn is None for fn in hmac_fn_chain]):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented hmac function in `{'`, `'.join(hash_fn.algorithms)}`"
        )

    def _hash_hmac(b: bytes):
        digest = b

        for fn in hmac_fn_chain:
            digest = fn(hmac_key, digest)

        return digest

    return _hash_hmac


def _resolve_hash_function_config(config: MaskConfig) -> HashFn:
    hash_fn = config.hash.function

    if hash_fn.key is None:
        return _resolve_hash_function(hash_fn)
    else:
        return _resolve_hmac_function(hash_fn)


_M = TypeVar("_M", bound=BaseModel)


def _new_balance_hardener(_h: BalanceHardener):
    return harden.balance()


def _new_xor_fold_hardener(_h: XORFoldHardener):
    return harden.xor_fold()


def _new_permute_hardener(h: PermuteHardener):
    return harden.permute(lambda: random.Random(h.seed))


def _new_randomized_response_hardener(h: RandomizedResponseHardener):
    return harden.randomized_response(lambda: random.Random(h.seed), h.probability)


def _new_rule_90_hardener(_h: Rule90Hardener):
    return harden.rule_90()


def _new_rehash_hardener(h: RehashHardener):
    return harden.rehash(h.window_size, h.window_step, h.samples)


_name_to_hardener_dict: dict[Hardener, Callable[[_M], harden.HardenerFn]] = {
    Hardener.balance: _new_balance_hardener,
    Hardener.xor_fold: _new_xor_fold_hardener,
    Hardener.permute: _new_permute_hardener,
    Hardener.randomized_response: _new_randomized_response_hardener,
    Hardener.rule_90: _new_rule_90_hardener,
    Hardener.rehash: _new_rehash_hardener
}


def _resolve_salt(
        entity: AttributeValueEntity,
        attr_config: StaticAttributeConfig | WeightedAttributeConfig | None
):
    if attr_config is None or attr_config.salt is None:
        return ""

    salt = attr_config.salt

    if salt.value is not None:
        return salt.value
    else:
        return entity.attributes[salt.attribute]


def _populate_bitarray(
        ba: bitarray,
        value: str,
        hash_fn: HashFn,
        hash_strategy: AnyHashStrategy,
        hash_values: int
):
    value_digest = hash_fn(value.encode())
    i0, i1, i2, i3 = common.destructure_digest(value_digest)

    if hash_strategy.name == HashStrategy.double_hash:
        bits.double_hash(ba, hash_values, i0 ^ i1, i2 ^ i3)
    elif hash_strategy.name == HashStrategy.triple_hash:
        bits.triple_hash(ba, hash_values, i0, i1, i2 ^ i3)
    elif hash_strategy.name == HashStrategy.enhanced_double_hash:
        bits.enhanced_double_hash(ba, hash_values, i0 ^ i1, i2 ^ i3)
    elif hash_strategy.name == HashStrategy.random_hash:
        bits.random_hash(ba, hash_values, random.Random(i0 ^ i1 ^ i2 ^ i3))
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented hash strategy `{hash_strategy.name}`",
        )


def _resolve_hardeners(config: MaskConfig) -> harden.HardenerFn:
    hardeners = [_name_to_hardener_dict.get(hardener.name) for hardener in config.hardeners]

    if any([h is None for h in hardeners]):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented hardener in `{'`, `'.join([h.name for h in config.hardeners])}`"
        )

    hardener_chain = [hardener_factory(model) for hardener_factory, model in zip(hardeners, config.hardeners)]

    def _harden(ba: bitarray):
        for hardener_fn in hardener_chain:
            ba = hardener_fn(ba)

        return ba

    return _harden


def _attribute_config_list_to_dict(
        attributes: list[StaticAttributeConfig] | list[WeightedAttributeConfig] | None
) -> dict[str, StaticAttributeConfig | WeightedAttributeConfig]:
    return {attr_conf.attribute_name: attr_conf for attr_conf in attributes or []}


def _mask_clk(mask_req: EntityMaskRequest):
    # 0) set up vars
    hash_fn = _resolve_hash_function_config(mask_req.config)
    attr_config_dict = _attribute_config_list_to_dict(mask_req.attributes)

    filter_size = mask_req.config.filter.filter_size
    padding = mask_req.config.padding
    token_size = mask_req.config.token_size
    hash_strategy = mask_req.config.hash.strategy
    hash_values = mask_req.config.filter.hash_values

    entity_bas: list[bitarray] = []

    # 1) mask entities
    for entity in mask_req.entities:
        # 1.1) construct bitarray of fixed size
        ba = bitarray(filter_size)

        for attr_name, attr_value in entity.attributes.items():
            # 1.2) determine salt for attribute, if exists
            attr_config = attr_config_dict.get(attr_name)
            salt = _resolve_salt(entity, attr_config)

            # 1.3) tokenize attribute value and insert into bitarray
            for token in common.tokenize(attr_value, token_size, padding):
                if mask_req.config.prepend_attribute_name:
                    token = attr_name + token

                _populate_bitarray(ba, salt + token, hash_fn, hash_strategy, hash_values)

        entity_bas.append(ba)

    return entity_bas


def _mask_clkrbf(mask_req: EntityMaskRequest):
    # 0) set up vars
    hash_fn = _resolve_hash_function_config(mask_req.config)
    attr_config_dict = _attribute_config_list_to_dict(mask_req.attributes)

    padding = mask_req.config.padding
    token_size = mask_req.config.token_size
    hash_strategy = mask_req.config.hash.strategy

    # 1) determine the weight of the attribute with the lowest weight
    min_weight = min(attr_conf.weight for attr_conf in mask_req.attributes)

    # 2) compute the amount of hash values to generate per attribute
    attr_name_to_hash_value_dict: dict[str, int] = {}
    total_average_token_insertions = 0
    base_hash_values = mask_req.config.filter.hash_values

    for attr_conf in mask_req.attributes:
        attr_weight = attr_conf.weight
        # 2.1) scale attribute weight based on the base amount of hash values
        attr_hash_values = int(math.ceil(base_hash_values * attr_weight / min_weight))
        attr_name_to_hash_value_dict[attr_conf.attribute_name] = attr_hash_values
        # 2.2) update the average amount of total insertions to determine the bitarray size
        total_average_token_insertions += attr_hash_values * attr_conf.average_token_count

    # 3) compute bitarray size s.t. 50% of all bits are set on average
    ba_size = bits.optimal_size(0.5, total_average_token_insertions)

    # 4) mask entities
    entity_bas: list[bitarray] = []

    for entity in mask_req.entities:
        # 4.1) construct bitarray of computed size
        ba = bitarray(ba_size)

        for attr_name, attr_value in entity.attributes.items():
            attr_conf = attr_config_dict.get(attr_name)
            # 4.2) retrieve the amount of hash values to generate for this attribute
            attr_hash_values = attr_name_to_hash_value_dict.get(attr_name)
            # 4.3) determine salt for attribute, if exists
            salt = _resolve_salt(entity, attr_conf)

            # 4.4) tokenize attribute value and insert into bitarray
            for token in common.tokenize(attr_value, token_size, padding):
                if mask_req.config.prepend_attribute_name:
                    token = attr_name + token

                _populate_bitarray(ba, salt + token, hash_fn, hash_strategy, attr_hash_values)

        entity_bas.append(ba)

    return entity_bas


def _compute_rbf_size_for_attribute(attr_conf: WeightedAttributeConfig, attr_bitarray_size: int, total_weight: float):
    weight = attr_conf.weight
    return int(math.ceil(attr_bitarray_size * total_weight / weight))


def _mask_rbf(mask_req: EntityMaskRequest):
    # 0) set up vars
    hash_fn = _resolve_hash_function_config(mask_req.config)
    attr_config_dict = _attribute_config_list_to_dict(mask_req.attributes)

    padding = mask_req.config.padding
    token_size = mask_req.config.token_size
    hash_strategy = mask_req.config.hash.strategy

    # 1) determine the total weight and the bitarray size for each attribute
    hash_values = mask_req.config.filter.hash_values
    # 1.1) sum up all attribute weights
    total_attribute_weight = sum(attr_conf.weight for attr_conf in mask_req.attributes)
    # 1.2) compute the bitarray size s.t. each attribute has 50% of bits set on average
    attr_name_to_bitarray_size_dict: dict[str, int] = {
        attr_conf.attribute_name: bits.optimal_size(
            p=0.5,
            n=attr_conf.average_token_count * hash_values
        ) for attr_conf in mask_req.attributes
    }

    # 2) sort all attribute names alphabetically s.t. bitarrays are always constructed consistently
    sorted_attr_names = sorted([attr_conf.attribute_name for attr_conf in mask_req.attributes])

    # 3) compute the size of the bitarray that is representative of this record
    # 3.1) this is done by computing the theoretical bitarray size for each attribute and taking the highest one
    parent_bitarray_size = max(
        int(math.ceil(
            # 3.2) this boils down to ceil(attribute_bitarray_size * total_weight / attribute_weight)
            attr_name_to_bitarray_size_dict.get(attr_conf.attribute_name) * total_attribute_weight / attr_conf.weight
        )) for attr_conf in mask_req.attributes
    )

    # 4) mask entities
    entity_bas: list[bitarray] = []

    for entity in mask_req.entities:
        attr_name_to_bitarray_dict: dict[str, bitarray] = {}

        # 4.1) first construct bitarrays for each attribute
        for attr_name in sorted_attr_names:
            attr_value = entity.attributes.get(attr_name)
            attr_conf = attr_config_dict.get(attr_name)

            # 4.1.1) construct bitarray with precomputed size for this attribute
            attr_bitarray_size = attr_name_to_bitarray_size_dict.get(attr_name)
            attr_ba = bitarray(attr_bitarray_size)

            # 4.1.2) determine salt for attribute, if exists
            salt = _resolve_salt(entity, attr_conf)

            # 4.1.3) tokenize attribute value and insert into bitarray
            for token in common.tokenize(attr_value, token_size, padding):
                if mask_req.config.prepend_attribute_name:
                    token = attr_name + token

                _populate_bitarray(attr_ba, salt + token, hash_fn, hash_strategy, hash_values)

            # 4.1.4) keep track of the attribute bitarray
            attr_name_to_bitarray_dict[attr_name] = attr_ba

        # 4.2) merge all attribute bitarrays into the parent bitarray
        parent_bitarray_offset = 0
        parent_ba = bitarray(parent_bitarray_size)

        # 4.2.1) use the seed configured for rbf to sample bits
        rng = random.Random(mask_req.config.filter.seed)

        for attr_name in sorted_attr_names:
            attr_conf = attr_config_dict.get(attr_name)
            attr_ba = attr_name_to_bitarray_dict.get(attr_name)
            attr_weight = attr_conf.weight

            # 4.2.2) compute the amount of bits that the attribute bitarray occupies in the parent bitarray
            attr_rel_weight = attr_weight / total_attribute_weight
            attr_bits_in_parent_ba = int(math.floor(attr_rel_weight * parent_bitarray_size))

            # 4.2.3) randomly sample bits from the attribute bitarray to set in the parent bitarray
            for i in range(attr_bits_in_parent_ba):
                # 4.2.3.1) sample random index
                idx = rng.randrange(len(attr_ba))
                # 4.2.3.2) set the bit in the parent bitarray if it's also set in the attribute bitarray
                if bits.test_bit(attr_ba, idx):
                    bits.set_bit(parent_ba, parent_bitarray_offset + idx)

            # 4.2.4) update the parent bitarray offset
            parent_bitarray_offset += attr_bits_in_parent_ba

        entity_bas.append(parent_ba)

    return entity_bas


@router.post("/")
async def mask_entities(mask_req: EntityMaskRequest) -> EntityMaskResponse:
    hardener_fn = _resolve_hardeners(mask_req.config)
    filter_type = mask_req.config.filter.type

    if filter_type == FilterType.clk:
        entity_bas = _mask_clk(mask_req)
    elif filter_type == FilterType.rbf:
        entity_bas = _mask_rbf(mask_req)
    elif filter_type == FilterType.clkrbf:
        entity_bas = _mask_clkrbf(mask_req)
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented filter type `{filter_type.name}`",
        )

    return EntityMaskResponse(
        config=mask_req.config,
        entities=[
            BitVectorEntity(
                id=entity.id,
                value=bits.to_base64(hardener_fn(entity_ba))
            ) for entity, entity_ba in zip(mask_req.entities, entity_bas)
        ]
    )
