# THE DAILY BYTE — Plano de Evolução

---

## Changelog

### v2.4 — 01/03/2026 (HTML Template + Feedback Loop + Optimizations)

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/sender.py` | Template HTML completo com inline CSS, table-based layout, mobile-first. Branded colors (#FF6B35 orange, #1a1a2e dark). Todas as 7 secoes renderizadas em HTML. `send()` agora envia HTML (preview continua markdown). Preview salva .md + .html |
| `scripts/feedback.py` | **NOVO** — Puxa metricas de engajamento do Buttondown API (opens, clicks, unsubs). Calcula open/click rate, top 3 temas, gera curator_hint. Salva em `/tmp/digest_feedback.json` |
| `scripts/processor.py` | Integra feedback loop — carrega metricas e injeta no prompt do curador (top temas, open rate, click rate) |
| `scripts/run.py` | +Step 1.5 (Feedback Loop) entre coleta e curadoria. Import graceful com try/except |
| `scripts/newsletter_collector.py` | Removido `raw_data` do output (token optimization). Adicionado `_fetch_feed()` com fallback requests. RSS inferido para Substack/Beehiiv sem rss_url configurado |
| `EVOLUTION-PLAN.md` | v2.4 changelog, backlog atualizado |
| `CLAUDE.md` | v2.4 |

**Item 4 — Feedback Loop (Buttondown API):**
- Novo modulo `feedback.py` com 8 funcoes
- Puxa emails dos ultimos 7 dias + analytics individuais
- Calcula: avg open rate, avg click rate, total opens/clicks/unsubs, subscriber count
- Top 3 temas mais clicados → injeta no prompt do curador
- Gera `curator_hint` textual com recomendacoes baseadas em benchmarks
- Integrado no pipeline: run.py (Step 1.5) + processor.py (prompt injection)
- Degradacao graceful: se API key ausente ou erro, pipeline continua normalmente

**Item 5 — Template HTML dedicado:**
- ~400 linhas de HTML com inline CSS (compatibilidade email clients)
- Layout table-based (600px max-width) com media queries para mobile
- Paleta branded: orange #FF6B35, dark #1a1a2e, cores por secao
- MSO conditionals para Outlook
- Secoes: header, numero do dia, mundo real, hoje no byte, saas & enterprise, tool do dia (com CTA + how_to_use + prompt_of_day), analise do dia, quick links, watch later, footer
- Heat score visual com emojis 🔥
- Tags coloridas por categoria ([AI], [BIG TECH], [ENTERPRISE], [BREAKING])
- Unsubscribe link via Buttondown template variable `{{ unsubscribe_url }}`
- Preview mode: markdown no terminal + HTML em `/tmp/digest_preview.html`

**Item 6 — Otimizar newsletter_collector.py:**
- Removido `raw_data` do `to_raw_dict()` (consistente com processor.py, 5x menos tokens)
- `_fetch_feed()` com fallback: feedparser direto → requests com headers + feedparser
- RSS inferido automaticamente para Substack (`/feed`) e Beehiiv (`/feed`)
- `_collect_via_rss()` tenta RSS antes de scraping para todas as fontes

---

### v2.3 — 22/02/2026 (Tier 1 Expansion + Resiliencia)

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | +21 X handles (45 total), +17 RSS tech (25 total), +18 RSS world (24 total), +29 Substacks novos, `_fetch_feed()` com fallback requests, `collect_substack_feeds()` |
| `scripts/processor.py` | Strip `raw_data` dos itens (67K→12.5K tokens, 5x reducao), cap 40→80 itens, sort por freshness, integracao dedup |
| `scripts/sender.py` | Integracao dedup — registra itens enviados no cache |
| `scripts/dedup.py` | **NOVO** — Cache de URLs ja enviadas (5 dias), normaliza URLs, previne repeticao |
| `scripts/alert_failure.py` | **NOVO** — Envia email alerta via Buttondown quando pipeline falha |
| `.github/workflows/daily-digest.yml` | +job `notify-failure`, +actions/cache para dedup, artifacts `if: always()` |
| `config.yaml` | v2.3, todas as novas fontes documentadas, secao substacks |
| `CLAUDE.md` | v2.3 (Tier 1 Expansion — 92 fontes Pulse.bot) |
| `Daily_Byte_Master_Sources_v2.3.xlsx` | **NOVO** — 2,143 fontes consolidadas (Pulse.bot + digest + backlog) |

**Fontes v2.3 (92 novas do Pulse.bot):**
- 21 novos X handles (VC, geopolitica, mercados, crypto)
- 17 novos RSS tech (VentureBeat, ZDNet, Engadget, CoinDesk, etc)
- 18 novos RSS world (CNBC, WSJ, NYT DealBook, Bloomberg, FT, Economist, etc)
- 29 Substacks curados (AI, fintech, biotech, business strategy)
- Total coletores: ~140 fontes ativas

**Resiliencia v2.3:**
- Alerta email automático quando pipeline falha (Buttondown → lab@nuvini.com.br)
- Dedup entre dias — cache de 5 dias via GitHub Actions cache
- Token optimization — 5x menos tokens por curadoria, 2x mais itens analisados

---

### v2.2 — 22/02/2026 (Novas Fontes + Micro-Secoes)

**Decisoes aprovadas pelo Toto:**
- Fontes: +4 (Import AI, Distrito News Inside VC, The Decoder RSS, Filipe Deschamps YT) + 3 X handles
- Formato: Prompt do Dia (copy-paste), Numero do Dia (data point), Subject line com gancho
- Engajamento: nenhum por enquanto

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `config.yaml` | v2.2, max_tokens 8192, +3 X handles, +1 RSS (The Decoder), +1 YouTube (Filipe Deschamps), +2 newsletters (Import AI, Distrito News) |
| `scripts/collector.py` | +3 X handles (TIER1_HANDLES), +1 RSS (the_decoder), +1 YouTube (filipe_deschamps), comment 9 newsletters |
| `scripts/newsletter_collector.py` | +2 fontes (Import AI, Distrito News) com suporte RSS nativo via feedparser |
| `scripts/processor.py` | CURATOR_SYSTEM v2.2: number_of_day, prompt_of_day, subject_hook. JSON schema atualizado |
| `scripts/sender.py` | +Numero do Dia (secao 0), +Prompt do Dia (dentro de Tool do Dia), subject line dinamico com hook |
| `CLAUDE.md` | v2.2, 9 newsletters, max_tokens 8192, novas secoes |

**Layout v2.2 (6 secoes + 2 micro-secoes):**
```
0. NUMERO DO DIA (data point impactante)
1. MUNDO REAL (3) — mundo + Brasil
2. HOJE NO BYTE (4-5) — tags: [BREAKING], [AI], [BIG TECH], [ENTERPRISE]
3. SaaS & ENTERPRISE (2)
4. TOOL DO DIA (1) + COMO USAR HOJE + PROMPT DO DIA (copy-paste ready)
5. ANALISE DO DIA (3 bullets)
6. QUICK LINKS (5-6) — headline + link, sem analise
+ WATCH LATER (1 video) no final
```

**Novas fontes (total: 9 newsletters + 1 RSS + 1 YouTube + 3 X handles):**
- Newsletters: +Import AI (Jack Clark, AI policy/research), +Distrito News Inside VC (BR VC/startups)
- RSS: +The Decoder (AI enterprise + EU policy)
- YouTube: +Filipe Deschamps (PT-BR)
- X: +@aravind_srinivas (CEO Perplexity), +@demishassabis (CEO DeepMind), +@ethanmollick (Wharton)

**Benchmarks analisados:** Pulse.bot, TLDR AI, The Rundown AI, Superhuman AI, The Neuron, Ben's Bites

---

### v2.1 — 15/02/2026 (Layout Consolidado)

**Decisoes aprovadas pelo Toto:**
- Fontes: TAAFT + Turing Post (StartSe so se for coisa mto inovadora)
- Formato: Quick Links + Como Usar Hoje + Consolidar secoes (8->6)
- Engajamento: nenhum por enquanto
- Curadoria: Sonnet 4.5 + fix max_items

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `config.yaml` | Modelo -> claude-sonnet-4-5-20250929, max_items=18, distribution consolidada (6 secoes), 2 novas newsletters |
| `scripts/processor.py` | Modelo atualizado, CURATOR_SYSTEM e CURATOR_USER_TEMPLATE reescritos para layout v2.1 |
| `scripts/sender.py` | generate_email_content() reescrito para 6 secoes, backward compat com formato antigo |
| `scripts/newsletter_collector.py` | +2 fontes: TAAFT (tool_of_day) e Turing Post (ai_models) |
| `scripts/collector.py` | Comentario atualizado listando 7 newsletters |
| `SKILL.md` | Layout v2.1, max_items=18, novas fontes |
| `prompts/curator.md` | JSON schemas atualizados, distribuicao v2.1 |

**Layout v2.1 (6 secoes, era 8):**
```
1. MUNDO REAL (3) — mundo + Brasil
2. HOJE NO BYTE (4-5) — consolida breaking + ai_models + big_tech, com tags
3. SaaS & ENTERPRISE (2)
4. TOOL DO DIA (1) + COMO USAR HOJE — objeto separado com how_to_use
5. ANALISE DO DIA (3 bullets)
6. QUICK LINKS (5-6) — headline + link, sem analise
+ WATCH LATER (1 video) no final
```

**Novas fontes (total: 7 newsletters):**
- AiDrop, Evolving AI, Update Diario, TechDrop, AlphaSignal, **TAAFT**, **Turing Post**

**Commit:** `1017c71` — `v2.1: Layout consolidado, novas fontes e modelo Sonnet 4.5`

---

### v2.0 — 06/02/2026 (Newsletters + Scraping)

**Diagnostico inicial:**
- Gap 1: Fontes 100% anglofonas (sem perspectiva BR)
- Gap 2: Sem capacidade de ingerir newsletters (so RSS/YouTube/X)
- Gap 3: Categorias limitadas (sem SaaS/Enterprise)
- Gap 4: Secao Mundo Real sem Brasil
- Gap 5: Analise superficial

**O que foi implementado:**
- Novo modulo `newsletter_collector.py` — scraper BeautifulSoup para newsletters sem RSS
- 5 newsletters iniciais: AiDrop, Evolving AI, Update Diario, TechDrop, AlphaSignal
- Secao SaaS & Enterprise
- Brasil integrado ao Mundo Real (opcao 2 aprovada)
- Cross-referencia newsletter vs RSS no curator prompt
- Janela de 36h para newsletters (vs 24h para RSS)
- Heat Score bonus para newsletters (+10 insight exclusivo, +5 cross-validacao)
- Dependencias: beautifulsoup4, lxml

---

### v1.0 — 02/02/2026 (Setup Inicial)

- Pipeline: collector.py -> processor.py -> sender.py
- Fontes: RSS feeds (HN, TechCrunch, The Verge, Reuters, etc), YouTube RSS, X/Twitter API
- Curadoria: Claude Sonnet via Anthropic API
- Envio: Buttondown API
- Deploy: GitHub Actions (diario 06:45 BRT)
- Heat Score: Freshness (40pts) + Fonte (30pts) + Impacto (30pts), threshold 60

---

## Proximas Evolucoes (Backlog)

### 🗓️ Proximo Domingo (08/03/2026) — Prioridades

**7. A/B test de subject lines:**
- [ ] Implementar variantes de subject no sender.py
- [ ] Tracking via Buttondown analytics
- [ ] Feedback loop informando qual estilo performa melhor

**8. Dashboard de metricas:**
- [ ] HTML dashboard com historico de open/click rates
- [ ] Growth de subscribers ao longo do tempo
- [ ] Top temas por engajamento

**9. Retry automatico para feeds com timeout:**
- [ ] Implementar retry com backoff no collector.py
- [ ] Fallback para cache do dia anterior se feed falhar

### ✅ Implementado em v2.4 (01/03/2026)

**4. Feedback loop com Buttondown:** ✅
- [x] Usar Buttondown API para puxar opens/clicks da semana
- [x] Top 3 assuntos mais clicados → informar curador
- [x] Metricas basicas: open rate, click rate, growth semanal

**5. Template HTML dedicado:** ✅
- [x] Substituir markdown puro por template HTML com identidade visual
- [x] Cores, layout fixo (header, sections, footer)
- [x] Mobile-first (media queries, 16px+ text, 44px+ tap targets)

**6. Otimizar newsletter_collector.py:** ✅
- [x] Remover `raw_data` do output (mesmo fix do processor.py)
- [x] Adicionar `_fetch_feed()` fallback (consistencia com collector.py)
- [x] RSS inferido para Substack/Beehiiv automaticamente

---

### Backlog Geral

**Fontes:**
- [ ] StartSe — adicionar se trouxer conteudo inovador/inedito
- [x] Filipe Deschamps (YouTube BR) — adicionado v2.2
- [x] Import AI (Jack Clark) — adicionado v2.2 via Substack RSS
- [ ] The Batch (Andrew Ng), Stratechery — fontes aspiracionais sem scraper
- [x] Crunchbase News — adicionado v2.3 via RSS

**Formato:**
- [ ] A/B test de subject lines
- [ ] Secao de engagement (enquetes, CTA)

**Curadoria:**
- [ ] Dedup mais inteligente (embeddings para similaridade semantica)
- [x] Cache de items ja enviados para evitar repeticao entre dias — implementado v2.3
- [ ] Feedback loop — rastrear opens/clicks para refinar selecao

**Infra:**
- [x] Monitoring/alertas quando o pipeline falha — implementado v2.3 (email alert)
- [ ] Retry automatico se um feed der timeout
- [ ] Dashboard com metricas (opens, clicks, growth)
