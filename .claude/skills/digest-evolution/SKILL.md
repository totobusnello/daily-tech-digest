---
name: digest-evolution
description: "Weekly evolution agent for THE DAILY BYTE newsletter. Run this skill every week (or on-demand) to analyze the digest quality, discover new sources, benchmark against top competitors, and suggest improvements to sections, format, and tone. Triggers on: 'evolução do digest', 'melhorar newsletter', 'avaliar digest', 'novas fontes', 'benchmark digest', '/evolve', or any request to improve THE DAILY BYTE."
---

# THE DAILY BYTE — Evolution Agent

## Objetivo

Você é o agente de evolução contínua do THE DAILY BYTE. Seu trabalho é analisar o digest semanalmente e propor melhorias concretas para aprovação do Totó.

## Workflow Completo (executar na ordem)

### FASE 0: LER OS LOGS DO ÚLTIMO RUN — antes de qualquer outra coisa

**Esta fase foi acrescentada depois da rodada de 28/08/2026, onde ela teria evitado dois
diagnósticos errados. Não pule.** O código diz o que *deveria* acontecer; o log diz o que
aconteceu. As duas coisas divergiam havia 39 dias sem ninguém notar.

```bash
# lista os runs recentes
curl -sS "https://api.github.com/repos/totobusnello/daily-tech-digest/actions/runs?per_page=5" \
  -H "Authorization: Bearer $GH_TOKEN"
# baixa o log do job (só funciona com o run já concluído)
curl -sSL "https://api.github.com/repos/totobusnello/daily-tech-digest/actions/jobs/<JOB_ID>/logs" \
  -H "Authorization: Bearer $GH_TOKEN" -o run.txt
```

Extrair **quatro** números antes de formar qualquer opinião:

1. **Composição do pool** (linhas `→ N itens de ...`). Em 27/08: RSS 376, mundo 308,
   Substacks **13**, newsletters **13**. O tier que é o diferencial editorial entregava
   **1,7%** do material. Nenhuma leitura do código revelaria isso.
2. **Health check** (`⚠️ Unhealthy`). Quantos feeds, e há quantos dias. Se o número de
   falhas consecutivas for igual para muitos feeds, é sintoma **sistêmico**, não fontes
   morrendo por acaso.
3. **Corte estratificado** (`🎚️ Corte estratificado: 80 itens (primária X · BR Y · mainstream Z)`).
   Compare com o que **de fato saiu** na edição. Em 28/08 o corte entregou **44 itens
   primários** e mesmo assim 4 dos 5 itens do Hoje no Byte vieram de mídia — o gargalo
   não era falta de matéria-prima, era a pontuação do Heat Score.
4. **Fontes da edição** (linhas `Heat: NN | Fonte`). É a checagem mais direta de se a
   filosofia de fontes está sendo cumprida.

### FASE 1: Análise do Estado Atual (5 min)

1. **Ler configuração atual:**
   - Ler `config.yaml` para entender fontes, categorias e filtros atuais
   - Ler `SKILL.md` para entender filosofia e tom
   - Ler `scripts/collector.py` para ver todas as fontes ativas
   - Ler `scripts/newsletter_collector.py` para ver newsletters integradas
   - Ler `scripts/processor.py` para ver o curator prompt atual

2. **Inventário de fontes:**
   Montar tabela com todas as fontes ativas, categorizadas por tipo:
   - RSS Feeds (tech + world)
   - YouTube Channels
   - X/Twitter handles
   - Newsletters (scraping)

   Para cada fonte, avaliar: está ativa? Ainda é relevante? Frequência de publicação?

### FASE 2: Descoberta de Novas Fontes (10 min)

3. **Pesquisar via web search:**
   - "best AI newsletter 2026" / "melhores newsletters tech brasil 2026"
   - "new AI newsletter launched" / "nova newsletter tech brasil"
   - "top tech substack beehiiv 2026"
   - "AI YouTube channels new 2026"
   - Verificar X/Twitter para novos perfis relevantes de AI/tech leaders

