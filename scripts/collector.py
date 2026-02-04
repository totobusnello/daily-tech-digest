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
    # AI Labs
    "xaborai", "Mistral", "PerplexityAI",
]

# RSS Feeds
RSS_FEEDS = {
    # Tech geral e impacto no cotidiano
    "hacker_news": "https://hnrss.org/frontpage?points=100",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
    "wired": "https://www.wired.com/feed/rss",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    "reuters_tech": "https://www.reuters.com/technology/rss",
    # AI específico
    "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    # Research (limitado a 1 feed)
    "arxiv_ai": "http://export.arxiv.org/rss/cs.AI",
}

# RSS Feeds - Mundo Real (governos, empresas, geopolítica)
WORLD_FEEDS = {
    "reuters_world": "https://www.reuters.com/world/rss",
    "reuters_business": "https://www.reuters.com/business/rss",
    "forbes_business": "https://www.forbes.com/business/feed/",
    "forbes_innovation": "https://www.forbes.com/innovation/feed/",
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
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

def _parse_feed_items(feeds: dict, cutoff, source_type_fn=None, max_per_feed: int = 20) -> List[RawItem]:
    """Coleta itens de um dicionário de RSS feeds"""
    items = []

    for source_name, feed_url in feeds.items():
        try:
            feed = feedparser.parse(feed_url)
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

    # X/Twitter
    print("🐦 Coletando X...")
    x_bearer = os.environ.get('X_BEARER_TOKEN', '')
    x_items = collect_x_posts(x_bearer)
    all_items.extend(x_items)
    print(f"   → {len(x_items)} tweets")

    # Sort by recency
    all_items.sort(key=lambda x: x.published_at, reverse=True)

    result = {
        "collected_at": datetime.utcnow().isoformat(),
        "total_items": len(all_items),
        "breakdown": {
            "rss": len(rss_items),
            "world": len(world_items),
            "youtube": len(youtube_items),
            "x": len(x_items)
        },
        "items": [item.to_dict() for item in all_items]
    }

    print(f"\n✅ Total coletado: {len(all_items)} itens")
    return result


if __name__ == "__main__":
    data = collect_all()

    # Save to file
    output_path = "/tmp/digest_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Salvo em {output_path}")
