import pytest
from pyphonetics import Soundex

from pprl_core import transform
from pprl_core.phonetics_extra import ColognePhonetics


def test_character_filter_custom():
    transform_fn = transform.character_filter("o")

    assert transform_fn("foobar") == "fbar"


def test_normalize():
    transform_fn = transform.normalize()

    assert transform_fn(" Fòo   bár ") == "foo bar"


def test_date_time():
    transform_fn = transform.date_time("%d.%m.%Y", "%Y-%m-%d")

    assert transform_fn("29.06.1998") == "1998-06-29"


def test_number_six_digits():
    transform_fn = transform.number(6)

    assert transform_fn("2") == "2.000000"
    assert transform_fn("2.11") == "2.110000"
    assert transform_fn("2.5000001") == "2.500000"
    assert transform_fn("-2.5000001") == "-2.500000"


def test_number_zero_digits():
    transform_fn = transform.number(0)

    assert transform_fn("2") == "2"
    assert transform_fn("2.11") == "2"
    assert transform_fn("-2.11") == "-2"


def test_phonetic_code():
    transform_fn = transform.phonetic_code(Soundex())

    assert transform_fn("foobar") == "F160"


def test_phonetic_code_extra():
    transform_fn = transform.phonetic_code(ColognePhonetics())

    assert transform_fn("Müller-Ludenscheidt") == "65752682"


def test_mapping_no_default():
    transform_fn = transform.mapping({"male": "m", "female": "f"})

    assert transform_fn("male") == "m"
    assert transform_fn("female") == "f"

    with pytest.raises(ValueError) as e:
        transform_fn("foobar")

    assert str(e.value) == "value `foobar` has no mapping, or no default value is present"


def test_mapping_with_default():
    transform_fn = transform.mapping({"male": "m", "female": "f"}, default_val="x")

    assert transform_fn("male") == "m"
    assert transform_fn("female") == "f"
    assert transform_fn("foobar") == "x"


def test_mapping_inline():
    # b's introduced by the replacement should not be replaced by the transformer.
    transform_fn = transform.mapping({"o": "b", "b": "a"}, inline=True)

    assert transform_fn("foobar") == "fbbaar"


def test_mapping_inline_collision():
    transform_fn = transform.mapping({"ob": "x", "ba": "y"}, inline=True)

    with pytest.raises(ValueError) as e:
        transform_fn("foobar")

    assert str(e.value) == (
        "cannot resolve inline mapping: replacement of `ba` with `y` "
        "at index 3 overlaps"
    )
