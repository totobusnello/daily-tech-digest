#!/usr/bin/env python3
"""
THE DAILY BYTE - Coletor de Fontes
Coleta notícias de X, YouTube, LinkedIn e RSS feeds
"""

import os
import json
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import re

# Import newsletter collector
try:
    from newsletter_collector import collect_all_newsletters
except ImportError:
    collect_all_newsletters = None

# ============================================
# CONFIGURAÇÃO
# ============================================

# Tier 1 - Primeira Mão (handles do X)
TIER1_HANDLES = [
    # OpenAI
    "sama", "gaborcselle", "maborak",
    # Anthropic
    "AnthropicAI", "alexalbert__", "daborak",
    # Microsoft
    "satyanadella", "mustafa",
    # Google
    "sundarpichai", "JeffDean",
    # Meta
    "ylecun", "AIatMeta",
    # Outros fundadores/researchers
    "karpathy", "drfeifei", "AndrewYNg",
    "EMostaque", "caborian", "demaboris",
    # AI-native CEOs + Research
    "aravind_srinivas", "demishassabis", "ethanmollick",
    # AI Labs
    "xaborai", "Mistral", "PerplexityAI",
    # ── v2.3 Tier 1 Expansion (Pulse.bot curated) ──
    # VC / Strategy / Leadership
    "vkhosla",            # Vinod Khosla — VC legend, AI bets
    "benedictevans",      # Benedict Evans — tech strategy analyst
    "jasonlk",            # Jason Lemkin — SaaStr, SaaS metrics
    "bznotes",            # Bilal Zuberi — Lux Capital VC
    "simonsinek",         # Simon Sinek — leadership voice
    "randfish",           # Rand Fishkin — marketing/SaaS founder
    "shaiwi",             # Shai Wininger — Lemonade CEO
    # Geopolitics / Think Tanks
    "CarnegieEndow",      # Carnegie Endowment
    "CSIS",               # Center for Strategic & Intl Studies
    "christogrozev",      # Christo Grozev — investigative (Bellingcat)
    "ChuckDBrooks",       # Chuck Brooks — cybersecurity/policy
    # Markets / Investing
    "charliebilello",     # Charlie Bilello — markets data
    "DivesTech",          # Dan Ives — Wedbush, tech analyst
    "EddyElfenbein",      # Eddy Elfenbein — investing
    "munster_gene",       # Gene Munster — Deepwater, tech investing
    "InvestingVisual",    # Investing Visuals — charts/data
    "LanceUlanoff",       # Lance Ulanoff — tech/media
    "LizAnnSonders",      # Liz Ann Sonders — Schwab chief strategist
    "tracyalloway",       # Tracy Alloway — Bloomberg Odd Lots
    # Crypto / Web3
    "cryptosauce_",       # Crypto insights
    "ADDerivs",           # AD Derivs — crypto options
]

# RSS Feeds — Tech & AI
RSS_FEEDS = {
    # ── Originais v2.2 ──
    "hacker_news": "https://hnrss.org/frontpage?points=100",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
    "wired": "https://www.wired.com/feed/rss",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    "reuters_tech": "https://www.reuters.com/technology/rss",
    "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    "arxiv_ai": "http://export.arxiv.org/rss/cs.AI",
    "the_decoder": "https://the-decoder.com/feed/",
    # ── v2.3 Expansion: AI & Enterprise Tech ──
    "venturebeat": "https://feeds.feedburner.com/venturebeat/SZYF",
    "ai_business": "https://aibusiness.com/rss.xml",
    "enterprise_ai": "https://www.enterpriseai.news/feed/",
    "aithority": "https://aithority.com/feed/",
    "ai_news": "https://www.artificialintelligence-news.com/feed/",
    "zdnet": "https://www.zdnet.com/news/rss.xml",
    "engadget": "https://www.engadget.com/rss.xml",
    "siliconangle": "https://siliconangle.com/feed/",
    "geekwire": "https://www.geekwire.com/feed/",
    "fast_company": "https://www.fastcompany.com/latest/rss",
    "inc": "https://www.inc.com/rss",
    # ── v2.3 Expansion: Crypto / Web3 ──
    "coindesk": "https://feeds.feedburner.com/CoinDesk",
    "decrypt": "https://decrypt.co/feed",
    # ── v2.3 Expansion: SaaS / Enterprise ──
    "saas_mag": "https://saas-mag.com/feed/",
    "saastock_blog": "https://www.saastock.com/blog/feed/",
    "crunchbase_news": "https://news.crunchbase.com/feed/",
}

