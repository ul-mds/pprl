import random

import pytest
from bitarray import bitarray

from pprl_core import harden


def test_balance():
    ba = bitarray("1010")

    harden_balance = harden.balance()
    ba_hardened = harden_balance(ba)
    ba_expected = bitarray("10100101")

    assert ba_hardened == ba_expected


def test_xor_fold():
    bits_1, bits_2 = "11111111", "10100011"

    harden_xor_fold = harden.xor_fold()
    ba = bitarray(bits_1 + bits_2)
    ba_hardened = harden_xor_fold(ba)
    ba_expected = bitarray(bits_1) ^ bitarray(bits_2)

    assert ba_hardened == ba_expected


def test_xor_fold_padded():
    bits_1, bits_2 = "11111111", "10100011"

    harden_xor_fold = harden.xor_fold()
    ba = bitarray(bits_1 + bits_2[:-1])
    ba_hardened = harden_xor_fold(ba)
    ba_expected = bitarray(bits_1) ^ bitarray("10100010")

    assert ba_hardened == ba_expected


def test_randomized_response(rng_factory, bitarray_factory):
    harden_rand_resp = harden.randomized_response(rng_factory, .5)

    ba = bitarray_factory()
    ba_hardened = harden_rand_resp(ba)

    assert ba != ba_hardened


def test_randomized_response_same_seed(rng_factory, bitarray_factory):
    harden_rand_resp_1 = harden.randomized_response(rng_factory, .5)
    harden_rand_resp_2 = harden.randomized_response(rng_factory, .5)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rand_resp_1(ba)
    ba_hardened_2 = harden_rand_resp_2(ba)

    assert ba_hardened_1 == ba_hardened_2


def test_randomized_response_same_seed_different_probability(rng_factory, bitarray_factory):
    harden_rand_resp_1 = harden.randomized_response(rng_factory, .5)
    harden_rand_resp_2 = harden.randomized_response(rng_factory, .25)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rand_resp_1(ba)
    ba_hardened_2 = harden_rand_resp_2(ba)

    assert ba_hardened_1 != ba_hardened_2


def test_randomized_response_same_instance(rng_factory, bitarray_factory):
    harden_rand_resp = harden.randomized_response(rng_factory, .5)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rand_resp(ba)
    ba_hardened_2 = harden_rand_resp(ba)

    assert ba_hardened_1 == ba_hardened_2


def test_permute(rng_factory, bitarray_factory):
    harden_permute = harden.permute(rng_factory)

    ba = bitarray_factory()
    ba_hardened = harden_permute(ba)

    assert ba != ba_hardened


def test_permute_same_seed(rng_factory, bitarray_factory):
    harden_permute_1 = harden.permute(rng_factory)
    harden_permute_2 = harden.permute(rng_factory)

    ba = bitarray_factory()

    ba_hardened_1 = harden_permute_1(ba)
    ba_hardened_2 = harden_permute_2(ba)

    assert ba_hardened_1 == ba_hardened_2


def test_permute_same_instance(rng_factory, bitarray_factory):
    harden_permute_1 = harden.permute(rng_factory)

    ba = bitarray_factory()
    ba_hardened_1 = harden_permute_1(ba)
    ba_hardened_2 = harden_permute_1(ba)

    assert ba_hardened_1 == ba_hardened_2


def test_permute_different_seed(bitarray_factory):
    harden_permute_1 = harden.permute(lambda: random.Random(123))
    harden_permute_2 = harden.permute(lambda: random.Random(456))

    ba = bitarray_factory()
    ba_hardened_1 = harden_permute_1(ba)
    ba_hardened_2 = harden_permute_2(ba)

    assert ba_hardened_1 != ba_hardened_2


@pytest.mark.parametrize(
    "ba_original,ba_expected",
    [
        (bitarray("10010"), bitarray("01100")),
        (bitarray("0110101"), bitarray("0110000")),
    ]
)
def test_rule_90(ba_original, ba_expected):
    harden_rule_90 = harden.rule_90()
    ba_hardened = harden_rule_90(ba_original)

    assert ba_hardened == ba_expected


def test_rehash(bitarray_factory):
    harden_rehash = harden.rehash(8, 8, 3)

    ba = bitarray_factory()
    ba_hardened = harden_rehash(ba)

    assert ba != ba_hardened


def test_rehash_different_window_size(bitarray_factory):
    harden_rehash_1 = harden.rehash(8, 8, 3)
    harden_rehash_2 = harden.rehash(16, 8, 3)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rehash_1(ba)
    ba_hardened_2 = harden_rehash_2(ba)

    assert ba_hardened_1 != ba_hardened_2


def test_rehash_different_window_step(bitarray_factory):
    harden_rehash_1 = harden.rehash(8, 8, 3)
    harden_rehash_2 = harden.rehash(8, 16, 3)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rehash_1(ba)
    ba_hardened_2 = harden_rehash_2(ba)

    assert ba_hardened_1 != ba_hardened_2


def test_rehash_different_hash_functions(bitarray_factory):
    harden_rehash_1 = harden.rehash(8, 8, 3)
    harden_rehash_2 = harden.rehash(8, 8, 5)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rehash_1(ba)
    ba_hardened_2 = harden_rehash_2(ba)

    assert ba_hardened_1 != ba_hardened_2


def test_rehash_same_instance(bitarray_factory):
    harden_rehash = harden.rehash(8, 8, 3)

    ba = bitarray_factory()
    ba_hardened_1 = harden_rehash(ba)
    ba_hardened_2 = harden_rehash(ba)

    assert ba_hardened_1 == ba_hardened_2
