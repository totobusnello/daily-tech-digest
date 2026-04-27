# THE DAILY BYTE - Skill

## Objetivo
Gerar um digest diário de Tech & AI com **notícias quentíssimas, primeira mão e impactantes** - zero mesmice.

## Filosofia de Curadoria

### O QUE NAO QUEREMOS
- Notícias requentadas de ontem
- Conteúdo genérico que todo mundo já viu
- "Resumos de resumos"
- Clickbait sem substância
- Previsões vagas sobre "o futuro da AI"

### O QUE QUEREMOS
- **BREAKING**: Anúncios que acabaram de sair (últimas 12-24h)
- **PRIMEIRA MAO**: Posts direto da fonte (fundadores, CTOs, researchers)
- **IMPACTANTE**: Notícias que mudam o jogo, não incrementais
- **EXCLUSIVO**: Angulos que outros digests não pegaram
- **ACIONAVEL**: Informação que o leitor pode usar hoje

## Critérios de Seleção (Heat Score)

Cada notícia recebe um "Heat Score" de 0-100:

```
FRESHNESS (40 pontos)
├── Últimas 6h:  40 pts
├── 6-12h:       30 pts
├── 12-24h:      20 pts
└── >24h:        0 pts (não entra)

FONTE (30 pontos)
├── Primeira mão (fundador/CEO anunciando): 30 pts
├── Leak/exclusivo de jornalista confiável: 25 pts
├── Release oficial da empresa: 20 pts
├── Newsletter curada com insight: 15 pts
└── Agregador/resumo de outros: 0 pts

IMPACTO (30 pontos)
├── Lançamento de produto/modelo novo: 30 pts
├── Aquisição/funding significativo: 25 pts
├── Mudança de política/regulação: 25 pts
├── Descoberta técnica breakthrough: 30 pts
├── Polêmica/drama relevante: 20 pts
└── Update incremental: 5 pts

NEWSLETTER BONUS:
├── Insight exclusivo: +10 pts
└── Cross-validação (mesmo fato em 2+ fontes): +5 pts
```

**Threshold mínimo: 60 pontos para entrar no digest**

## Fontes (~160 ativas)

### Tier 1 — Primeira Mao (51 X/Twitter handles)
AI Labs, fundadores, researchers, VCs, geopolítica, markets, crypto.
Ver `config.yaml` e `collector.py` para lista completa.

### Tier 2 — RSS Feeds (60 feeds)
**Tech/AI (30):** HN, Ars Technica, Wired, The Verge, TechCrunch AI, MIT Tech Review, The Decoder, VentureBeat, blogs oficiais (OpenAI, Anthropic, Google AI, HuggingFace), The Information, etc.
**World/Business (30):** Reuters, Forbes, BBC, CNBC, WSJ, NYT DealBook, Bloomberg, FT, Economist, AP News, Poder360, InfoMoney, Valor Economico, Startups.com.br, etc.

### Tier 3 — Newsletters (9 scrapers via scraping + RSS)
| Newsletter | Foco | Idioma |
|-----------|------|--------|
| AiDrop | AI, análise profunda | PT-BR |
| Evolving AI | Modelos, benchmarks | EN |
| Update Diário | Brasil, economia | PT-BR |
| TechDrop | SaaS, enterprise, CapEx | PT-BR |
| AlphaSignal | Research -> produto | EN |
| There's An AI For That | AI tools (2.8M subs) | EN |
| Turing Post | AI strategy, geopolítica | EN |
| Import AI | AI policy, research (Jack Clark) | EN |
| Distrito News Inside VC | VC/startups Brasil | PT-BR |

### Substacks Curados (31 feeds via RSS)
AI engineering (Latent Space), macro strategy (State of AI), business, fintech, biotech, AI prático. Ver `config.yaml`.

### YouTube (9 canais)
Fireship, Two Minute Papers, AI Explained, Matt Wolfe, Lex Fridman, Karpathy, AI Daily Brief, Filipe Deschamps, The AI Grid.

### Regras para Newsletters
- Janela ampliada: 36h (vs 24h de RSS)
- Cross-referência: preferir newsletter se trouxer análise > RSS bruto
- Dedup: newsletter repetindo RSS sem agregar = descartar

## Estrutura do Email (Layout v2.2 + Engagement v2.6)

```
THE DAILY BYTE                    Leitura: 3 min
News, insights & trends
[Data]

📊 NUMERO DO DIA
[Data point impactante — value + context]

🌍 MUNDO REAL (3 notícias — mundo + Brasil)
→ [Geopolítica, economia, regulação]

🔥 HOJE NO BYTE (4-5 itens com tags)
[BREAKING] Headline + análise (1-2 frases)
[AI] Headline + análise
[BIG TECH] Headline + análise
[ENTERPRISE] Headline + análise

💰 SaaS & ENTERPRISE (2 itens)

🛠️ TOOL DO DIA + 💡 COMO USAR HOJE + 🧠 PROMPT DO DIA
[1 ferramenta + prompt copy-paste ready]

🔮 ANÁLISE DO DIA
[3 bullets conectando os pontos]

⚡ QUICK LINKS (5-6 links rápidos)
→ Headline + link (sem análise)

📺 WATCH LATER (1 vídeo essencial)

👍 Esta edição foi útil? [Sim] [Mais ou menos] [Não]
📨 Encaminhe para um colega

Curated by Totó Busnello AI
```

**Total máximo:** 18 itens (12 principais + 6 quick links)

## Como Rodar

```bash
cd ~/daily-tech-digest/scripts

# Pipeline completo (preview)
python run.py --preview

# Pipeline completo (envio real)
python run.py

# Flags úteis
python run.py --skip-collect   # Pula coleta, usa /tmp/digest_raw.json existente
python run.py --skip-process   # Pula curadoria, usa /tmp/digest_curated.json existente
```

**Schedule:** Diário às 06:00 BRT via GitHub Actions.

## Anti-Patterns a Evitar

1. **Não seja o Hacker News** - Não liste 50 links. Curadoria > Quantidade.
2. **Não seja ChatGPT wrapper** - Nada de "10 prompts incríveis" ou "AI vai mudar tudo".
3. **Não seja PR release** - Questione, contextualize, não apenas repita.
4. **Não seja atrasado** - Se já vi em 3 newsletters, não é breaking.
5. **Não seja vago** - "Grande atualização" não diz nada. Seja específico.
6. **Não repita o subject** - Subject hooks devem variar entre dias (dedup via feedback.py).

## Tom de Voz

- **Direto**: Sem enrolação
- **Informado**: Mostra que entende o contexto
- **Levemente provocativo**: Uma pitada de opinião
- **Confiante**: Não usa "talvez", "possivelmente" demais
- **Acionável**: O que o leitor faz com essa info?

---

*THE DAILY BYTE v2.6 — Tech & AI para C-levels brasileiros*