# RSS Feeds - Mundo Real (governos, empresas, geopolítica, finanças)
WORLD_FEEDS = {
    # ── Originais v2.2 ──
    "reuters_world": "https://www.reuters.com/world/rss",
    "reuters_business": "https://www.reuters.com/business/rss",
    "forbes_business": "https://www.forbes.com/business/feed/",
    "forbes_innovation": "https://www.forbes.com/innovation/feed/",
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    # ── v2.3 Expansion: Business / Finance / Macro ──
    "cnbc_top_news": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "cnbc_markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "cnbc_economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910259",
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "nyt_dealbook": "https://rss.nytimes.com/services/xml/rss/nyt/DealBook.xml",
    "axios": "https://api.axios.com/feed/",
    "fortune": "https://fortune.com/feed/",
    "business_insider": "https://www.businessinsider.com/rss",
    "quartz": "https://qz.com/feed",
    "nikkei_asia": "https://asia.nikkei.com/rss",
    "politico_eu_tech": "https://www.politico.eu/section/technology/feed/",
    # ── v2.3 Expansion: Fintech / Payments ──
    "pymnts": "https://www.pymnts.com/feed/",
    "finextra": "https://www.finextra.com/rss/headlines.aspx",
    # ── v2.3 Expansion: Paywalled (may fail gracefully) ──
    "bloomberg_tech": "https://feeds.bloomberg.com/technology/news.rss",
    "ft_technology": "https://www.ft.com/technology?format=rss",
    "ft_startups": "https://www.ft.com/start-ups?format=rss",
    "economist_finance": "https://www.economist.com/finance-and-economics/rss.xml",
    "economist_business": "https://www.economist.com/business/rss.xml",
}

# YouTube Channels (via RSS)
YOUTUBE_CHANNELS = {
    "fireship": "UCsBjURrPoezykLs9EqgamOA",
    "two_minute_papers": "UCbfYPyITQ-7l4upoX8nvctg",
    "ai_explained": "UCNF8RjQNdHcz4n4vMBhlaJQ",
    "matt_wolfe": "UCJvbN6qX8gJM6Y4NRm81tSA",
    "lex_fridman": "UCSHZKyawb77ixDdsGog4iWA",
    "andrej_karpathy": "UCWN3xxRkmTPmbKwht9FuE5A",
    "ai_daily_brief": "UCKa4vLnfLYnxKZ4fKJttGsA",
    "filipe_deschamps": "UCU5JicSrEM5A63jkJ2QvGYw",
}

# Substack Feeds — v2.3 (curated newsletters via RSS)
SUBSTACK_FEEDS = {
    # ── Business / Strategy ──
    "sub_capital_wars": "https://capitalwars.substack.com/feed",
    "sub_cfo_dynamics": "https://cfodynamics.substack.com/feed",
    "sub_doomberg": "https://doomberg.substack.com/feed",
    "sub_beautiful_mess": "https://cutlefish.substack.com/feed",
    "sub_contrarian_hr": "https://thecontrarianhr.substack.com/feed",
    # ── AI / Tech ──
    "sub_ai_at_work": "https://aiatwork.substack.com/feed",
    "sub_ai_chat": "https://aichat.substack.com/feed",
    "sub_ai_explored": "https://aiexplored.substack.com/feed",
    "sub_ai_for_humans": "https://aiforhumans.substack.com/feed",
    "sub_ai_today": "https://aitoday.substack.com/feed",
    "sub_ai_marketing": "https://aima.substack.com/feed",
    "sub_authentic_ai": "https://authenticai.substack.com/feed",
    "sub_everyday_ai": "https://everydayai.substack.com/feed",
    "sub_how_i_ai": "https://howaiai.substack.com/feed",
    "sub_conversations_ai": "https://conversationsonappliedai.substack.com/feed",
    # ── Fintech ──
    "sub_fintech_biz_weekly": "https://fintechbusinessweekly.substack.com/feed",
    "sub_fintech_confidential": "https://fintechconfidential.substack.com/feed",
    "sub_fintech_hunting": "https://fintechhunting.substack.com/feed",
    "sub_fintech_newscast": "https://fintech-newscast.substack.com/feed",
    "sub_connecting_dots_fintech": "https://connectingdots.substack.com/feed",
    # ── Biotech / Pharma ──
    "sub_ai_pharma": "https://aiforpharmagrowth.substack.com/feed",
    "sub_biotech_blueprint": "https://biotechblueprint.substack.com/feed",
    "sub_biotech_bytes": "https://biotechbytes.substack.com/feed",
    "sub_biotech_strategy": "https://biotechstrategy.substack.com/feed",
    "sub_health_tech": "https://longyearhealth.substack.com/feed",
    # ── E-commerce / EdTech / Sustainability ──
    "sub_ecommerce_playbook": "https://ecommerceplaybook.substack.com/feed",
    "sub_edtech_partnerships": "https://edtechpartnerships.substack.com/feed",
    "sub_sustainability_numbers": "https://hannahritchie.substack.com/feed",
    # ── Education / AI in Edu ──
    "sub_toms_ai_edu": "https://tomstakesaitools.substack.com/feed",
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class RawItem:
    """Item bruto coletado das fontes"""
    title: str
    content: str
    url: str
    source_name: str
    source_type: str  # tweet, article, video, paper
    author: str
    published_at: datetime
    engagement: Dict  # likes, retweets, views, etc
    raw_data: Dict

    def hours_ago(self) -> float:
        return (datetime.utcnow() - self.published_at).total_seconds() / 3600

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['published_at'] = self.published_at.isoformat()
        d['hours_ago'] = round(self.hours_ago(), 1)
        return d


# ============================================
# COLETORES
# ============================================

def _fetch_feed(feed_url: str):
    """Fetch RSS feed with fallback: feedparser direct → requests + feedparser"""
    feed = feedparser.parse(feed_url)
    if feed.entries:
        return feed
    # Fallback: fetch via requests (handles redirects, user-agent blocks)
    try:
        resp = requests.get(
            feed_url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyByte/2.3)"},
            allow_redirects=True
        )
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
    except Exception:
        pass
    return feed


