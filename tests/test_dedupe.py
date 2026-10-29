from datetime import datetime, timezone

from waste_digest.dedupe import cluster_articles
from waste_digest.models import Article

T = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def art(title, url, origin="Google News", source="X"):
    return Article(title=title, url=url, source=source, published=T, origin=origin)


def test_groups_same_story_and_prefers_trade_press():
    arts = [
        art("California AG Bonta sues Waste Connections over closed Chiquita landfill", "https://a.com/1"),
        art("California AG Bonta sues Waste Connections over closed Chiquita landfill", "https://wastedive.com/x",
            origin="Trade feed", source="Waste Dive"),
        art("Calif. AG Bonta sues Waste Connections over Chiquita landfill", "https://b.com/2"),
        art("Republic Services opens polymer center in Indianapolis", "https://c.com/3"),
    ]
    clusters = cluster_articles(arts)
    assert len(clusters) == 2
    big = max(clusters, key=lambda c: len(c.articles))
    assert len(big.articles) == 3
    assert big.primary.source == "Waste Dive"


def test_same_url_merges():
    arts = [art("Headline one about landfill", "https://www.a.com/x?utm_source=rss"),
            art("Totally different wording here", "https://a.com/x/")]
    assert len(cluster_articles(arts)) == 1


def test_different_stories_stay_apart():
    arts = [art("Landfill expansion approved in Ohio county", "https://a.com/1"),
            art("Landfill expansion denied in Wisconsin town", "https://b.com/2")]
    assert len(cluster_articles(arts)) == 2


def test_merge_related_local_coverage():
    from waste_digest.dedupe import merge_related
    arts = [
        art("Bunnell commissioners unanimously deny special exception for Project Butterfly landfill", "https://a.com/1"),
        art("Bunnell Rejects Landfill Development Application on Appeal", "https://b.com/2"),
        art("Why did Bunnell reverse landfill approval? Here's what happened", "https://b.com/3"),
        art("Major change coming to Brooklyn trash collection", "https://c.com/3"),
        art("DSNY truck driver kills pedestrian at notorious Brooklyn intersection", "https://d.com/4"),
        art("Brooklyn woman hit and killed by garbage truck at Bay Parkway", "https://e.com/5"),
        art("DSNY truck kills pedestrian on Bay Parkway in Brooklyn", "https://f.com/6"),
        art("Recycling bins arrive in brooklyn park", "https://g.com/7"),  # lower-case use elsewhere is fine
    ]
    merged = merge_related(cluster_articles(arts))
    sizes = sorted(len(c.articles) for c in merged)
    titles = {c.primary.title: len(c.articles) for c in merged}
    assert any("Bunnell" in t and n == 3 for t, n in titles.items())
    assert titles["Major change coming to Brooklyn trash collection"] == 1
