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
