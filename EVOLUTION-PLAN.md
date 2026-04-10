# THE DAILY BYTE — Plano de Evolução

---

## Changelog

### v2.7 — 10/04/2026 (Workflow Sexta + Enquete + Why Action + Novas Fontes)

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/processor.py` | Why It Matters prescritivo ("O que o C-level deve FAZER?"). Workflow da Semana: sextas geram campo `weekly_workflow` com 3-4 steps praticos. Regra reforçada em CURATOR_SYSTEM + USER_TEMPLATE |
| `scripts/sender.py` | +Seção Workflow da Semana (renderiza `weekly_workflow` após Tool do Dia). +Enquete semanal (sextas): 4 opções com ?tag= tracking (AI Tools, Estratégia, Brasil, Deep Dive) |
| `scripts/collector.py` | +Sabrina Ramonov (YouTube, 1.4M+ followers, AI agents/automação). +@ziaborak (X, AI policy/regulação) |
| `scripts/newsletter_collector.py` | +The BRIEF (PT-BR, Beehiiv, tech+negócios diário) |
| `config.yaml` | v2.7 header. +1 newsletter, +1 YouTube, +1 X handle. Total: ~163 fontes |
| `CLAUDE.md` | v2.7 |
| `EVOLUTION-PLAN.md` | v2.7 changelog |

**Novas Fontes (3 adicoes):**
- The BRIEF (PT-BR, Beehiiv) — newsletter brasileira de tech+negócios, tom direto, envio diário 7h
- Sabrina Ramonov (YouTube, 1.4M+ followers) — AI agents, automação, workflows para negócios. 5 vídeos/semana
- @ziaborak (X) — AI policy, regulação, geopolítica de AI. Complementa @benedictevans

**Workflow da Semana (sextas):**
- processor.py detecta sexta-feira (weekday == 4) e injeta instrução extra no prompt
- Curador gera `weekly_workflow`: {title, steps[3-4]} com passos copy-paste para C-levels
- sender.py renderiza como seção separada entre Tool do Dia e Análise do Dia
- Inspirado no "AI Skill of the Day" do The Neuron (675K+ subs)

**Enquete Semanal (sextas):**
- sender.py mostra enquete com 4 opções: AI Tools, Estratégia, Brasil, Deep Dive
- Cada opção usa ?tag=tema-X para tracking no Buttondown analytics
- Inspirado no "Rundown Roundtable" do The Rundown AI (2M+ subs)

**Why It Matters Prescritivo:**
- Regra reforçada em 3 locais: CURATOR_SYSTEM (regra 5), USER_TEMPLATE (regra crítica), e nova seção final
- Agora exige: "O que o CEO/CFO/CMO deve FAZER?" em vez de descrição passiva
- Ex: "CFOs: revisem orçamento de cloud para Q3" > "Preços de cloud estão subindo"
- Benchmark: The Rundown AI e Superhuman AI já fazem isso com "Why it matters for your business"

---

### v2.6 — 29/03/2026 (Engagement + Subject Dedup + Novas Fontes)

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/feedback.py` | `recent_hooks` — extrai subject hooks dos ultimos 7 dias para evitar repeticao |
| `scripts/processor.py` | Injeta hooks recentes no prompt com regra de diversificacao. Numero do Dia mais ousado (valores absolutos > percentuais). Why It Matters encurtado para 1-2 frases incisivas (inclui tool_of_day) |
| `scripts/sender.py` | +1-click feedback (thumbs up/down no email), +"Leitura: 3 min" no header, +emoji no subject line, +CTA de referral no footer. Feedback URLs com ?tag= para tracking via Buttondown analytics |
| `scripts/collector.py` | +Latent Space (Substack RSS), +State of AI (Substack RSS), +The AI Grid (YouTube), +@alliekmiller (X handle). **Coleta paralela** com ThreadPoolExecutor (10 workers). `raw_data` removido de todos os coletores. YouTube simplificado para reusar `_parse_feed_items`. Dead import `re` removido |
| `scripts/dedup.py` | Removido dead code (`_title_hash`, `cached_title_hashes`) e imports nao usados (`hashlib`, `Set`) |
| `config.yaml` | v2.6 header. +2 Substacks, +1 YouTube, +1 X handle. Tier 1 handles sincronizado com collector.py (51 handles). Total: ~155 fontes |
| `CLAUDE.md` | v2.6 |
| `EVOLUTION-PLAN.md` | v2.6 changelog, backlog atualizado |

