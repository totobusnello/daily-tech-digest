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


def dedup_items(items: List[Dict], cache: Dict[str, str]) -> List[Dict]:
    """Remove itens que já foram enviados em dias anteriores"""
    cached_urls = {_normalize_url(url) for url in cache.keys()}

    clean = []
    duped = 0

    for item in items:
        url = item.get('url', '') or item.get('source_url', '')
        title = item.get('title', '') or item.get('headline', '')

        norm_url = _normalize_url(url)

        if norm_url and norm_url in cached_urls:
            duped += 1
            continue

        clean.append(item)

    if duped > 0:
        print(f"🔄 Dedup: removidos {duped} itens já enviados em dias anteriores")
    else:
        print(f"🔄 Dedup: nenhum item repetido encontrado")

    return clean


def register_sent(curated: Dict, cache: Dict[str, str]) -> Dict[str, str]:
    """Registra URLs dos itens enviados hoje no cache"""
    today = datetime.utcnow().isoformat()[:10]

    # Registra itens principais
    for item in curated.get('items', []):
        url = item.get('source_url', '')
        if url:
            cache[_normalize_url(url)] = today

    # Registra world items
    for item in curated.get('world', []):
        url = item.get('source_url', '')
        if url:
            cache[_normalize_url(url)] = today

    # Registra tool_of_day
    tool = curated.get('tool_of_day', {})
    if tool and tool.get('source_url'):
        cache[_normalize_url(tool['source_url'])] = today

    # Registra quick_links
    for item in curated.get('quick_links', []):
        url = item.get('source_url', '')
        if url:
            cache[_normalize_url(url)] = today

    return cache