def _parse_feed_items(feeds: dict, cutoff, source_type_fn=None, max_per_feed: int = 20) -> List[RawItem]:
    """Coleta itens de um dicionário de RSS feeds"""
    items = []

    for source_name, feed_url in feeds.items():
        try:
            feed = _fetch_feed(feed_url)
            for entry in feed.entries[:max_per_feed]:
                # Parse date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    published = datetime.utcnow()

                # Skip old items
                if published < cutoff:
                    continue

                if source_type_fn:
                    stype = source_type_fn(source_name)
                else:
                    stype = 'article' if 'arxiv' not in source_name else 'paper'

                items.append(RawItem(
                    title=entry.get('title', ''),
                    content=entry.get('summary', ''),
                    url=entry.get('link', ''),
                    source_name=source_name,
                    source_type=stype,
                    author=entry.get('author', source_name),
                    published_at=published,
                    engagement={},
                    raw_data=dict(entry)
                ))
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    return items


def collect_rss_feeds() -> List[RawItem]:
    """Coleta itens de RSS feeds de tech"""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return _parse_feed_items(RSS_FEEDS, cutoff)


def collect_world_feeds() -> List[RawItem]:
    """Coleta notícias do mundo real (governos, empresas, geopolítica)"""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return _parse_feed_items(
        WORLD_FEEDS, cutoff,
        source_type_fn=lambda _: 'world',
        max_per_feed=10
    )


def collect_youtube_feeds() -> List[RawItem]:
    """Coleta vídeos recentes via YouTube RSS"""
    items = []
    cutoff = datetime.utcnow() - timedelta(hours=48)  # 48h for videos

    for channel_name, channel_id in YOUTUBE_CHANNELS.items():
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Max 5 per channel
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                else:
                    published = datetime.utcnow()

                if published < cutoff:
                    continue

                items.append(RawItem(
                    title=entry.get('title', ''),
                    content=entry.get('summary', ''),
                    url=entry.get('link', ''),
                    source_name=channel_name,
                    source_type='video',
                    author=entry.get('author', channel_name),
                    published_at=published,
                    engagement={},
                    raw_data=dict(entry)
                ))
        except Exception as e:
            print(f"Error fetching YouTube {channel_name}: {e}")

    return items


def collect_substack_feeds() -> List[RawItem]:
    """Coleta posts recentes de Substacks curados via RSS (janela de 36h)"""
    cutoff = datetime.utcnow() - timedelta(hours=36)  # 36h window like newsletters
    return _parse_feed_items(
        SUBSTACK_FEEDS, cutoff,
        source_type_fn=lambda _: 'newsletter',
        max_per_feed=5  # Max 5 per Substack to avoid noise
    )


