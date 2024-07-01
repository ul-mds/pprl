This package enables core facilities for performing PPRL based on Bloom filters in Python.
It is mostly backed by the [bitarray](https://github.com/ilanschnell/bitarray) package which implements memory-efficient
arrays of bits in Python.
This package is composed of several submodules which implement different aspects of performing PPRL.
It is used by the [PPRL service package](https://github.com/ul-mds/pprl/tree/main/packages/pprl_service) under the hood 
to power its PPRL capabilities.

# Bitarray primitives

`pprl_core.bits` contains functions for setting bits in a bitarray.
It implements the double hash, enhanced double hash, triple hash and random hash schemes for setting bits based on
a set number of initial hash values in a bitarray.
It also offers other utility functions for working on PPRL with Bloom filters.

```python
from bitarray import bitarray
from pprl_core import bits

ba = bitarray(20)

# These are all equivalent and result in the bit with the index 5 to be set.
bits.set_bit(ba, 5)
bits.set_bit(ba, 25)
bits.set_bit(ba, -6)

# These are also equivalent and will return True.
bits.test_bit(ba, 5)
bits.test_bit(ba, 25)
bits.test_bit(ba, -6)

# pprl_core.bits implements the double hash, enhanced double hash, random hash and triple hash schemes.
# Depending on chosen scheme, the corresponding functions require different initial hash values.
h0, h1, h2 = 13, 37, 42
k = 5

ba_double = bitarray(32)
bits.double_hash(ba_double, k, h0, h1)
print(ba_double)
# => bitarray('01000010000000000010000100001000')

ba_enhanced_double = bitarray(32)
bits.enhanced_double_hash(ba_enhanced_double, k, h0, h1)
print(ba_enhanced_double)
# => bitarray('10000000000100000010000010100000')

ba_triple = bitarray(32)
bits.triple_hash(ba_triple, k, h0, h1, h2)
print(ba_triple)
# => bitarray('01000000001000000010000000100100')

from random import Random

ba_random = bitarray(32)
bits.random_hash(ba_random, k, Random(h0))
print(ba_random)
# => bitarray('00000000010100101010000000000000')

# Compute the size of a bitarray such that a certain percentage of its bits are set after
# a number of bits are picked at random and set. In this example, the percentage is set to 50% 
# and the amount of random bit sets is 100.
print(bits.optimal_size(.5, 100))
# => 145

# Serialize and deserialize a bitarray into a Base64-encoded form. The size of a deserialized
# bitarray may not always be the same size of the bitarray that generated the Base64 representation.
# This is because the deserialization will always return a bitarray whose length is a multiple of 8.
ba = bitarray("0010101110101001001010110101011101010010100000011101010100111100")
ba_b64_str = bits.to_base64(ba)
print(ba_b64_str)
# => "K6krV1KB1Tw="
ba_from_b64 = bits.from_base64(ba_b64_str)
print(ba == ba_from_b64)
# => True
```

# Hardening

`pprl_core.harden` contains factory functions for creating hardeners that can be applied to bitarrays.
These functions are guaranteed to always return a modified copy of the bitarrays they are supposed to harden.
They will never modify the input bitarrays.

```python
from pprl_core import harden
from random import Random
from bitarray import bitarray

# Create a new random bitarray.
rng = Random(727)
ba = bitarray([rng.random() < 0.5 for _ in range(64)])
print(ba)
# => bitarray('0000010100000100110010111001010101001000111110011011100100101000')

# Harden a bitarray by balancing its bits. With an original bitarray size of 64, the bitarray
# is expanded to a size of 128 in which 50% of its bits should be set. So the resulting bit
# count should be 64.
harden_balance = harden.balance()
ba_balance = harden_balance(ba.copy())
print(ba_balance)
# => bitarray('00000101000001001100101110010101010010001111100110111001001010001111101011111011001101000110101010110111000001100100011011010111')
print(ba.count(), ba_balance.count())
# => 27 64

# Harden a bitarray by performing XOR-folding. The resulting bitarray size should be half of the
# original bitarray.
harden_xor = harden.xor_fold()
ba_xor = harden_xor(ba.copy())
print(ba_xor)
# => bitarray('01001101111111010111001010111101')
print(len(ba), len(ba_xor))
# => 64 32

# Harden a bitarray by flipping bits using "randomized response". Performing an XOR of the resulting
# bitarray with the original bitarray will reveal the bits that have been modified as a result of this
# operation. This hardener requires a function that returns a random number generator and a probability
# with which a bit may be modified.
harden_rand_resp = harden.randomized_response(lambda: Random(727 * 2), .5)
ba_rand_resp = harden_rand_resp(ba.copy())
print(ba_rand_resp)
# => bitarray('0000010110000010110011001101110001001000111111011011101100001000')
print(ba ^ ba_rand_resp)
# => bitarray('0000000010000110000001110100100100000000000001000000001000100000')

# Harden a bitarray by randomly permuting its bits. This hardener requires a function that returns a
# random number generator for selecting bits to swap.
harden_permute = harden.permute(lambda: Random(727 * 3))
ba_permute = harden_permute(ba.copy())
print(ba_permute)
# => bitarray('0010110010110010101011110001010111000110001001001110000100001000')

# Harden a bitarray by having all bits be the result of an XOR of its left and right neighbors.
harden_rule_90 = harden.rule_90()
ba_rule_90 = harden_rule_90(ba.copy())
print(ba_rule_90)
# => bitarray('0000100010001011111100101110000000110101100011111010111011000100')

# Harden a bitarray by moving a sliding window over the bitarray which is used to instantiate a 
# random number generator to draw random bits to mutate. In this example, the sliding window has 
# a size of 8 bits and moves forward 4 bits after 2 random bits have been mutated.
harden_rehash = harden.rehash(8, 4, 2)
ba_rehash = harden_rehash(ba.copy())
print(ba_rehash)
# => bitarray('0000110101011110110110111001011111111010111111011011110100111000')
```

# Bitarray similarity

`pprl_core.similarity` contains functions for computing the similarity of bitarrays.
It implements the Dice coefficient, Cosine similarity and the Jaccard index.

```python
from pprl_core import similarity
from random import Random
from bitarray import bitarray

# Create new random bitarrays.
rng = Random(727)
ba_1 = bitarray([rng.random() < 0.5 for _ in range(32)])
ba_2 = bitarray([rng.random() < 0.5 for _ in range(32)])
print(ba_1)
# => bitarray('00000101000001001100101110010101')
print(ba_2)
# => bitarray('01001000111110011011100100101000')

# For all similarity functions, let n1 and n2 be the amount of set bits in ba_1 and ba_2 respectively,
# and let n12 be the amount of set bits in the intersection of ba_1 and ba_2.

# In ba_1 and ba_2, there are only 3 positions where bits are set in both bitarrays. Each similarity
# function will treat this a bit differently.
print((ba_1 & ba_2).count())
# => 3

# Dice coefficient (2 * n12 / (n1 + n2))
print(similarity.dice(ba_1, ba_2))
# => 0.2222222222222222

# Cosine similarity (n12 / sqrt(n1 * n2))
print(similarity.cosine(ba_1, ba_2))
# => 0.22360679774997896

# Jaccard index (n12 / (n1 + n2 - n12))
print(similarity.jaccard(ba_1, ba_2))
# => 0.125
```

# String transformation

`pprl_core.transform` contains factory functions for performing preprocessing on strings.

```python
from pprl_core import transform

# String normalization performs several steps. All non-ASCII characters are replaced with their
# closest ASCII variants. Unicode normalization in the NFKD form is performed. Non-ASCII characters
# are removed. All characters are converted to their lowercase counterparts and consecutive whitespaces 
# are reduced to a single one.
normalize = transform.normalize()
print(normalize("Müller-Ludenscheidt"))
# => "muller-ludenscheidt"

# Character filtering allows for the definition of a sequence of characters which must be removed
# from a string.
character_filter = transform.character_filter("äöüß")
print(character_filter("Müller-Ludenscheidt"))
# => "Mller-Ludenscheidt"

# Number formatting takes in any numeric string and reduces or expands it to a set amount of decimal places.
number_zero_digits = transform.number(0)
number_six_digits = transform.number(6)
print(number_zero_digits("12.34"))
# => "12"
print(number_six_digits("12.34"))
# => "12.340000"

# Date time formatting takes in date and time strings in a set format and outputs in another.
date_time = transform.date_time("%Y-%m-%d", "%d.%m.%Y")
print(date_time("2024-06-29"))
# => "29.06.2024"

# Phonetic code transformation applies a phonetic code on an input string. It uses the pyphonetics
# library under the hood.
from pyphonetics import Soundex

phonetic_code = transform.phonetic_code(Soundex())
print(phonetic_code("Müller-Ludenscheidt"))
# => "M464"

# Mapping transformation allows for single characters or entire character sequences to be
# replaced with another. 
mapping = transform.mapping({
    "male": "m",
    "female": "f"
})

print(mapping("male"))
# => "m"

# If no default value is set and no mapping is present, this will throw an error.
print(mapping("unknown"))
# => ValueError: value `unknown` has no mapping, or no default value is present

mapping_with_default = transform.mapping({
    "male": "m",
    "female": "f"
}, default_val="u")

# Setting a default value will prevent this error.
print(mapping("unknown"))
# => "u"

# By default, only entire strings are mapped. For inline transformations, set the corresponding 
# parameter to True.
mapping_inline = transform.mapping({
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss"
}, inline=True)

print(mapping_inline("Müller-Ludenscheidt"))
# => "Mueller-Ludenscheidt"
```

# Additional phonetic codes

`pprl_core.phonetics_extra` contains additional phonetic code implementations that are compatible with
[pyphonetics](https://github.com/Lilykos/pyphonetics).
At the time, only the "Kölner Phonetik" is implemented, which is a phonetic code that is specialized
for the German language.

```python
from pprl_core import phonetics_extra

cologne = phonetics_extra.ColognePhonetics()
print(cologne.phonetics("Müller-Ludenscheidt"))
# => "65752682"
```

# License

MIT.
