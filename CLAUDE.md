# THE DAILY BYTE — Instrucoes do Projeto

## O que e este projeto

Newsletter diaria automatizada de Tech & AI para C-levels brasileiros (CEOs, CFOs, CMOs, CPOs). Pipeline: coletar noticias -> curar com Claude -> enviar via Buttondown.

**Versao atual:** v2.3 (Tier 1 Expansion — 92 fontes Pulse.bot)
**Autor:** Toto Busnello (lab@nuvini.ai)

---

## Arquitetura

```
collector.py          -> /tmp/digest_raw.json
  (RSS + YouTube + X + Newsletters)
       |
processor.py          -> /tmp/digest_curated.json
  (Claude Sonnet 4.5 curadoria)
       |
sender.py             -> Buttondown API -> email
  (markdown rendering)
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
| `scripts/sender.py` | Renderiza email markdown e envia via Buttondown |
| `scripts/run.py` | Pipeline completo (collect -> process -> send) |
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

- **Curadoria:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
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

---

## Como rodar localmente

```bash
cd scripts

# So coletar
python collector.py

# So processar (precisa /tmp/digest_raw.json)
python processor.py

# So enviar preview (precisa /tmp/digest_curated.json)
python sender.py --preview

# Pipeline completo
python run.py --preview     # sem enviar
python run.py               # envia de verdade
```

**Env vars necessarias:**
- `ANTHROPIC_API_KEY` — obrigatoria
- `BUTTONDOWN_API_KEY` — para envio
- `X_BEARER_TOKEN` — opcional (coleta do X)

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
