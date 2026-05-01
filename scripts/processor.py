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

# v2.3: Dedup entre dias
try:
    from dedup import load_cache, dedup_items
except ImportError:
    load_cache = None
    dedup_items = None

# v2.4: Feedback loop — engagement data from Buttondown
try:
    from feedback import load_feedback
except ImportError:
    load_feedback = None

# ============================================
# CONFIGURAÇÃO
# ============================================

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

# ============================================
# PROMPTS
# ============================================

CURATOR_SYSTEM = """Você é o curador do THE DAILY BYTE, um digest de tech/AI para profissionais brasileiros (CEOs, CFOs, CMOs, CPOs) que traz notícias quentíssimas, primeira mão e impactantes.

Sua missão: ZERO mesmice. Os leitores são C-levels de tech que já viram tudo.

⚠️ IDIOMA OBRIGATÓRIO — PORTUGUÊS BRASILEIRO em 100% do output:
- Headlines em português
- "why_it_matters" em português
- Seção "mundo real" em português
- Análise do dia em português
- "how_to_use" em português (NUNCA use palavras em inglês como "Expect", "Result", "Open", "Click")
- "prompt_of_day" em português
- "subject_hook" em português
- "context" (number_of_day) em português
- Apenas URLs, nomes de ferramentas/produtos (ex: ChatGPT, Notion) e handles (ex: @sama) ficam em inglês
- NUNCA misture inglês no meio de frases em português. Se a palavra tem equivalente em PT-BR, USE o equivalente.

REGRAS DE OURO:
1. FRESHNESS - Só últimas 24h, priorize <12h (newsletters: janela de 36h)
2. PRIMEIRA MÃO - Post do CEO > Artigo sobre o post
3. IMPACTO PRÁTICO - Priorize notícias que afetam o cotidiano de quem trabalha com tech: lançamentos de produtos, mudanças em plataformas, M&A, regulações. Papers acadêmicos só entram se tiverem aplicação prática imediata.
4. EXCLUSIVO - Se já vi em 3 newsletters, não é breaking
5. ANÁLISE OBRIGATÓRIA - Cada item DEVE ter "why_it_matters" com 1-2 frases INCISIVAS e PRESCRITIVAS. Não é resumo — é "o que um C-level deve FAZER com essa informação". Responda: qual decisão, ação ou conversa isso deve disparar? Ex: "CFOs: revisem orçamento de cloud para Q3" > "Preços de cloud estão subindo". Máximo 2 frases curtas e densas.
6. INEDITISMO OBRIGATÓRIO - Pelo menos 30% dos itens (4+ de 12) devem ser notícias que NÃO apareceram em outros digests/newsletters populares. Busque fontes primárias, anúncios diretos, tweets de fundadores, papers originais. Histórias que todo mundo já cobriu valem MENOS do que um dado exclusivo de uma fonte primária.
7. DIVERSIDADE TEMÁTICA - NÃO coloque 3+ itens sobre o mesmo tema/empresa. Se há 5 notícias sobre OpenAI, escolha a MELHOR e mova as outras para quick_links (se merecerem menção).

LAYOUT CONSOLIDADO v2.2 — 6 SEÇÕES + 2 MICRO-SEÇÕES:

1. "world" (3 itens): Mundo Real — mundo + Brasil. Governos, geopolítica, economia real.
2. "hoje_no_byte" (4-5 itens): A seção principal. CONSOLIDA breaking + ai_models + big_tech.
   Cada item recebe uma TAG entre: [BREAKING], [AI], [BIG TECH], [ENTERPRISE].
   A tag vai no campo "tag" do JSON.
3. "saas_enterprise" (2 itens): SaaS, valuations, CapEx, enterprise tech.
4. "tool_of_day" (1 item): UMA ferramenta AI/tech prática que o leitor pode usar HOJE.
   DEVE incluir campo "how_to_use": um prompt ou mini-tutorial copy-paste de 2-3 linhas.
   DEVE incluir campo "prompt_of_day": um prompt COPY-PASTE ready para ChatGPT/Claude/Gemini, ligado à notícia principal do dia ou à ferramenta. Máximo 3 linhas.
   ⚠️ É um OBJETO SEPARADO no JSON (não vai no array "items").
5. "quick_links" (5-6 itens): Links rápidos — APENAS headline + URL, zero análise.
   São notícias que não cabem nas seções principais mas merecem menção.
6. "watch_later" (1 item): UM vídeo essencial. Vai no array "items" com category "watch_later".

MICRO-SEÇÃO — "number_of_day":
- UM data point impactante do dia, extraído das notícias analisadas.
- Formato: {"value": "$600B", "context": "Meta de compute da OpenAI até 2030"}
- Deve ser um número que CHOQUE e contextualize uma tendência macro.
- OUSADIA: prefira valores absolutos grandes ($600B, 10M usuários, 3x mais rápido) sobre percentuais genéricos (15% de crescimento). O número deve fazer o leitor parar e pensar.
- É um OBJETO SEPARADO no JSON.

TOTAL MÁXIMO: 18 itens (12 principais + 6 quick links)

SEÇÃO MUNDO REAL (obrigatório):
- Selecione 3 notícias do mundo real a partir dos itens com source_type "world" ou "newsletter" com category_hint "world"
- INCLUA notícias do Brasil quando relevantes (economia, mercado, política brasileira)
- Foque em: movimentações de governos, decisões políticas globais, grandes empresas da economia real, geopolítica, trade wars, regulações
- Cada item deve ter: headline curto (max 10 palavras), contexto breve (1 frase), e a URL original

SEÇÃO COMO USAR HOJE (dentro de tool_of_day):
- O campo "how_to_use" deve conter um prompt ou tutorial PRÁTICO e COPY-PASTE ready
- Formato: "Abra [ferramenta]. Cole: [prompt exato]. Resultado: [o que vai acontecer]."
- Deve estar ligado à ferramenta do dia OU à notícia principal do digest
- Máximo 3 linhas. Precisa ser acionável em 30 segundos.
- ⚠️ TUDO EM PORTUGUÊS. Não use "Expect", "Result", "Open" — use "Espere", "Resultado", "Abra".

REGRAS PARA ITENS DE NEWSLETTER (source_type "newsletter"):
- Newsletters são fontes CURADAS — tratá-las como Tier 2 de confiabilidade
- Quando o mesmo fato aparece em RSS E newsletter, PREFIRA a versão da newsletter se trouxer análise ou contexto adicional
- Se a newsletter apenas REPETE o que o RSS já trouxe sem adicionar valor, DESCARTE a duplicata
- Newsletters em português podem fornecer o ângulo brasileiro que falta nas fontes internacionais
- Fontes: AiDrop (AI), Evolving AI (AI/modelos), Update Diário (Brasil/geral), TechDrop (SaaS/enterprise), AlphaSignal (research→produto), There's An AI For That (AI tools), Turing Post (AI strategy), Import AI (policy/research, Jack Clark), Distrito News Inside VC (startups/VC Brasil)

Heat Score mínimo para entrar: 60 pontos
- Freshness (40 pts): <6h=40, 6-12h=30, 12-24h=20, >24h=0
- Fonte (30 pts): Fundador/blog oficial=30, Jornalista=25, Release=20, Newsletter curada=15, Agregador=0
- Impacto (30 pts): Lançamento=30, M&A=25, Drama=20, Incremental=5
- Newsletter Bonus: Insight exclusivo=+10, Cross-validação=+5
- Ineditismo Bonus: Fonte primária (blog oficial, tweet de fundador)=+15, Community-driven (Reddit, HN Show, Lobsters)=+10, Indie builder/practitioner=+10
- Penalidade Mainstream: Se 3+ fontes mainstream (TechCrunch, Wired, Verge, Reuters, BBC) cobriram a mesma história=-10 pontos. Se todo mundo já cobriu, não é notícia — é eco.

HIERARQUIA DE FONTES (do mais ao menos valioso):
1. FONTE PRIMÁRIA — Blog oficial do lab/empresa, tweet do CEO/fundador, press release, paper original. É a notícia ANTES da cobertura.
2. INDIE/BUILDER — Simon Willison, Lilian Weng, Chip Huyen, Latent Space, Stratechery, Pragmatic Engineer. Análise original com ponto de vista único.
3. COMMUNITY — Reddit r/MachineLearning, r/LocalLLaMA, HN Show, Lobsters. O que practitioners estão discutindo ANTES da mídia cobrir.
4. NEWSLETTER CURADA — AiDrop, AlphaSignal, Import AI. Contexto e análise que agrega valor.
5. MÍDIA ESPECIALIZADA — TechCrunch, The Decoder, VentureBeat. Boa cobertura mas todo mundo já leu.
6. MAINSTREAM — Reuters, BBC, CNBC. Útil para "mundo real" mas zero ineditismo em tech.

⚠️ SE TIVER QUE ESCOLHER: prefira a análise do Simon Willison sobre um novo modelo ao artigo do TechCrunch sobre o mesmo modelo. O leitor do Daily Byte quer o que ELE NÃO ENCONTRA sozinho scrollando o feed.

⚠️ REGRA CRÍTICA sobre source_url:
- Todo item DEVE ter o campo "source_url" preenchido com a URL ORIGINAL do artigo/post
- COPIE a URL exatamente como veio nos dados de entrada (campo "url")
- NUNCA deixe source_url vazio, nulo ou inventado
- Se não tiver URL, NÃO inclua o item

🎯 REGRA sobre why_it_matters (AÇÃO para C-level):
- O why_it_matters deve responder: "O que o CEO/CFO/CMO deve FAZER com essa informação?"
- NÃO seja descritivo — seja PRESCRITIVO. Qual decisão, ação ou conversa isso deve disparar?
- Ex: "CFOs devem reavaliar orçamento de cloud" > "Preços de cloud estão subindo"
- Ex: "CMOs: testem essa ferramenta na campanha de Q2" > "Nova ferramenta de marketing lançada" """


