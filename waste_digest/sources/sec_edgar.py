import time

from dateutil import parser as dateparser

from ..http import get
from ..models import Article

ITEMS_8K = {
    "1.01": "Material definitive agreement", "1.02": "Termination of material agreement",
    "1.05": "Cybersecurity incident", "2.01": "Completed acquisition/disposition",
    "2.02": "Results of operations", "2.03": "New financial obligation", "2.05": "Exit/disposal costs",
    "2.06": "Material impairment", "3.01": "Delisting notice", "3.02": "Unregistered equity sale",
    "4.01": "Auditor change", "4.02": "Non-reliance on prior financials", "5.01": "Change in control",
    "5.02": "Director/officer change", "5.03": "Bylaw/charter amendment", "5.07": "Shareholder vote results",
    "7.01": "Regulation FD disclosure", "8.01": "Other events", "9.01": "Financial statements/exhibits",
}


def fetch(cfg, since, now, status):
    headers = {"User-Agent": cfg["settings"].get("sec_user_agent") or "WasteNewsDigest research tool"}
    out = []
    for c in cfg["companies"]:
        cik = c.get("sec_cik")
        if not cik:
            continue
        forms = {str(f).upper() for f in c.get("sec_forms", ["8-K"])}
        try:
            status.requests += 1
            data = get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", headers=headers).json()
        except Exception as e:
            status.fail(c["key"], e)
            continue
        recent = data.get("filings", {}).get("recent", {})
        for i, form in enumerate(recent.get("form", [])[:200]):
            if form.upper() not in forms:
                continue
            accepted = dateparser.isoparse(recent["acceptanceDateTime"][i])
            if accepted < since:
                continue
            acc = recent["accessionNumber"][i]
            doc = recent["primaryDocument"][i]
            items = [x.strip() for x in (recent.get("items", [""] * (i + 1))[i] or "").split(",") if x.strip()]
            described = [ITEMS_8K.get(x, f"Item {x}") for x in items if x != "9.01"]
            desc = recent.get("primaryDocDescription", [""] * (i + 1))[i] or ""
            title = f"{c['key']} files {form}"
            if described:
                title += ": " + "; ".join(described)
            elif desc and form.upper() not in desc.upper():
                title += f": {desc}"
            out.append(Article(
                title=title,
                url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}",
                source="SEC EDGAR",
                published=accepted,
                summary=f"{c['name']} filed a {form} with the SEC"
                        + (f" (items {', '.join(items)})." if items else "."),
                origin="SEC EDGAR",
                kind="filing",
                forced_companies=[c["key"]],
            ))
        time.sleep(0.2)  # SEC limit is 10 requests/second
    return out
