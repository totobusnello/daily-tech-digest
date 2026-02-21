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
MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 8192

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
- "how_to_use" em português
- Apenas URLs e nomes próprios (como @sama, OpenAI) ficam em inglês

REGRAS DE OURO:
1. FRESHNESS - Só últimas 24h, priorize <12h (newsletters: janela de 36h)
2. PRIMEIRA MÃO - Post do CEO > Artigo sobre o post
3. IMPACTO PRÁTICO - Priorize notícias que afetam o cotidiano de quem trabalha com tech: lançamentos de produtos, mudanças em plataformas, M&A, regulações. Papers acadêmicos só entram se tiverem aplicação prática imediata.
4. EXCLUSIVO - Se já vi em 3 newsletters, não é breaking
5. ANÁLISE OBRIGATÓRIA - Cada item DEVE ter "why_it_matters" com 2-3 frases de análise contextual. Não é resumo — é o "por que um C-level deveria se importar". Este campo é ESSENCIAL para o valor do digest.

LAYOUT CONSOLIDADO v2.1 — 6 SEÇÕES:

1. "world" (3 itens): Mundo Real — mundo + Brasil. Governos, geopolítica, economia real.
2. "hoje_no_byte" (4-5 itens): A seção principal. CONSOLIDA breaking + ai_models + big_tech.
   Cada item recebe uma TAG entre: [BREAKING], [AI], [BIG TECH], [ENTERPRISE].
   A tag vai no campo "tag" do JSON.
3. "saas_enterprise" (2 itens): SaaS, valuations, CapEx, enterprise tech.
4. "tool_of_day" (1 item): UMA ferramenta AI/tech prática que o leitor pode usar HOJE.
   DEVE incluir campo "how_to_use": um prompt ou mini-tutorial copy-paste de 2-3 linhas.
   ⚠️ É um OBJETO SEPARADO no JSON (não vai no array "items").
5. "quick_links" (5-6 itens): Links rápidos — APENAS headline + URL, zero análise.
   São notícias que não cabem nas seções principais mas merecem menção.
6. "watch_later" (1 item): UM vídeo essencial. Vai no array "items" com category "watch_later".
   São notícias que não cabem nas seções principais mas merecem menção.

TOTAL MÁXIMO: 18 itens (12 principais + 6 quick links)

SEÇÃO MUNDO REAL (obrigatório):
- Selecione 3 notícias do mundo real a partir dos itens com source_type "world" ou "newsletter" com category_hint "world"
- INCLUA notícias do Brasil quando relevantes (economia, mercado, política brasileira)
- Foque em: movimentações de governos, decisões políticas globais, grandes empresas da economia real, geopolítica, trade wars, regulações
- Cada item deve ter: headline curto (max 10 palavras), contexto breve (1 frase), e a URL original

SEÇÃO COMO USAR HOJE (dentro de tool_of_day):
- O campo "how_to_use" deve conter um prompt ou tutorial PRÁTICO e COPY-PASTE ready
- Formato: "Abra [ferramenta]. Cole: [prompt exato]. Resultado: [o que esperar]."
- Deve estar ligado à ferramenta do dia OU à notícia principal do digest
- Máximo 3 linhas. Precisa ser acionável em 30 segundos.

REGRAS PARA ITENS DE NEWSLETTER (source_type "newsletter"):
- Newsletters são fontes CURADAS — tratá-las como Tier 2 de confiabilidade
- Quando o mesmo fato aparece em RSS E newsletter, PREFIRA a versão da newsletter se trouxer análise ou contexto adicional
- Se a newsletter apenas REPETE o que o RSS já trouxe sem adicionar valor, DESCARTE a duplicata
- Newsletters em português podem fornecer o ângulo brasileiro que falta nas fontes internacionais
- Fontes: AiDrop (AI), Evolving AI (AI/modelos), Update Diário (Brasil/geral), TechDrop (SaaS/enterprise), AlphaSignal (research→produto), There's An AI For That (AI tools), Turing Post (AI strategy)

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


