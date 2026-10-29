from pathlib import Path

import yaml


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for section in ("settings", "companies", "topics", "sources"):
        if section not in cfg:
            raise ValueError(f"config.yaml is missing the '{section}' section")
    return cfg


def news_queries(cfg: dict, source_key: str) -> list[str]:
    """All Google/Bing search queries: companies, topics, then extras (deduplicated, in order)."""
    queries = []
    for c in cfg["companies"]:
        queries += c.get("search", [])
    for t in cfg["topics"]:
        queries += t.get("search", [])
    queries += cfg["sources"].get(source_key, {}).get("extra_search", [])
    return list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
