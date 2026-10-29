import math
import time

import feedparser

from ..config import news_queries
from ..http import get
from ..models import Article
from ..textutil import short_summary, strip_source_suffix, struct_to_dt, summary_is_just_title

URL = "https://news.google.com/rss/search"


def fetch(cfg, since, now, status):
    opts = cfg["sources"]["google_news"]
    days = max(1, math.ceil((now - since).total_seconds() / 86400))
    out = []
    for q in news_queries(cfg, "google_news"):
        params = {"q": f"{q} when:{days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
        try:
            status.requests += 1
            parsed = feedparser.parse(get(URL, params=params).content)
        except Exception as e:
            status.fail(q, e)
            continue
        for e in parsed.entries:
            source = (e.get("source") or {}).get("title", "").strip(" -")
            title = strip_source_suffix(e.get("title", ""), source)
            summary = short_summary(e.get("summary", ""))
            out.append(Article(
                title=title,
                url=e.get("link", ""),
                source=source or "Google News",
                published=struct_to_dt(e.get("published_parsed")),
                summary="" if summary_is_just_title(summary, title) else summary,
                require_match=True,
                origin="Google News",
            ))
        time.sleep(opts.get("delay_seconds", 1.0))
    return out
