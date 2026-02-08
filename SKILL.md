# 🔥 THE DAILY BYTE - Skill

## Objetivo
Gerar um digest diário de Tech & AI com **notícias quentíssimas, primeira mão e impactantes** - zero mesmice.

## Filosofia de Curadoria

### ❌ O QUE NÃO QUEREMOS
- Notícias requentadas de ontem
- Conteúdo genérico que todo mundo já viu
- "Resumos de resumos"
- Clickbait sem substância
- Previsões vagas sobre "o futuro da AI"

### ✅ O QUE QUEREMOS
- **BREAKING**: Anúncios que acabaram de sair (últimas 12-24h)
- **PRIMEIRA MÃO**: Posts direto da fonte (fundadores, CTOs, researchers)
- **IMPACTANTE**: Notícias que mudam o jogo, não incrementais
- **EXCLUSIVO**: Ângulos que outros digests não pegaram
- **ACIONÁVEL**: Informação que o leitor pode usar hoje

## Critérios de Seleção (Heat Score)

Cada notícia recebe um "Heat Score" de 0-100:

```
FRESHNESS (40 pontos)
├── Últimas 6h:  40 pts  🔥🔥🔥
├── 6-12h:       30 pts  🔥🔥
├── 12-24h:      20 pts  🔥
└── >24h:        0 pts   ❌ (não entra)

FONTE (30 pontos)
├── Primeira mão (fundador/CEO anunciando): 30 pts
├── Leak/exclusivo de jornalista confiável: 25 pts
├── Release oficial da empresa: 20 pts
├── Reportagem com fontes originais: 15 pts
└── Agregador/resumo de outros: 0 pts ❌

IMPACTO (30 pontos)
├── Lançamento de produto/modelo novo: 30 pts
├── Aquisição/funding significativo: 25 pts
├── Mudança de política/regulação: 25 pts
├── Descoberta técnica breakthrough: 30 pts
├── Polêmica/drama relevante: 20 pts
└── Update incremental: 5 pts
```

**Threshold mínimo: 60 pontos para entrar no digest**

## Fontes Prioritárias

### 🎯 Tier 1 - Primeira Mão (SEMPRE monitorar)
```
@sama, @gaborcselle, @kaborai - OpenAI
@AnthropicAI, @alexalbert__ - Anthropic
@satlonavella, @mustafa - Microsoft
@sundarpichai, @JeffDean - Google
@ylecun, @AIatMeta - Meta
@drfeifei, @AndrewYNg - Stanford AI
@karpathy - Andrej Karpathy
@EMostaque - Stability
```

### 🎯 Tier 2 - Jornalistas Tech Confiáveis
```
@kylorobrien - The Information
@ZoeSchiffer - The Verge
@alexeheath - The Verge
@raborning - Bloomberg
@MilesKruppa - WSJ
```

### 🎯 Tier 3 - Newsletters Curadas (via scraping)
```
- AiDrop (aidrop.news) - Ecossistema AI, análise profunda, PT-BR
- Evolving AI (evolvingai.io) - Modelos AI, benchmarks, EN
- Update Diário (updatediario.beehiiv.com) - Brasil/economia/política, PT-BR
- TechDrop (techdrop.news) - SaaS/enterprise/CapEx, PT-BR
- AlphaSignal (alphasignalai.beehiiv.com) - Research→produto, papers com aplicação prática, EN
- The Batch (Andrew Ng)
- Import AI (Jack Clark)
- Stratechery (Ben Thompson)
```

### Regras para Newsletters
- Janela ampliada: 36h (vs 24h de RSS)
- Cross-referência: preferir newsletter se trouxer análise > RSS bruto
- Dedup: newsletter repetindo RSS sem agregar = descartar

## Estrutura do Email

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE DAILY BYTE
News, insights & trends
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌍 MUNDO REAL (5 notícias além da bolha tech)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ [Movimentação de governo/empresa relevante]
→ [Decisão geopolítica ou econômica]
→ [Tendência do mundo real]

🔥 BREAKING (só o que é REALMENTE breaking)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Apenas 2-4 itens REALMENTE novos]

Cada item:
📰 HEADLINE IMPACTANTE
   Por que importa: contexto em 2 linhas
   🔗 [Fonte original] | ⏰ Há Xh

🤖 AI & MODELS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Updates de modelos, papers importantes, demos]

💰 SaaS & ENTERPRISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SaaS, valuations, CapEx, enterprise tech]

💼 BIG TECH MOVES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Contratações, layoffs, M&A, pivots]

🛠️ TOOL DO DIA (1 ferramenta prática)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1 tool AI/tech que o leitor pode usar hoje]

🔮 ANÁLISE DO DIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[3 bullets conectando os pontos -
qual é a narrativa maior?]

📺 WATCH LATER (1-2 vídeos essenciais)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Curated by Totó Busnello AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Invocação

```bash
# Gerar e enviar digest
/digest

# Preview sem enviar
/digest preview

# Forçar refresh das fontes
/digest --refresh
```

## Configuração

```yaml
# config.yaml
newsletter:
  name: "THE DAILY BYTE"
  api_key: "${BUTTONDOWN_API_KEY}"

schedule:
  time: "08:00"
  timezone: "America/Sao_Paulo"

filters:
  max_age_hours: 24
  min_heat_score: 60
  max_items: 20

themes:
  priority:
    - "agentic engineering"
    - "agent swarms"
    - "foundation models"
    - "AI safety"
    - "enterprise AI"
```

## Anti-Patterns a Evitar

1. **Não seja o Hacker News** - Não liste 50 links. Curadoria > Quantidade.

2. **Não seja ChatGPT wrapper** - Nada de "10 prompts incríveis" ou "AI vai mudar tudo".

3. **Não seja PR release** - Questione, contextualize, não apenas repita.

4. **Não seja atrasado** - Se já vi em 3 newsletters, não é breaking.

5. **Não seja vago** - "Grande atualização" não diz nada. Seja específico.

## Tom de Voz

- **Direto**: Sem enrolação
- **Informado**: Mostra que entende o contexto
- **Levemente provocativo**: Uma pitada de opinião
- **Confiante**: Não usa "talvez", "possivelmente" demais
- **Acionável**: O que o leitor faz com essa info?

---

*Skill criado para THE DAILY BYTE newsletter*
*Foco: Notícias quentes, primeira mão, impactantes*
