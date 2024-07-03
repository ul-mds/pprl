import base64
import os
import urllib.parse
import uuid
from random import Random

import pytest
from click.testing import CliRunner
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


@pytest.fixture(scope="session")
def env_pprl_base_url() -> str:
    return os.environ.get("PPRL_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def env_pprl_testcontainer_image() -> str:
    return os.environ.get("PPRL_TESTCONTAINER_IMAGE", "ghcr.io/ul-mds/pprl:latest")


@pytest.fixture(scope="session")
def env_pprl_use_testcontainer() -> bool:
    return os.environ.get("PPRL_USE_TESTCONTAINER", "0") == "1"


@pytest.fixture(scope="session")
def env_pprl_request_timeout_secs() -> int:
    return int(os.environ.get("PPRL_REQUEST_TIMEOUT_SECS", "30"))


@pytest.fixture(scope="session")
def testcontainer_url(env_pprl_use_testcontainer, env_pprl_testcontainer_image) -> str | None:
    if not env_pprl_use_testcontainer:
        yield None
        return

    with DockerContainer(env_pprl_testcontainer_image).with_exposed_ports(8000) as container:
        wait_for_logs(container, "Application startup complete")
        yield urllib.parse.urlunsplit((
            "http",
            f"{container.get_container_host_ip()}:{container.get_exposed_port(8000)}",
            "", "", ""
        ))


@pytest.fixture(scope="session")
def pprl_base_url(env_pprl_base_url, testcontainer_url) -> str:
    return testcontainer_url or env_pprl_base_url


@pytest.fixture(scope="session", autouse=True)
def service_sanity_check(pprl_base_url):
    import httpx

    r = httpx.get(urllib.parse.urljoin(pprl_base_url, "healthz"))
    assert r.status_code == 200


@pytest.fixture(scope="session")
def rng_factory():
    def _rng():
        return Random(727)

    return _rng


@pytest.fixture()
def rng(rng_factory):
    return rng_factory()


@pytest.fixture(scope="session")
def uuid4_factory():
    def _uuid4():
        return str(uuid.uuid4())

    return _uuid4


@pytest.fixture(scope="session")
def base64_factory(rng_factory):
    rng = rng_factory()

    def _b64():
        return base64.b64encode(rng.randbytes(16)).decode("utf-8")

    return _b64


@pytest.fixture(scope="session", autouse=True)
def faker_session_locale():
    return ["en_US"]


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return 727


@pytest.fixture()
def cli_runner():
    return CliRunner()
