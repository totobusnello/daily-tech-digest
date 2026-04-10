#!/usr/bin/env python3
"""
THE DAILY BYTE - Newsletter Collector
Coleta posts recentes de newsletters no Beehiiv via scraping de HTML
"""

import re
import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

# ============================================
# CONFIGURAÇÃO DAS NEWSLETTERS
# ============================================

NEWSLETTER_SOURCES = {
    "aidrop": {
        "name": "AiDrop",
        "base_url": "https://www.aidrop.news",
        "language": "pt-br",
        "category_hint": "ai_models",
        "description": "AI ecosystem deep analysis in Portuguese"
    },
    "evolving_ai": {
        "name": "Evolving AI",
        "base_url": "https://evolvingai.io",
        "language": "en",
        "category_hint": "ai_models",
        "description": "AI model launches and competitive analysis"
    },
    "update_diario": {
        "name": "Update Diário",
        "base_url": "https://updatediario.beehiiv.com",
        "language": "pt-br",
        "category_hint": "world",
        "description": "Daily Brazilian news digest - economy, politics, market"
    },
    "techdrop": {
        "name": "TechDrop",
        "base_url": "https://www.techdrop.news",
        "language": "pt-br",
        "category_hint": "saas_enterprise",
        "description": "SaaS, enterprise tech, CapEx analysis"
    },
    "alphasignal": {
        "name": "AlphaSignal",
        "base_url": "https://alphasignalai.beehiiv.com",
        "language": "en",
        "category_hint": "ai_models",
        "description": "Research-to-product bridge: AI papers with practical applications"
    },
    "taaft": {
        "name": "There's An AI For That",
        "base_url": "https://newsletter.theresanaiforthat.com",
        "language": "en",
        "category_hint": "tool_of_day",
        "description": "World's largest AI tools newsletter (2.8M subs). Curated new AI tools and product launches."
    },
    "turing_post": {
        "name": "Turing Post",
        "base_url": "https://www.turingpost.com",
        "language": "en",
        "category_hint": "ai_models",
        "description": "Strategic AI analysis: geopolitics, open-source vs closed, enterprise AI decisions. 100K+ readers."
    },
    "import_ai": {
        "name": "Import AI",
        "base_url": "https://importai.substack.com",
        "rss_url": "https://importai.substack.com/feed",
        "language": "en",
        "category_hint": "ai_models",
        "description": "Jack Clark (ex-OpenAI policy). AI policy, research, geopolitics. Weekly deep analysis."
    },
    "distrito_news": {
        "name": "Distrito News Inside VC",
        "base_url": "https://insidevcnews.substack.com",
        "rss_url": "https://insidevcnews.substack.com/feed",
        "language": "pt-br",
        "category_hint": "saas_enterprise",
        "description": "Brazil VC/startup ecosystem. Funding rounds, valuations, exits. PT-BR."
    },
    # ── v2.7 ──
    "the_brief": {
        "name": "The BRIEF",
        "base_url": "https://thebrief-newsletter.beehiiv.com",
        "language": "pt-br",
        "category_hint": "world",
        "description": "Daily Brazilian tech+business newsletter. Direct tone, 7am delivery."
    },
}

# Headers to mimic a browser request
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ============================================
# DATA CLASS
# ============================================

@dataclass
class NewsletterItem:
    """Item extraído de uma newsletter"""
    title: str
    description: str
    url: str
    source_name: str
    source_key: str
    language: str
    category_hint: str
    published_at: Optional[datetime]

    def to_raw_dict(self) -> Dict:
        """Converte para formato compatível com RawItem do collector.py
        v2.4: Removido raw_data (token optimization — consistente com processor.py)
        """
        pub_at = self.published_at or datetime.utcnow()
        hours_ago = (datetime.utcnow() - pub_at).total_seconds() / 3600

        return {
            "title": self.title,
            "content": self.description,
            "url": self.url,
            "source_name": self.source_name,
            "source_type": "newsletter",
            "author": self.source_name,
            "published_at": pub_at.isoformat(),
            "hours_ago": round(hours_ago, 1),
            "engagement": {},
            "language": self.language,
            "category_hint": self.category_hint,
        }


# ============================================
# RSS FETCH WITH FALLBACK (v2.4)
# ============================================

