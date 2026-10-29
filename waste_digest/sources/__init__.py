from . import bing_news, federal_register, gdelt, google_news, sec_edgar, trade_feeds

# (config key, label shown in the report, module)
SOURCES = [
    ("trade_feeds", "Trade publications (RSS)", trade_feeds),
    ("sec_edgar", "SEC EDGAR filings", sec_edgar),
    ("federal_register", "Federal Register (EPA)", federal_register),
    ("google_news", "Google News", google_news),
    ("bing_news", "Bing News", bing_news),
    ("gdelt", "GDELT", gdelt),
]
