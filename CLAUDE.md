# THE DAILY BYTE — Instrucoes do Projeto

## O que e este projeto

Newsletter diaria automatizada de Tech & AI para C-levels brasileiros (CEOs, CFOs, CMOs, CPOs). Pipeline: coletar noticias -> curar com Claude -> enviar via Buttondown.

**Versao atual:** v2.4 (HTML Template + Feedback Loop + Optimizations)
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
  (Claude Sonnet 4.5 curadoria + feedback metrics)
       |
sender.py             -> Buttondown API -> email HTML
  (template HTML inline CSS, mobile-first)
```

**Orquestrador:** `run.py` (ou GitHub Actions via `daily-digest.yml`)
**Schedule:** Diario as 06:45 BRT (09:45 UTC) via GitHub Actions

---

## Arquivos-chave

| Arquivo | Funcao |
|---------|--------|
| `config.yaml` | Configuracao central: modelo, distribuicao, fontes, temas |
| `scripts/collector.py` | Coleta RSS, YouTube, X/Twitter, orquestra newsletters |
| `scripts/newsletter_collector.py` | Scraper BeautifulSoup + RSS para 9 newsletters |
| `scripts/processor.py` | Curadoria com Claude (CURATOR_SYSTEM + CURATOR_USER_TEMPLATE) |
| `scripts/sender.py` | Renderiza email HTML (template inline CSS) e envia via Buttondown |
| `scripts/feedback.py` | Puxa metricas Buttondown (opens, clicks, top temas) para informar curadoria |
| `scripts/run.py` | Pipeline completo (collect -> feedback -> process -> send) |
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
4. TOOL DO DIA (1 item) + COMO USAR HOJE + PROMPT DO DIA (copy-paste ready)
5. ANALISE DO DIA (3 bullets)
6. QUICK LINKS (5-6 itens) — headline + link, sem analise
+ WATCH LATER (1 video no final)
```

**Total maximo:** 18 itens (12 principais + 6 quick links)

**JSON do curador:**
- `subject_hook` — frase-gancho de max 6 palavras para subject line
- `number_of_day{}` — {value, context} — data point numerico impressionante
- `world[]` — array de 3 itens (headline, context, source_url, source_name)
- `items[]` — array com category `hoje_no_byte|saas_enterprise|watch_later` e campo `tag`
- `tool_of_day{}` — OBJETO SEPARADO (nao vai no items), com `how_to_use` e `prompt_of_day` obrigatorios
- `quick_links[]` — apenas headline + source_url + source_name
- `daily_analysis[]` — 3 strings com formato "**Tema** — Insight"

---

## Fontes

### Tier 1 — Primeira Mao (X/Twitter handles)
@sama, @AnthropicAI, @satyanadella, @sundarpichai, @ylecun, @karpathy, @aravind_srinivas, @demishassabis, @ethanmollick, etc.

### Tier 2 — RSS Feeds
**Tech:** HN (100+ pts), Ars Technica, Wired, The Verge, TechCrunch AI, MIT Tech Review, The Decoder
**World:** Reuters (world + business), Forbes (business + innovation), BBC (world + business)
**Research:** arXiv cs.AI

### Tier 3 — Newsletters (9 fontes, via scraping + RSS)
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

### YouTube (8 canais)
Fireship, Two Minute Papers, AI Explained, Matt Wolfe, Lex Fridman, Karpathy, AI Daily Brief, Filipe Deschamps

---

## Heat Score (curadoria)

```
Freshness (40 pts): <6h=40, 6-12h=30, 12-24h=20, >24h=0
Fonte (30 pts):     Fundador=30, Jornalista=25, Release=20, Newsletter=15, Agregador=0
Impacto (30 pts):   Lancamento=30, M&A=25, Drama=20, Incremental=5
Newsletter Bonus:   Insight exclusivo=+10, Cross-validacao=+5

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

10. **Email HTML** — sender.py envia HTML (inline CSS, table-based). Preview mode gera markdown (terminal) + HTML (`/tmp/digest_preview.html`). Template usa Buttondown `{{ unsubscribe_url }}`.

11. **Feedback loop** — feedback.py roda antes do processor.py (Step 1.5 no run.py). Metricas salvas em `/tmp/digest_feedback.json`. Degradacao graceful se BUTTONDOWN_API_KEY ausente.

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

Push para `main` -> GitHub Actions pega automaticamente no proximo run (06:45 BRT).
Nao precisa de deploy manual. O workflow faz `checkout@v4` fresh toda vez.

Para rodar manualmente: GitHub Actions -> "Run workflow" -> preview_only true/false.