def collect_x_posts(bearer_token: str) -> List[RawItem]:
    """
    Coleta posts recentes do X via API
    Requer X API Bearer Token
    """
    items = []

    if not bearer_token:
        print("X_BEARER_TOKEN not set, skipping X collection")
        return items

    headers = {"Authorization": f"Bearer {bearer_token}"}
    cutoff = datetime.utcnow() - timedelta(hours=24)

    for handle in TIER1_HANDLES:
        try:
            # Get user ID
            user_url = f"https://api.twitter.com/2/users/by/username/{handle}"
            user_resp = requests.get(user_url, headers=headers)
            if user_resp.status_code != 200:
                continue
            user_id = user_resp.json().get('data', {}).get('id')
            if not user_id:
                continue

            # Get recent tweets
            tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            params = {
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics,entities",
                "expansions": "author_id"
            }
            tweets_resp = requests.get(tweets_url, headers=headers, params=params)
            if tweets_resp.status_code != 200:
                continue

            tweets = tweets_resp.json().get('data', [])
            for tweet in tweets:
                created_at = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)

                if created_at < cutoff:
                    continue

                metrics = tweet.get('public_metrics', {})
                items.append(RawItem(
                    title=tweet['text'][:100],
                    content=tweet['text'],
                    url=f"https://x.com/{handle}/status/{tweet['id']}",
                    source_name=f"@{handle}",
                    source_type='tweet',
                    author=handle,
                    published_at=created_at,
                    engagement={
                        'likes': metrics.get('like_count', 0),
                        'retweets': metrics.get('retweet_count', 0),
                        'replies': metrics.get('reply_count', 0)
                    },
                    raw_data=tweet
                ))
        except Exception as e:
            print(f"Error fetching X @{handle}: {e}")

    return items


# ============================================
# MAIN
# ============================================

def collect_all() -> Dict:
    """Coleta de todas as fontes"""
    print("🔥 THE DAILY BYTE - Iniciando coleta...")

    all_items = []

    # RSS Feeds (tech)
    print("📰 Coletando RSS feeds...")
    rss_items = collect_rss_feeds()
    all_items.extend(rss_items)
    print(f"   → {len(rss_items)} itens de RSS")

    # World Feeds (Reuters, Forbes, BBC)
    print("🌍 Coletando mundo real...")
    world_items = collect_world_feeds()
    all_items.extend(world_items)
    print(f"   → {len(world_items)} itens do mundo real")

    # YouTube
    print("📺 Coletando YouTube...")
    youtube_items = collect_youtube_feeds()
    all_items.extend(youtube_items)
    print(f"   → {len(youtube_items)} vídeos")

    # Substacks (v2.3 — 29 curated Substacks via RSS)
    print("📝 Coletando Substacks...")
    substack_items = collect_substack_feeds()
    all_items.extend(substack_items)
    print(f"   → {len(substack_items)} itens de Substacks")

    # X/Twitter
    print("🐦 Coletando X...")
    x_bearer = os.environ.get('X_BEARER_TOKEN', '')
    x_items = collect_x_posts(x_bearer)
    all_items.extend(x_items)
    print(f"   → {len(x_items)} tweets")

    # Newsletters (9 fontes: AiDrop, Evolving AI, Update Diário, TechDrop, AlphaSignal, TAAFT, Turing Post, Import AI, Distrito News)
    newsletter_items_raw = []
    if collect_all_newsletters:
        print("📰 Coletando newsletters...")
        newsletter_items_raw = collect_all_newsletters()
        print(f"   → {len(newsletter_items_raw)} itens de newsletters")
    else:
        print("⚠️ Newsletter collector não disponível")

    # Sort by recency (RawItem objects)
    all_items.sort(key=lambda x: x.published_at, reverse=True)

    # Merge: convert RawItems to dicts + add newsletter items (already dicts)
    all_items_dicts = [item.to_dict() for item in all_items]
    all_items_dicts.extend(newsletter_items_raw)

    result = {
        "collected_at": datetime.utcnow().isoformat(),
        "total_items": len(all_items_dicts),
        "breakdown": {
            "rss": len(rss_items),
            "world": len(world_items),
            "substacks": len(substack_items),
            "youtube": len(youtube_items),
            "x": len(x_items),
            "newsletters": len(newsletter_items_raw)
        },
        "items": all_items_dicts
    }

    print(f"\n✅ Total coletado: {len(all_items_dicts)} itens")
    return result


if __name__ == "__main__":
    data = collect_all()

    # Save to file
    output_path = "/tmp/digest_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Salvo em {output_path}")