def _fetch_feed(url: str, timeout: int = 15, max_retries: int = 3):
    """Tenta requests com browser headers primeiro (Substack bloqueia bots),
    feedparser direto como fallback.
    v2.5: Retry com backoff exponencial (2s, 4s, 8s).
    """
    feed = None
    for attempt in range(max_retries):
        # Primary: requests com headers de browser (evita bloqueio Substack)
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                if feed.entries:
                    return feed
        except Exception as e:
            print(f"  ⚠️ _fetch_feed falhou para {url}: {e}")

        # Fallback: feedparser direto
        feed = feedparser.parse(url)
        if feed.entries:
            return feed

        # Backoff before next retry (skip on last attempt)
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)  # 2s, 4s
            print(f"  ⏳ Retry {attempt + 1}/{max_retries} for {url[:60]}... waiting {wait}s")
            time.sleep(wait)

    return feed or feedparser.parse('')  # retorna vazio se todos falharam


# ============================================
# PARSERS POR PLATAFORMA
# ============================================

def _parse_beehiiv_page(html: str, source_key: str, source_config: dict) -> List[NewsletterItem]:
    """
    Parse a Beehiiv newsletter homepage/archive to extract recent posts.
    Beehiiv pages typically have article cards with titles, descriptions, and dates.
    """
    items = []
    soup = BeautifulSoup(html, 'lxml')

    # Strategy 1: Look for article/post cards via common Beehiiv patterns
    # Beehiiv uses <article> tags or divs with post data
    articles = soup.find_all('article')

    if not articles:
        # Strategy 2: Look for links to /p/ (post URLs on Beehiiv)
        articles = soup.find_all('a', href=re.compile(r'/p/'))

    if not articles:
        # Strategy 3: Look for og:article or structured data
        articles = soup.find_all('div', class_=re.compile(r'post|article|card', re.I))

    seen_urls = set()

    for article in articles:
        try:
            # Extract URL
            url = None
            if article.name == 'a':
                url = article.get('href', '')
            else:
                link = article.find('a', href=re.compile(r'/p/'))
                if link:
                    url = link.get('href', '')

            if not url:
                continue

            # Make URL absolute
            if url.startswith('/'):
                url = source_config['base_url'] + url

            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Extract title
            title = ''
            title_el = article.find(['h1', 'h2', 'h3', 'h4'])
            if title_el:
                title = title_el.get_text(strip=True)
            elif article.name == 'a':
                title = article.get_text(strip=True)

            if not title:
                continue

            # Extract description
            description = ''
            desc_el = article.find('p')
            if desc_el:
                description = desc_el.get_text(strip=True)

            # Extract date (Beehiiv often has <time> tags)
            published_at = None
            time_el = article.find('time')
            if time_el:
                date_str = time_el.get('datetime', '')
                if date_str:
                    try:
                        published_at = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    except (ValueError, TypeError):
                        pass

            items.append(NewsletterItem(
                title=title,
                description=description[:500] if description else title,
                url=url,
                source_name=source_config['name'],
                source_key=source_key,
                language=source_config['language'],
                category_hint=source_config['category_hint'],
                published_at=published_at,
            ))

        except Exception as e:
            print(f"  ⚠️ Error parsing article from {source_key}: {e}")
            continue

    return items


def _parse_via_meta_tags(html: str, url: str, source_key: str, source_config: dict) -> List[NewsletterItem]:
    """
    Fallback: Extract info from meta tags (og:title, og:description).
    Less items but more reliable.
    """
    items = []
    soup = BeautifulSoup(html, 'lxml')

    # Try to get individual post links from the page
    post_links = soup.find_all('a', href=re.compile(r'/p/'))

    seen = set()
    for link in post_links:
        href = link.get('href', '')
        if href.startswith('/'):
            href = source_config['base_url'] + href

        if href in seen or not '/p/' in href:
            continue
        seen.add(href)

        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        items.append(NewsletterItem(
            title=title,
            description=title,
            url=href,
            source_name=source_config['name'],
            source_key=source_key,
            language=source_config['language'],
            category_hint=source_config['category_hint'],
            published_at=None,
        ))

    return items


# ============================================
# ENRICHMENT: Fetch individual post details
# ============================================

