__all__ = ["transform", "mask", "match"]

import json
import urllib.parse
from typing import TypeVar, Type

import httpx
from pprl_model import EntityTransformRequest, EntityTransformResponse, MatchRequest, MatchResponse, EntityMaskRequest, \
    EntityMaskResponse
from pydantic import BaseModel

from pprl_client.common import error_detail_of

_MI = TypeVar("_MI", bound=BaseModel)
_MO = TypeVar("_MO", bound=BaseModel)


def _coalesce_url(base_url: str, path: str, url: str | None = None) -> str:
    if url is None:
        url = urllib.parse.urljoin(base_url, path)

    return url


def _perform_request(url: str, model_in: _MI, model_out: Type[_MO]) -> _MO:
    r = httpx.post(url, json=model_in.model_dump())

    if r.status_code != 200:
        # bad request
        if r.status_code == 400:
            raise ValueError(f"bad request: {error_detail_of(r)}")

        # unimplemented
        if r.status_code == 501:
            raise ValueError(f"unimplemented parameter: {error_detail_of(r)}")

        # invalid request
        if r.status_code == 422:
            raise ValueError(f"invalid request: {json.dumps(error_detail_of(r), indent=2)}")

        # unknown error
        raise ValueError(f"unknown status code {r.status_code}: `{r.text}`")

    return model_out(**r.json())


def match(
        req: MatchRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
):
    url = _coalesce_url(base_url, "match/", url)
    return _perform_request(url, req, MatchResponse)


def transform(
        req: EntityTransformRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
) -> EntityTransformResponse:
    url = _coalesce_url(base_url, "transform/", url)
    return _perform_request(url, req, EntityTransformResponse)


def mask(
        req: EntityMaskRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
) -> EntityMaskResponse:
    url = _coalesce_url(base_url, "mask/", url)
    return _perform_request(url, req, EntityMaskResponse)
