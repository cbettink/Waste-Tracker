# Waste News Digest — instructions for Claude

The owner is an equity research analyst covering US waste (WM, RSG, WCN + peers). They use
Claude Code from a phone: no local terminal. Explain things simply, and do all the work yourself.

## "Run the waste news digest [for the last N hours/days]"

1. `pip install -q -r requirements.txt`
2. `python run_digest.py --hours N` (omit `--hours` for the default: 24h, or 72h on Mondays).
   `--days N` also works. It takes ~3 minutes and prints `REPORT_DIR=reports/<timestamp>`.
3. Read `REPORT_DIR/digest_brief.md` and write `REPORT_DIR/top_stories.md`:
   - Heading `## Top things to know`, then up to 10 bullets, most important for a waste-sector
     equity analyst first: core companies (WM, RSG, WCN) news, M&A, litigation/regulatory actions,
     earnings/guidance, pricing/volume signals, notable landfill or RNG developments.
   - Each bullet: **bold short label**, one sentence of why it matters, then `[Source](url)`
     (take the url from `digest.json`). Prefer NEW items; ignore "(chatter)" items unless material.
   - Only state facts that appear in the digest. Do not invent numbers.
4. `python run_digest.py --render REPORT_DIR` to add the top stories to the HTML.
5. Commit `reports/`, `data/history.json` and push to `main` (message: "Digest <date>").
6. Send the user `REPORT_DIR/digest.html` (display: render) and `REPORT_DIR/digest.xlsx`
   (display: attach) with SendUserFile, plus a 3–5 line chat summary. Mention any source
   that failed (see the "Sources checked" table / digest.json `sources`).

Test runs that shouldn't mark stories as seen: add `--no-history`.

## Editing settings
All companies, aliases, topics, keywords, search queries, noise filters and sources live in
`config.yaml`. When the user asks to add/remove a company, keyword, topic or source, edit only
that file (keep its comments), run `python -m pytest -q`, do a quick check with
`python run_digest.py --no-history --sources trade_feeds sec_edgar`, then commit and push.

## Layout
- `waste_digest/sources/` one module per source (`fetch(cfg, since, now, status)` -> Articles)
- `tagging.py` keyword rules, `dedupe.py` story grouping, `history.py` seen-story memory
- `report_html.py` mobile HTML, `report_excel.py` Excel, `pipeline.py` glue
- Known limits: GDELT rate-limits this cloud network (disabled); EPA newsroom blocks bots (EPA
  covered via Federal Register); CourtListener needs a free API token (not yet wired up).