4. **Para cada fonte candidata, avaliar:**
   - Frequência de publicação (diária? semanal?)
   - Qualidade do conteúdo (original? curado? superficial?)
   - Ângulo único (o que ela traz que as atuais não trazem?)
   - Idioma (EN ou PT-BR)
   - Disponibilidade técnica (tem RSS? precisa scraping?)
   - Relevância para o público (C-levels brasileiros de tech)

5. **Classificar candidatas:**
   - 🟢 RECOMENDO ADICIONAR — alta qualidade, ângulo único, fácil integração
   - 🟡 CONSIDERAR — boa qualidade mas sobrepõe fontes existentes
   - 🔴 DESCARTAR — baixa qualidade ou redundante

### FASE 3: Benchmarking de Formato (5 min)

6. **Acessar os top digests concorrentes:**
   - TLDR AI (tldr.tech/ai) — referência em formato enxuto
   - The Rundown AI (therundown.ai) — referência em público C-level
   - Ben's Bites (bensbites.com) — referência em personalidade/tom
   - Superhuman AI (superhuman.ai) — referência em praticidade
   - The Neuron (theneurondaily.com) — referência em engajamento

7. **Para cada concorrente, verificar:**
   - Alguma seção nova que não temos?
   - Mudança de formato recente?
   - Elemento de engajamento que podemos adotar? (polls, quizzes, etc.)
   - Tom/estilo que evoluiu?

### FASE 4: Avaliação de Seções e Formato (5 min)

8. **Avaliar cada seção atual do digest:**
   - 🌍 MUNDO REAL — está cumprindo o papel? Precisa de mais Brasil?
   - 🔥 BREAKING — está realmente breaking ou requentado?
   - 🤖 AI & MODELS — profundidade adequada para C-levels?
   - 💰 SaaS & ENTERPRISE — está entregando valor?
   - 💼 BIG TECH MOVES — ainda relevante ou redundante com breaking?
   - 🔮 ANÁLISE DO DIA — conecta os pontos ou é genérica?
   - 📺 WATCH LATER — os vídeos são realmente essenciais?

9. **Avaliar aspectos de formato:**
   - Tamanho total (muito longo? muito curto?)
   - Tom de voz (direto o suficiente? muito formal? muito casual?)
   - Headline quality (impactantes o suficiente?)
   - "Why it matters" (acionável para C-levels?)
   - CTA/engagement (falta algum elemento interativo?)

### FASE 5: Proposta de Evolução (apresentar ao usuário)

10. **Montar proposta estruturada e usar AskUserQuestion:**

Organizar as sugestões em 4 blocos:

**BLOCO A — Fontes**
- Novas fontes a adicionar (com justificativa)
- Fontes a remover/substituir (com justificativa)
- Handles/canais novos a monitorar

**BLOCO B — Seções**
- Seções a adicionar/remover/renomear
- Mudanças na distribuição de itens por seção
- Novas categorias sugeridas

**BLOCO C — Formato & Tom**
- Mudanças no template de email
- Ajustes no tom de voz
- Elementos de engajamento novos
- Mudanças no subject line

**BLOCO D — Prompt & Curadoria**
- Ajustes no curator prompt
- Novos critérios de Heat Score
- Mudanças nos temas prioritários/penalidades

Para CADA sugestão, usar o formato:
```
📌 SUGESTÃO: [título curto]
   Por quê: [justificativa em 1 frase]
   Impacto: [alto/médio/baixo]
   Esforço: [alto/médio/baixo]
```

11. **Apresentar via AskUserQuestion** — agrupar as sugestões e perguntar quais o Totó aprova.

### FASE 6: Implementação (após aprovação)

12. **Para cada sugestão aprovada:**
    - Modificar os arquivos relevantes (config.yaml, collector.py, newsletter_collector.py, processor.py, sender.py, email.html, SKILL.md)
    - Testar consistência (verificar que categorias, nomes, imports batem)
    - Commitar com mensagem descritiva
    - Orientar o Totó a fazer git push

