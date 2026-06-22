# Byte Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o indicador genérico de "heat" (🔥) por um classificador proprietário de impacto estratégico — o **Byte Score** (0-10) com tiers em unidades de dados (📦 GIGABYTE / 💿 MEGABYTE / 💾 KILOBYTE / 📄 byte), exibido em todo item noticioso.

**Architecture:** O curador (Claude, em `processor.py`) passa a retornar um `byte_score` (float 0-10) por item noticioso. O `sender.py` deriva tier/emoji/cor do número via função pura (`_byte_tier`) e renderiza um badge (`_byte_badge_html` / `_byte_badge_md`) antes do headline. O `heat_score` continua existindo só para seleção interna; o 🔥 sai da renderização.

**Tech Stack:** Python 3.10+ (stdlib only), HTML inline-CSS (email), Anthropic API (curadoria). Sem dependências novas.

## Global Constraints

- **Faixas (exatas):** `9.0–10.0` GIGABYTE · `7.0–8.9` MEGABYTE · `5.0–6.9` KILOBYTE · `0.0–4.9` byte.
- **Emojis (exatos):** 📦 GIGABYTE · 💿 MEGABYTE · 💾 KILOBYTE · 📄 byte.
- **Cores (fundo/texto):** GIGABYTE `#FF6B35`/`#ffffff` · MEGABYTE `#F7A072`/`#1a1a2e` · KILOBYTE `#6B7280`/`#ffffff` · byte `#E5E7EB`/`#6B7280`.
- **Escopo do selo:** `world[]`, `items[]` com category `hoje_no_byte` e `saas_enterprise`, `radar_brasil[]`, `quick_links[]`. **Fora:** `tool_of_day`, `watch_later` (category), `number_of_day`.
- **Tier derivado no código** a partir do número — o Claude nunca envia o tier.
- **Tudo em PT-BR** (regra do projeto). Só nomes próprios/URLs em inglês.
- **Sem dependência nova.** Verificação por `python scripts/test_byte_score.py` (lógica) e `python scripts/sender.py --preview` (visual).
- **Versão alvo:** v2.13.
- **Spec de referência:** `docs/superpowers/specs/2026-06-22-byte-score-design.md`.

---

### Task 1: Função de derivação `_byte_tier` / badges + teste standalone

Núcleo lógico puro: dado um número 0-10, retornar tier/emoji/cor, e montar os badges HTML e markdown. É a única parte determinística e testável isoladamente.

**Files:**
- Modify: `scripts/sender.py` (adicionar tabela `BYTE_TIERS` e funções logo após o dict `COLORS` e a função `_esc`, antes de `_heat_bar`)
- Create: `scripts/test_byte_score.py`

**Interfaces:**
- Produces:
  - `_byte_tier(score) -> tuple|None` — retorna `(label, emoji, bg, fg)` ou `None` se `score` for inválido/ausente.
  - `_byte_badge_html(score) -> str` — badge HTML completo (número + emoji + palavra) ou `""` se inválido.
  - `_byte_badge_md(score) -> str` — `"9.2 📦 GIGABYTE"` ou `""` se inválido.

- [ ] **Step 1: Escrever o teste standalone (falha primeiro)**

Criar `scripts/test_byte_score.py`:

