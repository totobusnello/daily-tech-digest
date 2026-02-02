#!/usr/bin/env python3
"""
THE DAILY BYTE - Processador de Curadoria
Usa Claude para filtrar e curar notícias quentíssimas
"""

import os
import json
import anthropic
from datetime import datetime
from pathlib import Path

# ============================================
# CONFIGURAÇÃO
# ============================================

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# ============================================
# PROMPTS
# ============================================

CURATOR_SYSTEM = """Você é o curador do THE DAILY BYTE, um digest de tech/AI para profissionais brasileiros que traz APENAS notícias quentíssimas, primeira mão e impactantes.

Sua missão: ZERO mesmice. Os leitores são profissionais de tech que já viram tudo.

⚠️ IDIOMA: TODO o output deve ser em PORTUGUÊS BRASILEIRO:
- Headlines em português
- "why_it_matters" em português
- TL;DR bullets em português
- Análise do dia em português
- Apenas URLs e nomes próprios (como @sama, OpenAI) ficam em inglês

REGRAS DE OURO:
1. FRESHNESS - Só últimas 24h, priorize <12h
2. PRIMEIRA MÃO - Post do CEO > Artigo sobre o post
3. IMPACTO - Muda o jogo, não incremental
4. EXCLUSIVO - Se já vi em 3 newsletters, não é breaking

Heat Score mínimo para entrar: 60 pontos
- Freshness (40 pts): <6h=40, 6-12h=30, 12-24h=20, >24h=0
- Fonte (30 pts): Fundador=30, Jornalista=25, Release=20, Agregador=0
- Impacto (30 pts): Lançamento=30, M&A=25, Drama=20, Incremental=5

IMPORTANTE: Todo item DEVE ter URL clicável para fonte original."""


CURATOR_USER_TEMPLATE = """Analise estes {total} itens coletados e selecione no MÁXIMO 15 para o digest de hoje.

DADOS COLETADOS:
```json
{items}
```

RETORNE JSON com esta estrutura:
{{
  "date": "YYYY-MM-DD",
  "tldr": ["bullet 1", "bullet 2", "bullet 3"],
  "items": [
    {{
      "headline": "Max 12 palavras",
      "why_it_matters": "2 linhas de contexto",
      "source_url": "URL ORIGINAL",
      "source_name": "@handle ou Publicação",
      "source_type": "tweet|article|video|paper",
      "hours_ago": 4,
      "heat_score": 75,
      "category": "breaking|ai_models|big_tech|watch_later"
    }}
  ],
  "daily_analysis": "Parágrafo conectando os pontos do dia",
  "stats": {{
    "total_analyzed": X,
    "selected": Y,
    "rejected_too_old": Z,
    "rejected_low_impact": W
  }}
}}

LEMBRE-SE:
- NO máximo 15 itens selecionados
- Priorize BREAKING real (não requentado)
- Todo item precisa de source_url válida
- Seja impiedoso na curadoria - menos é mais
- ⚠️ ESCREVA TUDO EM PORTUGUÊS BRASILEIRO (headlines, why_it_matters, tldr, análise)"""


# ============================================
# PROCESSADOR
# ============================================

def load_raw_data(path: str = "/tmp/digest_raw.json") -> dict:
    """Carrega dados brutos do coletor"""
    with open(path, 'r') as f:
        return json.load(f)


def curate_with_claude(raw_data: dict) -> dict:
    """Usa Claude para curar as notícias"""

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepare items (limit to recent and trim content)
    items = raw_data.get('items', [])

    # Pre-filter: only <24h
    items = [i for i in items if i.get('hours_ago', 100) <= 24]

    # Trim content for context
    for item in items:
        if len(item.get('content', '')) > 500:
            item['content'] = item['content'][:500] + '...'

    prompt = CURATOR_USER_TEMPLATE.format(
        total=len(items),
        items=json.dumps(items[:100], ensure_ascii=False, indent=2)  # Max 100 for context
    )

    print(f"🤖 Enviando {len(items)} itens para Claude curar...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=CURATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    response_text = response.content[0].text

    # Extract JSON from response
    try:
        # Try to find JSON in response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        curated = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"⚠️ Erro parsing JSON: {e}")
        print(f"Response: {response_text[:500]}")
        curated = {"error": str(e), "raw_response": response_text}

    return curated


def save_curated(data: dict, path: str = "/tmp/digest_curated.json"):
    """Salva dados curados"""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Curadoria salva em {path}")


# ============================================
# MAIN
# ============================================

def process():
    """Pipeline completo de processamento"""
    print("🔥 THE DAILY BYTE - Iniciando curadoria...")

    # Load raw data
    raw_data = load_raw_data()
    print(f"📥 Carregados {raw_data['total_items']} itens brutos")

    # Curate with Claude
    curated = curate_with_claude(raw_data)

    # Add metadata
    curated['processed_at'] = datetime.utcnow().isoformat()
    curated['raw_total'] = raw_data['total_items']

    # Save
    save_curated(curated)

    # Summary
    if 'items' in curated:
        print(f"\n✅ Curadoria completa!")
        print(f"   📊 Analisados: {curated.get('stats', {}).get('total_analyzed', '?')}")
        print(f"   ✨ Selecionados: {len(curated['items'])}")

        print(f"\n📌 TL;DR:")
        for bullet in curated.get('tldr', []):
            print(f"   → {bullet}")

        print(f"\n🔥 BREAKING:")
        for item in curated['items'][:5]:
            print(f"   • {item.get('headline', '?')}")
            print(f"     Heat: {item.get('heat_score', '?')} | {item.get('source_name', '?')}")

    return curated


if __name__ == "__main__":
    process()
