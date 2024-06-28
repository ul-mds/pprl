import pytest

from pprl_core.phonetics_extra import ColognePhonetics


@pytest.fixture()
def cologne():
    return ColognePhonetics()


@pytest.mark.parametrize(
    "word,expected_code",
    [
        # test cases from apache commons codec
        # https://github.com/apache/commons-codec/blob/master/src/test/java/org/apache/commons/codec/language/ColognePhoneticTest.java
        ("Müller-Lüdenscheidt", "65752682"),
        ("bergisch-gladbach", "174845214"),
        ("Müller", "657"),
        ("müller", "657"),
        ("schmidt", "862"),
        ("schneider", "8627"),
        ("fischer", "387"),
        ("weber", "317"),
        ("wagner", "3467"),
        ("becker", "147"),
        ("hoffmann", "0366"),
        ("schäfer", "837"),
        ("schÄfer", "837"),
        ("Breschnew", "17863"),
        ("Wikipedia", "3412"),
        ("peter", "127"),
        ("pharma", "376"),
        ("mönchengladbach", "664645214"),
        ("deutsch", "28"),
        ("deutz", "28"),
        ("hamburg", "06174"),
        ("hannover", "0637"),
        ("christstollen", "478256"),
        ("Xanthippe", "48621"),
        ("Zacharias", "8478"),
        ("Holzbau", "0581"),
        ("matsch", "68"),
        ("matz", "68"),
        ("Arbeitsamt", "071862"),
        ("Eberhard", "01772"),
        ("Eberhardt", "01772"),
        ("Celsius", "8588"),
        ("Ace", "08"),
        ("shch", "84"),
        ("xch", "484"),
        ("heithabu", "021"),
        # hyphenation
        ("Test test", "28282"),
        ("Testtest", "28282"),
        ("Test-test", "28282"),
        ("TesT#Test", "28282"),
        ("Test?test", "28282"),
        # variations
        ("mella", "65"),
        ("milah", "65"),
        ("moulla", "65"),
        ("mellah", "65"),
        ("muehle", "65"),
        ("mule", "65"),
        ("Meier", "67"),
        ("Maier", "67"),
        ("Mair", "67"),
        ("Meyer", "67"),
        ("Meyr", "67"),
        ("Mejer", "67"),
        ("Major", "67"),
        # edge cases
        ("a", "0"),
        ("e", "0"),
        ("i", "0"),
        ("o", "0"),
        ("u", "0"),
        ("ä", "0"),
        ("ö", "0"),
        ("ü", "0"),
        ("ß", "8"),
        ("aa", "0"),
        ("ha", "0"),
        ("h", ""),
        ("aha", "0"),
        ("b", "1"),
        ("p", "1"),
        ("ph", "3"),
        ("f", "3"),
        ("v", "3"),
        ("w", "3"),
        ("g", "4"),
        ("k", "4"),
        ("q", "4"),
        ("x", "48"),
        ("ax", "048"),
        ("cx", "48"),
        ("l", "5"),
        ("cl", "45"),
        ("acl", "085"),
        ("mn", "6"),
        ("{mn}", "6"),
        ("r", "7"),
    ]
)
def test_cologne_phonetics(word, expected_code, cologne):
    actual_code = cologne.phonetics(word)
    assert actual_code == expected_code