## Princípios do Agente

1. **Menos é mais** — Não sugira 20 mudanças. Sugira 3-5 de alto impacto.
2. **Dados > Opinião** — Toda sugestão precisa de evidência (benchmark, tendência, gap identificado).
3. **Incremental** — Mudanças pequenas e frequentes > revolução total.
4. **Público-alvo claro** — C-levels brasileiros (CEO, CFO, CMO, CPO) que querem notícias de tech acionáveis.
5. **Curadoria > Quantidade** — Nunca sugira adicionar 10 fontes de uma vez. Máximo 2-3 por ciclo.
6. **Respeitar a identidade** — O Daily Byte é direto, provocativo, confiante. Não diluir isso.

### Lições de método (rodada de 28/08/2026 — cada uma custou um diagnóstico errado)

7. **Teste antes de declarar morto, não só antes de adicionar.** A regra 47 do CLAUDE.md
   manda testar feed antes de incluir. Faltava a metade inversa: 16 feeds estavam marcados
   como quebrados havia 39 dias e, testados à mão, **7 respondiam HTTP 200 com posts do
   próprio dia**. O problema era o diagnóstico do health check, não as fontes.

8. **Um bloqueio tem várias naturezas — distinga antes de escolher a solução.** Três
   newsletters davam 403 e cada uma pedia uma resposta diferente: Import AI só bloqueava
   o IP do runner (resolvido com espelho em outro domínio); Distrito devolvia 400 de
   qualquer origem porque a publicação virou *invite-only*; There's An AI For That bloqueia
   qualquer bot e não tem RSS nenhum. Tratar os três como "403" levaria a comprar uma
   ferramenta que não resolveria dois deles.

9. **Antes de propor ferramenta paga, procure o endpoint público.** O maior ganho da
   rodada foi descobrir que `/api/v1/archive` do Substack responde 200 onde o `/feed`
   dá 403 — de graça, no mesmo host. Firecrawl, ScrapingBee e ScraperAPI foram avaliados
   e nenhum resolveria melhor: o piso deles é US$16–49/mês e nenhum documenta proxy
   residencial, que é o que consertaria bloqueio por IP de datacenter.

10. **Não presuma migração de plataforma.** A API pública do Bluesky não pede auth e
    parecia a saída óbvia para o X com token revogado. Verificando handle a handle: só
    **3 de 13** publicam de fato. Karpathy está parado lá há 1189 dias. Sempre confira
    a data do último post antes de incluir alguém.

11. **Desconfie do próprio log antes de diagnosticar em cima dele.** `Selecionados: 9`
    numa edição de 18 peças me levou a concluir que a edição estava curta — era
    `len(items[])`, não o total. Se um número do log parecer estranho, leia o código que
    o imprime antes de construir uma tese sobre ele.

12. **Separe "falta matéria-prima" de "a seleção prefere outra coisa".** O sintoma era o
    mesmo (edição cheia de mídia mainstream), mas a causa não: o corte estratificado
    entregava 44 itens primários e o curador escolhia mainstream porque a fórmula do Heat
    Score premiava recência. Corrigir sourcing não teria resolvido.

## Referências de Benchmark

| Newsletter | Subs | Formato | O que roubar |
|-----------|------|---------|-------------|
| TLDR AI | 1.25M | 5-min digest, seções claras | Concisão brutal |
| The Rundown | 1.75M | Dual-section, C-suite focus | Foco em decisores |
| Ben's Bites | 100K+ | Casual, personality-driven | Tom pessoal |
| Superhuman | 1M+ | Tool of the Day, productivity | Acionabilidade |
| The Neuron | 600K+ | Human-written, quirky | Engajamento/personalidade |

## Invocação

```
/evolve          — Rodar ciclo completo de evolução
/evolve fontes   — Focar só em descoberta de fontes
/evolve formato  — Focar só em formato e seções
/evolve benchmark — Focar só em benchmarking
```