**Subject Hook Dedup (fix de titulos repetidos):**
- feedback.py agora extrai `recent_hooks` dos emails enviados nos ultimos 7 dias
- processor.py injeta esses hooks no prompt com instrucao explicita: "NAO REPETIR temas similares"
- Se a noticia mais impactante for do mesmo tema de ontem, curador escolhe o segundo tema

**Engagement (benchmark vs concorrentes):**
- 1-click feedback: "Esta edicao foi util?" com thumbs up/neutral/down no footer
- "Leitura: 3 min" badge no header (todos os top competitors fazem isso)
- Emoji prefix no subject line (The Neuron cresceu rapido com isso, LATAM open rate 30.67%)
- CTA de referral: "Conhece alguem que precisa saber disso?" com link de compartilhamento

**Novas Fontes (4 adicoes):**
- Latent Space (swyx) — "AI Engineer newsletter", 200K+ subs, AI infra e agentes
- State of AI (Nathan Benaich) — Macro mensal, chip policy, enterprise AI spending
- The AI Grid (YouTube, 374K subs) — Demos praticos de ferramentas AI
- @alliekmiller (X, 2M followers) — TIME100 AI, Fortune 500 AI advisor

**Prompt Tuning:**
- Numero do Dia: valores absolutos grandes > percentuais genericos
- Why It Matters: 1-2 frases incisivas (era 2-3), menos texto mais impacto
- Consistencia total: tool_of_day alinhado com mesma regra de 1-2 frases

**Performance & Cleanup:**
- Coleta paralela: `ThreadPoolExecutor(max_workers=10)` — ~155 feeds buscados simultaneamente (era sequencial)
- YouTube `collect_youtube_feeds()` simplificado para reusar `_parse_feed_items` (eliminou 25 linhas duplicadas)
- `raw_data` removido de todos os coletores (RSS, YouTube, X) — economia de I/O no `/tmp/digest_raw.json`
- `to_dict()` faz `pop('raw_data')` como safety net
- dedup.py: removido `_title_hash()` (nunca chamado), `cached_title_hashes` (nunca populado), imports `hashlib` e `Set`
- collector.py: removido dead import `re`
- sender.py: `<br/>` self-closing para compatibilidade email
- Feedback URLs corrigidas: `?tag=feedback-positivo` (rastreavel pelo Buttondown analytics)
- config.yaml sincronizado com collector.py (51 X handles, contagens atualizadas)

---

### v2.5 — 08/03/2026 (Retry Resilience + Tracking + API Key Local)

**Mudancas implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | `_fetch_feed()` com retry + exponential backoff (2s, 4s — max 3 tentativas). `collect_youtube_feeds()` agora usa `_fetch_feed()` em vez de `feedparser.parse()` direto. Import `time` adicionado. User-Agent atualizado para 2.5 |
| `scripts/newsletter_collector.py` | `_fetch_feed()` com retry + exponential backoff (2s, 4s — max 3 tentativas). Import `time` adicionado |
| `~/.zshrc` | `BUTTONDOWN_API_KEY` configurado localmente (key "Claude" do dashboard) |
| Buttondown Dashboard | Tracking habilitado: Replies ON, Email clicks ON, Email opens ON (estavam todos OFF) |

**Item 9 — Retry com backoff:**
- `_fetch_feed()` em ambos os arquivos agora tenta 3x antes de desistir
- Backoff exponencial: 2s entre 1a e 2a tentativa, 4s entre 2a e 3a
- Log visual com emoji ⏳ mostrando retry em andamento
- YouTube feeds migrados de `feedparser.parse()` direto para `_fetch_feed()` (ganha retry automaticamente)

