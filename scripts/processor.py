#!/usr/bin/env python3
"""
THE DAILY BYTE - Processador de Curadoria
Usa Claude para filtrar e curar notícias quentíssimas
"""

import os
import json
import time
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

CURATOR_SYSTEM = """Você é o curador do THE DAILY BYTE, um digest de tech/AI para profissionais brasileiros (CEOs, CFOs, CMOs, CPOs) que traz notícias quentíssimas, primeira mão e impactantes.

Sua missão: ZERO mesmice. Os leitores são C-levels de tech que já viram tudo.

⚠️ IDIOMA: TODO o output deve ser em PORTUGUÊS BRASILEIRO:
- Headlines em português
- "why_it_matters" em português
- Seção "mundo real" em português
- Análise do dia em português
- Apenas URLs e nomes próprios (como @sama, OpenAI) ficam em inglês

REGRAS DE OURO:
1. FRESHNESS - Só últimas 24h, priorize <12h (newsletters: janela de 36h)
2. PRIMEIRA MÃO - Post do CEO > Artigo sobre o post
3. IMPACTO PRÁTICO - Priorize notícias que afetam o cotidiano de quem trabalha com tech: lançamentos de produtos, mudanças em plataformas, M&A, regulações. Papers acadêmicos só entram se tiverem aplicação prática imediata.
4. EXCLUSIVO - Se já vi em 3 newsletters, não é breaking
5. ANÁLISE OBRIGATÓRIA - Cada item DEVE ter "why_it_matters" com 2-3 frases de análise contextual. Não é resumo — é o "por que um C-level deveria se importar". Este campo é ESSENCIAL para o valor do digest.

EQUILÍBRIO DE CATEGORIAS (obrigatório):
- "breaking": 3-5 itens (notícias bombásticas do dia)
- "big_tech": 2-4 itens (movimentos de grandes empresas, lançamentos, M&A)
- "ai_models": 2-3 itens (novidades em IA com impacto real)
- "saas_enterprise": 2-3 itens (SaaS, valuations, CapEx, enterprise tech) — NOVO
- "tool_of_day": 1 item (UMA ferramenta AI/tech prática que o leitor pode usar HOJE — app, plugin, API, framework. Priorize ferramentas pouco conhecidas mas poderosas.)
- "watch_later": 1-2 itens (vídeos ou conteúdo longo)
Se não houver itens suficientes para uma categoria, tudo bem omitir. Mas NUNCA concentre tudo em uma só categoria.

SEÇÃO MUNDO REAL (obrigatório):
- Selecione 4-5 notícias do mundo real a partir dos itens com source_type "world" ou "newsletter" com category_hint "world"
- INCLUA notícias do Brasil quando relevantes (economia, mercado, política brasileira)
- Foque em: movimentações de governos, decisões políticas globais, grandes empresas da economia real (energia, indústria, infraestrutura, saúde), geopolítica, trade wars, regulações
- O objetivo é tirar o leitor da bolha tech e mostrar o que está acontecendo no mundo E no Brasil
- Cada item deve ter: headline curto (max 10 palavras), contexto breve (1 frase), e a URL original
- Priorize impacto global e relevância para profissionais brasileiros

REGRAS PARA ITENS DE NEWSLETTER (source_type "newsletter"):
- Newsletters são fontes CURADAS — tratá-las como Tier 2 de confiabilidade
- Quando o mesmo fato aparece em RSS E newsletter, PREFIRA a versão da newsletter se trouxer análise ou contexto adicional
- Se a newsletter apenas REPETE o que o RSS já trouxe sem adicionar valor, DESCARTE a duplicata
- Newsletters em português podem fornecer o ângulo brasileiro que falta nas fontes internacionais
- Fontes: AiDrop (AI), Evolving AI (AI/modelos), Update Diário (Brasil/geral), TechDrop (SaaS/enterprise), AlphaSignal (research→produto)

Heat Score mínimo para entrar: 60 pontos
- Freshness (40 pts): <6h=40, 6-12h=30, 12-24h=20, >24h=0
- Fonte (30 pts): Fundador=30, Jornalista=25, Release=20, Newsletter curada=15, Agregador=0
- Impacto (30 pts): Lançamento=30, M&A=25, Drama=20, Incremental=5
- Newsletter Bonus: Insight exclusivo=+10, Cross-validação=+5

⚠️ REGRA CRÍTICA sobre source_url:
- Todo item DEVE ter o campo "source_url" preenchido com a URL ORIGINAL do artigo/post
- COPIE a URL exatamente como veio nos dados de entrada (campo "url")
- NUNCA deixe source_url vazio, nulo ou inventado
- Se não tiver URL, NÃO inclua o item"""


