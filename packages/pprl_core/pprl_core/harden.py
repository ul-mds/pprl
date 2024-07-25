__all__ = [
    "HardenerFn",
    "balance",
    "xor_fold",
    "permute",
    "rule_90",
    "rehash",
    "randomized_response"
]

import random
import struct
from random import Random
from typing import Callable

from bitarray import bitarray

HardenerFn = Callable[[bitarray], bitarray]


def balance() -> HardenerFn:
    """
    Harden a bitarray by appending a flipped copy of it.
    This results in 50% of all bits being set.
    
    :return: function for balancing bits in a bitarray
    """

    def _harden(ba: bitarray) -> bitarray:
        ba = ba.copy()
        ba += ~ba

        return ba

    return _harden


def xor_fold() -> HardenerFn:
    """
    Harden a bitarray by splitting it in two halves of equal length and then merging them by performing a bitwise XOR 
    on them. If the length of the bitarray is odd, then an unset bit is appended to it before hardening.
    
    :return: function for performing xor-folding on a bitarray
    """

    def _harden(ba: bitarray) -> bitarray:
        ba = ba.copy()

        if len(ba) & 1 == 1:
            ba.append(0)

        m = len(ba) // 2

        return ba[0:m] ^ ba[m:m * 2]

    return _harden


def randomized_response(rng_factory: Callable[[], Random], probability: float) -> HardenerFn:
    """
    Harden a bitarray by randomly setting bits in a bitarray with a given probability.
    For each bit, there is a *1-p* probability that it remains unmodified.
    Otherwise, the bit is either set or unset with a probability of *p/2* each.
    
    :param rng_factory: function for instantiating a random number generator
    :param probability: probability of a bit being set or unset
    :return: function for performing randomized response hardening on a bitarray
    """
    p_half = probability / 2

    def _harden(ba: bitarray) -> bitarray:
        ba = ba.copy()
        rng = rng_factory()

        for i in range(len(ba)):
            d = rng.random()

            if d > probability:
                continue

            ba[i] = d < p_half

        return ba

    return _harden


def permute(rng_factory: Callable[[], Random]) -> HardenerFn:
    """
    Harden a bitarray by randomly permuting its bits.
    The bits are shuffled using a Fisher-Yates shuffle.
    
    :param rng_factory: function for instantiating a random number generator
    :return: function for randomly permuting bits in a bitarray
    """

    def _harden(ba: bitarray) -> bitarray:
        ba = ba.copy()
        rng = rng_factory()

        for i in range(len(ba) - 1, 0, -1):
            j = rng.randrange(i)

            ba[i], ba[j] = ba[j], ba[i]

        return ba

    return _harden


def rule_90() -> HardenerFn:
    """
    Harden a bitarray by having each bit be the result of an XOR of its left and right neighboring bits.
    To make sure that the start and end bit have a left and right neighbor respectively, the end bit is prepended
    and the start bit is appended to the original bitarray.
    
    :return: function for applying "rule 90" to a bitarray
    """

    def _harden(ba: bitarray) -> bitarray:
        ba_new = ba.copy()
        ba_new.extend([0, 0])  # extend with two bits of padding at the end
        ba_new >>= 1  # shift to right by one bit so that padding bit is on the left and right
        ba_new[0] = ba[len(ba) - 1]  # set left pad
        ba_new[len(ba_new) - 1] = ba[0]  # set right pad
        ba_new = (ba_new << 1) ^ (ba_new >> 1)  # perform xor
        return ba_new[1:len(ba_new) - 1]

    return _harden


def _compute_rehash_window_range(ba_len: int, window_size: int, window_step: int):
    return range(0, ba_len - window_size + 1, window_step)


def rehash(window_size: int, window_step: int, k: int) -> HardenerFn:
    """
    Harden a bitarray by rehashing its bits.
    A window of set size is moved in set steps to generate a seed for a random number generator.
    This random number generator is then used to randomly sample *k* bits in a bitarray which are then set.
    
    :param window_size: size of the sliding window in bits
    :param window_step: steps in bits in which the sliding window moves forward
    :param k: amount of bits to randomly sample with the RNG obtained from the seed in the sliding window
    :return: function performing rehashing on a bitarray
    """

    def _harden(ba: bitarray) -> bitarray:
        ba_new = ba.copy()

        for i in _compute_rehash_window_range(len(ba), window_size, window_step):
            ba_window = ba[i:i + window_size]
            # bytes from bitarray need to be padded because unpack() 
            # requires at least four bytes to work
            seed = struct.unpack_from("<i", ba_window.tobytes() + b"\x00" * 4)[0]
            rng = random.Random(seed)
            # draw k random indices from the seeded rng
            bits_to_set = [rng.randrange(len(ba)) for _ in range(k)]

            # set the drawn bits
            for j in bits_to_set:
                ba_new[j] = 1

        return ba_new

    return _harden
