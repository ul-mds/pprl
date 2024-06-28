import random
import uuid

import pprl_core.bits
import pytest
from bitarray import bitarray
from pprl_model import BitVectorEntity
from starlette.testclient import TestClient

from pprl_service.main import app


@pytest.fixture(scope="session")
def uuid4():
    def _new_uuid():
        return str(uuid.uuid4())

    return _new_uuid


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


@pytest.fixture(scope="session")
def bit_vector_entity_factory(bitarray_factory, uuid4):
    def _supply_bit_vector_entity():
        return BitVectorEntity(
            id=uuid4(),
            value=pprl_core.bits.to_base64(bitarray_factory()),
        )

    return _supply_bit_vector_entity


@pytest.fixture(scope="session")
def test_app():
    return app


@pytest.fixture(scope="session")
def test_client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client
