"""Group the same story covered by several outlets into one cluster."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

from rapidfuzz import fuzz

from .models import Article
from .textutil import canonical_url, normalize_title, title_key, url_key

# Which copy of a story to show first: trade press and primary sources beat aggregators.
ORIGIN_RANK = {"Trade feed": 0, "SEC EDGAR": 0, "Federal Register": 0, "Bing News": 1, "Google News": 2, "GDELT": 3}
MAX_DAYS_APART = timedelta(days=4)


@dataclass
class Cluster:
    articles: list[Article] = field(default_factory=list)
    norms: list[str] = field(default_factory=list)

    @property
    def primary(self) -> Article:
        return self.articles[0]

    def keys(self) -> set[str]:
        keys = set()
        for a in self.articles:
            keys.add(title_key(a.title))
            if a.url:
                keys.add(url_key(a.url))
        return keys


def _rank(a: Article):
    return (ORIGIN_RANK.get(a.origin, 5), 0 if a.summary else 1, -(a.published.timestamp() if a.published else 0))


def same_story(norm_a: str, norm_b: str) -> bool:
    if not norm_a or not norm_b:
        return False
    if fuzz.token_sort_ratio(norm_a, norm_b) >= 82:
        return True
    # one headline contains nearly all the words of the other (e.g. extra "- Local TV" text)
    shorter = min(len(norm_a.split()), len(norm_b.split()))
    return shorter >= 5 and fuzz.token_set_ratio(norm_a, norm_b) >= 92


def cluster_articles(articles: list[Article]) -> list[Cluster]:
    clusters: list[Cluster] = []
    by_url: dict[str, Cluster] = {}
    for a in sorted(articles, key=_rank):
        cu = canonical_url(a.url) if a.url else None
        if cu and cu in by_url:
            c = by_url[cu]
            c.articles.append(a)
            continue
        norm = normalize_title(a.title)
        match = None
        for c in clusters:
            p = c.primary.published
            if p and a.published and abs(p - a.published) > MAX_DAYS_APART:
                continue
            if any(same_story(norm, n) for n in c.norms):
                match = c
                break
        if match is None:
            match = Cluster()
            clusters.append(match)
        match.articles.append(a)
        match.norms.append(norm)
        if cu:
            by_url[cu] = match
    return clusters


# ---------------------------------------------------------------------------
# Second pass: local outlets word the same story very differently
# ("Bunnell rejects landfill" / "Project Butterfly landfill scrapped"). Merge clusters
# that share a distinctive name (a capitalized word that never appears in lower case
# in any headline and is used by only a handful of stories) plus one more content word.
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’]+")
GENERIC = set("""county city town state village board council commission commissioners department district
landfill landfills recycling recycle waste trash garbage solid news update updates report residents
officials north south east west new says said after over plan plans proposed proposal project
monday tuesday wednesday thursday friday saturday sunday sanitation truck trucks collection center centre
facility plant station transfer hauler haulers environmental services company group energy renewable
natural fire department public works program government governor mayor court judge federal""".split())
MAX_STORIES_PER_NAME = 10
MERGE_WINDOW = timedelta(hours=72)


def _distinctive_names(clusters: list[Cluster], skip: set[str]) -> dict[str, set[int]]:
    """Proper names: capitalized mid-headline in a sentence-case headline, never seen in lower case."""
    lower_seen, proper_evidence, cap_in = set(), set(), {}
    for idx, c in enumerate(clusters):
        for a in c.articles:
            words = _WORD_RE.findall(a.title)
            sentence_case = sum(w[0].islower() for w in words) >= len(words) / 2
            for pos, w in enumerate(words):
                lw = w.lower().strip("'’")
                if w[0].islower():
                    lower_seen.add(lw)
                    continue
                if len(lw) < 4 or lw in GENERIC or lw in skip:
                    continue
                cap_in.setdefault(lw, set()).add(idx)
                if sentence_case and pos > 0:
                    proper_evidence.add(lw)
    return {w: ids for w, ids in cap_in.items()
            if w in proper_evidence and w not in lower_seen and 2 <= len(ids) <= MAX_STORIES_PER_NAME}


def _content_words(c: Cluster) -> set[str]:
    return {w for n in c.norms for w in n.split() if len(w) >= 4 and not w.isdigit()}


def merge_related(clusters: list[Cluster], skip_words: set[str] = frozenset()) -> list[Cluster]:
    # stock chatter is left alone: its Title Case headlines make names unreliable
    eligible = [c for c in clusters if not all(a.chatter for a in c.articles)]
    rest = [c for c in clusters if all(a.chatter for a in c.articles)]
    return _merge(eligible, skip_words) + rest


def _merge(clusters: list[Cluster], skip_words) -> list[Cluster]:
    names = _distinctive_names(clusters, {w.lower() for w in skip_words})
    parent = list(range(len(clusters)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    words = [_content_words(c) for c in clusters]
    for name, ids in names.items():
        ids = sorted(ids)
        for x, i in enumerate(ids):
            for j in ids[x + 1:]:
                pi, pj = clusters[i].primary.published, clusters[j].primary.published
                if pi and pj and abs(pi - pj) > MERGE_WINDOW:
                    continue
                if (words[i] & words[j]) - {name}:
                    parent[find(j)] = find(i)

    groups: dict[int, Cluster] = {}
    for i, c in enumerate(clusters):
        root = find(i)
        if root not in groups:
            groups[root] = Cluster()
        g = groups[root]
        g.articles += c.articles
        g.norms += c.norms
    for g in groups.values():
        g.articles.sort(key=_rank)
    return list(groups.values())
