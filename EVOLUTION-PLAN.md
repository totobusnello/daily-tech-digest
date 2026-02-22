# THE DAILY BYTE — Plano de Evolução

---

## Changelog

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

**Fontes:**
- [ ] StartSe — adicionar se trouxer conteudo inovador/inedito
- [x] Filipe Deschamps (YouTube BR) — adicionado v2.2
- [x] Import AI (Jack Clark) — adicionado v2.2 via Substack RSS
- [ ] The Batch (Andrew Ng), Stratechery — fontes aspiracionais sem scraper
- [ ] Crunchbase Daily — precisa scraper dedicado

**Formato:**
- [ ] Template HTML dedicado (hoje e markdown puro via Buttondown)
- [ ] A/B test de subject lines
- [ ] Secao de engagement (enquetes, CTA)

**Curadoria:**
- [ ] Feedback loop — rastrear opens/clicks para refinar selecao
- [ ] Dedup mais inteligente (embeddings para similaridade semantica)
- [ ] Cache de items ja enviados para evitar repeticao entre dias

**Infra:**
- [ ] Monitoring/alertas quando o pipeline falha
- [ ] Retry automatico se um feed der timeout
- [ ] Dashboard com metricas (opens, clicks, growth)
