from waste_digest.config import load_config
from waste_digest.models import Article
from waste_digest.tagging import Tagger

tagger = Tagger(load_config())


def companies(title, summary=""):
    a = Article(title=title, url="", source="", published=None, summary=summary)
    tagger.tag(a)
    return a.companies


def test_core_companies():
    assert companies("Waste Management raises 2026 guidance") == ["WM"]
    assert companies("WM Renewable Energy opens RNG plant") == ["WM"]
    assert companies("Republic Services opens Polymer Center in Las Vegas") == ["RSG"]
    assert companies("California AG sues Waste Connections over closed Chiquita landfill") == ["WCN"]


def test_generic_waste_management_is_not_wm():
    assert companies("County Solid Waste Management District raises fees") == []
    assert companies("Ohio Department of Waste Management issues permit") == []
    assert companies("Tips for better waste management at home") == []


def test_short_caps_aliases_are_case_sensitive():
    assert companies("GFL sets deadline for take-private offers") == ["GFL"]
    assert companies("The gfl team") == []
    assert companies("wm") == []


def test_topics():
    a = Article(title="Landfill expansion permit approved after lawsuit", url="", source="", published=None)
    tagger.tag(a)
    assert max(a.topic_hits, key=a.topic_hits.get) == "landfills"
    b = Article(title="Recycled PET prices fall as OCC holds steady", url="", source="", published=None)
    tagger.tag(b)
    assert "recycling" in b.topic_hits
    c = Article(title="Pet food maker expands", url="", source="", published=None)
    tagger.tag(c)
    assert "recycling" not in c.topic_hits


def _noise(title, source="X"):
    return tagger.is_noise(Article(title=title, url="", source=source, published=None))


def test_noise():
    assert _noise("Acme Capital Boosts Stake in Waste Management, Inc. (NYSE:WM)")
    assert not _noise("Waste Management to acquire hauler in Texas")
    assert _noise("Bengaluru to get 4,900 new garbage collection vehicles")
    assert not _noise("Indiana landfill expansion approved")
    assert _noise("Anything", source="MarketBeat")


def test_wm_generic_title_case_phrases():
    assert companies("Using Scenario Modeling to Build Resiliency in Waste Management Systems") == []


def test_relevance_for_general_feeds():
    a = Article(title="GE Vernova in $9B deal to buy high-voltage manufacturer", url="", source="", published=None)
    tagger.tag(a)
    assert not tagger.is_relevant(a)
    b = Article(title="International Paper talks cost challenges", url="", source="", published=None,
                summary="The company noted inflated costs for energy, fuel and recovered fiber")
    tagger.tag(b)
    assert tagger.is_relevant(b)


def test_chatter():
    a = Article(title="Raymond James Adjusts Price Target on Waste Management", url="", source="MarketScreener",
                published=None)
    tagger.tag(a)
    assert a.chatter
    b = Article(title="Waste Management buys Texas hauler", url="", source="Houston Chronicle", published=None)
    tagger.tag(b)
    assert not b.chatter


def test_non_english_and_cleanaway():
    assert _noise("州政府指责奇基塔峡谷垃圾填埋场对危险废物管理不善")
    assert companies("Cleanaway Waste Management Limited to be acquired by EQT") == []


def test_us_places_not_excluded():
    for t in ["New Hampshire landfill expansion", "New England recycling markets", "New Mexico landfill permit",
              "Manchester NH trash contract", "Indian River County landfill"]:
        assert not _noise(t), t


def test_hard_news_on_stock_site_is_not_chatter():
    a = Article(title="Republic Services (RSG) Workers In Salinas Vote To Join Teamsters Local 350", url="",
                source="Yahoo Finance", published=None)
    tagger.tag(a)
    assert not a.chatter
    b = Article(title="Waste Management, Inc. (WM) Stock Forecasts", url="", source="Yahoo Finance", published=None)
    tagger.tag(b)
    assert b.chatter
