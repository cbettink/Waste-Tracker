import time
from datetime import datetime, timezone

from ..http import get
from ..models import Article
from ..textutil import clean_html

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
PAUSE = 6  # GDELT asks for at most one request every 5 seconds


def _query(q, hours):
    params = {"query": f"{q} sourcecountry:US sourcelang:english", "mode": "artlist", "format": "json",
              "maxrecords": "100", "sort": "datedesc", "timespan": f"{max(1, int(round(hours)))}h"}
    for attempt in range(3):
        r = get(URL, params=params, retries=0)
        try:
            return r.json()
        except ValueError:  # rate-limit notice comes back as plain text
            if attempt == 2:
                raise RuntimeError(r.text[:120])
            time.sleep(PAUSE * (attempt + 2))


def fetch(cfg, since, now, status):
    hours = (now - since).total_seconds() / 3600
    out = []
    for i, q in enumerate(cfg["sources"]["gdelt"].get("search", [])):
        if i:
            time.sleep(PAUSE)
        try:
            status.requests += 1
            data = _query(q, hours)
        except Exception as e:
            status.fail(q, e)
            continue
        for a in data.get("articles", []):
            try:
                published = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                published = None
            out.append(Article(
                title=clean_html(a.get("title", "")),
                url=a.get("url", ""),
                source=a.get("domain", "GDELT"),
                published=published,
                require_match=True,
                origin="GDELT",
            ))
    return out
