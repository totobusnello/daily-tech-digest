# THE DAILY BYTE — Plano de Evolução

---

## Changelog

### v2.17b — 2026-08-28 (destrava o tier indie e abre a camada primária)

Continuação direta da v2.17. A pergunta que originou: "que ferramenta incorporar para
aumentar o número de fontes diferentes e frescas?" A resposta acabou sendo **nenhuma
ferramenta paga** — o que faltava era usar endpoints públicos que já existiam.

**O achado principal: a API de arquivo do Substack.**

O `/feed` do Substack é bloqueado para automação, mas `/api/v1/archive` **no mesmo host**
responde 200 com JSON. Testado nos feeds que estavam mudos há 39 dias:

| Feed | Antes | Pela API de arquivo |
|---|---|---|
| doomberg | 0 itens | ✅ post de 28/08 |
| thezvi | 0 itens | ✅ post de 27/08 |
| capital_wars | 0 itens | ✅ post de 26/08 |
| import_ai | 403 | ✅ post de 24/08 |

Custo zero, sem chave, ~40 linhas. `_fetch_feed()` tenta esse caminho antes para hosts
`*.substack.com` e cai no `/feed` se falhar. **31 feeds do catálogo estão nesse domínio.**

**Camada primária nova** (tudo grátis, sem auth):
- `collect_hf_daily_papers()` — curadoria **humana** votada por praticantes, filtro de
  upvotes ≥ 3. O arXiv despeja centenas de papers/dia sem hierarquia; aqui o sinal de
  relevância vem de quem trabalha com o assunto.
- arXiv `cs.CL` e `cs.LG` — só `cs.AI` deixava de fora justamente onde sai o trabalho de LLM.
- GitHub releases `.atom` de 6 repos de infra AI — quando o vLLM lança versão aparece ali
  antes de qualquer veículo. ⚠️ Não verificados do sandbox; conferir no primeiro run.

**Bluesky: a migração do X não aconteceu.** A API pública não pede auth, o que resolveria o
token revogado do X. Mas verificando handle a handle, **só 3 publicam de fato**: Simon
Willison (hoje), Ethan Mollick (hoje), David Ha (1d). Karpathy está parado há 1189 dias,
levelsio 638, danshipper 618, swyx 164. Sem conta: benedictevans, chipro, natfriedman,
jack-clark. Handle inválido: ylecun. Entraram os 3 — não a lista inteira.

**Ferramentas pagas avaliadas e descartadas** (preços verificados em 28/08): Firecrawl não
documenta proxy residencial, que é o que consertaria bloqueio por IP de datacenter (free
1.000 créditos, depois US$16/mês); ScrapingBee e ScraperAPI pedem US$49/mês de piso para
~1.500 fetches. O caso principal se resolve de graça. Jina Reader foi reportado como
solução para o TAAFT mas **não consegui reproduzir** — deu 403 no meu teste; registrado
como não-confirmado em vez de adotado.

**Distrito:** a URL antiga devolvia 400 com o corpo dizendo `This publication is
invite-only` — a publicação foi fechada, não morreu. Conteúdo público migrou para
`distrito.substack.com`. Cadência mensal, então o feed fica vazio ~29 dias em 30.

