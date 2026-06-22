# Byte Score — Classificador de Impacto Estratégico

**Data:** 2026-06-22
**Status:** Design aprovado (aguardando review final)
**Versão alvo:** v2.13
**Autor:** Totó Busnello + brainstorm com Claude

---

## Problema

O Daily Byte já calcula um `heat_score` (0-100) por item e o exibe como emoji de fogo 🔥. Mas isso é genérico — *todo* digest de IA tem um indicador de "quão quente". Não tem a cara do produto e não responde à pergunta que um C-level realmente faz: **quão grande é o tremor estratégico desta notícia?**

Queremos um classificador proprietário, lúdico e on-brand que vire assinatura visual do Daily Byte.

## O que já existe (não reinventar)

- `heat_score` (0-100): calculado pelo curador, usado pra decidir o que entra (corte mínimo 60). Hoje também é renderizado como 🔥 no `sender.py` (`_heat_bar`, `heat_emoji`).
- `tag` por item: BREAKING / AI / BIG TECH / ENTERPRISE (badge laranja).
- `_cluster_size`: quantas fontes cobriram a história (ineditismo).
- `trending_score`: velocity por engajamento.

## Decisões de design

| Tema | Decisão |
|------|---------|
| **Eixo** | Impacto estratégico — *quanto a notícia move o jogo*, distinto do Heat (seleção) |
| **Forma** | Número `Byte Score` 0.0–10.0 + tier nomeado em unidades de dados |
| **Escala** | GIGABYTE > MEGABYTE > KILOBYTE > byte |
| **Emojis** | 📦 GIGA · 💿 MEGA · 💾 KILO · 📄 byte (+ cor por tier) |
| **Fogo 🔥** | Aposentado. Heat Score vira 100% interno (seleção/log), nunca renderizado |
| **Exibição** | Em **todo item noticioso** |
| **Calibração** | Juízo do Claude, **ancorado** (regra anti-inflação + few-shot) |
| **Tier** | Derivado no código a partir do número (não enviado pelo Claude) |

---

## Especificação

### 1. Conceito

**Byte Score = magnitude de impacto estratégico.** Independe de já ter passado no corte de seleção. Uma ferramenta excelente, mas incremental, é um KILOBYTE honesto; um novo paradigma de modelo é GIGABYTE.

**Byte Score ≠ Heat Score.** Heat decide *se entra* (freshness + fonte + impacto, corte 60). Byte Score mede *o tamanho do tremor* e é o único exposto ao leitor. Reusar o heat inflaria tudo (todo item publicado já tem heat ≥ 60).

### 2. Escala e faixas

| Byte Score | Tier | Emoji | Significa |
|------------|------|-------|-----------|
| 9.0 – 10.0 | GIGABYTE | 📦 | Redefine o mercado / novo paradigma |
| 7.0 – 8.9  | MEGABYTE | 💿 | Grande player muda o jogo |
| 5.0 – 6.9  | KILOBYTE | 💾 | Relevante, incremental |
| 0.0 – 4.9  | byte     | 📄 | Nota de rodapé |

### 3. Cores do badge (magnitude pela cor)

| Tier | Fundo | Texto |
|------|-------|-------|
| GIGABYTE | `#FF6B35` (laranja-brand) | `#FFFFFF` |
| MEGABYTE | `#F7A072` (âmbar) | `#1a1a2e` |
| KILOBYTE | `#6B7280` (cinza-azul) | `#FFFFFF` |
| byte | `#E5E7EB` (cinza claro) | `#6B7280` |

A cor carrega a magnitude (quente → neutro → apagado); o emoji dá a textura de "dados".

### 4. Escopo (onde aparece)

✅ **Com Byte Score:** `world[]` · `items[]` com category `hoje_no_byte` e `saas_enterprise` · `radar_brasil[]` · `quick_links[]`

❌ **Sem Byte Score:** `tool_of_day` · `watch_later` · `number_of_day` (utilidade/indicador, não impacto noticioso)

### 5. Calibração ancorada (anti-inflação)

