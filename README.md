# Daily Byte — Newsletter Automatizada de IA e Tecnologia

> Curadoria diária de notícias de IA e tecnologia gerada por inteligência artificial.

## Sobre

Daily Byte é um sistema completamente automatizado que coleta, cura e distribui uma newsletter diária sobre inteligência artificial e tecnologia para C-levels brasileiros (CEOs, CFOs, CMOs, CPOs). O sistema roda via GitHub Actions, integrando fontes de múltiplos canais (RSS, redes sociais, newsletters especializadas, YouTube) e aplicando curadoria inteligente com Claude para selecionar apenas o conteúdo mais relevante e acionável.

A arquitetura usa Python para coleta paralela, prompts especializados para curadoria editorial, e Buttondown como plataforma de distribuição. Versão 2.11 introduz workflow especial para sextas-feiras, enquetes de engajamento e dedup avançado em 6 camadas.

## Stack

- **Python 3.14** — scripts de coleta, processamento e curadoria
- **GitHub Actions** — CI/CD para agendamento e execução diária
- **Claude API** — curadoria inteligente e geração de conteúdo
- **Buttondown** — plataforma de newsletter e analytics
- **YAML/JSON** — configuração de fontes, filtros e parâmetros

## Funcionalidades Principais

- Coleta paralela de 154 feeds de múltiplas fontes (RSS, X/Twitter, YouTube, newsletters)
- Curadoria inteligente com Claude Sonnet 4.6 usando heat score (relevância + recência + fonte)
- Dedup em 6 camadas: URL (5 dias), hash de título, clustering semântico, cap por fonte, intra-edition, TF-IDF cosine
- Layout editorial de 6 seções: Numero do Dia, Mundo Real, Hoje no Byte, SaaS & Enterprise, Radar Brasil, Tool do Dia
- Deep Dive semanal (sextas) — análise profunda 3-5 parágrafos sobre tema mais quente
- Enquete de engajamento (sextas) com 4 opções de feedback
- Health check de feeds (detecção de fontes falhando)
- Suporte a preview (markdown + HTML em /tmp/) antes de envio real

## Estrutura

```
daily-tech-digest/
├── scripts/
│   ├── collector.py              # Coleta paralela (ThreadPoolExecutor, 10 workers)
│   ├── processor.py              # Curadoria com Claude (pre-clustering, heat score)
│   ├── sender.py                 # Renderização HTML e envio via Buttondown
│   ├── feedback.py               # Extração de métricas Buttondown (opens, clicks, hooks)
│   ├── dedup.py                  # Cache 5-dias + dedup URL/título/semântico
│   ├── health_check.py           # Monitor de saúde de feeds (154 fontes)
│   ├── alert_failure.py          # Cria GitHub Issue em caso de falha
│   └── run.py                    # Orquestrador (pipeline completo)
├── config.yaml                   # Configuração central (modelo, distribuição, fontes)
├── prompts/
│   └── curator.md                # Documentação do prompt de curadoria
├── .github/
│   └── workflows/
│       └── daily-byte.yml        # Workflow do digest (disparo VPS 06:41 BRT · fallback 07:40)
├── SKILL.md                      # Filosofia, critérios de curadoria, layout
├── EVOLUTION-PLAN.md             # Histórico de versões e backlog
└── .env                          # Chaves (ANTHROPIC_API_KEY, BUTTONDOWN_API_KEY, X_BEARER_TOKEN)
```

## Como Funciona

1. **Coleta** (06:41 BRT) — `collector.py` busca conteúdo de 154 fontes em paralelo, normaliza URLs, remove duplicatas crudas
2. **Feedback** (02:00 BRT) — `feedback.py` extrai métricas da última newsletter (opens, clicks, subject hooks) via Buttondown API
3. **Curadoria** (02:30 BRT) — `processor.py` aplica heat score (relevância 30pts + recência 40pts + fonte 30pts), pré-agrupa por tema, envia melhor representante de cada cluster ao Claude
4. **Renderização** (~06:45 BRT) — `sender.py` converte JSON curado para HTML (table-based, inline CSS) e envia via Buttondown
5. **Distribuição** (~06:45 BRT) — Buttondown entrega email, adiciona unsubscribe automático, tracked links