```python
"""Testes standalone do Byte Score (sem pytest). Rodar: python scripts/test_byte_score.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import sender

def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        check.failed += 1
check.failed = 0

# Faixas
check("9.0 -> GIGABYTE", sender._byte_tier(9.0)[0] == "GIGABYTE")
check("10 -> GIGABYTE", sender._byte_tier(10)[0] == "GIGABYTE")
check("8.9 -> MEGABYTE", sender._byte_tier(8.9)[0] == "MEGABYTE")
check("7.0 -> MEGABYTE", sender._byte_tier(7.0)[0] == "MEGABYTE")
check("6.9 -> KILOBYTE", sender._byte_tier(6.9)[0] == "KILOBYTE")
check("5.0 -> KILOBYTE", sender._byte_tier(5.0)[0] == "KILOBYTE")
check("4.9 -> byte", sender._byte_tier(4.9)[0] == "byte")
check("0 -> byte", sender._byte_tier(0)[0] == "byte")

# Emojis e cores
check("GIGA emoji", sender._byte_tier(9.5)[1] == "📦")
check("MEGA emoji", sender._byte_tier(7.5)[1] == "💿")
check("KILO emoji", sender._byte_tier(5.5)[1] == "💾")
check("byte emoji", sender._byte_tier(2.0)[1] == "📄")
check("GIGA bg", sender._byte_tier(9.5)[2] == "#FF6B35")

# Inválidos -> None / ""
check("None score -> None", sender._byte_tier(None) is None)
check("texto -> None", sender._byte_tier("abc") is None)
check("badge html vazio p/ None", sender._byte_badge_html(None) == "")
check("badge md vazio p/ None", sender._byte_badge_md(None) == "")

# Conteúdo dos badges
html = sender._byte_badge_html(9.2)
check("html tem numero 9.2", "9.2" in html)
check("html tem GIGABYTE", "GIGABYTE" in html)
check("html tem emoji", "📦" in html)
check("html tem cor giga", "#FF6B35" in html)
check("md formato", sender._byte_badge_md(7.1) == "7.1 💿 MEGABYTE")

print("\n%d falha(s)" % check.failed)
sys.exit(1 if check.failed else 0)
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `cd /Users/lab/Claude/Projetos/daily-tech-digest && python scripts/test_byte_score.py`
Expected: erro (`AttributeError: module 'sender' has no attribute '_byte_tier'`).

- [ ] **Step 3: Implementar a derivação + badges em `sender.py`**

Inserir logo após a função `_esc(...)` e **antes** de `def _heat_bar(`:

```python
# ── Byte Score (v2.13) — classificador de impacto estratégico ──
# (limite_inferior, label, emoji, cor_fundo, cor_texto)
BYTE_TIERS = [
    (9.0, "GIGABYTE", "📦", "#FF6B35", "#ffffff"),
    (7.0, "MEGABYTE", "💿", "#F7A072", "#1a1a2e"),
    (5.0, "KILOBYTE", "💾", "#6B7280", "#ffffff"),
    (0.0, "byte",     "📄", "#E5E7EB", "#6B7280"),
]

def _byte_tier(score):
    """Deriva (label, emoji, bg, fg) de um Byte Score 0-10. None se ausente/inválido."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    for lower, label, emoji, bg, fg in BYTE_TIERS:
        if s >= lower:
            return (label, emoji, bg, fg)
    return BYTE_TIERS[-1][1:]

def _byte_badge_html(score):
    """Badge HTML completo do Byte Score (número + emoji + palavra). '' se ausente."""
    tier = _byte_tier(score)
    if tier is None:
        return ""
    label, emoji, bg, fg = tier
    s = float(score)
    return (
        f'<span style="display:inline-block;background-color:{bg};color:{fg};'
        f'font-size:12px;font-weight:800;padding:3px 9px 3px 7px;border-radius:6px;'
        f'vertical-align:middle;margin-right:6px;white-space:nowrap;">'
        f'<span style="font-size:13px;">{s:.1f}</span> {emoji} '
        f'<span style="font-size:10px;font-weight:700;letter-spacing:0.6px;">{label}</span></span>'
    )

def _byte_badge_md(score):
    """Badge markdown do Byte Score: '9.2 📦 GIGABYTE'. '' se ausente."""
    tier = _byte_tier(score)
    if tier is None:
        return ""
    label, emoji, _, _ = tier
    return f"{float(score):.1f} {emoji} {label}"
```

- [ ] **Step 4: Rodar o teste e verificar que passa**

Run: `cd /Users/lab/Claude/Projetos/daily-tech-digest && python scripts/test_byte_score.py`
Expected: todas as linhas `PASS`, `0 falha(s)`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/sender.py scripts/test_byte_score.py
git commit -m "feat(byte-score): add _byte_tier derivation + HTML/MD badges with standalone tests"
```

---

### Task 2: Renderizar o badge nos itens principais (HTML) e aposentar o 🔥

Aplicar o badge em `_render_item_html` (usada por Mundo Real, Hoje no Byte, SaaS, Radar Brasil) e remover o `heat_html`/`_heat_bar` da renderização.

**Files:**
- Modify: `scripts/sender.py` — função `_render_item_html` (lê `heat_score`, monta `heat_html` via `_heat_bar`, usa na linha do headline). Também a renderização de `radar_brasil` se montar o item manualmente (verificar se reusa `_render_item_html`; se sim, nada extra).

**Interfaces:**
- Consumes: `_byte_badge_html` (Task 1).

- [ ] **Step 1: Substituir heat por byte_score em `_render_item_html`**

Em `_render_item_html`, trocar a leitura do heat e o uso na linha do headline. Onde hoje há:

```python
    heat = item.get('heat_score', 0)
```
e
```python
    heat_html = _heat_bar(heat)
```
substituir as duas por:
```python
    byte_html = _byte_badge_html(item.get('byte_score'))
```
E na linha que monta o headline, hoje:
```python
      {tag_html}{headline} {heat_html}
```
trocar para (badge ANTES do tag e do headline):
```python
      {byte_html}{tag_html}{headline}
```

- [ ] **Step 2: Verificar que `radar_brasil` também recebe o badge**

Localizar a renderização de `radar_brasil` em `sender.py` (busca: `radar_brasil`). Se ela **reusa** `_render_item_html`, nenhuma mudança é necessária. Se monta o HTML inline (com `why_it_matters` próprio), inserir `_byte_badge_html(rb.get('byte_score'))` imediatamente antes do headline, no mesmo padrão.

Run (para localizar): `grep -n "radar_brasil" scripts/sender.py`

- [ ] **Step 3: Montar um fixture e gerar o preview**

Criar `/tmp/digest_curated.json` com Byte Scores variados (cobre todos os tiers):

```bash
cat > /tmp/digest_curated.json <<'JSON'
{
  "subject_hook": "Teste Byte Score",
  "number_of_day": {"value": "$600B", "context": "Compute OpenAI até 2030"},
  "world": [
    {"headline": "UE aprova lei de rotulagem de IA", "context": "Regulação", "source_url": "https://x", "source_name": "Reuters", "byte_score": 7.8}
  ],
  "items": [
    {"headline": "OpenAI lança GPT-6", "tag": "BREAKING", "why_it_matters": "CTOs: testem em piloto.", "source_url": "https://x", "source_name": "@openai", "hours_ago": 2, "heat_score": 92, "category": "hoje_no_byte", "byte_score": 9.4},
    {"headline": "Anthropic corta preço enterprise", "tag": "AI", "why_it_matters": "CFOs: renegociem.", "source_url": "https://x", "source_name": "@anthropic", "hours_ago": 5, "heat_score": 80, "category": "hoje_no_byte", "byte_score": 7.2},
    {"headline": "Salesforce adiciona agentes", "tag": "ENTERPRISE", "why_it_matters": "CROs: peçam piloto.", "source_url": "https://x", "source_name": "TechCrunch", "hours_ago": 6, "heat_score": 70, "category": "saas_enterprise", "byte_score": 5.9}
  ],
  "tool_of_day": {"headline": "Cursor 2.0", "why_it_matters": "IDE com agentes.", "how_to_use": "Abra. Rode o agente.", "prompt_of_day": "Analise X.", "source_url": "https://x", "source_name": "Cursor"},
  "radar_brasil": [
    {"headline": "Nubank lança copiloto financeiro", "why_it_matters": "Maior deploy BR.", "source_url": "https://x", "source_name": "NeoFeed", "byte_score": 6.1}
  ],
  "quick_links": [
    {"headline": "Mistral fecha rodada europeia", "source_url": "https://x", "source_name": "Bloomberg", "byte_score": 5.2},
    {"headline": "Startup de RH levanta seed", "source_url": "https://x", "source_name": "Crunchbase", "byte_score": 3.4}
  ],
  "daily_analysis": ["**IA** — Insight.", "**Mercado** — Insight.", "**Tendência** — Insight."],
  "stats": {"total_analyzed": 100, "selected": 7, "rejected_too_old": 10, "rejected_low_impact": 5}
}
JSON
python scripts/sender.py --preview
```
Expected: gera `/tmp/digest_preview.html` sem erro.

- [ ] **Step 4: Verificar badges no HTML e ausência do fogo**

Run:
```bash
grep -c "GIGABYTE\|MEGABYTE\|KILOBYTE" /tmp/digest_preview.html
grep -c "1F525\|🔥" /tmp/digest_preview.html
```
Expected: primeira contagem ≥ 4 (itens principais com tier). Segunda contagem `0` (fogo removido da renderização dos itens principais; se ainda houver 🔥 em outra seção, será tratado nas Tasks 3-4).

- [ ] **Step 5: Commit**

```bash
git add scripts/sender.py
git commit -m "feat(byte-score): render Byte Score badge on main items, retire heat fire emoji"
```

---

### Task 3: Badge completo nos Quick Links (HTML)

Os quick links hoje renderizam só headline + link. Adicionar o badge **completo** (decisão do Totó: sem versão curta — classificação igual em toda a edição).

**Files:**
- Modify: `scripts/sender.py` — bloco de renderização HTML de `quick_links` (a partir do comentário `# ── 6. QUICK LINKS`, ~linha 460; o loop que monta cada link).

**Interfaces:**
- Consumes: `_byte_badge_html` (Task 1).

- [ ] **Step 1: Inserir o badge antes do headline de cada quick link**

Ler o bloco de quick links (`grep -n "QUICK LINKS" scripts/sender.py`, depois ler ~40 linhas a partir dali). Cada link é montado com `ql.get('headline')` dentro de um `<a>`. Imediatamente **antes** do texto/link do headline, inserir o badge:

```python
            ql_badge = _byte_badge_html(ql.get('byte_score'))
```
e prefixar o badge na célula do link, por exemplo de:
```python
            <a href="{_esc(ql.get('source_url','#'))}" ...>{_esc(ql.get('headline',''))}</a>
```
para:
```python
            {ql_badge}<a href="{_esc(ql.get('source_url','#'))}" ...>{_esc(ql.get('headline',''))}</a>
```
(usar o nome de variável real do loop — pode ser `ql`, `link` ou índice; adaptar ao código existente.)

- [ ] **Step 2: Regenerar o preview**

Run: `cd /Users/lab/Claude/Projetos/daily-tech-digest && python scripts/sender.py --preview`
Expected: sem erro.

- [ ] **Step 3: Verificar badge nos quick links**

Run: `grep -o "5.2 .*KILOBYTE\|3.4 .*byte" /tmp/digest_preview.html | head`
Expected: encontra os badges dos quick links do fixture (5.2 KILOBYTE, 3.4 byte).

Abrir visualmente para conferir que não aperta demais a headline:
Run: `open /tmp/digest_preview.html`

- [ ] **Step 4: Commit**

```bash
git add scripts/sender.py
git commit -m "feat(byte-score): add full Byte Score badge to quick links (HTML)"
```

---

### Task 4: Markdown legacy + legenda no rodapé

Atualizar o caminho markdown (`format_item` e o bloco markdown de quick links) para usar `_byte_badge_md` e remover o `heat_emoji` 🔥. Adicionar a legenda da escala no rodapé do HTML.

**Files:**
- Modify: `scripts/sender.py` — `format_item` (markdown legacy, remove `heat_emoji`); bloco markdown de quick links (~linha 829); rodapé HTML (adicionar legenda).

**Interfaces:**
- Consumes: `_byte_badge_md` (Task 1).

- [ ] **Step 1: Atualizar `format_item` (markdown)**

Em `format_item`, remover:
```python
    heat = item.get('heat_score', 0)

    heat_emoji = "🔥🔥🔥" if heat >= 80 else "🔥🔥" if heat >= 70 else "🔥"
```
e trocar a linha do título de:
```python
    return f"""{tag_str}**{headline}** {heat_emoji}
```
para:
```python
    byte_md = _byte_badge_md(item.get('byte_score'))
    byte_prefix = f"{byte_md} " if byte_md else ""
    return f"""{byte_prefix}{tag_str}**{headline}**
```

- [ ] **Step 2: Atualizar quick links no markdown**

Localizar o bloco markdown de quick links (`grep -n "quick_links" scripts/sender.py` → ~linha 829). Prefixar cada linha do quick link com `_byte_badge_md(ql.get('byte_score'))` (quando não vazio, seguido de espaço), no mesmo padrão do Step 1.

- [ ] **Step 3: Adicionar legenda no rodapé HTML**

Localizar a montagem do rodapé HTML (antes do footer/unsubscribe). Inserir uma linha de legenda (uma row de tabela com o mesmo estilo de texto muted do rodapé):

```python
    legend_html = (
        '<tr><td style="padding:12px 20px;font-size:11px;color:#6b7280;line-height:1.6;">'
        '<b style="color:#1a1a2e;">Byte Score</b> — impacto estratégico: '
        '📦 GIGABYTE redefine o mercado · 💿 MEGABYTE muda o jogo · '
        '💾 KILOBYTE relevante · 📄 byte nota de rodapé.'
        '</td></tr>'
    )
```
e adicioná-la a `body_rows` logo antes do footer.

- [ ] **Step 4: Verificar markdown e legenda no preview**

Run:
```bash
cd /Users/lab/Claude/Projetos/daily-tech-digest && python scripts/sender.py --preview
grep -c "🔥" /tmp/digest_preview.html
grep -c "Byte Score" /tmp/digest_preview.html
```
Expected: `🔥` = `0` (fogo 100% removido). `Byte Score` ≥ 1 (legenda presente).

- [ ] **Step 5: Commit**

```bash
git add scripts/sender.py
git commit -m "feat(byte-score): markdown badges, remove heat emoji, add footer legend"
```

---

### Task 5: Prompt do curador + schema `byte_score`

Ensinar o curador a atribuir o `byte_score` por julgamento ancorado, e adicionar o campo ao JSON schema dos arrays em escopo.

**Files:**
- Modify: `scripts/processor.py` — `CURATOR_SYSTEM` (adicionar bloco BYTE SCORE) e o JSON schema dentro de `CURATOR_USER_TEMPLATE` (campo `byte_score` em `world[]`, `items[]`, `radar_brasil[]`, `quick_links[]`).

**Interfaces:**
- Produces: cada item noticioso do JSON do curador passa a conter `byte_score` (float 0.0–10.0).

- [ ] **Step 1: Adicionar o bloco BYTE SCORE ao `CURATOR_SYSTEM`**

Inserir após a regra 7 (DIVERSIDADE TEMÁTICA), antes de "LAYOUT CONSOLIDADO":

```text
BYTE SCORE — CLASSIFICAÇÃO DE IMPACTO ESTRATÉGICO (v2.13):
Cada item noticioso recebe um "byte_score" (número de 0.0 a 10.0) = QUANTO a notícia move o jogo.
É diferente do critério de seleção: mede a MAGNITUDE do impacto, não se a notícia entra.
Faixas (o rótulo é derivado pelo sistema, você só envia o número):
- 9.0–10.0 GIGABYTE: redefine o mercado / novo paradigma
- 7.0–8.9  MEGABYTE: grande player muda o jogo
- 5.0–6.9  KILOBYTE: relevante, incremental
- 0.0–4.9  byte: nota de rodapé

REGRA ANTI-INFLAÇÃO: GIGABYTE é raro — a maioria das edições NÃO tem um. Reserve para a
notícia que você apostaria ser lembrada daqui a 6 meses. Se nada redefiniu o mercado hoje,
o teto da edição é MEGABYTE. Numa edição típica espere ~0 GIGABYTE, 1-2 MEGABYTE, várias
KILOBYTE e bytes nos quick links. NÃO infle.

EXEMPLOS-ÂNCORA:
- GIGABYTE (9-10): "Lab lança modelo que supera humanos em raciocínio geral" / "Regulação que redefine modelos fechados entra em vigor na UE"
- MEGABYTE (7-8.9): "Anthropic corta preço enterprise em 50%" / "Google embute Gemini nativo no Android para bilhões de devices"
- KILOBYTE (5-6.9): "SaaS conhecido adiciona feature de agentes" / "Novo benchmark mostra modelo 5% acima do anterior"
- byte (0-4.9): "Funding seed de US$2M para startup de nicho" / "Update de UI numa ferramenta popular"

O byte_score vai em CADA item de "world", "items", "radar_brasil" e "quick_links".
NÃO vai em "tool_of_day", "watch_later" nem "number_of_day".
```

- [ ] **Step 2: Adicionar `byte_score` ao JSON schema (`CURATOR_USER_TEMPLATE`)**

No schema do template, adicionar a chave `byte_score` (float) em cada um dos quatro arrays. Exemplos das linhas a alterar:

`world[]` — depois de `"source_name"`:
```json
      "source_name": "Reuters|Forbes|BBC",
      "byte_score": 7.0
```
`items[]` — depois de `"category"`:
```json
      "category": "hoje_no_byte|saas_enterprise|watch_later",
      "byte_score": 7.5
```
`radar_brasil[]` — depois de `"source_name"`:
```json
      "source_name": "NeoFeed|Startse|Exame|InfoMoney|Pipeline Valor",
      "byte_score": 6.0
```
`quick_links[]` — depois de `"source_name"`:
```json
      "source_name": "Fonte",
      "byte_score": 4.0
```
(atenção: o template usa chaves duplicadas `{{` `}}` por ser `.format()` — manter o padrão existente do arquivo.)

Adicionar também ao bloco "LEMBRE-SE" uma linha:
```text
- Cada item de world/items/radar_brasil/quick_links DEVE ter "byte_score" (0.0-10.0). GIGABYTE (9+) é raro.
```

- [ ] **Step 3: Verificar que o prompt monta sem erro de format**

Run:
```bash
cd /Users/lab/Claude/Projetos/daily-tech-digest && python -c "import scripts.processor as p" 2>&1 | head
```
(Se o import direto falhar por path, usar:) `cd scripts && python -c "import processor"`
Expected: sem `KeyError`/`IndexError` de `.format` (o módulo importa limpo). Se o template é formatado só em runtime, validar com um `.format(**kwargs)` de fumaça conforme o uso no arquivo.

- [ ] **Step 4: Commit**

```bash
git add scripts/processor.py
git commit -m "feat(byte-score): teach curator to assign byte_score (anchored) + schema fields"
```

---

### Task 6: Documentação v2.13

Refletir o Byte Score na documentação do projeto.

**Files:**
- Modify: `config.yaml` (header → v2.13 + nota), `SKILL.md` (seção Byte Score), `CLAUDE.md` (nova regra + versão atual), `EVOLUTION-PLAN.md` (changelog v2.13).

- [ ] **Step 1: Atualizar `config.yaml`**

Trocar o header de versão para `v2.13` e adicionar comentário no bloco de curadoria descrevendo o `byte_score` (faixas + escopo).

- [ ] **Step 2: Atualizar `SKILL.md`**

Adicionar uma subseção "Byte Score" sob a estrutura do email: escala (📦💿💾📄), faixas, escopo (itens noticiosos; fora tool/watch/number), e que o tier é derivado do número.

- [ ] **Step 3: Atualizar `CLAUDE.md`**

Atualizar "Versao atual" para v2.13 e adicionar uma regra numerada (na lista de "Regras importantes para editar") descrevendo o Byte Score: número 0-10 do curador, tier/emoji/cor derivados em `sender.py` via `_byte_tier`, heat_score 100% interno, escopo de exibição.

- [ ] **Step 4: Atualizar `EVOLUTION-PLAN.md`**

Adicionar entrada de changelog `### v2.13 — 2026-06-22 (Byte Score — Classificador de Impacto)` com a tabela de arquivos alterados e o resumo da feature. Marcar no backlog o item de "Classificacao automatica de ineditismo / score visível" como relacionado/parcialmente coberto.

- [ ] **Step 5: Commit**

```bash
git add config.yaml SKILL.md CLAUDE.md EVOLUTION-PLAN.md
git commit -m "docs(byte-score): document Byte Score classifier (v2.13)"
```

---

## Verificação final (após todas as tasks)

- [ ] `python scripts/test_byte_score.py` → `0 falha(s)`.
- [ ] `python scripts/sender.py --preview` → `grep -c "🔥" /tmp/digest_preview.html` = `0`; badges GIGABYTE/MEGABYTE/KILOBYTE/byte presentes; legenda presente.
- [ ] `open /tmp/digest_preview.html` → inspeção visual: hierarquia de cor clara, quick links com badge completo, Tool do Dia e Watch Later sem badge.

## Notas de execução

- **Worktree obrigatório se subagent-driven:** a regra do `~/Claude/CLAUDE.md` exige `isolation: "worktree"` para agentes que fazem commits em paralelo no mesmo repo. Esta é a `main` (deploy automático no push); isolar evita contaminar a branch.
- **Sem deploy acidental:** commits ficam na branch de trabalho (`feat/byte-score`); só vão a produção quando a branch for mergeada na `main`.
