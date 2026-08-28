#!/usr/bin/env python3
"""THE DAILY BYTE - Feed Health Check
Monitors RSS/Substack/YouTube feed health. Non-blocking."""

import json, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, feedparser
from collector import RSS_FEEDS, WORLD_FEEDS, SUBSTACK_FEEDS, YOUTUBE_CHANNELS

HEALTH_FILE = "/tmp/digest_feed_health.json"
TIMEOUT = 10
MAX_WORKERS = 15
FAILURE_THRESHOLD = 3

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _load_previous():
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def _build_feed_dict():
    """Merge all feed sources into {name: url}."""
    feeds = {}
    feeds.update(RSS_FEEDS)
    feeds.update(WORLD_FEEDS)
    feeds.update(SUBSTACK_FEEDS)
    for name, cid in YOUTUBE_CHANNELS.items():
        feeds[name] = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    return feeds

def _check_feed(name, url):
    """Try fetching a feed. Returns (name, ok, error_msg).

    O erro devolvido precisa dizer O QUE aconteceu. Até a v2.16 esta função
    engolia toda exceção num `except: pass` e caía num return genérico, então
    timeout, 403, DNS e feed-realmente-vazio viravam a MESMA string
    "No entries returned". Resultado: 16 feeds passaram 39 dias marcados como
    quebrados sem que ninguém pudesse agir, porque o sinal não distinguia
    "o site nos bloqueou" de "o autor não publicou".
    """
    erro_http = None
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers=_BROWSER_HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            if feed.entries:
                return (name, True, None)
            # 200 sem entries: pode ser feed vazio de verdade ou uma página de
            # desafio/anti-bot devolvida com status 200. Distinguir pelo content-type.
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
            if "html" in ctype.lower():
                erro_http = f"HTTP 200 mas veio HTML ({ctype}) — provável bloqueio anti-bot"
            else:
                erro_http = f"HTTP 200, content-type {ctype or 'desconhecido'}, zero entries"
        else:
            erro_http = f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        erro_http = f"timeout apos {TIMEOUT}s"
    except requests.exceptions.SSLError as e:
        erro_http = f"erro TLS: {str(e)[:80]}"
    except requests.exceptions.ConnectionError as e:
        erro_http = f"falha de conexao/DNS: {str(e)[:80]}"
    except Exception as e:
        erro_http = f"{type(e).__name__}: {str(e)[:80]}"

    # Fallback: feedparser sozinho (UA próprio dele, às vezes passa onde requests apanha)
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            return (name, True, None)
        erro_fb = "sem entries"
    except Exception as e:
        erro_fb = f"{type(e).__name__}: {str(e)[:60]}"

    return (name, False, f"{erro_http} | fallback feedparser: {erro_fb}")

def main():
    feeds = _build_feed_dict()
    previous = _load_previous()
    now = datetime.utcnow().isoformat() + "Z"
    print(f"🏥 Health check: {len(feeds)} feeds")

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_check_feed, n, u): n for n, u in feeds.items()}
        for future in as_completed(futures):
            name, ok, error = future.result()
            prev = previous.get(name, {})
            if ok:
                results[name] = {"last_success": now, "consecutive_failures": 0, "last_error": None}
            else:
                results[name] = {
                    "last_success": prev.get("last_success"),
                    "consecutive_failures": prev.get("consecutive_failures", 0) + 1,
                    "last_error": error,
                }

    with open(HEALTH_FILE, "w") as f:
        json.dump(results, f, indent=2)

    healthy = sum(1 for r in results.values() if r["consecutive_failures"] == 0)
    unhealthy = [n for n, r in results.items() if r["consecutive_failures"] >= FAILURE_THRESHOLD]
    print(f"   ✅ Healthy: {healthy}/{len(results)}")
    print(f"   ⚠️  Unhealthy (3+ failures): {len(unhealthy)}")
    for name in sorted(unhealthy):
        r = results[name]
        print(f"   WARNING: {name} — {r['consecutive_failures']} consecutive failures — {r['last_error']}")
    print(f"📄 Saved to {HEALTH_FILE}")

    # Alerta só para quem CRUZOU o limiar hoje (== FAILURE_THRESHOLD).
    # Alertar por todos os >= threshold repetiria a mesma issue todo dia:
    # os 16 feeds que ficaram 39 dias quebrados teriam gerado 39 issues idênticas.
    novos = sorted(n for n, r in results.items() if r["consecutive_failures"] == FAILURE_THRESHOLD)
    if novos:
        _abrir_issue(novos, results)


def _abrir_issue(novos, results):
    """Abre GitHub Issue para feeds que acabaram de cruzar o limiar de falhas.

    Silencioso fora do GitHub Actions (gh CLI ausente) — o health check é
    não-bloqueante e nunca deve derrubar o pipeline por causa do alerta.
    """
    import subprocess
    from datetime import date

    linhas = [f"- `{n}` — {results[n]['last_error']}" for n in novos]
    corpo = (
        f"## 🩺 {len(novos)} feed(s) cruzaram {FAILURE_THRESHOLD} falhas consecutivas\n\n"
        + "\n".join(linhas)
        + "\n\n### Como agir\n"
        "1. Teste o feed fora do runner: `curl -sI -A 'Mozilla/5.0' <url>`\n"
        "2. Se responder 200 na sua máquina e falhar aqui, é bloqueio ao IP do GitHub Actions "
        "— procure um feed alternativo (domínio próprio da publicação em vez de `*.substack.com`).\n"
        "3. Se o autor simplesmente parou de publicar, remova a fonte do `collector.py`.\n\n"
        "> Alerta automático do health check. Só dispara na virada do limiar, "
        "não todo dia — se a fonte continuar quebrada, esta issue segue valendo.\n"
    )
    try:
        subprocess.run(
            ["gh", "issue", "create",
             "--title", f"🩺 {len(novos)} feed(s) quebrados — {date.today().isoformat()}",
             "--body", corpo,
             "--label", "pipeline-failure"],
            check=True, capture_output=True, timeout=30,
        )
        print(f"   🔔 Issue aberta para {len(novos)} feed(s) recém-quebrados")
    except FileNotFoundError:
        print("   (gh CLI ausente — alerta só no log)")
    except Exception as e:
        print(f"   ⚠️ Não consegui abrir issue: {type(e).__name__}")

if __name__ == "__main__":
    main()
