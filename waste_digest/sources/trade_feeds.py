import feedparser

from ..http import get
from ..models import Article
from ..textutil import clean_html, short_summary, struct_to_dt


def fetch(cfg, since, now, status):
    out = []
    for feed in cfg["sources"]["trade_feeds"].get("feeds", []):
        try:
            status.requests += 1
            parsed = feedparser.parse(get(feed["url"]).content)
        except Exception as e:
            status.fail(feed["name"], e)
            continue
        if not parsed.entries:
            status.fail(feed["name"], "feed returned no items")
        for e in parsed.entries:
            published = struct_to_dt(e.get("published_parsed") or e.get("updated_parsed"))
            out.append(Article(
                title=clean_html(e.get("title", "")),
                url=e.get("link", ""),
                source=feed["name"],
                published=published,
                summary=short_summary(e.get("summary", "")),
                origin="Trade feed",
                require_match=bool(feed.get("require_match")),
            ))
    return out
