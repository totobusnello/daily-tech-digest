# THE DAILY BYTE — Instrucoes do Projeto

## O que e este projeto

Newsletter diaria automatizada de Tech & AI para C-levels brasileiros (CEOs, CFOs, CMOs, CPOs). Pipeline: coletar noticias -> curar com Claude -> enviar via Buttondown.

**Versao atual:** v2.14 (Big Story + Corte 15 + Heat 70 + Verbo Imperativo + LED VU + AI News/Karpathy)
**Autor:** Toto Busnello (lab@nuvini.ai)

---

## Arquitetura

```
collector.py          -> /tmp/digest_raw.json
  (RSS + YouTube + X + Newsletters)
       |
feedback.py           -> /tmp/digest_feedback.json
  (Buttondown API: opens, clicks, top temas)
       |
processor.py          -> /tmp/digest_curated.json
  (Claude Sonnet 4.6 curadoria + feedback metrics)
       |
sender.py             -> Buttondown API -> email HTML
  (template HTML inline CSS, mobile-first)
```

**Orquestrador:** `run.py` (ou GitHub Actions via `daily-digest.yml`)
**Schedule:** Diario as 03:00 BRT (06:00 UTC) via GitHub Actions — compensando delays de 2-6h da fila do GH Actions, entrega estimada 05:00-09:00 BRT

---

## Arquivos-chave

| Arquivo | Funcao |
|---------|--------|
| `config.yaml` | Configuracao central: modelo, distribuicao, fontes, temas |
| `scripts/collector.py` | Coleta paralela (ThreadPool) de RSS, YouTube, X/Twitter, Substacks, newsletters |
| `scripts/newsletter_collector.py` | Scraper BeautifulSoup + RSS para 9 newsletters |
| `scripts/processor.py` | Curadoria com Claude (CURATOR_SYSTEM + CURATOR_USER_TEMPLATE) |
| `scripts/sender.py` | Renderiza email HTML (template inline CSS, feedback, referral) e envia via Buttondown |
| `scripts/feedback.py` | Puxa metricas Buttondown (opens, clicks, top temas, recent_hooks) para informar curadoria |
| `scripts/dedup.py` | Cache de URLs ja enviadas (5 dias), normaliza URLs, previne repeticao entre dias |
| `scripts/run.py` | Pipeline completo (collect -> feedback -> process -> send). Flags: `--preview`, `--skip-collect`, `--skip-process` |
| `scripts/health_check.py` | Monitora saude de ~200 feeds (ThreadPool, 10s timeout, 3+ falhas consecutivas = alerta) |
| `scripts/alert_failure.py` | Cria GitHub Issue quando pipeline falha (via gh CLI no Actions). Notifica owner por email |
| `prompts/curator.md` | Documentacao de referencia do prompt de curadoria |
| `SKILL.md` | Filosofia, criterios, layout, fontes |
| `EVOLUTION-PLAN.md` | Historico de versoes e backlog |

---

## Layout v2.2 — 6 Secoes + 2 Micro-Secoes

```
0. NUMERO DO DIA (data point impactante — value + context)
1. MUNDO REAL (3 itens) — mundo + Brasil
2. HOJE NO BYTE (4-5 itens) — tags: [BREAKING], [AI], [BIG TECH], [ENTERPRISE]
3. SaaS & ENTERPRISE (2 itens)
3b. RADAR BRASIL (1-2 itens) — ecossistema tech/AI/negocios BR (opcional, array vazio se nada relevante)
4. TOOL DO DIA (1 item) + COMO USAR HOJE + PROMPT DO DIA (copy-paste ready)
5. ANALISE DO DIA (3 bullets)
5b. DEEP DIVE (sextas) — analise profunda do tema mais quente da semana (3-5 paragrafos)
6. QUICK LINKS (5-6 itens) — headline + link, sem analise
+ WATCH LATER (1 video no final)
```

**Total maximo:** 18 itens (12 principais + 6 quick links)

**JSON do curador:**
- `subject_hook` — frase-gancho de max 6 palavras para subject line
- `number_of_day{}` — {value, context} — data point numerico impressionante
- `world[]` — array de 3 itens (headline, context, source_url, source_name)
- `items[]` — array com category `hoje_no_byte|saas_enterprise|watch_later` e campo `tag`
- `radar_brasil[]` — array de 1-2 itens BR (headline, why_it_matters, source_url, source_name). Pode ser vazio.
- `tool_of_day{}` — OBJETO SEPARADO (nao vai no items), com `how_to_use` e `prompt_of_day` obrigatorios
- `quick_links[]` — apenas headline + source_url + source_name
- `daily_analysis[]` — 3 strings com formato "**Tema** — Insight"
- `deep_dive{}` — (sextas) {title, body} analise profunda 3-5 paragrafos
- `weekly_workflow{}` — (sextas) {title, steps[]} workflow pratico 3-4 steps

