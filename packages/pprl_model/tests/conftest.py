import uuid

import pytest


@pytest.fixture(scope="session")
def uuid4():
    def _new_uuid():
        return str(uuid.uuid4())

    return _new_uuid
