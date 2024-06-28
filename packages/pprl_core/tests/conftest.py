import random

import pytest
from bitarray import bitarray


@pytest.fixture(scope="session")
def rng_factory():
    def _supply_rng():
        return random.Random(727)

    return _supply_rng


@pytest.fixture(scope="session")
def rng(rng_factory):
    return rng_factory()


@pytest.fixture(scope="session")
def bitarray_factory(rng):
    def _supply_bitarray():
        # draw random numbers
        rand_vals = [rng.random() for _ in range(64)]
        # convert it to list of bools
        return bitarray([i < 0.5 for i in rand_vals])

    return _supply_bitarray