---

## Fontes (~200 feeds ativos)

### Filosofia de Fontes (v2.9)
**O Daily Byte existe para trazer o que C-levels NAO encontram sozinhos.**
Prioridade: fonte primaria > indie/builder > community > newsletter curada > midia especializada > mainstream.
Mainstream (Reuters, BBC, CNBC) serve para "Mundo Real" mas NUNCA deve dominar as secoes de tech/AI.

### Tier 1 — Primeira Mao (65+ X/Twitter handles)
**Fundadores/Labs:** @sama, @AnthropicAI, @satyanadella, @sundarpichai, @ylecun, @karpathy, @demishassabis, @aravind_srinivas, @ClementDelworker, etc.
**Indie/Builders:** @simonw, @chipro, @swaborak, @GergelyOrosz, @levelsio, @danshipper, @filipedeschamps
**Estrategia/VC:** @vkhosla, @benedictevans, @alliekmiller, @hardmaru, @ziaborak
Ver `collector.py` para lista completa.

### Tier 2 — RSS Feeds (45+ tech/AI + 37 world)
**Labs (primeira mao):** DeepMind, Meta AI, NVIDIA, Microsoft Research, OpenAI, Anthropic, HuggingFace, Stability, Mistral, Cohere
**Community-driven:** Reddit r/MachineLearning, r/LocalLLaMA, HN Show (50+ pts), Lobsters AI, Product Hunt
**Developer:** Changelog, InfoQ AI/ML
**Tech media:** HN (100+ pts), TechCrunch AI, MIT Tech Review, The Decoder
**World:** Reuters, BBC, Forbes, CNBC, WSJ
**Brasil:** Poder360, InfoMoney, Startups.com.br, Valor Economico, NeoFeed, Startse, Exame, Pipeline Valor, Brazil Journal, Tecmundo, Canaltech, IA Brasil Noticias
**Research:** arXiv cs.AI

### Tier 3 — Newsletters (10 fontes, via scraping + RSS)
| Newsletter | Foco | Idioma |
|-----------|------|--------|
| AiDrop | AI, analise profunda | PT-BR |
| Evolving AI | Modelos, benchmarks | EN |
| Update Diario | Brasil, economia | PT-BR |
| TechDrop | SaaS, enterprise, CapEx | PT-BR |
| AlphaSignal | Research -> produto | EN |
| There's An AI For That | AI tools (2.8M subs) | EN |
| Turing Post | AI strategy, geopolitica | EN |
| Import AI | AI policy, research (Jack Clark) | EN |
| Distrito News Inside VC | VC/startups Brasil | PT-BR |
| The BRIEF | Tech+business diario, tom direto | PT-BR |

### Substacks Curados (42 feeds via RSS)
**Indie/Practitioners (v2.9):** Simon Willison, Lilian Weng, Chip Huyen, One Useful Thing (Ethan Mollick), AI Snake Oil, SemiAnalysis, Interconnects, Stratechery, Pragmatic Engineer, Lenny's Newsletter, Neatprompts
**AI Engineering:** Latent Space, State of AI
**Business/Strategy:** Capital Wars, Doomberg, CFO Dynamics
**Verticais:** fintech, biotech, e-commerce, edtech, sustainability
Ver `collector.py` para lista completa.

### YouTube (11 canais)
Fireship, Two Minute Papers, AI Explained, Matt Wolfe, Lex Fridman, Karpathy, AI Daily Brief, Filipe Deschamps, The AI Grid, Sabrina Ramonov, Nate Herk

---

## Heat Score (curadoria)

```
Freshness (40 pts): <6h=40, 6-12h=30, 12-24h=20, >24h=0
Fonte (30 pts):     Fundador/blog oficial=30, Jornalista=25, Release=20, Newsletter=15, Agregador=0
Impacto (30 pts):   Lancamento=30, M&A=25, Drama=20, Incremental=5
Newsletter Bonus:   Insight exclusivo=+10, Cross-validacao=+5
Ineditismo Bonus:   Fonte primaria=+15, Community-driven=+10, Indie builder=+10
Penalidade:         3+ fontes mainstream cobrindo mesma historia=-10

Threshold minimo: 60 pontos
```

---

## Modelo AI