**Fica para depois:** IMAP próprio para newsletters que bloqueiam scraping mas entregam
email (caso do There's An AI For That, que não tem RSS — beehiiv com feed desativado).
Exige criar conta e assinar manualmente, então não cabia nesta rodada.

**Catálogo: 154 → 162 feeds** + HF Daily Papers + 3 handles de Bluesky.

---

### v2.17 — 2026-08-28 (recalibra curadoria, conserta observabilidade, +5 fontes, 3 melhorias de formato)

**Gatilho:** a edição de 28/08 saiu com subject quebrado e pauta fraca. Investigando os
logs dos runs de 27 e 28/08, os dois sintomas tinham raízes diferentes — e uma delas
estava escondida havia 39 dias.

**O que os dados mostraram (edição de 27/08, 757 itens coletados):**

| Origem | Itens | % |
|---|---|---|
| RSS tech/AI | 376 | 50% |
| Mundo (mainstream) | 308 | 41% |
| Substacks (indie/builder) | 13 | 1,7% |
| Newsletters curadas | 13 | 1,7% |

O tier que é o diferencial editorial do produto entregava 3,4% do pool. E na edição de
28/08, **4 dos 5 itens do Hoje no Byte vieram de mídia tech** — apesar de o corte
estratificado ter entregue **44 itens primários** ao curador. A matéria-prima estava lá;
a pontuação é que preferia mainstream.

| Arquivo | O que mudou |
|---------|------------|
| `scripts/processor.py` | **Heat Score recalibrado**: freshness 40→25, ineditismo +15→+25 (community/indie +10→+18). **subject_hook** 6→5-9 palavras com exigência de frase gramatical + regra de nomes próprios em PT-BR. **Teste de consequência** no Mundo Real (descarta trivia). **`details[]`** no schema da Big Story. **Log da curadoria** agrupa por categoria real e conta o digest inteiro. |
| `scripts/health_check.py` | `_check_feed()` passa a reportar o erro real (status HTTP, timeout, TLS, DNS, HTML-com-200) em vez de colapsar tudo em `"No entries returned"`. Abre GitHub Issue na **virada** do limiar. |
| `scripts/newsletter_collector.py` | Novo `rss_fallbacks` (espelho em outro domínio). Import AI ganha `jack-clark.net`. Distrito News e TAAFT anotados com estado verificado. |
| `scripts/collector.py` | +5 fontes verificadas: `nucleo_jor`, `embrace_the_red`, `cio_dive`, `cfo_dive`, `sub_chinatalk`. Catálogo vai a **154**. |
| `scripts/sender.py` | Big Story renderiza `details[]`. **PROMPT DO DIA** vira seção própria. **Tempo de leitura por item** derivado no código. |
| `.github/workflows/daily-digest.yml` | Cron sai do slot `:00` para `23 8 * * *` — ver seção abaixo. |

**Os 16 feeds mudos há 39 dias.** O health check os marcava como quebrados com a mensagem
`"No entries returned"`. Testados à mão, 7 deles respondiam **HTTP 200 com 20-32 entries e
posts do próprio dia** — Doomberg, Zvi, Capital Wars, State of AI, Beautiful Mess. Estavam
vivos. A causa era `_check_feed()` engolir toda exceção num `except: pass` e cair num return
genérico: timeout, 403, DNS e feed-vazio viravam a mesma string. O sinal existia, mas não
distinguia "o site nos bloqueou" de "o autor não publicou" — e por isso ninguém podia agir.

**As 3 newsletters em 403 têm naturezas diferentes** (verificado em 28/08):
- **Import AI** — 200 aqui, 403 no runner. Bloqueio por IP de datacenter. Resolvido com espelho.
- **Distrito News** — **400 de qualquer origem**. URL provavelmente morta, sem espelho conhecido.
- **There's An AI For That** — **403 para qualquer bot**, não é o runner. Sem rota de RSS.

Os dois últimos ficaram anotados no código aguardando decisão editorial, em vez de continuarem
quebrando em silêncio.

**Fontes rejeitadas nesta rodada** (pesquisadas e testadas): SVPG (403 Cloudflare + ~1-2/mês),
The News/Waffle (mainstream generalista com celebridades), Digg (sem RSS), Prompt Engineering
Daily (posta ~1x/ano apesar do nome), Fabricated Knowledge e Hyperdimensional (inativos há
>30 dias), MIT Tech Review Brasil (conteúdo traduzido = redundante).

**Correção de leitura durante a análise:** o log dizia `"Selecionados: 9"` numa edição de 18
peças, o que me levou a diagnosticar edição curta onde não havia. Era `len(items[])`, não o
total. O contador e o agrupamento do log foram corrigidos junto.

**Testes:** `scripts/test_byte_score.py` passa inteiro.

---

### Cron: por que a edição de 28/08 não saiu sozinha

O evento agendado **não foi enfileirado nem executado — foi descartado pelo GitHub**. Não é
falha de código: o workflow estava `active`, o cron sintaticamente correto, e todos os runs
anteriores tiveram sucesso.

| Período | Atraso vs 06:00 UTC |
|---|---|
| Ago 8–26 | 26–42 min (normal) |
| Ago 27 | **11h12m** |
| Ago 28 | **descartado** |

O cron estava em `0 6 * * *` — minuto `:00`, o slot mais congestionado do GH Actions. Quando a
fila dos runners compartilhados satura, eventos agendados são descartados silenciosamente.
Novo cron: `23 8 * * *` (08:23 UTC / 05:23 BRT) — minuto ímpar sai da contenção e, com o atraso
típico de ~30-40 min, a entrega cai **~06:00 BRT**, mais perto do horário de leitura real que os
~03:30 BRT anteriores. O YAML carrega o comentário explicando, para ninguém devolver ao `:00`.

---


### v2.16b — 2026-07-20 (Expansão do catálogo — 105 → 149 feeds)

**Contexto:** logo após a limpeza, ficou claro que 35 feeds líquidos a menos deixavam o corte estratificado sem alternativa — a quota BR era 12 e só havia 9 fontes brasileiras. A pergunta virou "como aumentar a base *utilizável*".

**A medição que mudou o critério.** Antes de adicionar qualquer coisa, medi a cadência real de cada feed (posts nos últimos 30 dias):

| Tier | Feeds | Publicam diariamente | Publicaram na janela de 36h |
|---|---|---|---|
| Mainstream | 24 | **21** | 22/24 (92%) |
| Primária | 72 | 15 | 40/72 (56%) |
| Brasil | **9** | 4 | 8/9 (89%) |

Conclusão: **mainstream não domina por privilégio, domina por cadência.** Um Substack semanal não cai na janela de 36h na maioria dos dias — adicionar mais um quase não move o ponteiro. O critério de seleção passou a ser cadência medida, não reputação da fonte.

**Onde as fontes foram buscadas — e o que rendeu:**

| Frente | Resultado |
|---|---|
| Planilha `Master Sources` (2.165 linhas) | **Rendeu pouco.** 1.994 são bench nunca implementado; **zero domínios `.br`**. Dos 1.262 domínios testáveis, 741 tinham feed vivo, mas só ~14 no nosso escopo — o resto é health tech UK, construction, solar, cripto de varejo. |
| 201 canais de YouTube da planilha | **Rendeu nada.** 121 resolvidos, 71 ativos, **2 relevantes** — e nenhum serve. Os "ativos" são Cruise Hive, Don's Family Vacations, Cleveland Clinic, BiggerPockets. |
| Pesquisa dirigida BR | **12 fontes**, todas com cadência medida. |
| Pesquisa dirigida primária | **18 fontes** (blogs de eng AI-first, changelogs, análise). |

**Resultado:**

| Tier | Feeds (antes → depois) | Alta cadência (≥15/30d) |
|---|---|---|
| Primária | 72 → **104** | 15 → **40** |
| Brasil | 9 → **21** | — → **10** |
| Mainstream | 24 → 24 | 21 |
| **Total** | 105 → **149** | 0 quebrados |

O desequilíbrio estrutural inverteu: antes o mainstream tinha mais fontes diárias (21) que toda a camada primária (15); agora são 40 contra 21.

**Efeito na edição (1 rodada):** mainstream caiu para **41%** — abaixo do baseline de 58% e fora da faixa 59-72% observada nas rodadas pós-limpeza. Radar Brasil preenchido. Pool coletado: 306 (v2.15.1) → 484 (v2.16) → **669** itens.
⚠️ *É uma rodada só.* A variância entre rodadas do mesmo dia chegou a 13 pontos antes — o próximo ciclo deve confirmar com vários dias.

**Decisões editoriais registradas:**
- **TLDR AI e The Rundown AI ficaram de fora** apesar de RSS ativo e cadência diária: republicar a curadoria de concorrente contradiz a premissa do produto, e quem assina os dois percebe. **Ben's Bites entrou** por ser comentário autoral, não digest.
- Descartadas por fugirem do escopo: Consumidor Moderno (CX/marketing), Projeto Draft (impacto social), Money Times (mistura política), 6 feeds redundantes de segurança, 4 de health tech UK.

**Bugs encontrados no caminho:**
- **O canal cadastrado como Karpathy era do Siraj Raval** — e ele saiu como fonte na edição 182. ID correto confirmado via oEmbed oficial; scraping da página do canal devolve `channelId` de recomendados (retornou 3Blue1Brown para `@AndrejKarpathy`).
- **Adicionei 12 fontes BR e o contador continuou em 9** — `_BR_HINTS` não foi atualizado, então `_source_tier` as classificava como primária e elas não contavam na quota de Brasil.
- Blogs de engenharia dos unicórnios BR (iFood, QuintoAndar, Loft, Stone, PicPay, Mercado Livre) estão **todos parados no Medium desde 2021-2023**; só o Nubank sobreviveu. Nenhum VC brasileiro mantém RSS ativo.

---

### v2.16 — 2026-07-20 (Auditoria do catálogo — 41% dos feeds estavam mortos)

**Contexto:** a revisão semanal começou como "vamos evoluir" e virou "tem coisa quebrada". Testando os 140 feeds ao vivo, um a um, a auditoria encontrou **57 mortos (41%)** e três bugs que rodavam em silêncio havia meses. Nenhum deles aparecia no monitoramento — porque o monitoramento também estava quebrado.

**O diagnóstico (medido, não estimado):**

| Lista | Total | Quebrados | Abandonados | % morto |
|---|---|---|---|---|
| RSS tech/AI | 46 | 14 | 1 | 33% |
| World/business | 37 | 12 | 1 | 35% |
| Substacks | 46 | 11 | 12 | **50%** |
| YouTube | 11 | 5 | 1 | **55%** |
| X/Twitter | 66 handles | — | — | **coletava 0** |

Casos que doem: `sub_karpathy` parado há **1199 dias** e `sub_ai_news_swyx` há **451** — ambos adicionados na v2.14 como "alta qualidade", nunca testados. SemiAnalysis (306d), Chip Huyen (550d), Anthropic, Mistral, Stability, Meta AI, Reuters (×3), Valor, Exame, Pipeline Valor, Startse, TecMundo: todos 404/401/403.

**Causa-raiz do mainstream dominar.** Não era preferência do curador — era aritmética. O pool chegava com 51% de mainstream porque 27 das 35 fontes indie declaradas retornavam zero, e o corte final (`slim_items[:80]`) era por **puro frescor**, o que premia quem publica de hora em hora. Nas 7 edições auditadas: Bloomberg 17×, FT 13×, contra Simon Willison 3×.

**Mudanças por arquivo:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | **CATÁLOGO** 140 → 105 feeds, todos testados (0 quebrados, 99% com post ≤60d). URLs corrigidas: Mistral, SemiAnalysis, AI News (→`news.smol.ai`), Meta (→`engineering.fb.com`), Anthropic (mirror comunitário), Valor (`/rss/valor/`), Exame, TecMundo, FT, + 5 channel IDs do YouTube. **+4 fontes novas** verificadas: Geopolitechs (geopolítica de AI), AI to ROI (ROI enterprise), AI Factory News/Distrito (PT-BR), The AI Engineer (agentic coding). **X**: 66 → 16 handles + cache de `user_id` + log explícito por status code. |
| `scripts/processor.py` | **CORTE ESTRATIFICADO** — `_stratified_cut()` reserva quota por tier (primária 32 / BR 12 / mainstream ≤24) antes de completar por frescor; teto suave que cede se não houver alternativa. **FILTRO BR** — `_br_item_relevante()` descarta esporte/política/variedades dos feeds BR generalistas (as editorias de tech deles retornam 400/404). **BYTE SCORE** — 4 testes objetivos para liberar 9-10. **RADAR BRASIL** — prompt passa a alocar notícia BR no Radar, não em `world`. **ORTOGRAFIA** — acento em nomes próprios + lista de PT-europeu proibido. |
| `scripts/feedback.py` | **MÉTRICA FALSA** — `recipients: 0` da API zerava as taxas e o hint mandava "Open rate baixo (0%), revise o horário" todo dia, quando o real era ~70%. Agora usa `subscriber_count` como fallback, marca `rates_estimated`, e omite o conselho quando não há denominador confiável. |
| `scripts/sender.py` | `_strip_leading_fire()` — fim do `🔥 🔥 🔥 TSMC investe`. |
| `scripts/test_byte_score.py` | **REESCRITO** — o suite estava quebrado desde a v2.14 (referenciava funções removidas) e nada o executava. 64 casos cobrindo Byte Score, `_safe_url`, strip de emoji, classificação de fonte, filtro BR e corte estratificado. |
| `.github/workflows/daily-digest.yml` | **HEALTH CHECK CEGO** — `digest_feed_health.json` não estava no `actions/cache`, então o contador de falhas reiniciava a cada run e o alerta (threshold 3) nunca disparava. Adicionado restore+save. **+ step de testes** obrigatório. |
| `config.yaml`, `CLAUDE.md` | v2.16, regras 47-54, bloco `stratified_cut`. |

**Resultado medido:**
- Catálogo: 57 feeds mortos → **0** (105 feeds, 99% saudáveis)
- Pool que chega ao curador: mainstream 51% → **30%** (teto), primária 36, BR 20
- Volume coletado: 306 → **484 itens** (+58%); Substacks 4 → 12, YouTube 2 → 10
- Filtro BR: **16 itens/dia** de esporte e variedades deixam de ocupar a quota
- Testes: **64/64** passando, rodando no CI

**O que NÃO melhorou — e é honesto registrar:** a composição da *edição final* segue em ~60% mainstream (baseline 58%), mesmo com o pool a 30%. Em 5 rodadas do mesmo dia o número oscilou entre 59% e 72%, e o Byte Score chegou a 9 em apenas uma delas. Ou seja: o curador continua escolhendo grande imprensa mesmo com alternativa farta na mesa — seja porque as notícias do dia eram genuinamente essas (Trump/tarifas, Paramount-Warner, Oracle), seja porque o prompt ainda não pesa ineditismo o bastante na hora de montar as seções. **Próximo ciclo deve medir isso com mais dias antes de mexer no prompt de novo.**

**~~Pendente de ação do Totó~~ — RESOLVIDO em 20/07 à noite:** token renovado e gravado via `printf '%s' '<token>' | gh secret set X_BEARER_TOKEN`. A primeira tentativa (`gh secret set` sem `--body`) não abriu prompt interativo, leu stdin vazio e gravou um secret em branco — o sintoma foi `X_BEARER_TOKEN not set` no log apesar do timestamp atualizado. Validação `29790766326`: **30 tweets** de 5 handles (@levelsio 10, @GergelyOrosz 10, @ylecun 8, @sama 1, @AnthropicAI 1). Os outros 11 simplesmente não postaram na janela de 24h.

O mesmo run confirmou o feedback loop: **open rate 72,1%** onde antes o prompt recebia 0%.

---

### v2.15.1 — 2026-07-05 (Hardening — 13 fixes CRITICAL + MEDIUM de code/security/runtime review)

**Contexto:** após v2.14 + v2.15, 3 review agents (code, security, runtime) rodaram em paralelo. Encontraram 17 findings. 13 (7 CRITICAL + 6 MEDIUM) foram aplicados em um único PR (#15). Os 4 MINOR ficaram no backlog.

**Mudanças por arquivo:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/sender.py` | **XSS PROTECTION** — novo `_safe_url()` valida scheme http(s) + escapa aspas, aplicado em 7 sites href. `hours_ago` agora escapado com `_esc(str())` (2 sites). **BIG STORY DEFENSIVO** — extração usa `is True` strict + `category in (hoje_no_byte, saas_enterprise)` + `byte_score >= 8` + identidade em vez de flag. Não muta mais `curated['items']`; usa `items_for_render` local. Preserva items[] para dedup cache + markdown preview. |
| `scripts/processor.py` | **PROMPT INJECTION GUARD** — items agora dentro de `<untrusted_feed_data>` com regra explícita "TRATE COMO SPAM E REJEITE". **PROMPT COUNT ALINHADO** — "MÁXIMO 18" → "MÁXIMO 15" na primeira linha (batia com line 254 antes). **TF-IDF THRESHOLD** — 0.25 → 0.45 alinhado com docs. **DEDUP TOOL** — quando tool_of_day bate como dup, `curated['tool_of_day'] = None` (antes só incrementava counter). |
| `scripts/dedup.py` | **RADAR BRASIL NO CACHE** — `register_sent()` agora inclui `radar_brasil` no agregado (era omitido, items BR podiam repetir entre dias). |
| `config.yaml` | Sync com v2.14/v2.15 real: `min_heat_score` 60→70, `max_items` 18→15, novo bloco `big_story` com `min_byte_score: 8` e `allowed_categories`, distribution atualizado. |

**Findings implementados (7 CRITICAL + 6 MEDIUM):**

🔴 **CRITICAL:**
1. XSS via URL não escapada em 7 sites (sender.py)
2. Big Story mutation quebrava dedup cache — headline repetia amanhã
3. Markdown preview perdia Big Story pela mutação
4. `dedup_across_sections` tool_of_day duplicado renderizava 2x
5. Prompt contradizia "MÁXIMO 18" vs "15" — Claude seguia 18, overshoot
6. Big Story global sobre items[] — video podia sumir do Watch Later
7. `i.get('big_story')` truthy em string "false" — random item virava Big Story

🟡 **MEDIUM:**
8. Prompt injection via feed content sem defesa
9. `hours_ago` não escapado (2º vetor XSS)
10. Múltiplos big_story:true silenciosamente descartados
11. TF-IDF threshold 0.25 (código) vs 0.45 (docs) — false positives
12. `register_sent` omitia radar_brasil — items BR podiam repetir
13. config.yaml stale

🟢 **MINOR (backlog):**
- SSRF via `allow_redirects=True` (baixo risco, feeds hardcoded)
- Retry usa assistant-in-middle (funciona no 4.6 mas frágil)
- `if number and number.get('value')` trata 0 como falsy
- Dead code em `_titles_overlap`

**Testes locais:**
- Sintaxe válida (ast.parse) para sender/processor/dedup/collector
- `_safe_url()` passa em 8 attack vectors (javascript:, data:, vbscript:, quote breakout, None, empty)
- Big Story não muta curated
- Big Story valida category (rejeita watch_later)

**PR:** #15 (squash merged em `a895ee0`)

---

### v2.15 — 2026-07-05 (+3 fontes de alta qualidade)

**Mudanças:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | +3 fontes em SUBSTACK_FEEDS e RSS_FEEDS: `sub_not_boring` (Packy McCormick), `sub_astral_codex_ten` (Scott Alexander), `the_shift_br` (Cristina De Luca + Silvia Bassi). |

**Fontes adicionadas (validadas com rigor: RSS testado + frequência confirmada + ângulo único):**
- **Not Boring** (Packy McCormick) — https://www.notboring.co/feed — semanal, 271k subs, tech strategy essays otimista, respeitado em círculo exec
- **Astral Codex Ten** (Scott Alexander) — https://www.astralcodexten.com/feed — 1-2/semana, AI/policy rigoroso, angle rationalist
- **The Shift** (Cristina De Luca + Silvia Bassi) — https://theshift.info/feed/ — diária Seg-Sex, tech/inovação PT-BR, reforça Radar Brasil

**Fontes pesquisadas e REJEITADAS após análise:**
- **SVPG** (Marty Cagan) — RSS 403 Cloudflare + baixa freq (~1-2/mês)
- **The News (Waffle)** — mainstream generalista com celebridades, não fit C-level tech
- **Digg** — sem RSS, redundante com HN
- **Prompt Engineering Daily** — inativa (posta ~1x/ano apesar do nome)

**Total de feeds ativos:** ~205 (de ~200 em v2.14)

**PR:** #14 (squash merged em `16836db`)

---

### v2.14 — 2026-07-05 (Big Story + Corte 15 + Heat 70 + Verbo Imperativo + LED VU + AI News/Karpathy)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | +2 fontes de alta qualidade: AI News (swyx, daily buttondown, recomendado por Karpathy) + Andrej Karpathy Substack (baixa freq, alto impacto). |
| `scripts/processor.py` | **BIG STORY** — CURATOR_SYSTEM/USER_TEMPLATE ganham campo `big_story: true` em UM único item de items[] (maior byte_score da edição, mínimo 8). **CORTE** — total máximo 18→15 (10 principais + 5 quick links). **HEAT THRESHOLD** — mínimo sobe 60→70. **VERBO IMPERATIVO** — nova regra: cada why_it_matters começa com verbo (Renegocie/Ignore/Priorize/Teste/Antecipe/Investigue/etc.). **BYTE SCORE INTEIRO** — schema mudou de float (7.5) para int (7-8). Exemplos-âncora ajustados. |
| `scripts/sender.py` | **BIG STORY renderer** — `_render_big_story_html()` renderiza card destacado no topo (borda laranja brand, badge "★ BIG STORY", botão CTA). Extração via `next(i for i in items if i.get('big_story'))`, item removido de items[] para não duplicar. **READING TIME dinâmico** — `_estimate_reading_time()` calcula min baseado em palavras totais (220 wpm, min 2). Substitui "3 min" fixo. **LED VU meter** — `_byte_led_html/_md` renderiza 10 barras verticais crescendo em altura (3-12px), gradient verde→amarelo→laranja, número inteiro ao lado. LED inline após source/hours (mesma linha, `vertical-align:2px` para nivelar piso). **LEGEND removida** (100% minimalista, sem GIGA/MEGA/KILO/byte no email). |
| `CLAUDE.md`, `config.yaml`, `EVOLUTION-PLAN.md` | Bump v2.14 + changelog. |

**Fluxo do usuário aprovando:**
- PR#1 (fontes + reading time + verbo) → PR#2 (Big Story + corte + threshold + LED refinements)
- Iterações no LED: badge grande → barra células uniformes → VU meter alto → reduzido → inline → nivelado piso

---

### v2.13 — 2026-06-22 (Byte Score — Classificador de Impacto)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/processor.py` | Bloco "BYTE SCORE" no `CURATOR_SYSTEM`: conceito, faixas, regra anti-inflação, exemplos-âncora few-shot (2 por tier). Schema JSON: campo `byte_score` (float 0.0–10.0) em todos os itens em escopo. `heat_score` permanece no schema para seleção interna. |
| `scripts/sender.py` | Nova função `_byte_tier(score)` → (tier, emoji, bg, fg). Badge renderizado (número + emoji + palavra) em todos os itens noticiosos (HTML + markdown), incluindo quick_links. Legenda no rodapé (uma linha com a escala). `_heat_bar` e `heat_emoji` removidos da renderização. |
| `config.yaml` | Header v2.13. Comentário detalhado no bloco de filtros de curadoria documentando faixas, cores e escopo do Byte Score. |
| `SKILL.md` | Nova subseção "Byte Score — Classificador de Impacto Estratégico": tabela de faixas (score/tier/emoji/significado), tabela de cores (fundo/texto), regras de escopo, explicação do fluxo curador→código, nota de calibração anti-inflação. Layout do email atualizado com badges de exemplo. Versão bumpeada para v2.13. |
| `CLAUDE.md` | "Versao atual" bumpeada para v2.13. Regra 33 adicionada documentando: número 0-10 do curador, derivação tier/emoji/cor em `sender.py` via `_byte_tier`, heat_score 100% interno, escopo de exibição, calibração anti-inflação. |

**Feature: Byte Score**

O Byte Score é o classificador de impacto estratégico proprietário do Daily Byte — responde à pergunta que C-levels realmente fazem: *quão grande é o tremor estratégico desta notícia?*

Distinção fundamental:
- **Heat Score**: critério de seleção interno (0-100, corte 60). Mede freshness + fonte + impacto para decidir *se a notícia entra*. Continua calculado, nunca exibido ao leitor.
- **Byte Score**: exibido ao leitor (0.0-10.0). Mede a *magnitude do impacto estratégico* da notícia publicada. Juízo do curador, calibrado por regra anti-inflação + few-shot.

A derivação tier/emoji/cor é sempre feita no código (`sender.py`), nunca enviada pelo Claude — garante consistência entre número e rótulo.

Backlog relacionado marcado como parcialmente coberto:
- "Classificação automática de ineditismo / score visível" → Byte Score resolve a face de visibilidade do score (o leitor vê o impacto); a face programática de ineditismo (`_cluster_size`) já existia desde v2.9.

---

### v2.11 — 04/06/2026 (Novas Fontes + Priority Themes)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/collector.py` | +3 fontes: Neatprompts (Substack RSS, AI tools/prompts EN), IA Brasil Notícias (RSS, ecossistema AI brasileiro PT-BR), Nate Herk (YouTube, AI prático/negócios). |
| `config.yaml` | v2.11. +4 priority themes: "A2A protocol", "coding agents", "Marco Legal da IA", "AI unicorn". |
| `CLAUDE.md` | v2.11. Fontes atualizadas. |
| `EVOLUTION-PLAN.md` | v2.11 changelog. |

**Novas fontes:**
- **Neatprompts** (Substack): AI tools, prompts e produtividade — ângulo prático que complementa AlphaSignal (research) e There's An AI For That (catálogo)
- **IA Brasil Notícias** (RSS): Cobertura dedicada ao ecossistema AI brasileiro — reforça Radar Brasil com fonte nativa
- **Nate Herk** (YouTube): AI para negócios e produtividade — complementa Fireship (dev) e Matt Wolfe (ferramentas)

**Priority themes atualizados:**
- A2A protocol (Google Agent-to-Agent, 150+ orgs)
- Coding agents (Codex, Jules, Claude Code — mercado em explosão)
- Marco Legal da IA (PL 2338/2023, regulação brasileira em votação)
- AI unicorn (Enter como 1º unicórnio AI da LATAM, $1.2B)

---

### v2.10 — 01/05/2026 (Health Check + Radar Brasil + Deep Dive + Trending Velocity + Fallback Cache + TF-IDF Dedup)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/health_check.py` | **NOVO.** Monitora ~200 feeds com ThreadPoolExecutor(15 workers). Timeout 10s, browser UA + feedparser fallback. Rastreia falhas consecutivas em `/tmp/digest_feed_health.json`. Alerta em 3+ falhas. |
| `scripts/processor.py` | Radar Brasil no CURATOR_SYSTEM (seção 3b) + CURATOR_USER_TEMPLATE (campo `radar_brasil[]`). Deep Dive semanal (sextas): campo `deep_dive` com {title, body}. Trending velocity: calcula `trending_score` (likes/retweets + recência) e injeta no prompt. TF-IDF dedup: `_tfidf_similarity()` com cosine similarity stdlib-only, threshold 0.45, integrado em `_titles_overlap()` como 3º check. `radar_brasil` no `dedup_across_sections()` (step 2.5). Console summary mostra Radar Brasil. |
| `scripts/sender.py` | Radar Brasil: HTML (bandeira BR + cor verde #16a34a) + markdown. Deep Dive: HTML (microscópio + azul escuro #1e40af) + markdown. Cores adicionadas ao COLORS dict. |
| `scripts/run.py` | Fallback cache: se coleta falhar e `/tmp/digest_raw.json` tem <48h, continua com dados antigos. Log de warning com idade do cache. |
| `.github/workflows/daily-digest.yml` | Health check step (continue-on-error). Raw data cache: restore antes da coleta + save após coleta (actions/cache@v4). `digest_feed_health.json` nos artifacts. |
| `config.yaml` | v2.10. |
| `CLAUDE.md` | v2.10. Regras 27-32 (health check, Radar Brasil, Deep Dive, trending velocity, fallback cache, TF-IDF dedup). Dedup 5→6 camadas. Layout atualizado com seções 3b e 5b. |

**Novas funcionalidades:**
- **Health Check**: monitoramento proativo de ~200 feeds antes da coleta
- **Radar Brasil**: seção dedicada ao ecossistema brasileiro (1-2 itens diários)
- **Deep Dive**: análise profunda semanal (sextas) — 3-5 parágrafos conectando pontos da semana
- **Trending Velocity**: bonus no heat score baseado em engagement (likes/retweets) + recência
- **Fallback Cache**: resiliência — se coleta falha, reutiliza dados anteriores (<48h)
- **TF-IDF Dedup**: similaridade semântica leve (stdlib-only) como 6ª camada de dedup

---

### v2.9 — 01/05/2026 (Dedup 5 Camadas + Pré-Clustering + Ineditismo + Fontes Alternativas)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/processor.py` | Dedup intra-edição reescrito com entity extraction + keyword overlap (60%+ match) em vez de primeiras 5 palavras. Novas funções: `_extract_entities()`, `_title_keywords()`, `_titles_overlap()`, `_cluster_and_pick_best()`, `_cap_per_source()`. Stopwords PT+EN. Pré-clustering agrupa itens sobre o mesmo assunto e mantém melhor representante (`_cluster_size`). Cap 5 itens/fonte. Prompt reforçado: regras 6 (INEDITISMO OBRIGATÓRIO, 30% mínimo) e 7 (DIVERSIDADE TEMÁTICA, max 2/tema). Hierarquia de fontes no prompt (primária > indie > community > newsletter > mídia > mainstream). Heat score com bonus ineditismo (+15/+10) e penalidade mainstream (-10). Regra anti-repetição expandida com teste final por empresa/evento. |
| `scripts/dedup.py` | Title hash cross-edição implementado (prometido v2.6, nunca ativado). `_title_hash()` normaliza títulos: remove stopwords PT+EN, ordena 8 keywords. `load_title_cache()` / `save_title_cache()` para persistência. `dedup_items()` agora filtra por URL + title hash. `register_sent()` consolidado: salva URLs + title hashes de todas as seções. |
| `scripts/collector.py` | +45 fontes alternativas: 7 labs primários (DeepMind, Meta AI, NVIDIA, MS Research, Stability, Mistral, Cohere), 5 community (Reddit ML, LocalLLaMA, HN Show 50+pts, Lobsters AI, Product Hunt), 2 developer (Changelog, InfoQ), 10 Substacks indie (Simon Willison, Lilian Weng, Chip Huyen, SemiAnalysis, Stratechery, etc.), 7 Brasil (NeoFeed, Startse, Exame, Pipeline Valor, Brazil Journal, Tecmundo, Canaltech), 14 X handles indie/builders (@simonw, @chipro, @levelsio, @GergelyOrosz, @filipedeschamps, etc.). |
| `.github/workflows/daily-digest.yml` | Cron adiantado 09:45→09:00 UTC (06:00 BRT). Cache inclui `digest_sent_titles.json`. Artifacts atualizados. |
| `config.yaml` | v2.9. Fontes: ~200 ativas. |
| `CLAUDE.md` | v2.9. Filosofia de fontes. Heat score com ineditismo. Dedup 5 camadas. Regras 25 (pré-clustering) e 26 (ineditismo 30%). |

**Dedup em 5 camadas:**
1. Cross-edição por URL (existia)
2. Cross-edição por title hash (novo — normaliza, remove stopwords, ordena keywords)
3. Pré-clustering (novo — agrupa itens sobre mesmo assunto, mantém melhor representante)
4. Cap por fonte (novo — max 5 itens/fonte para forçar diversidade)
5. Intra-edição semântica (melhorado — entity extraction + keyword overlap 60%)

**Fontes ~153 → ~200 (+45):**
- Filosofia: fonte primária > indie/builder > community > newsletter > mídia > mainstream
- Labs primários: decisões técnicas em primeira mão
- Community: o que practitioners discutem ANTES da mídia cobrir
- Indie voices: análise original com ponto de vista único
- Brasil expandido: cobertura tech/negócios BR de 4→11 fontes

---

### v2.8 — 17/04/2026 (Resiliência + Dedup Forte + Idioma + Alertas Privados)

**Mudanças implementadas:**

| Arquivo | O que mudou |
|---------|------------|
| `scripts/processor.py` | Modelo atualizado para `claude-sonnet-4-6`. Removido assistant prefill (não suportado pelo 4.6) — agora usa instrução explícita "Responda APENAS com JSON". Injeção de `recent_hooks` no prompt para evitar título repetido entre edições. Regra de idioma PT-BR 100% reforçada em 4 pontos do prompt (incl. lista de palavras em inglês proibidas: Expect→Espere, Open→Abra etc). Regra crítica de ortografia: proibido inventar palavras (ex: "céfico" não existe, é "cético"). Regra anti-duplicação entre seções com exemplo real. **Nova função `dedup_across_sections()`**: rede de segurança programática que remove duplicatas por URL normalizada OU assinatura de título (primeiras 5 palavras > 3 letras) entre `items`/`world`/`tool_of_day`/`quick_links`. |
| `scripts/collector.py` | X bearer token com `.strip()` para remover whitespace/EOF. User-Agent Chrome (macOS) substituindo UA bot que era bloqueado por Substacks. Fetch invertido: `requests` com headers de browser primeiro, `feedparser` como fallback. Safe fallback para variável unbound. |
| `scripts/newsletter_collector.py` | Mesma inversão de fetch (browser UA first, feedparser fallback). Safe fallback. |
| `scripts/dedup.py` | Ativado dedup por hash de título (cruza edições): previne mesma notícia de fontes diferentes. Novo store `digest_sent_hooks.json` com histórico de `subject_hook` dos últimos 7 dias. Funções: `_register_hook()`, `load_hooks()`, `save_hooks()`, `get_recent_hooks(days=3)`. |
| `scripts/alert_failure.py` | **Reescrito**: antes enviava email para toda lista via Buttondown broadcast — agora cria GitHub Issue via `gh` CLI (owner recebe só por email do GitHub). Aceita `--failed-step` para mostrar qual step quebrou. |
| `.github/workflows/daily-digest.yml` | Step IDs (`collect`, `curate`, `send`) + detecção do step que falhou via `steps.*.outcome`. `notify-failure` agora usa `permissions: issues: write` + `GH_TOKEN`. Cache path inclui `/tmp/digest_sent_hooks.json`. |
| `config.yaml` | Modelo: `claude-sonnet-4-6`. |
| `CLAUDE.md` | v2.8 + modelo atualizado. |
| `EVOLUTION-PLAN.md` | v2.8 changelog. |

**Problemas resolvidos:**
- Pipeline falhando silenciosamente: modelo deprecado (`claude-sonnet-4-5-20250929`) e prefill do assistant incompatível com `claude-sonnet-4-6`
- Alerta de falha indo para todos os subscribers: agora só o owner é notificado (GitHub Issue)
- X/Twitter retornando 0 items: bearer token com whitespace no final
- Substacks retornando 0 items: User-Agent bot bloqueado, trocado para Chrome UA
- Detecção genérica de falha: agora o alerta diz exatamente qual step quebrou (collector/processor/sender)
- **Título repetido entre edições** (dedup fraco): ativado hash de título + hooks recentes injetados no prompt
- **Inglês misturado em PT-BR** ("Expect" no how_to_use): regras reforçadas em 4 pontos do prompt com exemplos de palavras proibidas
- **Palavras inventadas** ("céfico" em vez de "cético"): regra crítica de ortografia + lista de palavras comuns
- **Mesma notícia em 2 seções** (Manus em `world` E `hoje_no_byte`): prompt anti-dup + nova função `dedup_across_sections()` como rede de segurança programática

**Dedup em 3 camadas (anti-repetição):**
1. **Cross-edition por URL** (já existia) — `dedup.py` filtra URLs já enviadas nos últimos 5 dias
2. **Cross-edition por título** (NOVO) — hash MD5 do título normalizado evita mesma notícia de fontes diferentes
3. **Intra-edition por URL + assinatura** (NOVO) — `dedup_across_sections()` remove duplicatas entre `items`/`world`/`tool_of_day`/`quick_links` dentro da mesma edição

**Alertas Privados (owner-only):**
- Antes: `alert_failure.py` enviava broadcast via Buttondown quando pipeline falhava → todos os subscribers recebiam email de falha
- Agora: cria GitHub Issue com label `pipeline-failure` → owner recebe notificação por email do GitHub (configurado em github.com/settings/notifications)
- Label `pipeline-failure` precisa existir no repo (criar em Issues → Labels)

---

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
- Deploy: GitHub Actions (diario 06:00 BRT)
- Heat Score: Freshness (40pts) + Fonte (30pts) + Impacto (30pts), threshold 60

---

## Proximas Evolucoes (Backlog)

### 🗓️ Próximo ciclo — aberto na v2.17 (28/08/2026)

**A. Confirmar no runner o que só foi validado do sandbox** — *olhar no primeiro run.*
- [ ] **API de arquivo do Substack.** Funcionou daqui em Doomberg, Zvi, Capital Wars e Import AI. Se no runner voltar a dar 0 itens, o fallback para `/feed` segura (não quebra), mas o ganho não aconteceu. Sinal no log: `📝 Coletando Substacks` deve subir bem acima dos 13 itens de 27/08.
- [ ] **GitHub releases (6 repos).** Não consegui testar — o sandbox bloqueia github.com. Se derem 0 itens, remover as 6 linhas de `RSS_FEEDS`.

**B. Medir o efeito da recalibração do Heat Score** — *não mexer de novo antes de ter dados.*
- [ ] A régua nova (freshness 25, ineditismo +25) foi calculada, não observada. Acompanhar por ~1 semana quantos itens do Hoje no Byte vêm de fonte primária/indie contra mídia. Baseline de 28/08: **4 de 5 eram mídia**.
- [ ] Se continuar mainstream mesmo com o pool cheio de primárias, o problema não é a régua — é o prompt não amarrar ineditismo na montagem das seções.

**C. IMAP para newsletters que bloqueiam scraping** — aprovado em conceito, adiado por exigir passo manual.
- [ ] Caso concreto: **There's An AI For That** (2,8M assinantes) não tem RSS — é beehiiv com feed desativado, e responde 403 a qualquer cliente automatizado.
- [ ] Desenho: conta dedicada (Fastmail ~US$5/mês é mais confiável que Gmail para uso não-supervisionado), assinar as newsletters com ela, ler por IMAP no pipeline.
- [ ] Destrava uma classe inteira: **qualquer** newsletter que bloqueie bot mas entregue email.
- [ ] Passo manual do Totó: criar a conta e assinar. Por isso ficou fora da v2.17.

**D. Fontes que seguem quebradas ou limitadas**
- [ ] **X/Twitter** — token revogado, coleta falhando. Bluesky cobre só 3 handles (Simon Willison, Ethan Mollick, David Ha); os outros não migraram de fato. Decidir: renovar o token ou aposentar o X.
- [ ] **Distrito** — URL corrigida, mas cadência é **mensal**. Feed vazio ~29 dias em 30 é esperado, não falha.
- [ ] **Health check** — agora abre issue na virada do limiar. Conferir que os 16 feeds antigos saem da lista de quebrados quando a API de arquivo pegar.

### 🗓️ Próximo ciclo — aberto na v2.16b (20/07/2026)

**A. Medir mainstream ao longo de vários dias** — *antes de mexer no prompt de novo.*
- [ ] A única rodada pós-expansão deu **41%** contra baseline de 58%. É `n=1`, e a variância observada entre rodadas do mesmo dia chegou a **13 pontos** — não dá para chamar de resolvido.
- [ ] Se confirmar >50% em vários dias, aí sim o prompt precisa pesar ineditismo na montagem das seções (hoje o `_cluster_size` chega ao curador mas não amarra nada).

**B. Validar os 16 handles do X contra a API** — o token voltou, a lista nunca foi conferida.
- [ ] Um handle devolveu HTTP 400 na validação. O log da v2.16 só nomeava 404/401/403/429, então o agregado não disse qual — corrigido em PR #19, que faz qualquer status nomear o handle.
- [ ] Rodar `collector.py` e conferir o log por `handle inexistente`. Remover os que não resolverem.

**C. Versão em áudio (TTS)** — aprovada pelo Totó na revisão de 20/07, **ainda não implementada**.
- [ ] Escopo acordado: **Big Story + Análise do Dia** (não o digest inteiro — ~1 min de áudio, não 8).
- [ ] Decisões em aberto: engine de TTS (ElevenLabs? OpenAI? Google?), onde hospedar o arquivo, e se entra como **link no email** ou player embarcado (a maioria dos clientes de email bloqueia `<audio>` — link é o caminho realista).
- [ ] Diferencial competitivo: nenhum dos 8 concorrentes benchmarkados oferece áudio.

### 🗓️ Backlog anterior

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

### ✅ Implementado em v2.9 (01/05/2026)

**Dedup 5 Camadas:** ✅
- [x] Cross-edição por title hash (prometido v2.6, implementado agora)
- [x] Pré-clustering de itens sobre mesmo assunto
- [x] Cap por fonte (max 5/fonte)
- [x] Intra-edição com entity extraction + keyword overlap 60%
- [x] Dedup semântico (substitui primeiras 5 palavras)

**Fontes Alternativas (ineditismo):** ✅
- [x] 7 blogs primários de AI labs (DeepMind, Meta AI, NVIDIA, etc.)
- [x] 5 community-driven (Reddit ML, LocalLLaMA, HN Show, Lobsters, Product Hunt)
- [x] 10 Substacks indie (Simon Willison, Lilian Weng, Chip Huyen, SemiAnalysis, Stratechery, etc.)
- [x] 7 fontes Brasil (NeoFeed, Startse, Exame, Pipeline Valor, Brazil Journal, Tecmundo, Canaltech)
- [x] 14 X handles indie/builders
- [x] StartSe — adicionado v2.9
- [x] Stratechery — adicionado v2.9 via RSS

**Prompt Ineditismo:** ✅
- [x] Hierarquia de fontes (primária > indie > community > newsletter > mídia > mainstream)
- [x] Ineditismo mínimo 30% (4+ de 12 itens de fontes exclusivas)
- [x] Heat score com bonus ineditismo e penalidade mainstream

---

### Backlog Geral

**Fontes:**
- [x] StartSe — adicionado v2.9
- [x] Filipe Deschamps (YouTube BR) — adicionado v2.2
- [x] Import AI (Jack Clark) — adicionado v2.2 via Substack RSS
- [x] Stratechery — adicionado v2.9 via RSS
- [x] Crunchbase News — adicionado v2.3 via RSS

**Formato:**
- [x] Secao de engagement — 1-click feedback + referral CTA (v2.6)
- [x] Secao "Deep Dive" semanal — implementado v2.10 (sextas)
- [x] "Radar Brasil" — implementado v2.10; passou a ser preenchido de fato na v2.16 (filtro de relevancia BR)
- [ ] **Versao audio (TTS)** — aprovado no ciclo de 2026-07-20, nao implementado.
      Escopo: resumo de ~2 min do Big Story + Analise do Dia, anexado ou linkado no email.
      Evidencia: The Neuron lancou podcast em 2026; beehiiv reporta ~22% de ganho de
      retencao em newsletters com formato cruzado. Decisoes em aberto: engine de TTS
      (custo por edicao), hospedagem do audio, e se entra como link ou player embutido.

**Do benchmark de 2026-07-20 (levantados, NAO priorizados):**
- [ ] Personalizacao por persona (CFO ve corte X, CTO ve corte Y no mesmo envio) —
      nenhum dos 6 concorrentes analisados faz isso; seria first-mover, nao catch-up.
- [ ] "Totó's Take" — coluna editorial assinada com lente board/capital.
- [ ] Case de ROI enterprise semanal — a fonte AI to ROI (adicionada na v2.16) ja alimenta isso.
- [ ] Quiz de onboarding → trilha personalizada (modelo Rundown University).

**Curadoria:**
- [x] Dedup mais inteligente — implementado v2.9 (entity extraction + keyword overlap + clustering)
- [x] Cache de items ja enviados para evitar repeticao entre dias — implementado v2.3
- [x] Feedback loop — rastrear opens/clicks para refinar selecao — implementado v2.4
- [~] Classificacao automatica de ineditismo — _cluster_size (v2.9) ja pontua internamente; Byte Score (v2.13) expoe o impacto visualmente ao leitor. Face programatica completa pendente.
- [ ] Score de "trending velocity" — itens que ganham engajamento rapido nas ultimas 2h valem mais

**Infra:**
- [x] Monitoring/alertas quando o pipeline falha — implementado v2.3 (GitHub Issue alert)
- [x] Retry automatico se um feed der timeout — implementado v2.5 (backoff exponencial)
- [ ] Dashboard com metricas (opens, clicks, growth)
- [ ] Health check de fontes — detectar feeds que nao retornam itens ha 3+ dias
- [ ] Fallback para cache do dia anterior se coleta falhar completamente
- [ ] Custom domain para click tracking — configurar dominio proprio no Buttondown para melhorar deliverability

**Custom Domain Tracking (instruções):**
Para configurar dominio proprio no Buttondown:
1. Escolher subdominio: ex. `byte.nuvini.ai` ou `news.nuvini.ai`
2. No Buttondown Settings > Custom domain > Adicionar dominio
3. Configurar DNS no registrador:
   - CNAME `byte.nuvini.ai` → `buttondown-proxy.fly.dev`
   - TXT record para verificacao SPF/DKIM (Buttondown fornece)
4. Aguardar propagacao DNS (24-48h)
5. Testar deliverability com mail-tester.com
Beneficio: links no email apontam para `byte.nuvini.ai` em vez de `buttondown.com`, melhor reputacao de dominio e open rates.
