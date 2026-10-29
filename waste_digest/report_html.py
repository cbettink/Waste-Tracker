"""Mobile-first, single-file HTML report."""
from __future__ import annotations

import html
import re
from pathlib import Path

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1b;--muted:#6b6a65;--line:#e4e2dc;--accent:#1f6f4a;
--accent-soft:#e3f1ea;--new:#c2410c;--new-soft:#fdeee5;--chip:#efede8;--link:#14532d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141513;--card:#1d1f1c;--ink:#ecebe6;
--muted:#a3a29b;--line:#2f322d;--accent:#5cc28f;--accent-soft:#1d3428;--new:#fb923c;--new-soft:#3a2416;
--chip:#2a2c28;--link:#8ad7ad}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:760px;margin:0 auto;padding:0 16px 48px}
header{padding:20px 0 8px}
h1{font-size:1.45rem;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:.9rem}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 4px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 10px;font-size:.85rem}
.stat b{font-size:1.05rem;margin-right:3px}
.stat.new b{color:var(--new)}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line)}
.controls{display:flex;gap:8px;align-items:center}
.controls input[type=search]{flex:1;min-width:0;font-size:16px;padding:8px 10px;border:1px solid var(--line);
border-radius:10px;background:var(--card);color:var(--ink)}
.toggle{display:flex;align-items:center;gap:6px;font-size:.85rem;white-space:nowrap;background:var(--card);
border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.nav{display:flex;gap:6px;overflow-x:auto;padding-top:8px;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}
.nav a{flex:none;font-size:.8rem;text-decoration:none;color:var(--ink);background:var(--chip);border-radius:999px;
padding:5px 10px}
.nav a span{color:var(--muted)}
.group{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:28px 0 0}
details.sec{margin-top:10px}
details.sec>summary{list-style:none;cursor:pointer;display:flex;align-items:baseline;gap:8px;padding:6px 0}
details.sec>summary::-webkit-details-marker{display:none}
details.sec>summary h2{font-size:1.1rem;margin:0}
details.sec>summary .n{color:var(--muted);font-size:.85rem}
details.sec>summary .nn{color:var(--new);font-size:.8rem;font-weight:600}
details.sec>summary::after{content:"▾";margin-left:auto;color:var(--muted)}
details.sec:not([open])>summary::after{content:"▸"}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0}
.card.new{border-left:4px solid var(--new)}
.tags{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}
.tag{font-size:.7rem;background:var(--chip);color:var(--muted);border-radius:6px;padding:2px 6px}
.tag.co{background:var(--accent-soft);color:var(--accent);font-weight:600}
.tag.newb{background:var(--new-soft);color:var(--new);font-weight:700}
.card h3{font-size:1rem;margin:0;line-height:1.3}
.card h3 a{color:var(--ink);text-decoration:none}
.card h3 a:active,.card h3 a:hover{color:var(--link);text-decoration:underline}
.meta{color:var(--muted);font-size:.8rem;margin-top:4px}
.sum{font-size:.9rem;margin:6px 0 0}
.more{margin-top:6px;font-size:.8rem}
.more summary{color:var(--link);cursor:pointer}
.more ul{margin:6px 0 0;padding-left:18px}
.more li{margin:3px 0}
.more a{color:var(--link)}
details.chat{margin:6px 0 4px}
details.chat>summary{cursor:pointer;font-size:.85rem;color:var(--muted);padding:6px 2px}
details.chat .card{opacity:.92}
.top{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:12px;
padding:4px 16px;margin-top:16px}
.top h2{font-size:1.05rem;margin:12px 0 4px}
.top ul{padding-left:18px}
.top li{margin:6px 0;font-size:.93rem}
.top a{color:var(--link)}
.health{margin-top:32px;font-size:.8rem;color:var(--muted)}
.health table{border-collapse:collapse;width:100%;margin-top:6px}
.health td,.health th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
.err{color:var(--new)}
.empty{color:var(--muted);text-align:center;padding:40px 0}
.hide{display:none!important}
"""

JS = """
const q=document.getElementById('q'),onlyNew=document.getElementById('onlynew');
function apply(){const t=q.value.trim().toLowerCase(),n=onlyNew.checked;
document.querySelectorAll('.card').forEach(c=>{const ok=(!n||c.classList.contains('new'))&&(!t||c.dataset.text.includes(t));
c.classList.toggle('hide',!ok)});
document.querySelectorAll('details.sec').forEach(s=>{const v=s.querySelectorAll('.card:not(.hide)').length;
s.classList.toggle('hide',v===0);const nav=document.querySelector('.nav a[href="#'+s.id+'"]');if(nav)nav.classList.toggle('hide',v===0)});
document.querySelectorAll('.group').forEach(g=>{let el=g.nextElementSibling,any=false;
while(el&&!el.classList.contains('group')){if(!el.classList.contains('hide'))any=true;el=el.nextElementSibling}
g.classList.toggle('hide',!any)});}
q.addEventListener('input',apply);onlyNew.addEventListener('change',apply);
document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',()=>{const d=document.querySelector(a.getAttribute('href'));if(d)d.open=true}));
"""

e = html.escape


def _md_inline(text: str) -> str:
    text = e(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def markdown_to_html(md: str) -> str:
    """Tiny Markdown subset for the top-stories note: ## headings, - bullets, **bold**, [links](url)."""
    out, in_list = [], False
    for line in md.splitlines():
        s = line.strip()
        if s.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_md_inline(re.sub(r'^([-*]|\d+\.)\s+', '', s))}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if s.startswith("#"):
            out.append(f"<h2>{_md_inline(s.lstrip('#').strip())}</h2>")
        elif s:
            out.append(f"<p>{_md_inline(s)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _card(i: dict) -> str:
    tags = []
    if i["is_new"]:
        tags.append('<span class="tag newb">NEW</span>')
    tags += [f'<span class="tag co">{e(k)}</span>' for k in i["companies"]]
    tags += [f'<span class="tag">{e(n.split(":")[0])}</span>' for n in i["topic_names"][:2]]
    others = ""
    if i["others"]:
        lis = "".join(f'<li><a href="{e(o["url"])}" target="_blank" rel="noopener">{e(o["source"])}</a>'
                      f' — {e(o["headline"])}</li>' for o in i["others"])
        n = len(i["others"])
        others = (f'<details class="more"><summary>Also covered by {n} other outlet{"s" if n > 1 else ""}'
                  f'</summary><ul>{lis}</ul></details>')
    search_text = " ".join([i["headline"], i["source"], i["summary"], " ".join(i["companies"]),
                            " ".join(i["topic_names"])] + [o["source"] for o in i["others"]]).lower()
    summary = f'<p class="sum">{e(i["summary"])}</p>' if i["summary"] else ""
    return (f'<article class="card{" new" if i["is_new"] else ""}" data-text="{e(search_text)}">'
            f'<div class="tags">{"".join(tags)}</div>'
            f'<h3><a href="{e(i["url"])}" target="_blank" rel="noopener">{e(i["headline"])}</a></h3>'
            f'<div class="meta">{e(i["source"])} · {e(i["published_local"])}</div>{summary}{others}</article>')


def render(digest: dict, top_stories_md: str | None = None) -> str:
    st = digest["stats"]
    nav, body, last_group = [], [], None
    for s in digest["sections"]:
        sid = ("c-" if s["kind"] == "company" else "t-") + s["key"].lower()
        main = [i for i in s["items"] if not i.get("chatter")]
        chatter = [i for i in s["items"] if i.get("chatter")]
        n, nn = len(main), sum(i["is_new"] for i in main)
        label = s["key"] if s["kind"] == "company" else s["title"].split(":")[0]
        nav.append(f'<a href="#{sid}">{e(label)} <span>{n}</span></a>')
        if s["group"] != last_group:
            body.append(f'<div class="group">{e(s["group"])}</div>')
            last_group = s["group"]
        new_badge = f'<span class="nn">{nn} new</span>' if nn else ""
        drawer = ""
        if chatter:
            drawer = (f'<details class="chat"><summary>Stock &amp; analyst chatter ({len(chatter)})</summary>'
                      + "".join(_card(i) for i in chatter) + "</details>")
        body.append(f'<details class="sec" id="{sid}" open><summary><h2>{e(s["title"])}</h2>'
                    f'<span class="n">{n}</span>{new_badge}</summary>'
                    + "".join(_card(i) for i in main) + drawer + "</details>")
    if not body:
        body.append('<p class="empty">No stories found in this window.</p>')

    top = ""
    if top_stories_md and top_stories_md.strip():
        top = f'<section class="top">{markdown_to_html(top_stories_md)}</section>'

    rows = []
    for s in digest["sources"]:
        errs = "<br>".join(e(x) for x in s["errors"][:5])
        status = "OK" if not s["failures"] else f'<span class="err">{s["failures"]} of {s["requests"]} failed</span>'
        rows.append(f'<tr><td>{e(s["name"])}</td><td>{s["items"]}</td><td>{status}'
                    f'{"<br><span class=err>" + errs + "</span>" if errs else ""}</td></tr>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Waste News Digest</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>Waste News Digest</h1>
<div class="sub">Last {digest['hours']} hours · since {e(digest['since_local'])}<br>Generated {e(digest['generated_local'])}</div>
<div class="stats"><div class="stat"><b>{st['stories'] - st.get('chatter', 0)}</b>stories</div>
<div class="stat new"><b>{st['new']}</b>new</div>
<div class="stat"><b>{st['company_stories']}</b>company</div>
<div class="stat"><b>{st.get('chatter', 0)}</b>stock chatter</div>
<div class="stat"><b>{st.get('fetched', st['articles']):,}</b>articles scanned</div></div>
</header>
{top}
<div class="bar"><div class="controls"><input id="q" type="search" placeholder="Filter stories">
<label class="toggle"><input id="onlynew" type="checkbox"> New only</label></div>
<nav class="nav">{''.join(nav)}</nav></div>
{''.join(body)}
<details class="health"><summary>Sources checked</summary>
<table><tr><th>Source</th><th>Items</th><th>Status</th></tr>{''.join(rows)}</table></details>
</div><script>{JS}</script></body></html>"""


def write(digest: dict, path: Path) -> None:
    top_path = path.parent / "top_stories.md"
    top = top_path.read_text(encoding="utf-8") if top_path.exists() else None
    path.write_text(render(digest, top), encoding="utf-8")