**Agendamento:** o gatilho é um cron na VPS (KVM2, UTC) às **09:41 UTC / 06:41 BRT**, que chama `workflow_dispatch` na API do GitHub. Dispatch entra em 0s, o pipeline leva ~3,5 min → email às **06:45 BRT**, com desvio de segundos.

O `schedule` do próprio GitHub ficou às 10:40 UTC (07:40 BRT) **apenas como rede de segurança**: a fila dele é best-effort e chegou a atrasar 8h e 11h em 2 de 12 runs medidos. Quando esse fallback dispara, o `sender.py` roda com `--skip-if-sent-today` e pergunta ao Buttondown se a edição de hoje já saiu — se sim, encerra sem enviar. Falha na VPS atrasa a entrega em 1h; nunca perde a edição nem duplica email.

## Fontes (154 feeds)

### Tier 1 — Primeira Mão (65+ X/Twitter)
Fundadores e labs (Sam Altman, Anthropic, Sundar Pichai, LeCun, Demis Hassabis, Karpathy), builders indie (Simonw, Chipro, Gergelý Orosz, Levelsio), investidores e estrategistas.

### Tier 2 — RSS Feeds (45+ tech/AI + 37 world)
**Labs:** DeepMind, Meta AI, NVIDIA, Microsoft Research, OpenAI, Anthropic, HuggingFace.
**Community:** Reddit r/MachineLearning, r/LocalLLaMA, HackerNews, Lobsters.
**Tech media:** HN, TechCrunch AI, MIT Tech Review, The Decoder, Changelog.
**Mundo:** Reuters, BBC, Forbes, CNBC, WSJ.
**Brasil:** Poder360, InfoMoney, Startups.com.br, Valor Econômico, Tecmundo, NeoFeed, Startse.

### Tier 3 — Newsletters (10+ fontes)
AiDrop, Evolving AI, Update Diário, TechDrop, AlphaSignal, There's An AI For That, Turing Post, Import AI, Distrito News, The BRIEF, e 42 Substacks curados (Lilian Weng, Chip Huyen, Ethan Mollick, Latent Space, Pragmatic Engineer, etc.).

## Critérios de Curadoria

**Heat Score (máximo 100 pontos):**
- Freshness (25): <6h=25, 6-12h=20, 12-24h=12, 24-36h=6, >36h=0   [v2.17: era 40]
- Fonte (30): Fundador/blog oficial=30, Jornalista=25, Release=20, Newsletter=15
- Impacto (30): Lançamento=30, M&A=25, Drama=20, Incremental=5
- Bônus: Ineditismo (+25 primária / +18 community / +18 indie), Engagement alto (+10), Cross-validação (+5)   [v2.17: ineditismo era +15/+10/+10]

**Regras críticas:**
- Mínimo 60 pontos para entrar
- 30% dos itens de fontes primárias (ineditismo obrigatório)
- Máximo 18 itens por edição (12 principais + 6 quick links)
- Sem repetição de temas em hooks semanais
- 100% português brasileiro (headlines, análises, how-to)

## Como Rodar Localmente

### Setup inicial

```bash
cd ~/daily-tech-digest
python3 -m venv venv
source venv/bin/activate
pip install anthropic feedparser beautifulsoup4 lxml requests pyyaml python-dotenv
```

### Criar .env

```bash
ANTHROPIC_API_KEY=sk-ant-...
BUTTONDOWN_API_KEY=...
X_BEARER_TOKEN=...
```

### Executar

```bash
source venv/bin/activate
source .env

cd scripts

# Preview (salva em /tmp/ sem enviar)
python run.py --preview

# Pipeline completo (envia de verdade)
python run.py

# Flags úteis
python run.py --skip-collect   # reutiliza /tmp/digest_raw.json
python run.py --skip-process   # reutiliza /tmp/digest_curated.json
```

## Troubleshooting

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError` | `source venv/bin/activate && pip install -r requirements.txt` |
| `ANTHROPIC_API_KEY not set` | `source .env` antes de rodar scripts |
| `Couldn't find tree builder: lxml` | `pip install lxml` |
| `GH013: Push cannot contain secrets` | Certifique que `.env` está em `.gitignore` |

## Roadmap

- v2.12 — Integração com X API v2 nativa (RSS deprecado)
- v3.0 — Dashboard de analytics com Vercel Analytics + PostHog
- v3.1 — Agendamento flexível (horários diferentes por pessoa)

## Status

🟢 Ativo

---

> Repositório privado — uso interno
