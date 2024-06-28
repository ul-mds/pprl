__all__ = [
    "tokenize",
    "destructure_digest"
]

import struct


def tokenize(value: str, q=2, padding="_") -> set[str]:
    """
    Split a string into tokens of fixed size.
    
    Args:
        value: string to tokenize
        q: size of tokens
        padding: padding character to append and prepend to string

    Returns:
        set of unique tokens obtained from string
    """
    padding = (q - 1) * padding
    value = padding + value + padding
    tokens: set[str] = set()

    for i in range(len(value) - q + 1):
        tokens.add(value[i: i + q])

    return tokens


def destructure_digest(digest: bytes) -> (int, int, int, int):
    """
    Use the first 16 bytes of a hash digest to extract four integers from.
    This is used to compute hash values for all kinds of hashing schemes.
    
    Args:
        digest: hash digest

    Returns:
        four integers extracted from the first 16 bytes of the hash digest
    """
    unpacked_ints = struct.unpack_from("<iiii", digest)
    return unpacked_ints[0], unpacked_ints[1], unpacked_ints[2], unpacked_ints[3]
