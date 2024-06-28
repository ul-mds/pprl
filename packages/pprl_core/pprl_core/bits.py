__all__ = [
    "set_bit",
    "test_bit",
    "double_hash",
    "enhanced_double_hash",
    "triple_hash",
    "random_hash",
    "from_base64",
    "to_base64",
    "optimal_size"
]

import base64
import math
from random import Random

from bitarray import bitarray


def _compute_idx(ba: bitarray, i: int) -> int:
    """
    Compute an index within a bitarray from an arbitrary integer.
    If the integer is negative, all of its bits are flipped.
    If the integer is higher than the amount of bits in the bitarray, the integer is taken mod the
    bitarray's size.
    
    Args:
        ba: bitarray to compute index for
        i: integer to convert into index

    Returns:
        index within bitarray
    """
    if i < 0:
        i = ~i

    return i % len(ba)


def set_bit(ba: bitarray, i: int):
    """
    Set a bit in a bitarray.
    The supplied integer is used to determine a corresponding index within the bitarray.
    
    Args:
        ba: bitarray to set bit in
        i: integer to compute index with
    """
    ba[_compute_idx(ba, i)] = 1


def test_bit(ba: bitarray, i: int) -> bool:
    """
    Test if a bit is set in a bitarray.
    The supplied integer is used to determine a corresponding index within the bitarray.
    
    Args:
        ba: bitarray to test bit in
        i: integer to compute index with

    Returns:
        True if the bit at the computed index is set, False otherwise
    """
    return ba[_compute_idx(ba, i)] == 1


def double_hash(ba: bitarray, k: int, h1: int, h2: int):
    """
    Set bits in a bitarray using the double hashing scheme.
    The supplied hash values are used to compute the indices for the bits to set.
    
    Args:
        ba: bitarray to set bits in
        k: amount of indices to compute
        h1: first hash value
        h2: second hash value
    """
    for i in range(1, k + 1):
        set_bit(ba, h1 + i * h2)


def triple_hash(ba: bitarray, k: int, h1: int, h2: int, h3: int):
    """
    Set bits in a bitarray using the triple hashing scheme.
    The supplied hash values are used to compute the indices for the bits to set.
    
    Args:
        ba: bitarray to set bits in
        k: amount of indices to compute
        h1: first hash value
        h2: second hash value
        h3: third hash value
    """
    for i in range(1, k + 1):
        set_bit(ba, h1 + i * h2 + h3 * (i * (i - 1)) // 2)


def enhanced_double_hash(ba: bitarray, k: int, h1: int, h2: int):
    """
    Set bits in a bitarray using the enhanced double hashing scheme.
    The supplied hash values are used to compute the indices for the bits to set.
    
    Args:
        ba: bitarray to set bits in
        k: amount of indices to compute
        h1: first hash value
        h2: second hash value
    """
    for i in range(1, k + 1):
        set_bit(ba, h1 + i * h2 + (i ** 3 - i) // 6)


def random_hash(ba: bitarray, k: int, rng: Random):
    """
    Set bits in a bitarray using the random hashing scheme.
    The supplied random number generator is used to compute the indices for the bits to set.
    
    Args:
        ba: bitarray to set bits in 
        k: amount of indices to compute
        rng: random number generator to use
    """
    for i in range(1, k + 1):
        set_bit(ba, rng.randrange(len(ba)))


def optimal_size(p: float, n: float) -> int:
    """
    Compute the optimal size for a bitarray such that *p* percent of all bits within it are set after
    *n* insertions.
    
    Args:
        p: percentage of bits to set
        n: amount of expected insertions

    Returns:
        size of bitarray that satisfies the given constraints
    """
    if n <= 0:
        raise ValueError(f"amount of expected insertions must be positive, is {n}")

    if p < 0 or p >= 1:
        raise ValueError(f"percentage of set bits must be in range of [0,1), is {p}")

    return int(math.ceil(1 / (1 - math.pow(p, 1 / n))))


def to_base64(ba: bitarray) -> str:
    """
    Convert a bitarray to a base64 encoded string.
    
    Args:
        ba: bitarray to convert

    Returns:
        bits of the bitarray in base64 encoded form
    """
    return base64.b64encode(ba.tobytes()).decode()


def from_base64(b64str: str) -> bitarray:
    """
    Convert a base64 encoded string to a bitarray.
    
    Args:
        b64str: base64 encoded string to convert

    Returns:
        bitarray with bits obtained from the base64 encoded string
    """
    ba_bytes = base64.b64decode(b64str.encode())
    ba = bitarray()
    ba.frombytes(ba_bytes)

    return ba