**Tracking + API Key:**
- Habilitado Replies, Email clicks, Email opens no Buttondown (Settings > Tracking)
- API key "Claude" (criada 02/02/2026, nunca usada) configurada em `~/.zshrc`
- feedback.py agora pode rodar localmente para testes

---

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

### 🗓️ Proximo Domingo — Prioridades

**7. Dashboard de metricas:**
- [ ] HTML dashboard com historico de open/click rates
- [ ] Growth de subscribers ao longo do tempo
- [ ] Top temas por engajamento

**8. Retry automatico para feeds com timeout:** ✅ (v2.5)
- [x] Implementar retry com backoff no collector.py
- [x] Implementar retry com backoff no newsletter_collector.py
- [x] YouTube feeds usando _fetch_feed() com retry
- [ ] Fallback para cache do dia anterior se feed falhar

**9. Buttondown Feb Updates — Oportunidades (email 03/03/2026):**
- [ ] Custom domain para click tracking — configurar dominio proprio para melhorar deliverability
- [ ] Sort/filter por open e click rates via API — melhorar feedback.py com sorting nativo
- [ ] Avaliar custom template no Buttondown vs HTML raw no sender.py (trade-off: simplicidade vs controle)
- [ ] Novas settings na API (locale, timezone, reply-to, socials) — automatizar config
- [ ] Reply tracking como metrica adicional de engajamento no feedback loop
- [ ] OpenAPI spec para archives — explorar para melhor integracao

### ✅ Implementado em v2.6 (29/03/2026)

**Subject Hook Dedup:** ✅
- [x] Extrair hooks recentes dos ultimos 7 dias via feedback.py
- [x] Injetar no prompt com instrucao de diversificacao
- [x] Fix de titulos repetidos (Pentagono/Anthropic em dias consecutivos)

**Engagement Features:** ✅
- [x] 1-click feedback no email (thumbs up/neutral/down) com URLs rastreaveis
- [x] "Leitura: 3 min" badge no header
- [x] Emoji prefix no subject line (🔥)
- [x] CTA de referral no footer

**Novas Fontes:** ✅
- [x] Latent Space (AI engineering, Substack RSS)
- [x] State of AI (macro strategy, Substack RSS)
- [x] The AI Grid (tool demos, YouTube RSS)
- [x] @alliekmiller (Fortune 500 AI, X handle)

**Prompt Tuning:** ✅
- [x] Numero do Dia mais ousado (valores absolutos > percentuais)
- [x] Why It Matters mais curto (1-2 frases incisivas, inclui tool_of_day)

**Performance & Cleanup:** ✅
- [x] Coleta paralela com ThreadPoolExecutor (10 workers)
- [x] raw_data removido de todos os coletores (RSS, YouTube, X)
- [x] YouTube simplificado para reusar _parse_feed_items
- [x] Dead code removido: dedup.py (_title_hash, hashlib, Set), collector.py (import re)
- [x] sender.py: self-closing br, feedback URLs com ?tag=
- [x] config.yaml sincronizado com collector.py (51 handles)

### ✅ Implementado em v2.5 (08/03/2026)

**9. Retry com backoff:** ✅
- [x] Retry exponencial (2s, 4s) em `_fetch_feed()` — collector.py + newsletter_collector.py
- [x] YouTube feeds migrados para `_fetch_feed()` (ganham retry automatico)
- [x] BUTTONDOWN_API_KEY configurado localmente
- [x] Tracking habilitado no Buttondown (opens, clicks, replies)

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
- [x] Secao de engagement — 1-click feedback + referral CTA (v2.6)

**Curadoria:**
- [ ] Dedup mais inteligente (embeddings para similaridade semantica)
- [x] Cache de items ja enviados para evitar repeticao entre dias — implementado v2.3
- [x] Feedback loop — rastrear opens/clicks para refinar selecao — implementado v2.4

**Infra:**
- [x] Monitoring/alertas quando o pipeline falha — implementado v2.3 (GitHub Issue alert)
- [x] Retry automatico se um feed der timeout — implementado v2.5 (backoff exponencial)
- [ ] Dashboard com metricas (opens, clicks, growth)
