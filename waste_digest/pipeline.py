"""Fetch -> filter -> tag -> dedupe -> flag new -> write reports."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import report_excel, report_html
from .dedupe import Cluster, cluster_articles, merge_related
from .history import History
from .models import Article, SourceStatus
from .sources import SOURCES
from .tagging import Tagger

GROUP_LABELS = {"core": "Core coverage", "peer": "Peers", "private": "Private players"}


def pick_hours(cfg: dict, now: datetime) -> int:
    s = cfg["settings"]
    tz = ZoneInfo(s.get("timezone", "America/New_York"))
    if now.astimezone(tz).weekday() == 0:  # Monday
        return int(s.get("monday_hours", 72))
    return int(s.get("default_hours", 24))


def fetch_all(cfg: dict, since: datetime, now: datetime, only: list[str] | None = None):
    articles: list[Article] = []
    statuses: list[SourceStatus] = []
    for key, label, module in SOURCES:
        if not cfg["sources"].get(key, {}).get("enabled", False) or (only and key not in only):
            continue
        status = SourceStatus(label)
        started = time.time()
        print(f"  fetching {label} ...", flush=True)
        try:
            found = module.fetch(cfg, since, now, status)
        except Exception as e:  # one broken source must never stop the digest
            status.fail("source crashed", e)
            found = []
        status.items = len(found)
        print(f"    {len(found)} items, {status.failures} errors, {time.time() - started:.0f}s", flush=True)
        articles += found
        statuses.append(status)
    return articles, statuses


def in_window(a: Article, since: datetime, tz) -> bool:
    if a.published is None:
        return True
    if a.date_only:
        return a.published.date() >= since.astimezone(tz).date()
    return a.published >= since


def _fmt_local(dt: datetime | None, tz) -> str:
    if not dt:
        return ""
    return dt.astimezone(tz).strftime("%b %-d, %-I:%M %p")


def build_digest(cfg, clusters: list[Cluster], history: History, statuses, now, since, hours, tz) -> dict:
    companies = {c["key"]: c for c in cfg["companies"]}
    company_order = [c["key"] for c in cfg["companies"]]
    topics = {t["key"]: t for t in cfg["topics"]}
    topic_order = [t["key"] for t in cfg["topics"]]

    sections: dict[str, dict] = {}
    for c in cfg["companies"]:
        sections["c:" + c["key"]] = {"key": c["key"], "kind": "company", "title": c["name"],
                                     "group": GROUP_LABELS.get(c.get("group"), "Other companies"), "items": []}
    for t in cfg["topics"]:
        sections["t:" + t["key"]] = {"key": t["key"], "kind": "topic", "title": t["name"],
                                     "group": "Industry", "items": []}
    sections["t:other"] = {"key": "other", "kind": "topic", "title": "Other industry news",
                           "group": "Industry", "items": []}

    for cl in clusters:
        comp = [k for k in company_order if any(k in a.companies for a in cl.articles)]
        hits: dict[str, int] = {}
        for a in cl.articles:
            for k, n in a.topic_hits.items():
                hits[k] = hits.get(k, 0) + n
        topic_keys = sorted(hits, key=lambda k: (-hits[k], topic_order.index(k) if k in topic_order else 99))
        p = cl.primary
        keys = cl.keys()
        item = {
            "id": sorted(keys)[0],
            "is_new": history.is_new(keys),
            "first_seen": history.first_seen(keys),
            "headline": p.title,
            "url": p.url,
            "source": p.source,
            "published": p.published.isoformat() if p.published else None,
            "published_local": _fmt_local(p.published, tz) if not p.date_only else p.published.strftime("%b %-d"),
            "summary": next((a.summary for a in cl.articles if a.summary), ""),
            "companies": comp,
            "company_names": [companies[k]["name"] for k in comp],
            "topics": topic_keys,
            "topic_names": [topics[k]["name"] for k in topic_keys if k in topics],
            "chatter": all(a.chatter for a in cl.articles),
            "origin": p.origin,
            "kind": p.kind,
            "others": [{"source": a.source, "url": a.url, "headline": a.title,
                        "published_local": _fmt_local(a.published, tz)}
                       for a in _distinct_outlets(cl.articles[1:], p.source)],
        }
        if comp:
            sections["c:" + comp[0]]["items"].append(item)
        elif topic_keys:
            sections["t:" + topic_keys[0]]["items"].append(item)
        else:
            sections["t:other"]["items"].append(item)

    for s in sections.values():
        s["items"].sort(key=lambda i: i["published"] or "", reverse=True)

    items = [i for s in sections.values() for i in s["items"]]
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_local": now.astimezone(tz).strftime("%a %b %-d, %Y, %-I:%M %p %Z"),
        "hours": hours,
        "since_local": since.astimezone(tz).strftime("%a %b %-d, %-I:%M %p %Z"),
        "stats": {
            "stories": len(items),
            "new": sum(i["is_new"] for i in items),
            "company_stories": sum(1 for i in items if i["companies"] and not i.get("chatter")),
            "chatter": sum(1 for i in items if i.get("chatter")),
            "articles": sum(1 + len(i["others"]) for i in items),
        },
        "sources": [vars(s) for s in statuses],
        "sections": [s for s in sections.values() if s["items"]],
    }


def _distinct_outlets(articles: list[Article], skip_source: str) -> list[Article]:
    seen = {skip_source}
    out = []
    for a in articles:
        if a.source not in seen:
            seen.add(a.source)
            out.append(a)
    return out


def write_brief(digest: dict, path: Path) -> None:
    """A compact text version of the digest, for Claude to read when writing the top-stories summary."""
    lines = [f"# Digest {digest['generated_local']} (last {digest['hours']}h)", ""]
    for s in digest["sections"]:
        lines.append(f"## {s['title']}")
        for i in s["items"]:
            flag = ("NEW " if i["is_new"] else "") + ("(chatter) " if i.get("chatter") else "")
            more = f" (+{len(i['others'])} outlets)" if i["others"] else ""
            lines.append(f"- {flag}[{i['id']}] {i['headline']} | {i['source']}{more} | {i['published_local']}"
                         + (f" | {i['summary']}" if i["summary"] else ""))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(config: dict, hours: int | None = None, out_root: str | Path = "reports",
        history_path: str | Path = "data/history.json", update_history: bool = True,
        only_sources: list[str] | None = None) -> Path:
    tz = ZoneInfo(config["settings"].get("timezone", "America/New_York"))
    now = datetime.now(timezone.utc)
    hours = hours or pick_hours(config, now)
    since = now - timedelta(hours=hours)
    print(f"Waste news digest: last {hours} hours (since {since.astimezone(tz):%b %-d %-I:%M %p %Z})")

    articles, statuses = fetch_all(config, since, now, only_sources)
    tagger = Tagger(config)
    kept = []
    for a in articles:
        if not a.title or not a.url or not in_window(a, since, tz) or tagger.is_noise(a):
            continue
        tagger.tag(a)
        if a.require_match and not tagger.is_relevant(a):
            continue
        kept.append(a)
    alias_words = {w for c in config["companies"] for alias in c.get("aliases", []) for w in alias.split()}
    clusters = merge_related(cluster_articles(kept), alias_words)
    print(f"  {len(articles)} fetched -> {len(kept)} in window and relevant -> {len(clusters)} unique stories")

    history = History(history_path, keep_days=int(config["settings"].get("history_days", 120)))
    digest = build_digest(config, clusters, history, statuses, now, since, hours, tz)
    digest["stats"]["fetched"] = len(articles)

    out_dir = Path(out_root) / now.astimezone(tz).strftime("%Y-%m-%d_%H%M")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "digest.json").write_text(json.dumps(digest, indent=1), encoding="utf-8")
    write_brief(digest, out_dir / "digest_brief.md")
    report_html.write(digest, out_dir / "digest.html")
    report_excel.write(digest, out_dir / "digest.xlsx")

    if update_history:
        for c in clusters:
            history.add(c.keys(), now)
        history.save(now)

    st = digest["stats"]
    print(f"  {st['stories']} stories ({st['new']} new, {st['company_stories']} company-specific)")
    print(f"REPORT_DIR={out_dir}")
    return out_dir


def rerender(report_dir: str | Path) -> Path:
    """Rebuild the HTML (e.g. after Claude adds top_stories.md)."""
    report_dir = Path(report_dir)
    digest = json.loads((report_dir / "digest.json").read_text(encoding="utf-8"))
    report_html.write(digest, report_dir / "digest.html")
    return report_dir / "digest.html"
