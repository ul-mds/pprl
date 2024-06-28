import pytest
from bitarray import bitarray

from pprl_core import bits


@pytest.mark.parametrize(
    "p,n,expected",
    [
        (.5, 5, 8),
        (.75, 5, 18),
        (.5, 20, 30)
    ]
)
def test_optimal_size(p, n, expected):
    assert bits.optimal_size(p, n) == expected


def test_optimal_size_raises_p_too_low():
    with pytest.raises(ValueError) as e:
        bits.optimal_size(-.01, 20)

    assert str(e.value) == "percentage of set bits must be in range of [0,1), is -0.01"


def test_optimal_size_raises_p_too_high():
    with pytest.raises(ValueError) as e:
        bits.optimal_size(1, 20)

    assert str(e.value) == "percentage of set bits must be in range of [0,1), is 1"


def test_optimal_size_raises_n_too_low():
    with pytest.raises(ValueError) as e:
        bits.optimal_size(.5, 0)

    assert str(e.value) == "amount of expected insertions must be positive, is 0"


def test_set_bit():
    ba = bitarray(20)
    bits.set_bit(ba, 5)

    assert ba.count() == 1
    assert ba[5] == 1


def test_clk_set_bit_wraparound():
    ba = bitarray(20)
    bits.set_bit(ba, 25)

    assert ba.count() == 1
    assert ba[5] == 1


def test_clk_set_bit_same_index():
    ba = bitarray(20)
    bits.set_bit(ba, 5)
    bits.set_bit(ba, 25)

    assert ba.count() == 1
    assert ba[5] == 1


def test_clk_set_bit_negative():
    ba1 = bitarray(20)
    ba2 = bitarray(20)

    i = -1

    bits.set_bit(ba1, i)
    bits.set_bit(ba2, ~i)

    assert ba1 == ba2


def test_clk_test():
    ba = bitarray(20)
    bits.set_bit(ba, 5)

    assert bits.test_bit(ba, 5)


def test_clk_test_wraparound():
    ba = bitarray(20)
    bits.set_bit(ba, 5)

    assert bits.test_bit(ba, 25)


def test_double_hash():
    ba = bitarray(20)
    h1, h2, k = 2, 3, 5

    bits.double_hash(ba, k, h1, h2)
    set_idx = [h1 + h2 * i for i in range(1, k + 1)]

    for i in set_idx:
        assert bits.test_bit(ba, i)


def test_triple_hash():
    ba = bitarray(20)
    h1, h2, h3, k = 2, 3, 5, 7

    bits.triple_hash(ba, k, h1, h2, h3)
    set_idx = [h1 + i * h2 + h3 * (i * (i - 1)) // 2 for i in range(1, k + 1)]

    for i in set_idx:
        assert bits.test_bit(ba, i)


def test_enhanced_double_hash():
    ba = bitarray(20)
    h1, h2, k = 2, 3, 5

    bits.enhanced_double_hash(ba, k, h1, h2)
    set_idx = [h1 + i * h2 + (i ** 3 - i) // 6 for i in range(1, k + 1)]

    for i in set_idx:
        assert bits.test_bit(ba, i)


def test_random_hash(rng_factory):
    m = 20
    ba = bitarray(m)

    k = 5
    r1, r2 = rng_factory(), rng_factory()

    bits.random_hash(ba, k, r1)
    set_idx = [r2.randrange(m) for _ in range(k)]

    for i in set_idx:
        assert bits.test_bit(ba, i)


def test_base64(bitarray_factory):
    ba1 = bitarray_factory()
    ba2 = bits.from_base64(bits.to_base64(ba1))
    ba1.fill()

    assert ba1 == ba2
