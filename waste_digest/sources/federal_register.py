from datetime import datetime, timezone

from ..http import get
from ..models import Article
from ..textutil import short_summary

URL = "https://www.federalregister.gov/api/v1/documents.json"
FIELDS = ["title", "abstract", "html_url", "publication_date", "type", "document_number"]


def fetch(cfg, since, now, status):
    opts = cfg["sources"]["federal_register"]
    out = []
    for term in opts.get("terms", []):
        params = [("conditions[term]", f'"{term}"' if " " in term else term),
                  ("conditions[publication_date][gte]", since.date().isoformat()),
                  ("per_page", "100"), ("order", "newest")]
        params += [("conditions[type][]", t) for t in opts.get("types", [])]
        if opts.get("agency"):
            params.append(("conditions[agencies][]", opts["agency"]))
        params += [("fields[]", f) for f in FIELDS]
        try:
            status.requests += 1
            data = get(URL, params=params).json()
        except Exception as e:
            status.fail(term, e)
            continue
        for d in data.get("results", []):
            pub = datetime.fromisoformat(d["publication_date"]).replace(hour=12, tzinfo=timezone.utc)
            out.append(Article(
                title=f"EPA {d.get('type', 'document')}: {d.get('title', '')}",
                url=d.get("html_url", ""),
                source="Federal Register",
                published=pub,
                summary=short_summary(d.get("abstract") or ""),
                origin="Federal Register",
                kind="regulation",
                date_only=True,
                forced_topics=["regulation_policy"],
            ))
    return out
