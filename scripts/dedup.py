#!/usr/bin/env python3
"""
THE DAILY BYTE - Dedup entre dias
Mantém cache de URLs já enviadas para evitar repetição.
Cache é um JSON com {url: date_sent} — guardado via GitHub Actions cache.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

CACHE_PATH = Path("/tmp/digest_sent_cache.json")
TITLE_CACHE_PATH = Path("/tmp/digest_sent_titles.json")
CACHE_MAX_DAYS = 5  # Guarda 5 dias de histórico, depois limpa


def load_cache() -> Dict[str, str]:
    """Carrega cache de URLs já enviadas"""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, 'r') as f:
                cache = json.load(f)
            print(f"📋 Cache carregado: {len(cache)} URLs dos últimos dias")
            return cache
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Cache corrompido, iniciando limpo: {e}")
    return {}


def save_cache(cache: Dict[str, str]):
    """Salva cache atualizado"""
    # Limpa entradas antigas (> CACHE_MAX_DAYS)
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_MAX_DAYS)).isoformat()
    clean = {url: date for url, date in cache.items() if date >= cutoff}

    with open(CACHE_PATH, 'w') as f:
        json.dump(clean, f, indent=2)
    print(f"💾 Cache salvo: {len(clean)} URLs (limpou {len(cache) - len(clean)} antigas)")


def _normalize_url(url: str) -> str:
    """Normaliza URL para comparação (remove tracking params, trailing slash)"""
    url = url.strip().rstrip('/')
    # Remove common tracking params
    for param in ['?utm_source=', '?ref=', '?source=', '&utm_']:
        if param in url:
            url = url.split(param)[0]
    return url.lower()


def _title_hash(title: str) -> str:
    """Gera hash normalizado de título para dedup cross-edição"""
    if not title:
        return ""
    import re
    t = title.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for',
                 'of', 'and', 'or', 'but', 'not', 'no', 'by', 'as', 'it', 'its', 'be',
                 'um', 'uma', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na',
                 'nos', 'nas', 'por', 'com', 'sem', 'que', 'se', 'ou', 'ao', 'aos'}
    words = [w for w in t.split() if w not in stopwords and len(w) > 2]
    return " ".join(sorted(words[:8]))


def load_title_cache() -> Dict[str, str]:
    """Carrega cache de title hashes já enviados"""
    if TITLE_CACHE_PATH.exists():
        try:
            with open(TITLE_CACHE_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
    return {}


def save_title_cache(cache: Dict[str, str]):
    """Salva cache de title hashes"""
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_MAX_DAYS)).isoformat()
    clean = {h: date for h, date in cache.items() if date >= cutoff}
    with open(TITLE_CACHE_PATH, 'w') as f:
        json.dump(clean, f, indent=2)


def dedup_items(items: List[Dict], cache: Dict[str, str]) -> List[Dict]:
    """Remove itens já enviados em dias anteriores (por URL + title hash)"""
    cached_urls = {_normalize_url(url) for url in cache.keys()}

    title_cache = load_title_cache()
    cached_titles = set(title_cache.keys())

    clean = []
    duped_url = 0
    duped_title = 0

    for item in items:
        url = item.get('url', '') or item.get('source_url', '')
        title = item.get('title', '') or item.get('headline', '')

        norm_url = _normalize_url(url)

        if norm_url and norm_url in cached_urls:
            duped_url += 1
            continue

        t_hash = _title_hash(title)
        if t_hash and t_hash in cached_titles:
            duped_title += 1
            continue

        clean.append(item)

    total_duped = duped_url + duped_title
    if total_duped > 0:
        print(f"🔄 Dedup cross-edição: {duped_url} por URL + {duped_title} por título = {total_duped} removidos")
    else:
        print(f"🔄 Dedup: nenhum item repetido encontrado")

    return clean


def register_sent(curated: Dict, cache: Dict[str, str]) -> Dict[str, str]:
    """Registra URLs e title hashes dos itens enviados hoje no cache"""
    today = datetime.utcnow().isoformat()[:10]
    title_cache = load_title_cache()

    all_items = []
    all_items.extend(curated.get('items', []))
    all_items.extend(curated.get('world', []))
    all_items.extend(curated.get('quick_links', []))
    tool = curated.get('tool_of_day', {})
    if tool:
        all_items.append(tool)

    for item in all_items:
        url = item.get('source_url', '')
        if url:
            cache[_normalize_url(url)] = today
        title = item.get('headline', '') or item.get('title', '')
        t_hash = _title_hash(title)
        if t_hash:
            title_cache[t_hash] = today

    save_title_cache(title_cache)
    return cache
