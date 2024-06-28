from bitarray import bitarray

from pprl_core import similarity

_ba_left = bitarray("1" * 40)
_ba_right = bitarray("1" * 10 + "0" * 30)


def test_dice():
    assert similarity.dice(_ba_left, _ba_right) == .4


def test_cosine():
    assert similarity.cosine(_ba_left, _ba_right) == .5


def test_jaccard():
    assert similarity.jaccard(_ba_left, _ba_right) == .25