- **Curadoria:** Claude Sonnet 4.6 (`claude-sonnet-4-6`)
- **Max tokens:** 8192
- **Retry:** 3 tentativas com backoff (60s, 120s, 180s) para rate limit

---

## Regras importantes para editar

1. **Prompts vivem em `processor.py`** (CURATOR_SYSTEM e CURATOR_USER_TEMPLATE), nao em arquivos separados. O `prompts/curator.md` e so documentacao de referencia.

2. **tool_of_day e objeto separado** — nunca colocar no array `items`. Deve ter `how_to_use` E `prompt_of_day`. O sender.py tem fallback para formato antigo.

3. **Backward compatibility** — sender.py suporta categorias antigas (breaking/ai_models/big_tech) como fallback.

4. **Tudo em portugues brasileiro** — headlines, why_it_matters, analise, how_to_use. So URLs e nomes proprios ficam em ingles.

5. **source_url obrigatorio** — nenhum item entra sem URL original. Copiar exatamente do dado de entrada.

6. **Newsletters tem janela de 36h** (vs 24h para RSS/X).

7. **max_items = 18** em todos os arquivos (config.yaml, SKILL.md, prompts).

8. **subject_hook** — frase-gancho de max 6 palavras sobre a noticia mais impactante. Usada no subject do email.

9. **number_of_day** — data point numerico impressionante extraido das noticias (value + context).

10. **Email HTML** — sender.py envia HTML (inline CSS, table-based). Preview mode gera markdown (terminal) + HTML (`/tmp/digest_preview.html`). Buttondown adiciona unsubscribe automaticamente; `{{ unsubscribe_url }}` so existe no footer markdown legado.

11. **Feedback loop** — feedback.py roda antes do processor.py (Step 1.5 no run.py). Metricas salvas em `/tmp/digest_feedback.json`. Degradacao graceful se BUTTONDOWN_API_KEY ausente. Inclui `recent_hooks` para evitar subject lines repetidas.

12. **Subject hook dedup** — feedback.py extrai hooks dos ultimos 7 dias. processor.py injeta no prompt com regra: "NAO repetir temas similares". Se o tema top for igual ao de ontem, curador escolhe o segundo tema.

13. **Coleta paralela** — collector.py usa `ThreadPoolExecutor(max_workers=10)` para buscar ~163 feeds simultaneamente. `raw_data` removido de todos os coletores para economizar I/O.

14. **Engagement no email** — sender.py inclui: emoji no subject line, "Leitura: 3 min" no header, 1-click feedback (thumbs up/neutral/down com ?tag= para tracking), CTA de referral no footer, enquete semanal (sextas).

15. **why_it_matters = 1-2 frases PRESCRITIVAS** — regra consistente em TODO o prompt. Deve responder: "O que o CEO/CFO/CMO deve FAZER com essa informacao?" Acao > descricao.

16. **Workflow da Semana (sextas)** — processor.py detecta sexta-feira e pede ao curador um `weekly_workflow` com 3-4 steps praticos. sender.py renderiza apos Tool do Dia. Campo opcional no JSON.

17. **Enquete semanal (sextas)** — sender.py mostra enquete com 4 opcoes (AI Tools, Estrategia, Brasil, Deep Dive) usando ?tag= para tracking. So aparece as sextas.

18. **Dedup em 6 camadas (v2.10)** — (1) cross-edition por URL em `dedup.py` (5 dias), (2) cross-edition por hash de titulo em `dedup.py` (evita mesma noticia de fontes diferentes), (3) pre-clustering em `processor.py` (agrupa itens sobre o mesmo assunto antes de enviar ao Claude, mantendo so o melhor representante), (4) cap por fonte (max 5 itens/fonte para forcar diversidade), (5) intra-edition em `dedup_across_sections()` com entity extraction + keyword overlap (remove duplicatas entre items/world/radar_brasil/tool_of_day/quick_links dentro da mesma edicao), (6) TF-IDF cosine similarity (threshold 0.45) como fallback semantico para duplicatas com wording diferente. Prioridade: items > world > radar_brasil > tool_of_day > quick_links.

19. **Idioma PT-BR 100%** — regra reforcada em 4 pontos do CURATOR_SYSTEM/USER_TEMPLATE. Palavras proibidas com traducao explicita: Expect→Espere, Open→Abra, Result→Resultado, Click→Clique. So URLs, nomes proprios (empresas/produtos/pessoas) e handles ficam em ingles.

20. **Ortografia estrita** — curador NAO pode inventar palavras. Regra lista explicitamente palavras comuns que nao podem ser escritas erradas: cetico (nao "cefico"), analise, estrategia, trajetoria, ate, ja, esta, nao. Em caso de duvida, usar palavra mais simples.

