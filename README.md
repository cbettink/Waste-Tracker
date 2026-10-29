# Waste News Digest

Daily digest of US waste-industry news: company news for WM, RSG, WCN and peers, plus industry
topics (landfills, recycling, RNG, pricing/volumes, regulation, M&A, innovation, labor/safety).

**Sources:** trade press RSS (Waste Dive, Waste360, Waste Today, Recycling Today, Resource
Recycling, E-Scrap News, BioCycle, Waste Advantage, Packaging/Utility/Construction Dive),
Google News and Bing News searches (these catch local outlets), SEC EDGAR filings, and the Federal Register (EPA).

**Output:** `reports/<date_time>/digest.html` (phone-friendly), `digest.xlsx` (filterable),
and `data/history.json` so repeat runs flag only new stories.

```
pip install -r requirements.txt
python run_digest.py              # last 24h (72h on Mondays)
python run_digest.py --days 7     # last week
```

Edit `config.yaml` to change companies, keywords, topics and sources.