CURATOR_USER_TEMPLATE = """Analise estes {total} itens coletados e selecione no MÁXIMO 18 para o digest de hoje.

DADOS COLETADOS:
```json
{items}
```

RETORNE JSON com esta estrutura (layout consolidado v2.1):
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
      "tag": "BREAKING|AI|BIG TECH|ENTERPRISE",
      "why_it_matters": "OBRIGATÓRIO: 2-3 frases de análise explicando POR QUE esta notícia importa para o leitor. Não é resumo — é contexto estratégico e impacto prático.",
      "source_url": "URL ORIGINAL",
      "source_name": "@handle ou Publicação",
      "source_type": "tweet|article|video|paper|newsletter",
      "hours_ago": 4,
      "heat_score": 75,
      "category": "hoje_no_byte|saas_enterprise|watch_later"
    }}
  ],
  "tool_of_day": {{
    "headline": "Nome da ferramenta — o que faz em 5 palavras",
    "why_it_matters": "2-3 frases sobre por que usar esta ferramenta",
    "how_to_use": "Prompt ou tutorial copy-paste em 2-3 linhas. Ex: Abra [tool]. Cole: [prompt]. Resultado: [o que esperar].",
    "source_url": "URL da ferramenta",
    "source_name": "Fonte"
  }},
  "quick_links": [
    {{
      "headline": "Headline curto max 8 palavras",
      "source_url": "URL ORIGINAL",
      "source_name": "Fonte"
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
- NO máximo 18 itens selecionados (12 principais + 6 quick links)
- A seção "items" usa category "hoje_no_byte" para a maioria. Cada item DEVE ter "tag" (BREAKING, AI, BIG TECH, ou ENTERPRISE)
- "saas_enterprise" é categoria separada (2 itens)
- "tool_of_day" é um OBJETO separado (não vai no array items) — DEVE ter "how_to_use"
- "quick_links" são APENAS headline + URL + fonte. SEM why_it_matters.
- "watch_later" vai no array items com category "watch_later" (1 vídeo)
- 3 itens em "world" (inclua Brasil quando relevante)
- Seja impiedoso na curadoria - menos é mais
- Notícias boas que não cabem nas seções → vão para quick_links
- ⚠️ ESCREVA TUDO EM PORTUGUÊS BRASILEIRO

⚠️ REGRA CRÍTICA sobre why_it_matters:
- CADA item (exceto quick_links) DEVE ter "why_it_matters" com 2-3 frases SUBSTANCIAIS
- NÃO é resumo — é ANÁLISE do impacto e contexto para C-levels
- NUNCA deixe why_it_matters vazio ou com apenas 1 frase curta

⚠️ REGRA CRÍTICA sobre how_to_use (tool_of_day):
- DEVE ser PRÁTICO e COPY-PASTE ready
- Máximo 3 linhas. Acionável em 30 segundos.
- Formato: "Abra [X]. Cole: [prompt]. Resultado: [Y]." """


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

    # Use assistant prefill to force JSON output (Claude will continue from '{')
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "{"}
    ]

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=CURATOR_SYSTEM,
                messages=messages
            )
            break
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"⏳ Rate limit atingido, aguardando {wait}s (tentativa {attempt + 1}/3)...")
            time.sleep(wait)
    else:
        raise RuntimeError("❌ Rate limit persistente após 3 tentativas")

    # Parse response — prepend the '{' from prefill and extract JSON
    response_text = "{" + response.content[0].text
    curated = _extract_json(response_text)

    # Check if response was truncated (stop_reason)
    stop_reason = response.stop_reason
    if stop_reason == "max_tokens":
        print(f"⚠️ Resposta TRUNCADA (max_tokens={MAX_TOKENS}). JSON incompleto.")

    if curated is None:
        # Retry once with explicit JSON-only instruction
        print("⚠️ Claude não retornou JSON válido. Fazendo retry com instrução reforçada...")
        print(f"   Stop reason: {stop_reason}")
        print(f"   Resposta original (primeiros 200 chars): {response_text[:200]}")

        retry_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=CURATOR_SYSTEM,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_text},
                {"role": "user", "content": "Sua resposta não está em formato JSON. Por favor, retorne APENAS o JSON válido conforme a estrutura solicitada. Sem texto explicativo, sem markdown, sem análise — SOMENTE o JSON."}
            ]
        )
        retry_text = retry_response.content[0].text
        curated = _extract_json(retry_text)

        if curated is None:
            print(f"❌ Retry também falhou. Resposta: {retry_text[:300]}")
            raise RuntimeError("Claude não retornou JSON válido após retry. Abortando.")

        print("✅ Retry bem-sucedido — JSON extraído.")

    return curated


def _extract_json(text: str) -> dict | None:
    """Extrai JSON de uma resposta que pode conter texto/markdown ao redor"""
    # Try 1: JSON in code block
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0]
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

    # Try 2: any code block
    if "```" in text:
        try:
            json_str = text.split("```")[1].split("```")[0]
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

    # Try 3: find first { and last } (raw JSON)
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    # Try 4: entire text is JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None


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

        print(f"\n🔥 HOJE NO BYTE:")
        for item in curated['items'][:5]:
            tag = item.get('tag', '')
            print(f"   • [{tag}] {item.get('headline', '?')}")
            print(f"     Heat: {item.get('heat_score', '?')} | {item.get('source_name', '?')}")

        tool = curated.get('tool_of_day', {})
        if tool:
            print(f"\n🛠️ TOOL DO DIA: {tool.get('headline', '?')}")

        quick = curated.get('quick_links', [])
        if quick:
            print(f"\n⚡ QUICK LINKS: {len(quick)} links")

    return curated


if __name__ == "__main__":
    process()