CURATOR_USER_TEMPLATE = """Analise estes {total} itens coletados e selecione no MÁXIMO 18 para o digest de hoje.

DADOS COLETADOS:
```json
{items}
```

RETORNE JSON com esta estrutura (layout consolidado v2.2):
{{
  "date": "YYYY-MM-DD",
  "subject_hook": "Frase-gancho de max 6 palavras sobre a notícia mais impactante do dia. Ex: 'OpenAI mira $600B em compute'",
  "number_of_day": {{
    "value": "$600B",
    "context": "Meta de compute da OpenAI até 2030 — o maior CapEx da história da tecnologia"
  }},
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
      "why_it_matters": "OBRIGATÓRIO: 1-2 frases INCISIVAS de análise explicando POR QUE esta notícia importa. Direto ao ponto, sem resumo.",
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
    "why_it_matters": "1-2 frases INCISIVAS sobre por que usar esta ferramenta",
    "how_to_use": "Prompt ou tutorial copy-paste em 2-3 linhas. Ex: Abra [tool]. Cole: [prompt]. Resultado: [o que esperar].",
    "prompt_of_day": "Um prompt COPY-PASTE ready para ChatGPT/Claude/Gemini ligado à notícia principal ou à ferramenta. Ex: 'Analise o impacto de [notícia] no setor de [setor]. Liste 3 riscos e 2 oportunidades em formato executivo.'",
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
- "tool_of_day" é um OBJETO separado (não vai no array items) — DEVE ter "how_to_use" E "prompt_of_day"
- "quick_links" são APENAS headline + URL + fonte. SEM why_it_matters.
- "watch_later" vai no array items com category "watch_later" (1 vídeo)
- 3 itens em "world" (inclua Brasil quando relevante)
- Seja impiedoso na curadoria - menos é mais
- Notícias boas que não cabem nas seções → vão para quick_links
- ⚠️ ESCREVA TUDO EM PORTUGUÊS BRASILEIRO — ZERO palavras em inglês no texto (exceto nomes de produtos/pessoas/URLs). Palavras como "Expect", "Result", "Click", "Open" devem ser escritas em PT-BR: "Espere", "Resultado", "Clique", "Abra".
- "subject_hook" é uma frase-gancho de max 6 palavras sobre a notícia mais impactante
- "number_of_day" é UM data point numérico impressionante extraído das notícias (value + context)

{feedback_section}

⚠️ REGRA CRÍTICA sobre why_it_matters:
- CADA item (exceto quick_links) DEVE ter "why_it_matters" com 1-2 frases INCISIVAS e PRESCRITIVAS
- NÃO é resumo — é AÇÃO: "O que o CEO/CFO/CMO deve FAZER com essa informação?"
- Ex: "CTOs: avaliem migração para esta API antes do Q3" > "Nova API foi lançada"
- Seja DIRETO: menos texto, mais impacto. Máximo 2 frases curtas e densas.
- NUNCA deixe why_it_matters vazio

⚠️ REGRA CRÍTICA sobre how_to_use (tool_of_day):
- DEVE ser PRÁTICO e COPY-PASTE ready
- Máximo 3 linhas. Acionável em 30 segundos.
- Formato: "Abra [X]. Cole: [prompt]. Resultado: [Y]."
- ⚠️ 100% EM PORTUGUÊS. Nunca misture inglês (ex: "Expect" → "Espere", "Open" → "Abra").

⚠️ ÚLTIMO LEMBRETE — IDIOMA:
Todo texto que você gerar DEVE estar em português brasileiro. Se você perceber qualquer palavra em inglês no meio de uma frase portuguesa, substitua pelo equivalente em PT-BR. Nomes próprios de empresas/produtos/pessoas são a ÚNICA exceção.

⚠️ REGRA CRÍTICA — ORTOGRAFIA PORTUGUESA:
- Revise CADA palavra antes de escrever. Use apenas palavras que EXISTEM no português brasileiro.
- NÃO invente palavras. Ex: "céfico" NÃO EXISTE — o correto é "cético" (com S, não C).
- Acentuação correta obrigatória: "análise" (não "analise"), "estratégia" (não "estrategia"), "mercê" (não "merce").
- Em caso de dúvida sobre grafia, escolha uma palavra mais simples que você tenha 100% de certeza.
- Palavras comumente erradas que você NÃO pode escrever errado: cético, análise, estratégia, trajetória, até, já, está, não.

⚠️ REGRA CRÍTICA — DEDUPLICAÇÃO ENTRE SEÇÕES (ANTI-REPETIÇÃO):
- A MESMA notícia NÃO pode aparecer em múltiplas seções do digest — nem com headline diferente!
- Se uma notícia sobre "X" está em "hoje_no_byte", ela NÃO PODE estar em "world", "saas_enterprise", "quick_links" ou "watch_later".
- Isso vale para o MESMO TÓPICO/EVENTO/EMPRESA, mesmo com ângulos diferentes. Ex: "regulação EU de AI" não pode estar em "world" (como política) E em "hoje_no_byte" (como tech) — escolha UMA seção.
- Antes de finalizar, FAÇA UMA VERIFICAÇÃO ITEM A ITEM: percorra CADA headline de CADA seção e confira se há notícias sobre o mesmo fato/empresa/evento em seções diferentes.
- Se detectar duplicata, MANTENHA na seção mais relevante e REMOVA das outras.
- O mesmo vale para quick_links: não repetir headline que já foi coberta em item completo acima.
- TESTE FINAL: liste mentalmente todas as empresas/eventos mencionados — se algum aparece em 2+ seções, remova a duplicata.

⚠️ REGRA CRÍTICA — INEDITISMO E FRESCOR:
- PRIORIZE notícias de fontes primárias (tweets de fundadores, blogs oficiais, press releases) sobre artigos de cobertura (TechCrunch, The Verge cobrindo o mesmo lançamento).
- Quando o campo "_cluster_size" existir no item, ele indica quantas fontes cobriram a mesma história. Itens com _cluster_size alto (>3) são amplamente cobertos = MENOS inéditos. Prefira itens com _cluster_size=1 ou sem esse campo.
- Se todos os itens são "óbvios" (cobertos por toda a mídia), procure pelo menos 2-3 itens de nicho, análise original ou dados exclusivos para balancear. """