21. **Alertas via GitHub Issue** — `alert_failure.py` cria Issue (nao envia email para lista). Label `pipeline-failure` deve existir no repo. Owner recebe notificacao por email do GitHub. O step que falhou e detectado via `steps.*.outcome` no workflow e passado como `--failed-step`.

22. **Assistant prefill nao suportado** — `claude-sonnet-4-6` nao aceita `{"role": "assistant", "content": "{"}`. Em vez disso, usar instrucao explicita no user message: `"Responda APENAS com o JSON valido. Sem texto antes ou depois."`. Nao re-adicionar o prefill.

23. **Hooks recentes no prompt** — dedup.py mantem `digest_sent_hooks.json` com subject_hooks dos ultimos 7 dias. processor.py injeta no prompt com regra: "NAO repetir temas similares". Se o tema top for igual ao de ontem, curador escolhe o segundo tema.

24. **Browser UA obrigatorio para RSS** — collector.py e newsletter_collector.py usam User-Agent Chrome (macOS) para nao ser bloqueado por Substacks. Fetch order: `requests` com headers de browser primeiro, `feedparser` puro como fallback.

25. **Pre-clustering obrigatorio (v2.9)** — processor.py agrupa itens sobre o mesmo assunto ANTES de enviar ao Claude via `_cluster_and_pick_best()`. Usa keyword overlap (60%+ match) + entity extraction. O melhor representante de cada cluster recebe campo `_cluster_size` que indica quantas fontes cobriram a mesma historia. Claude usa esse campo para priorizar noticias exclusivas (cluster_size=1) sobre amplamente cobertas.

26. **Ineditismo minimo 30% (v2.9)** — prompt exige que pelo menos 4 dos 12 itens principais sejam de fontes primarias ou noticias nao amplamente cobertas. Regra 6 do CURATOR_SYSTEM: "INEDITISMO OBRIGATORIO".

27. **Health check de feeds (v2.10)** — `health_check.py` monitora ~200 feeds antes da coleta. ThreadPoolExecutor(15 workers), timeout 10s, requests com browser UA + feedparser fallback. Rastreia falhas consecutivas em `/tmp/digest_feed_health.json`. Alerta se feed tem 3+ falhas consecutivas. Roda como step no workflow com `continue-on-error: true` (nao-bloqueante).

28. **Radar Brasil (v2.10)** — secao 3b do layout. 1-2 itens sobre ecossistema brasileiro de tech/AI/negocios (NeoFeed, Startse, Exame, InfoMoney, Pipeline Valor, Brazil Journal, etc). Pode ser array vazio se nao houver noticia BR relevante. Dedup integrado em `dedup_across_sections()` (step 2.5). Renderizado em sender.py (HTML + markdown) com bandeira BR e cor verde.

29. **Deep Dive semanal (v2.10)** — so nas sextas. processor.py pede `deep_dive` com {title, body} — analise profunda 3-5 paragrafos sobre o tema mais quente da semana. Tom analitico, recomendacoes concretas para C-levels. sender.py renderiza apos Analise do Dia com icone microscópio e cor azul escuro.

30. **Trending velocity (v2.10)** — processor.py calcula `trending_score` baseado em engagement (likes/retweets) + recencia: likes>1000=+20, likes>500/RT>200=+15, likes>100 & <6h=+10. Injetado no prompt como campo do item. Heat score tem bonus: "engagement alto + recente = +10 pts".

31. **Fallback cache (v2.10)** — run.py: se coleta falhar, verifica se `/tmp/digest_raw.json` existe e tem <48h. Se sim, continua com dados antigos (log de warning com idade do cache). Se nao, aborta. Workflow: raw data cache via `actions/cache@v4` (save apos coleta, restore antes).

32. **TF-IDF dedup (v2.10)** — `_tfidf_similarity()` em processor.py: similaridade cosine TF-IDF entre titulos curtos. Tokeniza, remove stopwords, calcula IDF suavizado (log(1+N/df)), vetores TF-IDF normalizados, cosine similarity. Threshold 0.45. Usado como terceiro check em `_titles_overlap()` (apos keyword overlap 60% e entity overlap 40%). Implementacao stdlib-only (math, re, collections).

