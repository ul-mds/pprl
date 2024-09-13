__all__ = ["ColognePhonetics"]

import re

from pyphonetics.phonetics import PhoneticAlgorithm, check_str, check_empty
from unidecode import unidecode

_PAD = "#"


def _get_char_context(word: str, idx: int):
    """
    Retrieve the character at the specified index within a word and its neighboring characters.
    
    Args:
        word: word to get character from
        idx: index to get character from

    Returns:
        tuple with previous, selected and next character within the word
    """
    # avoid ValueError if idx is out of range
    return word[idx - 1: idx] or _PAD, word[idx:idx + 1], word[idx + 1:idx + 2] or _PAD


class ColognePhonetics(PhoneticAlgorithm):
    """
    Implementation of the Kölner Phonetik, which is specially tailored for the German language. 
    """

    def phonetics(self, word: str):
        check_empty(word)
        check_str(word)

        word = unidecode(word).upper()
        word = re.sub(r'[^A-Z]', '', word)

        raw_code = ""

        for i in range(len(word)):
            prev_char, this_char, next_char = _get_char_context(word, i)

            if this_char in "AEIJOUY":
                raw_code += "0"
            elif this_char == "B":
                raw_code += "1"
            elif this_char == "P":
                if next_char == "H":
                    raw_code += "3"
                else:
                    raw_code += "1"
            elif this_char in "DT":
                if next_char in "CSZ":
                    raw_code += "8"
                else:
                    raw_code += "2"
            elif this_char in "FVW":
                raw_code += "3"
            elif this_char in "GKQ":
                raw_code += "4"
            elif this_char == "C":
                if i == 0:
                    if next_char in "AHKLOQRUX":
                        raw_code += "4"
                    else:
                        raw_code += "8"
                else:
                    if prev_char in "SZ":
                        raw_code += "8"
                    else:
                        if next_char in "AHKOQUX":
                            raw_code += "4"
                        else:
                            raw_code += "8"
            elif this_char == "X":
                if prev_char in "CKQ":
                    raw_code += "8"
                else:
                    raw_code += "48"
            elif this_char == "L":
                raw_code += "5"
            elif this_char in "MN":
                raw_code += "6"
            elif this_char == "R":
                raw_code += "7"
            elif this_char in "SZ":
                raw_code += "8"

        if raw_code == "":
            return ""

        last_char = ""
        code = ""

        for char in raw_code:
            if last_char == char:
                continue

            code += char
            last_char = char

        return code[0] + re.sub("0", "", code[1:])


class GenericSoundex(PhoneticAlgorithm):
    DEFAULT_DIGIT_COUNT = 3

    @staticmethod
    def us_english(num_digits=DEFAULT_DIGIT_COUNT):
        return GenericSoundex({
            0: list("AEIOUYHW"),
            1: list("BFPV"),
            2: list("CGJKQSXZ"),
            3: list("DT"),
            4: list("L"),
            5: list("MN"),
            6: list("R")
        }, ignore_chars=list("HW"), num_digits=num_digits)

    @staticmethod
    def us_english_simplified(num_digits=DEFAULT_DIGIT_COUNT):
        return GenericSoundex({
            0: list("AEIOUYHW"),
            1: list("BFPV"),
            2: list("CGJKQSXZ"),
            3: list("DT"),
            4: list("L"),
            5: list("MN"),
            6: list("R")
        }, num_digits=num_digits)

    @staticmethod
    def us_english_genealogy(num_digits=DEFAULT_DIGIT_COUNT):
        return GenericSoundex({
            0: list("AEIOUYHW"),
            1: list("BFPV"),
            2: list("CGJKQSXZ"),
            3: list("DT"),
            4: list("L"),
            5: list("MN"),
            6: list("R")
        }, ignore_chars=list("AEIOUYHW"), num_digits=num_digits)

    @staticmethod
    def german(num_digits=DEFAULT_DIGIT_COUNT):
        return GenericSoundex({
            0: list("AEIOUÄÖÜ"),
            1: list("BPFV"),
            2: list("CGKQXSZẞß"),
            3: list("DT"),
            4: list("L"),
            5: list("MN"),
            6: list("R"),
            7: ["CH"]
        }, ignore_chars=list("WHYJ"), num_digits=num_digits)

    def phonetics(self, word):
        check_str(word)
        check_empty(word)

        word = unidecode(word).upper()
        first_digit, start_idx = None, 0

        # skip unmapped characters at the start
        while True:
            # noinspection PyArgumentList
            first_digit, first_char = self._resolve_digit_at_index_fn(word, start_idx)

            if first_digit is not None:
                break
            else:
                start_idx += len(first_char)

        digits = []

        i = start_idx

        while i < len(word):
            # noinspection PyArgumentList
            digit_chr, subseq_chr = self._resolve_digit_at_index_fn(word, i)
            i += len(subseq_chr)

            if digit_chr is None or subseq_chr in self._ignore_letters:
                continue

            digits.append(digit_chr)

        code = first_char
        last_digit = first_digit

        for digit in digits:
            if digit != "0" and digit != last_digit:
                code += digit

            last_digit = digit

        code += "0" * self._num_digits
        return code[:self._num_digits + len(first_char)]

    def _resolve_digit_at_index_static(self, word: str, idx: int):
        return self._chars_to_digit_dict.get(word[idx]), word[idx]

    def _resolve_digit_at_index_variable(self, word: str, idx: int):
        for chr_len in range(self._max_char_len, 0, -1):
            char = word[idx: idx + chr_len]
            digit = self._chars_to_digit_dict.get(char)

            if digit is not None:
                return digit, char

        return None, word[idx]

    def __init__(
            self,
            digit_to_chars_dict: dict[int, list[str]],
            ignore_chars: list[str] | None = None,
            num_digits: int = DEFAULT_DIGIT_COUNT
    ):
        super().__init__()
        self._chars_to_digit_dict: dict[str, str] = {}
        self._max_char_len = 0

        if ignore_chars is None:
            ignore_chars = []

        self._ignore_letters = ignore_chars

        for char in ignore_chars:
            self._chars_to_digit_dict[char] = "0"

        for digit, chars in digit_to_chars_dict.items():
            for char in chars:
                self._chars_to_digit_dict[char.upper()] = str(digit)
                self._max_char_len = max(self._max_char_len, len(char))

        self._num_digits = num_digits

        if self._max_char_len == 1:
            self._resolve_digit_at_index_fn = self._resolve_digit_at_index_static
        else:
            self._resolve_digit_at_index_fn = self._resolve_digit_at_index_variable
