__all__ = ["transform", "mask", "match", "AttributeStats", "compute_attribute_stats"]

import json
import math
import urllib.parse
from collections import defaultdict, Counter
from typing import TypeVar, Type, NamedTuple

import httpx
import pprl_core
from pprl_model import EntityTransformRequest, EntityTransformResponse, VectorMatchRequest, VectorMatchResponse, \
    EntityMaskRequest, EntityMaskResponse, AttributeValueEntity, BaseTransformRequest
from pydantic import BaseModel

from pprl_client.common import error_detail_of

_MI = TypeVar("_MI", bound=BaseModel)
_MO = TypeVar("_MO", bound=BaseModel)

_DEFAULT_TIMEOUT_SECS = 10


class AttributeStats(NamedTuple):
    average_tokens: float
    ngram_entropy: float


def _coalesce_url(base_url: str, path: str, url: str | None = None) -> str:
    if url is None:
        url = urllib.parse.urljoin(base_url, path)

    return url


def _perform_request(url: str, model_in: _MI, model_out: Type[_MO],
                     timeout_secs: int | None = _DEFAULT_TIMEOUT_SECS) -> _MO:
    r = httpx.post(url, json=model_in.model_dump(), timeout=timeout_secs)

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
        req: VectorMatchRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
        timeout_secs: int | None = _DEFAULT_TIMEOUT_SECS
):
    url = _coalesce_url(base_url, "match/", url)
    return _perform_request(url, req, VectorMatchResponse, timeout_secs)


def transform(
        req: EntityTransformRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
        timeout_secs: int | None = _DEFAULT_TIMEOUT_SECS
) -> EntityTransformResponse:
    url = _coalesce_url(base_url, "transform/", url)
    return _perform_request(url, req, EntityTransformResponse, timeout_secs)


def mask(
        req: EntityMaskRequest,
        base_url="http://localhost:8000",
        url: str | None = None,
        timeout_secs: int | None = _DEFAULT_TIMEOUT_SECS
) -> EntityMaskResponse:
    url = _coalesce_url(base_url, "mask/", url)
    return _perform_request(url, req, EntityMaskResponse, timeout_secs)


def split_into_wordlist(entities: list[AttributeValueEntity]) -> dict[str, list[str]]:
    """Split a list of entities into a dictionary of attribute names to values."""
    attr_name_to_wordlist: dict[str, list[str]] = defaultdict(list)

    for entity in entities:
        for attr_name, attr_value in entity.attributes.items():
            attr_name_to_wordlist[attr_name].append(attr_value)

    return attr_name_to_wordlist


def tokenize_wordlist(wordlist: list[str], token_size=2, padding="_") -> list[set[str]]:
    return [pprl_core.common.tokenize(word, q=token_size, padding=padding) for word in wordlist]


def compute_average_tokens_for_token_list(token_list: list[set[str]]) -> float:
    total_token_count = sum(len(tokens) for tokens in token_list)

    if total_token_count == 0:
        return 0

    return total_token_count / len(token_list)


def count_tokens_in_token_list(token_list: list[set[str]]) -> dict[str, int]:
    token_counter: dict[str, int] = Counter()

    for word_tokens in token_list:
        for token in word_tokens:
            token_counter[token] += 1

    return token_counter


def compute_ngram_entropy(token_counts: dict[str, int]) -> float:
    total_ngram_count = sum(c for c in token_counts.values())
    entropy = 0

    for count in token_counts.values():
        p = count / total_ngram_count
        entropy += p * math.log2(p)

    return -entropy


def compute_attribute_stats(
        entities: list[AttributeValueEntity],
        base_transform_request: BaseTransformRequest,
        token_size: int = 2,
        padding: str = "_",
        base_url="http://localhost:8000",
        url: str | None = None,
        timeout_secs: int | None = _DEFAULT_TIMEOUT_SECS,
        batch_size: int = 100,
):
    processed_entities: list[AttributeValueEntity] = []

    for i in range(0, len(entities), batch_size):
        transform_req = base_transform_request.with_entities(entities[i:i + batch_size])
        transform_resp = transform(transform_req, base_url=base_url, url=url, timeout_secs=timeout_secs)
        processed_entities.extend(transform_resp.entities)

    attr_name_to_wordlist = split_into_wordlist(processed_entities)

    def _compute_stats_for_wordlist(wordlist: list[str]) -> AttributeStats:
        token_list = tokenize_wordlist(wordlist, token_size=token_size, padding=padding)
        average_tokens = compute_average_tokens_for_token_list(token_list)
        token_counts = count_tokens_in_token_list(token_list)
        ngram_entropy = compute_ngram_entropy(token_counts)

        return AttributeStats(average_tokens, ngram_entropy)

    return {
        attr_name: _compute_stats_for_wordlist(wordlist) for attr_name, wordlist in attr_name_to_wordlist.items()
    }
