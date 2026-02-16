# THE DAILY BYTE — Instrucoes do Projeto

## O que e este projeto

Newsletter diaria automatizada de Tech & AI para C-levels brasileiros (CEOs, CFOs, CMOs, CPOs). Pipeline: coletar noticias -> curar com Claude -> enviar via Buttondown.

**Versao atual:** v2.1 (Layout Consolidado)
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
| `scripts/newsletter_collector.py` | Scraper BeautifulSoup para 7 newsletters |
| `scripts/processor.py` | Curadoria com Claude (CURATOR_SYSTEM + CURATOR_USER_TEMPLATE) |
| `scripts/sender.py` | Renderiza email markdown e envia via Buttondown |
| `scripts/run.py` | Pipeline completo (collect -> process -> send) |
| `prompts/curator.md` | Documentacao de referencia do prompt de curadoria |
| `SKILL.md` | Filosofia, criterios, layout, fontes |
| `EVOLUTION-PLAN.md` | Historico de versoes e backlog |

---

## Layout v2.1 — 6 Secoes

```
1. MUNDO REAL (3 itens) — mundo + Brasil
2. HOJE NO BYTE (4-5 itens) — tags: [BREAKING], [AI], [BIG TECH], [ENTERPRISE]
3. SaaS & ENTERPRISE (2 itens)
4. TOOL DO DIA (1 item) + COMO USAR HOJE (prompt copy-paste)
5. ANALISE DO DIA (3 bullets)
6. QUICK LINKS (5-6 itens) — headline + link, sem analise
+ WATCH LATER (1 video no final)
```

**Total maximo:** 18 itens (12 principais + 6 quick links)

**JSON do curador:**
- `world[]` — array de 3 itens (headline, context, source_url, source_name)
- `items[]` — array com category `hoje_no_byte|saas_enterprise|watch_later` e campo `tag`
- `tool_of_day{}` — OBJETO SEPARADO (nao vai no items), com `how_to_use` obrigatorio
- `quick_links[]` — apenas headline + source_url + source_name
- `daily_analysis[]` — 3 strings com formato "**Tema** — Insight"

---

## Fontes

### Tier 1 — Primeira Mao (X/Twitter handles)
@sama, @AnthropicAI, @satyanadella, @sundarpichai, @ylecun, @karpathy, etc.

### Tier 2 — RSS Feeds
**Tech:** HN (100+ pts), Ars Technica, Wired, The Verge, TechCrunch AI, MIT Tech Review
**World:** Reuters (world + business), Forbes (business + innovation), BBC (world + business)
**Research:** arXiv cs.AI

### Tier 3 — Newsletters (7 fontes, via scraping)
| Newsletter | Foco | Idioma |
|-----------|------|--------|
| AiDrop | AI, analise profunda | PT-BR |
| Evolving AI | Modelos, benchmarks | EN |
| Update Diario | Brasil, economia | PT-BR |
| TechDrop | SaaS, enterprise, CapEx | PT-BR |
| AlphaSignal | Research -> produto | EN |
| There's An AI For That | AI tools (2.8M subs) | EN |
| Turing Post | AI strategy, geopolitica | EN |

### YouTube (7 canais)
Fireship, Two Minute Papers, AI Explained, Matt Wolfe, Lex Fridman, Karpathy, AI Daily Brief

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
- **Max tokens:** 4096
- **Retry:** 3 tentativas com backoff (60s, 120s, 180s) para rate limit

---

## Regras importantes para editar

1. **Prompts vivem em `processor.py`** (CURATOR_SYSTEM e CURATOR_USER_TEMPLATE), nao em arquivos separados. O `prompts/curator.md` e so documentacao de referencia.

2. **tool_of_day e objeto separado** — nunca colocar no array `items`. O sender.py tem fallback para formato antigo.

3. **Backward compatibility** — sender.py suporta categorias antigas (breaking/ai_models/big_tech) como fallback.

4. **Tudo em portugues brasileiro** — headlines, why_it_matters, analise, how_to_use. So URLs e nomes proprios ficam em ingles.

5. **source_url obrigatorio** — nenhum item entra sem URL original. Copiar exatamente do dado de entrada.

6. **Newsletters tem janela de 36h** (vs 24h para RSS/X).

7. **max_items = 18** em todos os arquivos (config.yaml, SKILL.md, prompts).

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
