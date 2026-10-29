"""Remembers which stories were already shown, so repeat runs can flag what's new."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class History:
    def __init__(self, path: str | Path, keep_days: int = 120):
        self.path = Path(path)
        self.keep_days = keep_days
        self.seen: dict[str, str] = {}
        if self.path.exists():
            self.seen = json.loads(self.path.read_text(encoding="utf-8")).get("seen", {})

    def is_new(self, keys: set[str]) -> bool:
        return not any(k in self.seen for k in keys)

    def first_seen(self, keys: set[str]) -> str | None:
        dates = [self.seen[k] for k in keys if k in self.seen]
        return min(dates) if dates else None

    def add(self, keys: set[str], when: datetime) -> None:
        stamp = when.astimezone(timezone.utc).isoformat(timespec="seconds")
        for k in keys:
            self.seen.setdefault(k, stamp)

    def save(self, now: datetime) -> None:
        cutoff = (now - timedelta(days=self.keep_days)).astimezone(timezone.utc).isoformat(timespec="seconds")
        self.seen = {k: v for k, v in self.seen.items() if v >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"seen": self.seen}, indent=0, sort_keys=True), encoding="utf-8")