# ============================================
# PROCESSADOR
# ============================================

def load_raw_data(path: str = "/tmp/digest_raw.json") -> dict:
    """Carrega dados brutos do coletor"""
    with open(path, 'r') as f:
        return json.load(f)


_SOURCE_PRIORITY = {
    'tweet': 4, 'newsletter': 3, 'article': 2, 'paper': 2,
    'video': 1, 'world': 2,
}


def _cluster_and_pick_best(items: list) -> list:
    """
    Agrupa itens sobre o mesmo assunto e mantém apenas o melhor de cada cluster.
    'Melhor' = mais fresco + fonte de maior prioridade.
    Itens únicos passam direto.
    """
    clusters = []
    for item in items:
        title = item.get('title', '') or item.get('headline', '')
        matched = False
        for cluster in clusters:
            rep_title = cluster[0].get('title', '') or cluster[0].get('headline', '')
            if _titles_overlap(title, rep_title):
                cluster.append(item)
                matched = True
                break
        if not matched:
            clusters.append([item])

    result = []
    clustered_count = 0
    for cluster in clusters:
        if len(cluster) == 1:
            result.append(cluster[0])
        else:
            clustered_count += len(cluster) - 1
            best = min(cluster, key=lambda x: (
                -_SOURCE_PRIORITY.get(x.get('source_type', ''), 0),
                x.get('hours_ago', 999),
            ))
            best['_cluster_size'] = len(cluster)
            result.append(best)

    if clustered_count > 0:
        print(f"🔗 Pré-clustering: {clustered_count} itens redundantes removidos ({len(clusters)} clusters)")

    return result


