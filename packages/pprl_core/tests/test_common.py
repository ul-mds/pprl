from pprl_core import common


def test_tokenize_default():
    assert common.tokenize("foobar") == {
        "_f", "fo", "oo", "ob", "ba", "ar", "r_"
    }


def test_tokenize_with_padding():
    assert common.tokenize("foobar", padding="#") == {
        "#f", "fo", "oo", "ob", "ba", "ar", "r#"
    }


def test_tokenize_with_size():
    assert common.tokenize("foobar", q=3) == {
        "__f", "_fo", "foo", "oob", "oba", "bar", "ar_", "r__"
    }


def test_destructure_digest():
    assert common.destructure_digest(b"\x01" * 4 + b"\x23" * 4 + b"\x45" * 4 + b"\x67" * 4) == (
        0x01010101,
        0x23232323,
        0x45454545,
        0x67676767
    )
