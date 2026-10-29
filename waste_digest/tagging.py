"""Tag articles with companies and topics using the keyword rules in config.yaml."""
import re

from .models import Article


def keyword_regex(kw: str, case_sensitive: bool = False) -> re.Pattern:
    """Whole-word match. Short ALL-CAPS keywords are case-sensitive; trailing * = any ending."""
    kw = kw.strip()
    wildcard = kw.endswith("*")
    core = kw.rstrip("*")
    pattern = re.escape(core).replace(r"\ ", r"\s+")
    pattern = r"(?<![\w&])" + pattern + (r"[\w-]*" if wildcard else r"(?![\w&])")
    case_sensitive = case_sensitive or (core.isupper() and len(core) <= 6)
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


class Tagger:
    def __init__(self, cfg: dict):
        self.companies = []
        for c in cfg["companies"]:
            # company names are proper nouns: match them with the capitalization written
            aliases = [keyword_regex(a, case_sensitive=True) for a in c.get("aliases", [])]
            excludes = [keyword_regex(x) for x in c.get("exclude", [])]
            self.companies.append((c["key"], aliases, excludes))
        self.topics = [(t["key"], [keyword_regex(k) for k in t.get("keywords", [])]) for t in cfg["topics"]]
        self.noise = [keyword_regex(n) for n in cfg["settings"].get("noise_headlines", [])]
        self.bad_sources = {x.lower() for x in cfg["settings"].get("exclude_sources", [])}
        self.relevance = [keyword_regex(k) for k in cfg["settings"].get("relevance_keywords", [])]
        self.chatter_sources = tuple(x.lower() for x in cfg["settings"].get("chatter_sources", []))
        self.chatter_words = [keyword_regex(k) for k in cfg["settings"].get("chatter_headlines", [])]
        self.hard_news = [keyword_regex(k) for k in cfg["settings"].get("hard_news_words", [])]

    def is_noise(self, a: Article) -> bool:
        letters = [ch for ch in a.title if ch.isalpha()]
        if letters and sum(ch.isascii() for ch in letters) / len(letters) < 0.6:
            return True  # not in English
        return a.source.lower() in self.bad_sources or any(n.search(a.title) for n in self.noise)

    def is_relevant(self, a: Article) -> bool:
        """For general-business feeds: keep only stories naming a tracked company or a waste word."""
        text = f"{a.title}. {a.summary}"
        return bool(a.companies) or any(p.search(text) for p in self.relevance)

    def match_companies(self, text: str) -> list[str]:
        found = []
        for key, aliases, excludes in self.companies:
            t = text
            for x in excludes:
                t = x.sub(" ", t)
            if any(a.search(t) for a in aliases):
                found.append(key)
        return found

    def topic_hits(self, text: str) -> dict[str, int]:
        hits = {}
        for key, patterns in self.topics:
            n = sum(len(p.findall(text)) for p in patterns)
            if n:
                hits[key] = n
        return hits

    def tag(self, a: Article) -> None:
        text = f"{a.title}. {a.summary}"
        a.companies = list(dict.fromkeys(a.forced_companies + self.match_companies(text)))
        hits = self.topic_hits(text)
        for t in a.forced_topics:
            hits[t] = hits.get(t, 0) + 1
        # headline matches count double: the headline says what the story is about
        for t, n in self.topic_hits(a.title).items():
            hits[t] = hits.get(t, 0) + n
        a.topic_hits = hits
        a.chatter = self.is_chatter(a)

    def is_chatter(self, a: Article) -> bool:
        if any(p.search(a.title) for p in self.chatter_words):
            return True
        if a.source.lower().startswith(self.chatter_sources):
            return not any(p.search(a.title) for p in self.hard_news)
        return False
