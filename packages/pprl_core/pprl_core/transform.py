__all__ = [
    "character_filter",
    "normalize",
    "number",
    "date_time",
    "phonetic_code",
    "mapping",
    "StringTransformFn"
]

import operator
import re
import unicodedata
from datetime import datetime
from typing import Callable, NamedTuple

from bitarray import bitarray
from pyphonetics.phonetics import PhoneticAlgorithm
from unidecode import unidecode

StringTransformFn = Callable[[str], str]


def character_filter(chars: str) -> StringTransformFn:
    def _transform(str_in: str) -> str:
        return "".join(c for c in str_in if c not in chars)

    return _transform


def normalize() -> StringTransformFn:
    def _transform(str_in: str) -> str:
        # replace all non-ascii characters with their closest ascii variants
        str_in = unidecode(str_in)
        # perform unicode normalization
        str_in = unicodedata.normalize("NFKD", str_in)
        # replace all non-ascii characters
        str_in = re.sub(r"[^\x00-\x7f]]", r"", str_in)
        # make everything lowercase
        str_in = str_in.lower()
        # replace 2+ whitespaces
        str_in = re.sub(r"\s{2,}", " ", str_in)
        # remove leading and trailing whitespaces
        return str_in.strip()

    return _transform


def number(decimal_places: int) -> StringTransformFn:
    number_format = f"{{:0.{decimal_places}f}}"

    def _transform(str_in: str) -> str:
        return number_format.format(float(str_in))

    return _transform


def date_time(input_format: str, output_format: str) -> StringTransformFn:
    def _transform(str_in: str) -> str:
        return datetime.strptime(str_in, input_format).strftime(output_format)

    return _transform


def phonetic_code(phon_algo: PhoneticAlgorithm) -> StringTransformFn:
    def _transform(str_in: str) -> str:
        return phon_algo.phonetics(str_in)

    return _transform


class _MappingReplacement(NamedTuple):
    index: int
    source: str
    target: str
    length_diff: int


def _mapping_replacement_for(index: int, source: str, target: str):
    return _MappingReplacement(index, source, target, len(target) - len(source))


def mapping(
        char_dict: dict[str, str], default_val: str | None = None, inline=False
) -> StringTransformFn:
    def _transform_default(str_in: str) -> str:
        str_out = char_dict.get(str_in, default_val)

        if str_out is None:
            raise ValueError(
                f"value `{str_in}` has no mapping, or no default value is present"
            )

        return str_out

    def _transform_inline(str_in: str) -> str:
        pending_replacements: list[_MappingReplacement] = []
        # track indices that are affected by a replacement
        overlap_bitarray = bitarray(len(str_in))

        for source, target in char_dict.items():
            source_len = len(source)

            # find first occurrence of source string
            i = str_in.find(source, 0)

            # find() returns -1 on failure
            while i != -1:
                # check if any index is already affected by a replacement in this range
                if overlap_bitarray[i: i + source_len].any():
                    raise ValueError(
                        f"cannot resolve inline mapping: replacement of `{source}` with `{target}` "
                        f"at index {i} overlaps"
                    )

                # mark replacement
                pending_replacements.append(_mapping_replacement_for(i, source, target))
                overlap_bitarray[i: i + source_len] = 1

                # find next occurrence of source string
                i = str_in.find(source, i + 1)

        # return early if no replacements were found
        if len(pending_replacements) == 0:
            return str_in

        # sort replacements by index in ascending order (0=index property of tuple)
        pending_replacements.sort(key=operator.itemgetter(0))

        # start constructing the output string
        str_out, i = "", 0

        for replacement in pending_replacements:
            # append from the input string until the next replacement
            str_out += str_in[i: replacement.index]
            # append the next replacement
            str_out += replacement.target
            # move past the replaced sequence in the input string
            i = replacement.index + len(replacement.source)

        # add everything else that hasn't been added yet
        str_out += str_in[i:]

        return str_out

    return _transform_inline if inline else _transform_default
