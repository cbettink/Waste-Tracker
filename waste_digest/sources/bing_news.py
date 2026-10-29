import time
from urllib.parse import parse_qs, urlparse

import feedparser

from ..config import news_queries
from ..http import get
from ..models import Article
from ..textutil import clean_html, short_summary, struct_to_dt

URL = "https://www.bing.com/news/search"


def _real_url(link: str) -> str:
    """Bing wraps links in a click-tracking URL; pull out the article URL."""
    qs = parse_qs(urlparse(link).query)
    return qs.get("url", [link])[0]


def fetch(cfg, since, now, status):
    opts = cfg["sources"]["bing_news"]
    hours = (now - since).total_seconds() / 3600
    params_extra = {}
    if hours <= 24:
        params_extra["qft"] = 'interval="7"'   # past 24 hours
    elif hours <= 24 * 7:
        params_extra["qft"] = 'interval="8"'   # past week
    out = []
    for q in news_queries(cfg, "bing_news"):
        try:
            status.requests += 1
            r = get(URL, params={"q": q, "format": "rss", **params_extra})
            parsed = feedparser.parse(r.content)
        except Exception as e:
            status.fail(q, e)
            continue
        for e in parsed.entries:
            out.append(Article(
                title=clean_html(e.get("title", "")),
                url=_real_url(e.get("link", "")),
                source=e.get("news_source") or "Bing News",
                published=struct_to_dt(e.get("published_parsed")),
                summary=short_summary(e.get("summary", "")),
                require_match=True,
                origin="Bing News",
            ))
        time.sleep(opts.get("delay_seconds", 1.0))
    return out