O Claude atribui o número por julgamento, mas o `CURATOR_SYSTEM` recebe:

**Regra de raridade:**
> GIGABYTE é raro: a maioria das edições NÃO tem um. Reserve para a notícia que você apostaria ser lembrada daqui a 6 meses. Se nada redefiniu o mercado hoje, o teto da edição é MEGABYTE. Numa edição típica, espere ~0 GIGABYTE, 1-2 MEGABYTE, várias KILOBYTE e bytes nos quick links. Resista a inflar.

**Exemplos-âncora (few-shot), 2 por tier:**
- **GIGABYTE (9-10):** "Lab lança modelo que supera humanos em raciocínio geral" · "Regulação que redefine modelos fechados entra em vigor na UE"
- **MEGABYTE (7-8.9):** "Anthropic corta preço enterprise em 50%" · "Google embute Gemini nativo no Android para bilhões de devices"
- **KILOBYTE (5-6.9):** "SaaS conhecido adiciona feature de agentes" · "Novo benchmark mostra modelo 5% acima do anterior"
- **byte (0-4.9):** "Funding seed de US$2M para startup de nicho" · "Update de UI numa ferramenta popular"

### 6. Modelo de dados

- O curador retorna `byte_score` (float, 1 casa decimal, 0.0–10.0) em cada item dos arrays em escopo.
- O **tier, emoji e cor são derivados no código** (`sender.py`) a partir do número. O Claude nunca envia o tier — garante que número e rótulo jamais divirjam.
- `heat_score` permanece no schema para seleção/log interno; deixa de ser renderizado.

### 7. Renderização

- **Todo item (HTML), inclusive Quick Links:** badge completo (número + emoji + palavra) antes do headline → `[ 9.2 📦 GIGABYTE ]  {headline}`. Sem exceção — a classificação é igual em toda a edição.
- **Preview markdown:** `9.2 📦 GIGABYTE — {headline}`
- **Legenda no rodapé:** uma linha explicando a escala (📦 GIGABYTE = redefine o mercado · 💿 MEGABYTE = muda o jogo · 💾 KILOBYTE = relevante · 📄 byte = nota de rodapé), pra o leitor entender o selo na primeira edição.
- Função única `_byte_badge(score) -> (tier, emoji, bg, fg)` centraliza a derivação.

---

## Mudanças por arquivo

| Arquivo | Mudança |
|---------|---------|
| `scripts/processor.py` | Bloco "BYTE SCORE" no `CURATOR_SYSTEM` (conceito + faixas + regra anti-inflação + few-shot). JSON schema: `byte_score` (float) nos itens em escopo. `heat_score` permanece no schema (seleção interna). |
| `scripts/sender.py` | Nova `_byte_badge(score)`. Renderizar badge nos itens em escopo (HTML + markdown), incluindo versão curta nos quick links. Remover `_heat_bar` / `heat_emoji` da renderização. |
| `config.yaml` | Header v2.13. Documentar Byte Score nos comentários de curadoria. |
| `SKILL.md` | Seção do Byte Score (escala, faixas, escopo). |
| `CLAUDE.md` | Regra nova documentando o classificador. Bump v2.13. |
| `EVOLUTION-PLAN.md` | Changelog v2.13. |

## Compatibilidade

- Item sem `byte_score` → renderiza sem badge (não quebra). Backward-compatible.
- `heat_score` continua existindo internamente; nenhuma lógica de seleção muda.

## Fora de escopo (YAGNI)

- Índice agregado "O Byte do Dia" no topo (magnitude da edição inteira) — evolução futura.
- Versão em áudio do digest.
- Byte Score em Tool do Dia / Watch Later.

## Critérios de sucesso

1. Todo item noticioso renderiza badge com número + emoji + tier coerentes (derivação correta das faixas).
2. Distribuição realista ao longo de uma semana — não "tudo GIGABYTE". Verificável nos previews.
3. Fogo 🔥 removido da renderização; Heat Score só interno.
4. Nenhuma quebra com itens legados sem `byte_score`.