33. **Byte Score (v2.13)** — classificador de impacto estrategico exibido em todo item noticioso. O curador retorna `byte_score` (float 0.0–10.0) por item. O tier, emoji e cor sao derivados SEMPRE no codigo (`sender.py` via `_byte_tier()`) — Claude nunca envia o tier, apenas o numero. Faixas: 9.0–10.0 = 📦 GIGABYTE (#FF6B35/branco) · 7.0–8.9 = 💿 MEGABYTE (#F7A072/escuro) · 5.0–6.9 = 💾 KILOBYTE (#6B7280/branco) · 0.0–4.9 = 📄 byte (#E5E7EB/cinza). Escopo: world[], items[] (hoje_no_byte e saas_enterprise), radar_brasil[], quick_links[]. Excluidos: tool_of_day, watch_later, number_of_day. `heat_score` continua 100% interno (criterio de selecao, corte 60) — nunca renderizado ao leitor. Calibracao anti-inflacao: GIGABYTE e raro; numa edicao tipica espere ~0 GIGABYTE, 1-2 MEGABYTE, varias KILOBYTE, bytes nos quick links.

---

## Como rodar localmente

### Setup inicial (so precisa fazer uma vez)

```bash
# 1. Python 3.14 via Homebrew (macOS)
brew install python@3.14

# 2. Criar virtual environment na raiz do projeto
cd ~/daily-tech-digest
python3 -m venv venv

# 3. Ativar venv e instalar dependencias
source venv/bin/activate
pip install anthropic feedparser beautifulsoup4 lxml requests pyyaml python-dotenv

# 4. Criar .env com as chaves (ja esta no .gitignore)
# O arquivo .env deve conter:
#   ANTHROPIC_API_KEY=sk-ant-...
#   BUTTONDOWN_API_KEY=...
#   X_BEARER_TOKEN=...
```

### Rodar o pipeline

```bash
cd ~/daily-tech-digest
source venv/bin/activate
source .env   # carrega as chaves no shell

cd scripts

# So coletar
python collector.py

# So processar (precisa /tmp/digest_raw.json)
python processor.py

# So enviar preview (precisa /tmp/digest_curated.json)
python sender.py --preview

# Pipeline completo
python run.py --preview     # sem enviar (salva .md + .html em /tmp/)
python run.py               # envia de verdade via Buttondown

# Flags de skip (usar dados ja coletados/processados em /tmp/)
python run.py --skip-collect   # pula coleta, usa /tmp/digest_raw.json existente
python run.py --skip-process   # pula curadoria, usa /tmp/digest_curated.json existente
```

### Env vars necessarias

| Variavel | Onde conseguir | Obrigatoria? |
|----------|---------------|--------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | Sim |
| `BUTTONDOWN_API_KEY` | buttondown.com/settings | Sim (envio + feedback) |
| `X_BEARER_TOKEN` | developer.x.com | Opcional (coleta do X) |

Estas chaves tambem estao configuradas no GitHub Secrets para o Actions.

---

## Troubleshooting (erros comuns)

| Erro | Causa | Fix |
|------|-------|-----|
| `ModuleNotFoundError: No module named 'anthropic'` | venv nao ativado ou deps faltando | `source venv/bin/activate && pip install -r requirements.txt` |
| `zsh: command not found: python` | macOS usa `python3` | Usar `python3` ou ativar venv (que cria alias `python`) |
| `error: externally-managed-environment` | Python Homebrew bloqueia pip global (PEP 668) | Usar venv (`python3 -m venv venv`) |
| `Couldn't find tree builder: lxml` | lxml nao instalado | `pip install lxml` |
| `ANTHROPIC_API_KEY not set` | Chaves nao exportadas no shell | `source .env` antes de rodar |
| `GH013: Push cannot contain secrets` | .env commitado por engano | `git reset HEAD~1`, add `.env` ao `.gitignore` |
| `another git process seems to be running` | Lock file travado | `rm -f .git/HEAD.lock .git/index.lock` |
| `unsupported operand type(s) for \|: 'type' and 'NoneType'` | Syntax `dict \| None` requer Python 3.10+ | Ja corrigido no processor.py (v2.4) |

---

## Rotina de Evolucao

**Domingos** — usar skill `digest-evolution` para:
1. Analisar estado atual do projeto
2. Pesquisar novas fontes e benchmarks
3. Propor melhorias ao Toto
4. Implementar mudancas aprovadas

Ver `EVOLUTION-PLAN.md` para historico e backlog.

---

## Deploy

Push para `main` -> GitHub Actions pega automaticamente no proximo run (03:00 BRT / 06:00 UTC).
Nao precisa de deploy manual. O workflow faz `checkout@v4` fresh toda vez.

Para rodar manualmente: GitHub Actions -> "Run workflow" -> preview_only true/false.
