import pytest

from pprl_core.phonetics_extra import ColognePhonetics, GenericSoundex


@pytest.fixture()
def cologne():
    return ColognePhonetics()


@pytest.fixture()
def soundex_us():
    return GenericSoundex.us_english()


@pytest.fixture()
def soundex_us_simplified():
    return GenericSoundex.us_english_simplified()


@pytest.fixture()
def soundex_us_genealogy():
    return GenericSoundex.us_english_genealogy()


@pytest.fixture()
def soundex_german():
    return GenericSoundex.german()


@pytest.fixture()
def soundex_german_4():
    return GenericSoundex.german(num_digits=4)


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


@pytest.mark.parametrize(
    "word,expected_code",
    [
        # B650
        ("BARHAM", "B650"),
        ("BARONE", "B650"),
        ("BARRON", "B650"),
        ("BERNA", "B650"),
        ("BIRNEY", "B650"),
        ("BIRNIE", "B650"),
        ("BOOROM", "B650"),
        ("BOREN", "B650"),
        ("BORN", "B650"),
        ("BOURN", "B650"),
        ("BOURNE", "B650"),
        ("BOWRON", "B650"),
        ("BRAIN", "B650"),
        ("BRAME", "B650"),
        ("BRANN", "B650"),
        ("BRAUN", "B650"),
        ("BREEN", "B650"),
        ("BRIEN", "B650"),
        ("BRIM", "B650"),
        ("BRIMM", "B650"),
        ("BRINN", "B650"),
        ("BROOM", "B650"),
        ("BROOME", "B650"),
        ("BROWN", "B650"),
        ("BROWNE", "B650"),
        ("BRUEN", "B650"),
        ("BRUHN", "B650"),
        ("BRUIN", "B650"),
        ("BRUMM", "B650"),
        ("BRUN", "B650"),
        ("BRUNO", "B650"),
        ("BRYAN", "B650"),
        ("BURIAN", "B650"),
        ("BURN", "B650"),
        ("BURNEY", "B650"),
        ("BYRAM", "B650"),
        ("BYRNE", "B650"),
        ("BYRON", "B650"),
        ("BYRUM", "B650"),
        # bad characters
        ("HOL>MES", "H452"),
        # quick brown fox
        ("testing", "T235"),
        ("The", "T000"),
        ("quick", "Q200"),
        ("brown", "B650"),
        ("fox", "F200"),
        ("jumped", "J513"),
        ("over", "O160"),
        ("the", "T000"),
        ("lazy", "L200"),
        ("dogs", "D200"),
        # genealogy examples
        ("Allricht", "A462"),
        ("Eberhard", "E166"),
        ("Engebrethson", "E521"),
        ("Heimbach", "H512"),
        ("Hanselmann", "H524"),
        ("Hildebrand", "H431"),
        ("Kavanagh", "K152"),
        ("Lind", "L530"),
        ("McDonnell", "M235"),
        ("McGee", "M200"),
        ("Opnian", "O155"),
        ("Oppenheimer", "O155"),
        ("Riedemanas", "R355"),
        ("Zita", "Z300"),
        ("Zitzmeinn", "Z325"),
        # census
        ("Washington", "W252"),
        ("Lee", "L000"),
        ("Gutierrez", "G362"),
        ("Pfister", "P236"),
        ("Jackson", "J250"),
        ("Tymczak", "T522"),
        ("VanDeusen", "V532"),
        # myatt
        ("HOLMES", "H452"),
        ("ADOMOMI", "A355"),
        ("VONDERLEHR", "V536"),
        ("BALL", "B400"),
        ("SHAW", "S000"),
        ("JACKSON", "J250"),
        ("SCANLON", "S545"),
        ("SAINTJOHN", "S532"),
        # apostrophes
        ("OBrien", "O165"),
        ("'OBrien", "O165"),
        ("O'Brien", "O165"),
        ("OB'rien", "O165"),
        ("OBr'ien", "O165"),
        ("OBri'en", "O165"),
        ("OBrie'n", "O165"),
        ("OBrien'", "O165"),
        # hyphens
        ("KINGSMITH", "K525"),
        ("-KINGSMITH", "K525"),
        ("K-INGSMITH", "K525"),
        ("KI-NGSMITH", "K525"),
        ("KIN-GSMITH", "K525"),
        ("KING-SMITH", "K525"),
        ("KINGS-MITH", "K525"),
        ("KINGSM-ITH", "K525"),
        ("KINGSMI-TH", "K525"),
        ("KINGSMIT-H", "K525"),
        ("KINGSMITH-", "K525"),
        # trimmable chars
        (" \t\n\r Washington \t\n\r ", "W252"),
        # hw-rule
        ("Ashcraft", "A261"),
        ("Ashcroft", "A261"),
        ("yehudit", "Y330"),
        ("yhwdyt", "Y330"),
        ("BOOTHDAVIS", "B312"),
        ("BOOTH-DAVIS", "B312"),
        ("Sgler", "S460"),
        ("Swhgler", "S460"),
        ("SAILOR", "S460"),
        ("SALYER", "S460"),
        ("SAYLOR", "S460"),
        ("SCHALLER", "S460"),
        ("SCHELLER", "S460"),
        ("SCHILLER", "S460"),
        ("SCHOOLER", "S460"),
        ("SCHULER", "S460"),
        ("SCHUYLER", "S460"),
        ("SEILER", "S460"),
        ("SEYLER", "S460"),
        ("SHOLAR", "S460"),
        ("SHULER", "S460"),
        ("SILAR", "S460"),
        ("SILER", "S460"),
        ("SILLER", "S460"),
        # mssql
        ("Smith", "S530"),
        ("Smythe", "S530"),
        ("Erickson", "E625"),
        ("Erikson", "E625"),
        ("Ericson", "E625"),
        ("Ericksen", "E625"),
        ("Ericsen", "E625"),
        ("Ann", "A500"),
        ("Andrew", "A536"),
        ("Janet", "J530"),
        ("Margaret", "M626"),
        ("Steven", "S315"),
        ("Michael", "M240"),
        ("Robert", "R163"),
        ("Laura", "L600"),
        ("Anne", "A500"),
        ("Williams", "W452"),
        # wikipedia
        ("Rupert", "R163"),
        ("Honeyman", "H555"),
        # wikipedia (de)
        ("Britney", "B635"),
        ("bewährten", "B635"),
        ("Spears", "S162"),
        ("Superzicke", "S162"),
    ]
)
def test_soundex_us_english(word, expected_code, soundex_us):
    actual_code = soundex_us.phonetics(word)
    assert actual_code == expected_code


