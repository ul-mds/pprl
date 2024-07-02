import httpx


def error_detail_of(r: httpx.Response) -> str:
    return r.json()["detail"]