CURATOR_USER_TEMPLATE = """Analise estes {total} itens coletados e selecione no MÁXIMO 20 para o digest de hoje.

DADOS COLETADOS:
```json
{items}
```

RETORNE JSON com esta estrutura:
{{
  "date": "YYYY-MM-DD",
  "world": [
    {{
      "headline": "Max 10 palavras",
      "context": "1 frase de contexto",
      "source_url": "URL ORIGINAL",
      "source_name": "Reuters|Forbes|BBC"
    }}
  ],
  "items": [
    {{
      "headline": "Max 12 palavras",
      "why_it_matters": "OBRIGATÓRIO: 2-3 frases de análise explicando POR QUE esta notícia importa para o leitor. Não é resumo — é contexto estratégico e impacto prático.",
      "source_url": "URL ORIGINAL",
      "source_name": "@handle ou Publicação",
      "source_type": "tweet|article|video|paper",
      "hours_ago": 4,
      "heat_score": 75,
      "category": "breaking|ai_models|big_tech|saas_enterprise|tool_of_day|watch_later"
    }}
  ],
  "daily_analysis": [
    "**Tema curto** — Insight conectando pontos do dia em 1-2 frases",
    "**Outro tema** — Outro insight relevante",
    "**Tendência** — O que isso sinaliza para o futuro próximo"
  ],
  "stats": {{
    "total_analyzed": X,
    "selected": Y,
    "rejected_too_old": Z,
    "rejected_low_impact": W
  }}
}}

LEMBRE-SE:
- NO máximo 20 itens selecionados
- Priorize BREAKING real (não requentado)
- Todo item precisa de source_url válida
- Seja impiedoso na curadoria - menos é mais
- Inclua itens de NEWSLETTER quando trouxerem análise ou ângulo único
- A categoria "saas_enterprise" cobre: SaaS, CapEx, valuations, enterprise tech
- Na seção "world", inclua pelo menos 1 notícia relevante do Brasil quando disponível
- ⚠️ ESCREVA TUDO EM PORTUGUÊS BRASILEIRO (headlines, why_it_matters, mundo real, análise)

⚠️ REGRA CRÍTICA sobre why_it_matters:
- CADA item DEVE ter um "why_it_matters" com 2-3 frases SUBSTANCIAIS
- NÃO é um resumo da notícia — é uma ANÁLISE do impacto e contexto
- Responda: "Por que um CEO/CFO/CMO/CPO deveria se importar com isso?"
- Conecte com tendências maiores, impacto no mercado, ou ação prática
- NUNCA deixe why_it_matters vazio ou com apenas 1 frase curta"""


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

    # Pre-filter: <24h for regular sources, <36h for newsletters
    items = [i for i in items if (
        i.get('hours_ago', 100) <= 36 if i.get('source_type') == 'newsletter'
        else i.get('hours_ago', 100) <= 24
    )]

    # Trim content for context
    for item in items:
        if len(item.get('content', '')) > 500:
            item['content'] = item['content'][:500] + '...'

    prompt = CURATOR_USER_TEMPLATE.format(
        total=len(items),
        items=json.dumps(items[:40], ensure_ascii=False, indent=2)  # Max 40 items (increased for newsletters)
    )

    print(f"🤖 Enviando {len(items)} itens para Claude curar...")

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=CURATOR_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            break
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"⏳ Rate limit atingido, aguardando {wait}s (tentativa {attempt + 1}/3)...")
            time.sleep(wait)
    else:
        raise RuntimeError("❌ Rate limit persistente após 3 tentativas")

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

    # Check for override file (resend)
    override_path = Path(__file__).parent / "resend_curated.json"
    if override_path.exists():
        print("📦 Usando curadoria override (resend)...")
        with open(override_path, 'r') as f:
            curated = json.load(f)
        save_curated(curated)
        print(f"✅ Override aplicado com {len(curated.get('items', []))} itens")
        return curated

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

        print(f"\n🌍 MUNDO REAL:")
        for item in curated.get('world', []):
            print(f"   → {item.get('headline', '?')}")

        print(f"\n🔥 BREAKING:")
        for item in curated['items'][:5]:
            print(f"   • {item.get('headline', '?')}")
            print(f"     Heat: {item.get('heat_score', '?')} | {item.get('source_name', '?')}")

    return curated


if __name__ == "__main__":
    process()