@pytest.mark.parametrize(
    "word,expected_code",
    [
        ("WILLIAMS", "W452"),
        ("BARAGWANATH", "B625"),
        ("DONNELL", "D540"),
        ("LLOYD", "L300"),
        ("WOOLCOCK", "W422"),
        ("Dodds", "D320"),
        ("Dwdds", "D320"),
        ("Dhdds", "D320"),
    ]
)
def test_soundex_us_english_simplified(word, expected_code, soundex_us_simplified):
    actual_code = soundex_us_simplified.phonetics(word)
    assert actual_code == expected_code


@pytest.mark.parametrize(
    "word,expected_code",
    [
        ("Heggenburger", "H251"),
        ("Blackman", "B425"),
        ("Schmidt", "S530"),
        ("Lippmann", "L150"),
        ("Dodds", "D200"),
        ("Dhdds", "D200"),
        ("Dwdds", "D200"),
    ]
)
def test_soundex_us_english_genealogy(word, expected_code, soundex_us_genealogy):
    actual_code = soundex_us_genealogy.phonetics(word)
    assert actual_code == expected_code


@pytest.mark.parametrize(
    "word,expected_code",
    [
        ("CHARISMA", "CH625"),
        ("MACHER", "M760"),
        ("SÜßER", "S260"),
        ("SÜSSER", "S260"),
        ("SUESSER", "S260"),
        ("SÜẞER", "S260"),
        ("MAJOR", "M600")
    ]
)
def test_soundex_german(word, expected_code, soundex_german):
    actual_code = soundex_german.phonetics(word)
    assert actual_code == expected_code


@pytest.mark.parametrize(
    "word,expected_code",
    [
        ("CHARISMATISCH", "CH6253"),
        ("CHARISMA", "CH6250"),
        ("MACHER", "M7600"),
        ("SÜßER", "S2600"),
        ("SÜSSER", "S2600"),
        ("SUESSER", "S2600"),
        ("SÜẞER", "S2600"),
        ("MAJOR", "M6000")
    ]
)
def test_soundex_german_4(word, expected_code, soundex_german_4):
    actual_code = soundex_german_4.phonetics(word)
    assert actual_code == expected_code
