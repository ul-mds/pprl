import sys

import httpx
from httpx import HTTPError

if __name__ == "__main__":
    health_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/healthz"
    print(f"GET {health_url}... ", end="")

    try:
        r = httpx.get(health_url, follow_redirects=True)
        print(r.status_code)
        r.raise_for_status()
    except HTTPError as e:
        print("failed")
        print(e, file=sys.stderr)
        exit(1)