def _enrich_post(item: NewsletterItem) -> NewsletterItem:
    """
    Fetch an individual newsletter post page to extract better
    description and publish date from meta tags.
    """
    try:
        resp = requests.get(item.url, headers=REQUEST_HEADERS, timeout=15)
        if resp.status_code != 200:
            return item

        soup = BeautifulSoup(resp.text, 'lxml')

        # Better description from og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            item.description = og_desc['content'][:500]

        # Better title from og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            item.title = og_title['content']

        # Publish date from article:published_time or datePublished
        date_meta = soup.find('meta', property='article:published_time')
        if not date_meta:
            date_meta = soup.find('meta', attrs={'name': 'datePublished'})

        if date_meta and date_meta.get('content'):
            try:
                item.published_at = datetime.fromisoformat(
                    date_meta['content'].replace('Z', '+00:00')
                ).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        # Also try schema.org datePublished in JSON-LD
        if not item.published_at:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'datePublished' in data:
                        item.published_at = datetime.fromisoformat(
                            data['datePublished'].replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                        break
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

    except Exception as e:
        print(f"  ⚠️ Error enriching {item.url}: {e}")

    return item


# ============================================
# MAIN COLLECTOR
# ============================================

def _collect_via_rss(source_key: str, source_config: dict, cutoff: datetime, max_items: int = 5) -> List[Dict]:
    """Coleta posts via RSS feed (Substack nativo ou inferido)
    v2.4: Usa _fetch_feed() com fallback requests + tenta RSS inferido
    """
    rss_url = source_config.get('rss_url', '')

    # v2.4: Tenta inferir RSS para Substacks e Beehiiv se nao configurado
    if not rss_url:
        base = source_config.get('base_url', '')
        if 'substack.com' in base:
            rss_url = base.rstrip('/') + '/feed'
        elif 'beehiiv.com' in base:
            rss_url = base.rstrip('/') + '/feed'

    if not rss_url:
        return []

    items = []
    try:
        feed = _fetch_feed(rss_url)
        for entry in feed.entries[:max_items]:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            if published and published < cutoff:
                continue

            item = NewsletterItem(
                title=entry.get('title', ''),
                description=entry.get('summary', '')[:500] if entry.get('summary') else entry.get('title', ''),
                url=entry.get('link', ''),
                source_name=source_config['name'],
                source_key=source_key,
                language=source_config['language'],
                category_hint=source_config['category_hint'],
                published_at=published,
            )
            items.append(item.to_raw_dict())

    except Exception as e:
        print(f"  ⚠️ RSS falhou para {source_config['name']}: {e}")

    return items


def collect_newsletter(source_key: str, source_config: dict, cutoff: datetime, max_items: int = 5) -> List[Dict]:
    """Coleta posts recentes de uma newsletter específica"""
    items = []

    # Try RSS first if available (more reliable for Substack)
    if source_config.get('rss_url'):
        print(f"  📰 Coletando {source_config['name']} via RSS...")
        items = _collect_via_rss(source_key, source_config, cutoff, max_items)
        if items:
            print(f"    → {len(items)} itens via RSS")
            return items
        print(f"    → RSS vazio, tentando scraping...")

    try:
        print(f"  📰 Coletando {source_config['name']} ({source_config['base_url']})...")

        resp = requests.get(
            source_config['base_url'],
            headers=REQUEST_HEADERS,
            timeout=20
        )

        if resp.status_code != 200:
            print(f"  ⚠️ {source_config['name']}: HTTP {resp.status_code}")
            return []

        # Try main parser first
        newsletter_items = _parse_beehiiv_page(resp.text, source_key, source_config)

        # Fallback to meta tag parser
        if not newsletter_items:
            newsletter_items = _parse_via_meta_tags(
                resp.text, source_config['base_url'], source_key, source_config
            )

        print(f"    → Encontrados {len(newsletter_items)} posts")

        # Enrich top posts with individual page data
        for i, item in enumerate(newsletter_items[:max_items]):
            item = _enrich_post(item)
            newsletter_items[i] = item

        # Filter by date (if we have dates)
        filtered = []
        for item in newsletter_items[:max_items]:
            if item.published_at and item.published_at < cutoff:
                continue
            filtered.append(item.to_raw_dict())

        # If no dates available, include all (Claude will filter)
        if not filtered and newsletter_items:
            filtered = [item.to_raw_dict() for item in newsletter_items[:max_items]]

        items = filtered
        print(f"    → {len(items)} itens após filtro de data")

    except Exception as e:
        print(f"  ❌ Erro coletando {source_config['name']}: {e}")

    return items


def collect_all_newsletters() -> List[Dict]:
    """Coleta posts de todas as newsletters configuradas"""
    print("📰 Coletando newsletters...")

    all_items = []
    # Newsletters have a wider window (36h) since they may publish late
    cutoff = datetime.utcnow() - timedelta(hours=36)

    for source_key, source_config in NEWSLETTER_SOURCES.items():
        items = collect_newsletter(source_key, source_config, cutoff)
        all_items.extend(items)

    print(f"   → Total newsletters: {len(all_items)} itens")
    return all_items


# ============================================
# STANDALONE EXECUTION
# ============================================

if __name__ == "__main__":
    import json

    results = collect_all_newsletters()

    print(f"\n📊 Resumo:")
    print(f"   Total: {len(results)} itens")

    for item in results:
        print(f"\n   📰 {item['source_name']}")
        print(f"      {item['title'][:80]}")
        print(f"      {item['url'][:80]}")
        print(f"      {item.get('hours_ago', '?')}h atrás")

    # Save
    output_path = "/tmp/newsletter_raw.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Salvo em {output_path}")
