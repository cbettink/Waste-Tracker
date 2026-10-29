import time

import requests

USER_AGENT = "Mozilla/5.0 (compatible; WasteNewsDigest/1.0; +https://github.com/cbettink/Waste-Tracker)"

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers["User-Agent"] = USER_AGENT
    return _session


def get(url, params=None, headers=None, timeout=25, retries=2, backoff=3.0) -> requests.Response:
    """GET with a couple of retries on timeouts, 429s and 5xx errors."""
    for attempt in range(retries + 1):
        try:
            r = session().get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError("unreachable")
