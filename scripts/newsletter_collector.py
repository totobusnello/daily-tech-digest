#!/usr/bin/env python3
"""
THE DAILY BYTE - Newsletter Collector
Coleta posts recentes de newsletters no Beehiiv via scraping de HTML
"""

import re
import requests
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
        """Converte para formato compatível com RawItem do collector.py"""
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
            "raw_data": {
                "source_key": self.source_key,
                "language": self.language,
                "category_hint": self.category_hint,
            }
        }


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

def collect_newsletter(source_key: str, source_config: dict, cutoff: datetime, max_items: int = 5) -> List[Dict]:
    """Coleta posts recentes de uma newsletter específica"""
    items = []

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
