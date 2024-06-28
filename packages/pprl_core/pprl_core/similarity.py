__all__ = [
    "SimilarityFn",
    "dice",
    "cosine",
    "jaccard"
]

import math
from typing import Callable

import bitarray.util as bitarray_util
from bitarray import bitarray

SimilarityFn = Callable[[bitarray, bitarray], float]


def _bitarray_count(ba1: bitarray, ba2: bitarray):
    """
    Compute the popcount of the input bitarrays and the popcount of their intersection.
    
    Args:
        ba1: first bitarray
        ba2: second bitarray

    Returns:
        popcount of first and second bitarray, and popcount of intersection
    """
    n1 = ba1.count()
    n2 = ba2.count()
    n12 = bitarray_util.count_and(ba1, ba2)

    return n1, n2, n12


def dice(ba1: bitarray, ba2: bitarray) -> float:
    """
    Compute the similarity of two bitarrays using the Dice coefficient.
    
    Args:
        ba1: first bitarray
        ba2: second bitarray

    Returns:
        similarity of bitarrays
    """
    n1, n2, n12 = _bitarray_count(ba1, ba2)

    return 2 * n12 / (n1 + n2)


def cosine(ba1: bitarray, ba2: bitarray) -> float:
    """
    Compute the similarity of two bitarrays using the cosine similarity.
    
    Args:
        ba1: first bitarray
        ba2: second bitarray

    Returns:
        similarity of bitarrays
    """
    n1, n2, n12 = _bitarray_count(ba1, ba2)

    return n12 / math.sqrt(n1 * n2)


def jaccard(ba1: bitarray, ba2: bitarray) -> float:
    """
    Compute the similarity of two bitarrays using the Jaccard index.
    
    Args:
        ba1: first bitarray
        ba2: second bitarray

    Returns:
        similarity of bitarrays
    """
    n1, n2, n12 = _bitarray_count(ba1, ba2)

    return n12 / (n1 + n2 - n12)