def _cap_per_source(items: list, max_per_source: int = 5) -> list:
    """Limita itens por fonte para forçar diversidade"""
    counts = {}
    result = []
    capped = 0
    for item in items:
        src = (item.get('source_name', '') or '').lower()
        counts[src] = counts.get(src, 0) + 1
        if counts[src] <= max_per_source:
            result.append(item)
        else:
            capped += 1
    if capped > 0:
        print(f"✂️ Cap por fonte: {capped} itens cortados (max {max_per_source}/fonte)")
    return result


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

    # v2.3: Dedup — remove itens já enviados em dias anteriores
    if dedup_items and load_cache:
        cache = load_cache()
        items = dedup_items(items, cache)

    # Trim content and strip heavy fields to save tokens
    CURATOR_FIELDS = ['title', 'content', 'url', 'source_name', 'source_type', 'author', 'published_at', 'hours_ago', 'engagement', '_cluster_size']
    slim_items = []
    for item in items:
        slim = {k: item.get(k) for k in CURATOR_FIELDS if item.get(k) is not None}
        # Trim content to 500 chars
        if len(slim.get('content', '')) > 500:
            slim['content'] = slim['content'][:500] + '...'
        slim_items.append(slim)

    # v2.9: Pre-cluster — agrupar itens sobre o mesmo assunto e manter apenas o melhor representante
    slim_items = _cluster_and_pick_best(slim_items)

    # v2.9: Cap por fonte — max 5 itens por source_name para forçar diversidade
    slim_items = _cap_per_source(slim_items, max_per_source=5)

    # Sort by freshness (hours_ago ascending) then send top 80
    slim_items.sort(key=lambda x: x.get('hours_ago', 999))

    # v2.4: Load feedback data from Buttondown (if available)
    feedback_section = ""
    if load_feedback:
        feedback_data = load_feedback()
        if feedback_data and feedback_data.get('status') == 'ok':
            hint = feedback_data.get('curator_hint', '')
            top_themes = feedback_data.get('top_themes', [])
            agg = feedback_data.get('aggregate', {})

            feedback_lines = ["📊 FEEDBACK DA SEMANA (dados de engajamento dos últimos 7 dias):"]
            if hint:
                feedback_lines.append(f"💡 Dica: {hint}")
            if agg:
                feedback_lines.append(f"📈 Open rate médio: {agg.get('avg_open_rate', 0)}% | Click rate: {agg.get('avg_click_rate', 0)}% | Subscribers: {agg.get('subscriber_count', 0)}")
            if top_themes:
                theme_strs = [f"  - \"{t.get('hook', '')}\" ({t.get('clicks', 0)} clicks, {t.get('open_rate', 0)}% open rate)" for t in top_themes]
                feedback_lines.append("🏆 Temas com mais engajamento:\n" + "\n".join(theme_strs))
            feedback_lines.append("→ Use estes dados para PRIORIZAR temas similares aos que geraram mais engajamento.")

            # v2.6: Hooks recentes para evitar subject lines repetidas
            recent_hooks = feedback_data.get('recent_hooks', [])
            if recent_hooks:
                hook_strs = [f"  - {h.get('date', '?')}: \"{h.get('hook', '')}\"" for h in recent_hooks[:5]]
                feedback_lines.append("\n⚠️ SUBJECT HOOKS RECENTES (NÃO REPETIR temas similares):\n" + "\n".join(hook_strs))
                feedback_lines.append("→ O subject_hook de HOJE deve ser sobre um tema DIFERENTE dos listados acima. Diversifique! Se a notícia mais impactante for do mesmo tema, escolha o SEGUNDO tema mais impactante para o hook.")

            feedback_section = "\n".join(feedback_lines)
            print(f"📊 Feedback loop ativo: {len(top_themes)} temas top, open rate {agg.get('avg_open_rate', 0)}%")
        else:
            print("📊 Feedback loop: sem dados disponíveis (primeiro run ou API indisponível)")

    # v2.7: Workflow da Semana (sextas-feiras)
    is_friday = datetime.utcnow().weekday() == 4  # Monday=0, Friday=4
    workflow_section = ""
    if is_friday:
        workflow_section = """

🗓️ HOJE É SEXTA — INCLUA O "WORKFLOW DA SEMANA":
- Adicione o campo "weekly_workflow" no JSON com um mini-workflow prático de 3-4 steps
- Tema: baseado na notícia mais impactante ou na ferramenta do dia
- Formato: {"title": "Título do workflow", "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ..."]}
- Cada step deve ser ACIONÁVEL e copy-paste ready para um C-level implementar na empresa
- Ex: {"title": "Automatize relatórios com Claude", "steps": ["1. Exporte seu dashboard em CSV", "2. Abra Claude e cole: 'Analise este CSV...'", "3. Peça: 'Gere um resumo executivo...'", "4. Configure agendamento semanal no Zapier"]}
"""

    prompt = CURATOR_USER_TEMPLATE.format(
        total=len(slim_items),
        items=json.dumps(slim_items[:80], ensure_ascii=False, indent=2),  # v2.3: 80 items (stripped raw_data)
        feedback_section=feedback_section + workflow_section
    )

    print(f"🤖 Enviando {len(items)} itens para Claude curar...")

    messages = [
        {"role": "user", "content": prompt + "\n\nResponda APENAS com o JSON válido. Sem texto antes ou depois."}
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

    # Parse response
    response_text = response.content[0].text
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


def _extract_json(text: str):
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


def _normalize_for_dedup(text: str) -> str:
    """Normaliza texto (URL ou título) para comparação de duplicatas"""
    if not text:
        return ""
    t = text.lower().strip()
    # Remove querystring de URLs
    if '?' in t and ('http' in t or '/' in t):
        t = t.split('?')[0]
    # Remove trailing slash
    t = t.rstrip('/')
    return t


_STOPWORDS_PT = {
    'para', 'como', 'mais', 'pela', 'pelo', 'seus', 'suas', 'esta', 'este',
    'esse', 'essa', 'isso', 'isto', 'aqui', 'pode', 'novo', 'nova', 'novos',
    'novas', 'sobre', 'após', 'apos', 'ante', 'deve', 'será', 'sera', 'dois',
    'três', 'tres', 'muito', 'toda', 'todo', 'cada', 'qual', 'quem', 'onde',
    'entre', 'ainda', 'assim', 'mesmo', 'desde', 'with', 'from', 'that',
    'this', 'have', 'will', 'what', 'your', 'they', 'their', 'been', 'into',
    'than', 'just', 'also', 'more', 'most', 'some', 'when', 'could', 'after',
    'says', 'said', 'gets', 'amid', 'over', 'first', 'major',
}


def _extract_entities(headline: str) -> set:
    """Extrai entidades-chave (empresas, produtos, siglas) de um título"""
    if not headline:
        return set()
    import re
    entities = set()
    for match in re.findall(r'[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*', headline):
        if len(match) > 2 and match.lower() not in _STOPWORDS_PT:
            entities.add(match.lower())
    for match in re.findall(r'\b[A-Z]{2,}\b', headline):
        entities.add(match.lower())
    return entities


def _title_keywords(headline: str) -> set:
    """Extrai keywords significativas de um título (remove stopwords)"""
    if not headline:
        return set()
    words = headline.lower().split()
    return {w.strip('.,;:!?"\'()[]') for w in words
            if len(w) > 3 and w.strip('.,;:!?"\'()[]') not in _STOPWORDS_PT}


def _title_signature(headline: str) -> str:
    """Cria assinatura de título: keywords ordenadas (sem stopwords)"""
    kw = _title_keywords(headline)
    return " ".join(sorted(kw)) if kw else ""


def _titles_overlap(headline_a: str, headline_b: str) -> bool:
    """Verifica se dois títulos falam do mesmo assunto via overlap de keywords + entidades"""
    kw_a = _title_keywords(headline_a)
    kw_b = _title_keywords(headline_b)
    if not kw_a or not kw_b:
        return False

    overlap = kw_a & kw_b
    min_len = min(len(kw_a), len(kw_b))
    if min_len == 0:
        return False
    ratio = len(overlap) / min_len
    if ratio >= 0.6:
        return True

    ent_a = _extract_entities(headline_a)
    ent_b = _extract_entities(headline_b)
    if ent_a and ent_b and ent_a & ent_b:
        if ratio >= 0.4:
            return True

    return False


def dedup_across_sections(curated: dict) -> dict:
    """
    Remove notícias duplicadas entre seções do digest.
    Prioridade (quem fica): items > world > tool_of_day > quick_links.
    Compara por URL normalizada, keywords de título E overlap semântico.
    """
    seen_urls = set()
    seen_headlines = []
    removed_count = 0

    def _is_dup(url: str, headline: str) -> bool:
        u = _normalize_for_dedup(url)
        if u and u in seen_urls:
            return True
        for prev_hl in seen_headlines:
            if _titles_overlap(headline, prev_hl):
                return True
        return False

    def _mark(url: str, headline: str):
        u = _normalize_for_dedup(url)
        if u:
            seen_urls.add(u)
        if headline:
            seen_headlines.append(headline)

    # 1. items (prioridade máxima — seção principal)
    new_items = []
    for item in curated.get('items', []):
        if _is_dup(item.get('source_url', ''), item.get('headline', '')):
            removed_count += 1
            continue
        _mark(item.get('source_url', ''), item.get('headline', ''))
        new_items.append(item)
    curated['items'] = new_items

    # 2. world
    new_world = []
    for item in curated.get('world', []):
        if _is_dup(item.get('source_url', ''), item.get('headline', '')):
            removed_count += 1
            continue
        _mark(item.get('source_url', ''), item.get('headline', ''))
        new_world.append(item)
    curated['world'] = new_world

    # 3. tool_of_day (objeto único)
    tool = curated.get('tool_of_day')
    if tool and _is_dup(tool.get('source_url', ''), tool.get('headline', '')):
        removed_count += 1
    elif tool:
        _mark(tool.get('source_url', ''), tool.get('headline', ''))

    # 4. quick_links
    new_quick = []
    for item in curated.get('quick_links', []):
        if _is_dup(item.get('source_url', ''), item.get('headline', '')):
            removed_count += 1
            continue
        _mark(item.get('source_url', ''), item.get('headline', ''))
        new_quick.append(item)
    curated['quick_links'] = new_quick

    if removed_count > 0:
        print(f"🔁 Dedup intra-edição: {removed_count} duplicata(s) removida(s) entre seções")

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

    # Post-process: remove duplicatas entre seções (rede de segurança)
    curated = dedup_across_sections(curated)

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
