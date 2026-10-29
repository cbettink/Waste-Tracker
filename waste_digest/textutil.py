import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")

STOPWORDS = set("""a an the and or of to in on for at by with from as is are was were be been it its this that
into over after about amid says say said new will could would may can how why what who""".split())


def clean_html(text: str | None) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = html.unescape(text).replace("\u00ad", "")  # drop soft hyphens
    return _WS_RE.sub(" ", text).strip()


def short_summary(text: str, max_chars: int = 320) -> str:
    """First one or two sentences, capped at max_chars."""
    text = clean_html(text)
    text = re.sub(r"\s*(The post .* appeared first on .*|Continue reading.*|Read more.*)$", "", text)
    if not text:
        return ""
    sentences = _SENT_RE.split(text)
    out = sentences[0]
    if len(sentences) > 1 and len(out) + len(sentences[1]) < max_chars:
        out += " " + sentences[1]
    if len(out) > max_chars:
        out = out[: max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


def strip_source_suffix(title: str, source: str) -> str:
    """Google News titles end with ' - Outlet Name'."""
    title = clean_html(title).rstrip(" -")
    if source and title.endswith(" - " + source):
        return title[: -len(source) - 3].strip()
    return title


def summary_is_just_title(summary: str, title: str) -> bool:
    if not summary:
        return True
    return len(summary) < len(title) + 60 and fuzz.partial_ratio(title.lower(), summary.lower()) > 90


def normalize_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(w for w in words if w not in STOPWORDS)


def canonical_url(url: str) -> str:
    p = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "fbclid", "gclid", "ocid"))]
    host = p.netloc.lower().removeprefix("www.")
    return urlunparse(("", host, p.path.rstrip("/"), "", urlencode(query), ""))


def title_key(title: str) -> str:
    return "t:" + hashlib.sha1(normalize_title(title).encode()).hexdigest()[:16]


def url_key(url: str) -> str:
    return "u:" + hashlib.sha1(canonical_url(url).encode()).hexdigest()[:16]


def struct_to_dt(st) -> datetime | None:
    if not st:
        return None
    return datetime(*st[:6], tzinfo=timezone.utc)
