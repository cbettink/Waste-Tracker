from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    source: str                      # outlet name, e.g. "Waste Dive"
    published: datetime | None       # timezone-aware UTC
    summary: str = ""
    origin: str = ""                 # how we found it, e.g. "Google News", "Trade feed"
    kind: str = "news"               # news | filing | regulation
    date_only: bool = False          # published has a date but no time
    require_match: bool = False      # drop unless a company or waste keyword matches
    chatter: bool = False            # stock-site rewrite / analyst note
    forced_companies: list[str] = field(default_factory=list)
    forced_topics: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    topic_hits: dict[str, int] = field(default_factory=dict)


@dataclass
class SourceStatus:
    name: str
    requests: int = 0
    failures: int = 0
    items: int = 0
    errors: list[str] = field(default_factory=list)

    def fail(self, what: str, err: Exception | str) -> None:
        self.failures += 1
        msg = f"{what}: {err}"
        self.errors.append(msg[:300])
